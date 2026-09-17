"""4a's population: k diverse honest solutions per task (FORK_PLAN §5).

Two things this must get right, both from review.

DIVERSITY IS PRODUCED, NOT ASSUMED. Ask one model for twenty solutions and you get twenty
near-identical ones, and `honest_pass` over a homogeneous population measures almost nothing. So
generation varies BOTH the model and an explicit idiom directive, and `diversity()` reports how
structurally distinct the result actually was. That number is published beside honest_pass; if it
is low, honest_pass is not trustworthy.

SPENDING IS DELIBERATE. `estimate()` prices a run before a single token is bought, and nothing
calls the API until `confirm=True`. Every solution is appended to a JSONL checkpoint as it
arrives, so a spend cap hitting mid-sweep costs the remainder of the run, not the run.
"""

from __future__ import annotations

import ast
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..substrate import Task
from .honest import Candidate

# TRACKED, not gitignored. The generated population is committed so §3.1 reproduces with no API
# calls at all — the numbers in the write-up are a property of this repository, not of a run
# someone would have to pay to repeat.
CHECKPOINT_DIR = Path("data/solutions")

# USD per million tokens. Cross-check against the pricing docs before quoting a number publicly.
MODEL_PRICES = {
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
}

# Spreading k across models is what makes the population diverse; it is also ~60% cheaper than
# generating everything on the largest model.
DEFAULT_MODELS = ("claude-sonnet-5", "claude-haiku-4-5", "claude-opus-5")

# `output_config.effort` is not universal — Haiku 4.5 rejects it with a 400. Send it only where
# it is supported rather than dropping it everywhere; on the models that take it, low effort is
# both correct for "write one short function" and cheaper.
_SUPPORTS_EFFORT = frozenset({"claude-opus-5", "claude-sonnet-5"})

# Idiom directives. Each asks for a DIFFERENT SHAPE of correct solution, never a different answer.
IDIOMS = (
    "Write it as straightforwardly as possible.",
    "Use an explicit loop with an accumulator; avoid comprehensions entirely.",
    "Use comprehensions and built-ins; avoid explicit loops where you can.",
    "Use recursion instead of iteration.",
    "Make a single pass over the input, even if that costs readability.",
    "Use helper functions liberally; several small functions instead of one body.",
    "Use only the standard library, and reach for itertools/functools where they fit.",
    "Write it defensively, handling degenerate inputs explicitly and early.",
    "Optimise for brevity; the shortest correct implementation you can write.",
    "Write it as a careful engineer would for review: named intermediates, no cleverness.",
)

_SYSTEM = (
    "You write correct Python solutions. Output ONLY the function body and any helpers, as a "
    "complete module that defines the requested function. No markdown fences, no explanation, "
    "no tests. Correctness comes first; the style directive shapes HOW you write it, never "
    "whether it is right."
)

_ESTIMATED_INPUT_TOKENS = 300  # prompt + docstring + directive
_ESTIMATED_OUTPUT_TOKENS = 200  # a short function


@dataclass(frozen=True)
class CostEstimate:
    calls: int
    per_model: dict[str, float]

    @property
    def total(self) -> float:
        return sum(self.per_model.values())

    def render(self) -> str:
        lines = [f"{self.calls} calls, estimated ${self.total:.2f}"]
        lines += [f"  {model:20} ${cost:.2f}" for model, cost in sorted(self.per_model.items())]
        lines.append("Estimates assume ~300 input / ~200 output tokens per call. Re-check after a")
        lines.append("pilot task: actual usage is reported by the API and may differ.")
        return "\n".join(lines)


def estimate(n_tasks: int, k: int, models: tuple[str, ...] = DEFAULT_MODELS) -> CostEstimate:
    """Price a sweep before spending anything. Unknown model ids raise rather than guess."""
    calls = n_tasks * k
    per_model: dict[str, float] = {}
    for i, model in enumerate(models):
        if model not in MODEL_PRICES:
            raise KeyError(f"no price on file for {model!r}; add it rather than guessing")
        share = calls // len(models) + (1 if i < calls % len(models) else 0)
        in_price, out_price = MODEL_PRICES[model]
        per_model[model] = (
            share * _ESTIMATED_INPUT_TOKENS / 1e6 * in_price
            + share * _ESTIMATED_OUTPUT_TOKENS / 1e6 * out_price
        )
    return CostEstimate(calls=calls, per_model=per_model)


