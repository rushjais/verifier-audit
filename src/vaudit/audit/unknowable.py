"""4c — unknowability: what does the grader assert that the prompt never made derivable?

Mechanize's own example of a bad task is a grader that "checked if the model used a specific
query parameter name in an API route that it had no way of knowing from the information
available to it". The same essay names the hardest thing they cannot grade: "open-ended
instructions from customers who don't have a full technical specification". Both are this check.

Method: list what the grader actually asserts, then ask of each assertion whether the SPEC ALONE
determines it. Anything asserted but not derivable is an unfair assertion — a model can fail it
while doing everything it was asked.

PILOT, AND FALSIFIABLE. An LLM listing assertions is exactly the kind of instrument that can look
convincing and be wrong, so this ships pointed at a task whose gaps are known in advance
(`tasks.replication.KNOWN_GAPS`). `score_pilot` reports how many it recovered and what it missed.
An auditor that cannot find four gaps we planted is not ready to be believed about gaps we did
not. Results are hand-verified before they are written down, and the keyword matching below is a
convenience for that review, not evidence on its own.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

_EXTRACT = """\
Here is the SPECIFICATION a developer was given:

<spec>
{spec}
</spec>

Here is what the GRADER checks:

<grader>
{grader}
</grader>

List every distinct property the grader requires of a submission. For each, decide whether the
SPECIFICATION ALONE determines it — could a careful developer, reading only the spec, know the
grader would require this?

Return ONLY a JSON array, no prose, no markdown fence:
[{{"assertion": "<what the grader requires>", "derivable": true|false,
   "reasoning": "<one sentence>"}}]
"""


@dataclass(frozen=True)
class Assertion:
    text: str
    derivable: bool
    reasoning: str


@dataclass(frozen=True)
class UnknowabilityReport:
    task_id: str
    assertions: tuple[Assertion, ...]

    @property
    def unknowable(self) -> tuple[Assertion, ...]:
        """Asserted by the grader, not determined by the spec. Each one is a fairness bug."""
        return tuple(a for a in self.assertions if not a.derivable)

    @property
    def population(self) -> str:
        return (
            f"unknowable = |{{a in {len(self.assertions)} asserted : spec does not determine a}}| "
            f"= {len(self.unknowable)}"
        )


def parse_assertions(raw: str) -> tuple[Assertion, ...]:
    """Parse the model's JSON array. Malformed output raises rather than silently returning []."""
    text = "\n".join(ln for ln in raw.strip().splitlines() if not ln.strip().startswith("```"))
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise ValueError(f"expected a JSON array, got {type(rows).__name__}")
    return tuple(
        Assertion(
            text=str(row["assertion"]),
            derivable=bool(row["derivable"]),
            reasoning=str(row.get("reasoning", "")),
        )
        for row in rows
    )


def audit_unknowable(
    task_id: str, spec: str, grader: str, *, ask: Callable[[str], str]
) -> UnknowabilityReport:
    """Ask which of the grader's requirements the spec fails to determine. `ask` is injected."""
    raw = ask(_EXTRACT.format(spec=spec.strip(), grader=grader.strip()))
    return UnknowabilityReport(task_id=task_id, assertions=parse_assertions(raw))


def claude_asker(client, model: str = "claude-opus-5") -> Callable[[str], str]:
    """An `ask` backed by Claude. One call per audit; a few cents at most."""

    def ask(prompt: str) -> str:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text")

    return ask


# --- scoring the pilot against gaps we already know about --------------------------------------


@dataclass(frozen=True)
class PilotScore:
    recovered: tuple[str, ...]
    missed: tuple[str, ...]
    unmatched: tuple[str, ...]  # flagged, but not one of the known gaps — hand-check these

    @property
    def recall(self) -> float | None:
        known = len(self.recovered) + len(self.missed)
        return len(self.recovered) / known if known else None

    def render(self) -> str:
        return (
            f"4c pilot: recovered {len(self.recovered)}/"
            f"{len(self.recovered) + len(self.missed)} known gaps"
            + (f"; missed {list(self.missed)}" if self.missed else "")
            + (f"; {len(self.unmatched)} further flags to hand-check" if self.unmatched else "")
        )


def score_pilot(report: UnknowabilityReport, known_gaps: dict[str, tuple[str, ...]]) -> PilotScore:
    """Match flagged assertions to known gaps by keyword. A review aid, not evidence."""
    flagged = [a.text.lower() for a in report.unknowable]
    recovered, missed = [], []
    matched_indices: set[int] = set()

    for gap, keywords in known_gaps.items():
        hits = [i for i, text in enumerate(flagged) if any(kw in text for kw in keywords)]
        if hits:
            recovered.append(gap)
            matched_indices.update(hits)
        else:
            missed.append(gap)

    unmatched = tuple(
        report.unknowable[i].text for i in range(len(flagged)) if i not in matched_indices
    )
    return PilotScore(recovered=tuple(recovered), missed=tuple(missed), unmatched=unmatched)
