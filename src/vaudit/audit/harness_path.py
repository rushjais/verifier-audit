"""4b-prime — harness path: is the grader's own test exercising the path the rollout exercises?

THE DEFECT THIS CATCHES. Every other check in `audit/` assumes the thing under test is the thing
that runs. When that assumption breaks, all of them pass and none of them mean anything.

From a production system of mine: a lane allocator was recorded as shipped. Its budget was
`(share * top_k) // 100` behind a `MIN_TOP_K = 50` gate. The acceptance script called it with
`top_k=100`, so the allocator ran there and the test went green. Production defaults to `top_k=10`
and the batch runner to 25, both under the gate, so every production search silently fell back to
the old path. The feature's log line appeared **zero** times in a production-shaped run. Green for
a reason unrelated to the thing being measured.

A grader fails the same way: the suite calls it with a generous timeout, a patched grader, or an
environment the rollout never has. Nothing errors. The number is simply about something else.

SCOPE, HONESTLY. This is **not** a generic checker. It is an instrumentation helper plus the
checklist below, meant to be run per grader by a human who reads the diff. The generic version is
line-level coverage comparison between the two settings; that is v2.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..grader import Grader

CHECKLIST = """\
Per grader, confirm by hand:
  1. The grader is invoked at least once in the rollout.        (zero invocations = the bug above)
  2. Timeout and memory limits match between harness and rollout.
  3. The patch chain matches — the harness is not testing a hardened grader the rollout never uses.
  4. Any threshold or gate in the grader receives values from the same range in both settings.
  5. Environment differences (env vars, cwd, installed packages) do not change the verdict.
"""


@dataclass
class Observation:
    """Every invocation of a grader in one setting, with the config that decided its behaviour."""

    label: str
    calls: list[dict[str, Any]] = field(default_factory=list)

    @property
    def invoked(self) -> int:
        return len(self.calls)


def describe(grader: Grader, **call_kwargs: Any) -> dict[str, Any]:
    """The config that actually decides this grader's verdict — what a diff should compare."""
    return {
        "task_id": grader.task.task_id,
        "patches": tuple(grader.patches),
        **call_kwargs,
    }


class CallRecorder:
    """Wraps a grade callable so each invocation's decisive config lands in an Observation."""

    def __init__(self, label: str):
        self.observation = Observation(label=label)

    def wrap(self, grade: Callable[..., int], **extra: Any) -> Callable[..., int]:
        def recording(grader: Grader, solution_src: str, *args, **kwargs) -> int:
            self.observation.calls.append(describe(grader, **{**extra, **kwargs}))
            return grade(grader, solution_src, *args, **kwargs)

        return recording


@dataclass(frozen=True)
class PathDiff:
    harness: Observation
    rollout: Observation

    @property
    def never_invoked(self) -> bool:
        """The sharpest form of the bug: the harness exercised it and the rollout never did."""
        return self.harness.invoked > 0 and self.rollout.invoked == 0

    @property
    def differences(self) -> dict[str, tuple[Any, Any]]:
        """Config keys whose observed value sets differ between the two settings."""
        if self.never_invoked:
            return {"__invocations__": (self.harness.invoked, 0)}

        def values(observation: Observation, key: str) -> tuple:
            return tuple(sorted({repr(call.get(key)) for call in observation.calls}))

        keys = {k for call in self.harness.calls + self.rollout.calls for k in call}
        return {
            key: (values(self.harness, key), values(self.rollout, key))
            for key in sorted(keys)
            if values(self.harness, key) != values(self.rollout, key)
        }

    @property
    def matches(self) -> bool:
        return not self.differences

    def render(self) -> str:
        if self.matches:
            return f"harness-path ok ({self.harness.invoked} vs {self.rollout.invoked} calls)"
        if self.never_invoked:
            return (
                f"harness-path MISMATCH: invoked {self.harness.invoked}x in "
                f"'{self.harness.label}' and 0x in '{self.rollout.label}' — the rollout never "
                "runs this code"
            )
        lines = ["harness-path MISMATCH:"]
        lines += [
            f"  {key}: {self.harness.label}={h} vs {self.rollout.label}={r}"
            for key, (h, r) in self.differences.items()
        ]
        return "\n".join(lines)


def compare(harness: Observation, rollout: Observation) -> PathDiff:
    return PathDiff(harness=harness, rollout=rollout)
