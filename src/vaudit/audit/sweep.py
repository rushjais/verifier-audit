"""M1a's sweep: point every check at real EvalPlus graders and print the table (FORK_PLAN §5).

    python -m vaudit.audit.sweep --tasks 5            # prices the run, spends nothing
    python -m vaudit.audit.sweep --tasks 5 --confirm  # generates, then measures

The headline is NOT honest_pass on the stock grader. On unpatched EvalPlus the grader is the
base HumanEval suite and the oracle is the stricter extended suite, so anything the oracle
accepts the base grader accepts too and the rate is ~1.0 by construction. The number that means
something is the DELTA once the grader is hardened: what sealing cheats costs in legitimate work.

Generation is checkpointed, so re-running after a spend cap resumes instead of restarting. Every
measurement after generation is local and free.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..grader import Grader, run_oracle
from ..grader import grade as grade_solution
from ..substrate import load_hardest
from .determinism import measure_determinism
from .generate import DEFAULT_MODELS, diversity, estimate, generate_solutions
from .honest import Candidate, measure_honest_pass
from .mutation import generate_mutants, measure_catch_rate

REPORT_PATH = Path("runs/m1a_sweep.json")


@dataclass
class TaskRow:
    task_id: str
    generated: int
    distinct_shapes: int
    verified: int
    discarded: int
    honest_pass: float | None
    catch_rate: float | None
    flake_rate: float | None
    rejections: list[str]


def measure_task(task, candidates: list[Candidate], *, mutants: int = 8) -> TaskRow:
    """Every check, on one task. No API calls happen in here — this half is free."""
    grader = Grader(task=task)

    honest = measure_honest_pass(grader, candidates, grade=grade_solution, verify=run_oracle)
    verified = [c for c in candidates if c.label not in honest.discarded]

    gold = task.prompt + task.canonical_solution
    caught = measure_catch_rate(
        grader, generate_mutants(gold, limit=mutants), grade=grade_solution, verify=run_oracle
    )
    flake = measure_determinism(
        grader, verified[:5], grade=grade_solution, component="procedural", runs=3, timeout=30.0
    )

    return TaskRow(
        task_id=task.task_id,
        generated=len(candidates),
        distinct_shapes=diversity(candidates).distinct,
        verified=honest.verified,
        discarded=len(honest.discarded),
        honest_pass=honest.honest_pass,
        catch_rate=caught.catch_rate,
        flake_rate=flake.flake_rate,
        rejections=[r.label for r in honest.rejections],
    )


def render(rows: list[TaskRow]) -> str:
    def cell(value):
        return "  n/a" if value is None else f"{value:5.2f}"

    lines = [
        f"{'task':16}{'gen':>5}{'shape':>6}{'ver':>5}{'honest':>8}{'catch':>7}{'flake':>7}",
        "-" * 54,
    ]
    for row in rows:
        lines.append(
            f"{row.task_id:16}{row.generated:>5}{row.distinct_shapes:>6}{row.verified:>5}"
            f"{cell(row.honest_pass):>8}{cell(row.catch_rate):>7}{cell(row.flake_rate):>7}"
        )
    unfair = sorted({label for row in rows for label in row.rejections})
    lines += [
        "",
        "honest = of oracle-verified-correct solutions, the fraction the grader accepts.",
        "catch  = of oracle-broken mutants, the fraction the grader rejects.",
        "shape  = distinct AST shapes among the generated solutions; a low number makes",
        "         honest untrustworthy, because the population was not actually diverse.",
        f"Verified-correct solutions the grader rejected: {len(unfair)} {unfair[:6] or ''}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="M1a sweep over the hardest EvalPlus tasks")
    parser.add_argument("--tasks", type=int, default=5)
    parser.add_argument("--k", type=int, default=20)
    parser.add_argument("--mutants", type=int, default=8)
    parser.add_argument("--confirm", action="store_true", help="actually spend money")
    parser.add_argument(
        "--max-spend",
        type=float,
        default=2.00,
        help="refuse to run if the estimate exceeds this, in USD (default 2.00)",
    )
    args = parser.parse_args(argv)

    priced = estimate(args.tasks, args.k, DEFAULT_MODELS)
    print(priced.render())
    if priced.total > args.max_spend:
        print(
            f"\nREFUSED: estimate ${priced.total:.2f} exceeds the cap of ${args.max_spend:.2f}. "
            "Raise --max-spend deliberately or reduce --tasks/--k."
        )
        return 1
    if not args.confirm:
        print("\nDry run. Re-run with --confirm to generate. Everything after generation is free.")
        return 0

    import anthropic

    client = anthropic.Anthropic()
    tasks = load_hardest(args.tasks)

    rows = []
    for task in tasks:
        print(f"\n[{task.task_id}] generating {args.k}…", flush=True)
        candidates = generate_solutions(task, args.k, client=client, confirm=True)
        print(f"[{task.task_id}] measuring…", flush=True)
        rows.append(measure_task(task, candidates, mutants=args.mutants))
        print(render(rows[-1:]))

    print("\n" + render(rows))
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps([asdict(r) for r in rows], indent=2))
    print(f"\nwrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
