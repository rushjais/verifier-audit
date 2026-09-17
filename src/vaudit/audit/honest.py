"""4a — honest-solution coverage (FORK_PLAN §5).

The repo today answers "is this grader fair?" with: does the ONE gold solution still pass.
That is the weakest form of the question. A grader can accept the gold and still reject most
legitimate ways of solving the task — and every such rejection is a model scoring zero for the
task designer's mistake rather than its own.

So we ask it over a population: of k DIVERSE correct solutions, how many does the grader accept?

The load-bearing detail is the denominator. A proposed solution only joins the population after
the ORACLE confirms it is actually correct. Without that gate a rejection is ambiguous — the
grader may have been right — and the metric means nothing. Hence:

    honest_pass = |accepted| / |{s in proposed : oracle(s) = 1}|

Candidates the oracle rejects are discarded and reported separately, never silently dropped.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from ..grader import Grader, run_oracle
from ..grader import grade as default_grade


@dataclass(frozen=True)
class Candidate:
    """One proposed honest solution. `label` says how it was produced, for the repro."""

    label: str
    source: str


@dataclass(frozen=True)
class Rejection:
    """A verified-correct solution the grader refused. This is the fairness bug itself."""

    label: str
    source: str

    def repro(self, task_id: str) -> str:
        """The exact snippet that reproduces this rejection (anti-theater rule 5).

        Write `self.source` to solution.py next to it and run; it prints 0, the refusal.
        """
        return "\n".join(
            [
                "from vaudit.grader import Grader, grade",
                "from vaudit.substrate import load_task",
                "",
                f"src = open('solution.py').read()  # {self.label}",
                f"print(grade(Grader(task=load_task({task_id!r})), src))  # expect 1, prints 0",
            ]
        )


@dataclass(frozen=True)
class HonestPassReport:
    task_id: str
    proposed: int
    accepted: int
    rejections: tuple[Rejection, ...] = ()
    discarded: tuple[str, ...] = ()  # labels the oracle judged incorrect — not honest solutions
    grader_patches: tuple[str, ...] = field(default=())

    @property
    def verified(self) -> int:
        """The population: proposals the oracle confirmed correct."""
        return self.accepted + len(self.rejections)

    @property
    def honest_pass(self) -> float | None:
        """None when no proposal survived verification — a rate over nothing is not a rate."""
        return self.accepted / self.verified if self.verified else None

    @property
    def population(self) -> str:
        """State what the number is over, every time (anti-theater rule 6)."""
        return (
            f"honest_pass = accepted / |{{s in {self.proposed} proposed : oracle(s) = 1}}| "
            f"= {self.accepted}/{self.verified}"
        )


def measure_honest_pass(
    grader: Grader,
    candidates: Iterable[Candidate],
    *,
    grade: Callable[[Grader, str], int] = default_grade,
    verify: Callable[[Grader, str], int] | None = None,
) -> HonestPassReport:
    """Run every candidate past the oracle, then past the grader. See the module docstring.

    `grade` and `verify` are injected so this is testable without a sandbox or a network.
    """
    verify = verify if verify is not None else run_oracle

    proposed = 0
    accepted = 0
    rejections: list[Rejection] = []
    discarded: list[str] = []

    for candidate in candidates:
        proposed += 1
        if verify(grader, candidate.source) != 1:
            discarded.append(
                candidate.label
            )  # not a correct solution; says nothing about the grader
            continue
        if grade(grader, candidate.source) == 1:
            accepted += 1
        else:
            rejections.append(Rejection(label=candidate.label, source=candidate.source))

    return HonestPassReport(
        task_id=grader.task.task_id,
        proposed=proposed,
        accepted=accepted,
        rejections=tuple(rejections),
        discarded=tuple(discarded),
        grader_patches=tuple(grader.patches),
    )