# --- structural diversity ---------------------------------------------------------------------


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def fingerprint(source: str) -> str:
    """A hash of a solution's SHAPE: node types and nesting, with all names erased.

    Two solutions with the same fingerprint are the same algorithm written with different
    identifiers. Unparseable source fingerprints as itself, so it is never silently merged.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return "unparseable:" + hashlib.sha1(source.encode()).hexdigest()[:12]

    shape: list[str] = []

    def walk(node, depth):
        shape.append(f"{depth}:{type(node).__name__}")
        for child in ast.iter_child_nodes(node):
            walk(child, depth + 1)

    walk(tree, 0)
    return hashlib.sha1("|".join(shape).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class DiversityReport:
    total: int
    distinct: int
    largest_cluster: int

    @property
    def ratio(self) -> float | None:
        return self.distinct / self.total if self.total else None

    @property
    def population(self) -> str:
        return (
            f"structural_diversity = distinct shapes / generated = {self.distinct}/{self.total}; "
            f"largest identical cluster {self.largest_cluster}"
        )


def diversity(candidates: list[Candidate]) -> DiversityReport:
    """How structurally distinct the generated population actually is."""
    prints = [fingerprint(c.source) for c in candidates]
    counts = {p: prints.count(p) for p in set(prints)}
    return DiversityReport(
        total=len(prints),
        distinct=len(counts),
        largest_cluster=max(counts.values(), default=0),
    )


# --- generation -------------------------------------------------------------------------------


def _strip_fences(text: str) -> str:
    """Models add markdown fences despite being told not to. Remove them, keep everything else."""
    lines = [ln for ln in text.strip().splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines).strip() + "\n"


def _checkpoint_path(task_id: str, directory: Path | None = None) -> Path:
    directory = directory if directory is not None else CHECKPOINT_DIR
    return directory / f"{task_id.replace('/', '_')}.jsonl"


def load_checkpoint(task_id: str, directory: Path | None = None) -> list[Candidate]:
    """Solutions already generated for this task. Empty when the sweep has not run."""
    path = _checkpoint_path(task_id, directory)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [Candidate(label=r["label"], source=r["source"]) for r in rows]


def provenance(task_id: str, directory: Path | None = None) -> list[dict]:
    """Model, idiom, timestamp and token usage for each committed solution."""
    path = _checkpoint_path(task_id, directory)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [{k: v for k, v in r.items() if k != "source"} for r in rows]


def generate_solutions(
    task: Task,
    k: int = 20,
    *,
    client,
    confirm: bool = False,
    models: tuple[str, ...] = DEFAULT_MODELS,
    directory: Path | None = None,
    create: Callable | None = None,
) -> list[Candidate]:
    """Generate k diverse correct solutions for `task`, resuming from any checkpoint.

    Nothing is bought unless `confirm=True` — the default prints the estimate and returns what is
    already on disk. `create` is injected in tests; in production it is `client.messages.create`.
    """
    existing = load_checkpoint(task.task_id, directory)
    remaining = k - len(existing)
    if remaining <= 0:
        return existing[:k]

    if not confirm:
        print(estimate(1, remaining, models).render())
        print(f"{len(existing)}/{k} already on disk. Pass confirm=True to generate the rest.")
        return existing

    create = create if create is not None else client.messages.create
    path = _checkpoint_path(task.task_id, directory)
    path.parent.mkdir(parents=True, exist_ok=True)

    generated = list(existing)
    with path.open("a") as checkpoint:
        for i in range(len(existing), k):
            model = models[i % len(models)]
            idiom = IDIOMS[i % len(IDIOMS)]
            label = f"{model.split('-')[1]}_{i:02d}"
            request = {
                "model": model,
                "max_tokens": 1500,
                "system": _SYSTEM,
            }
            if model in _SUPPORTS_EFFORT:
                request["output_config"] = {"effort": "low"}  # one short function is not hard
            response = create(
                **request,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Implement this function.\n\n{task.prompt}\n\nStyle directive: {idiom}"
                        ),
                    }
                ],
            )
            text = "".join(b.text for b in response.content if b.type == "text")
            candidate = Candidate(label=label, source=_strip_fences(text))
            usage = getattr(response, "usage", None)
            # Provenance travels with every solution: which model wrote it, under which style
            # directive, when. There is no seed to record — the Anthropic API exposes no sampling
            # seed — so reproducibility comes from committing the solutions, not from replaying
            # the sampler. That limitation is stated in the write-up rather than implied away.
            record = {
                "label": label,
                "model": model,
                "idiom": idiom,
                "generated_at": _now(),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "source": candidate.source,
            }
            # Written before the next call, so a spend cap costs the remainder and not the run.
            checkpoint.write(json.dumps(record) + "\n")
            checkpoint.flush()
            generated.append(candidate)

    return generated
