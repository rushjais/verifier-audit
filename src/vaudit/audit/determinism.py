"""4b — determinism: does this grader return the same verdict twice?

"Deterministic" is a word every RL environment claims and none measures. A grader that flips its
verdict injects noise straight into the reward signal, which is the thing RL tolerates least —
and unlike an unfair grader, a flaky one is invisible in any single run.

Method: hold the submissions fixed, run the grader m times, and report every submission whose
verdict was not unanimous.

    flake_rate = unstable / |{submissions run m times}|

`component` is supplied by the caller rather than inferred, because only the caller knows which
half of a composite grader it just handed over. Attribution is the point of the check: procedural
flakiness (timeouts, iteration order, unseeded randomness, wall-clock) and rubric flakiness (LLM
drift at fixed temperature) have completely different fixes. Per-run durations are recorded for
the same reason — a verdict that flips while the slowest run sits near the timeout is a timeout,
not a mystery.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from ..grader import Grader
from .honest import Candidate


@dataclass(frozen=True)
class Trace:
    """One submission's verdict on each of the m runs, in order."""

    label: str
    verdicts: tuple[int, ...]
    durations: tuple[float, ...]

    @property
    def stable(self) -> bool:
        return len(set(self.verdicts)) <= 1

    @property
    def minority(self) -> int:
        """How many runs disagreed with the most common verdict — the size of the flake."""
        if not self.verdicts:
            return 0
        return len(self.verdicts) - max(self.verdicts.count(v) for v in set(self.verdicts))

    @property
    def slowest(self) -> float:
        return max(self.durations, default=0.0)


@dataclass(frozen=True)
class DeterminismReport:
    task_id: str
    component: str  # "procedural" | "rubric" | whatever the caller handed over
    runs: int
    traces: tuple[Trace, ...] = ()
    timeout: float | None = None

    @property
    def submissions(self) -> int:
        return len(self.traces)

    @property
    def unstable(self) -> tuple[Trace, ...]:
        return tuple(t for t in self.traces if not t.stable)

    @property
    def flake_rate(self) -> float | None:
        return len(self.unstable) / self.submissions if self.submissions else None

    @property
    def timeout_adjacent(self) -> tuple[Trace, ...]:
        """Unstable submissions whose slowest run got within 20% of the timeout.

        A hint about WHERE the flake came from, not a diagnosis — verify by hand before writing
        it down as the cause.
        """
        if self.timeout is None:
            return ()
        return tuple(t for t in self.unstable if t.slowest >= 0.8 * self.timeout)

    @property
    def population(self) -> str:
        return (
            f"flake_rate = unstable / |{{{self.submissions} submissions x {self.runs} runs}}| "
            f"= {len(self.unstable)}/{self.submissions} [{self.component}]"
        )


def measure_determinism(
    grader: Grader,
    submissions: Iterable[Candidate],
    *,
    grade: Callable[[Grader, str], int],
    component: str = "procedural",
    runs: int = 10,
    timeout: float | None = None,
) -> DeterminismReport:
    """Grade every submission `runs` times; report the ones that did not agree with themselves."""
    if runs < 2:
        raise ValueError("determinism needs at least 2 runs")

    traces = []
    for submission in submissions:
        verdicts, durations = [], []
        for _ in range(runs):
            started = time.perf_counter()
            verdicts.append(grade(grader, submission.source))
            durations.append(time.perf_counter() - started)
        traces.append(
            Trace(label=submission.label, verdicts=tuple(verdicts), durations=tuple(durations))
        )

    return DeterminismReport(
        task_id=grader.task.task_id,
        component=component,
        runs=runs,
        traces=tuple(traces),
        timeout=timeout,
    )
