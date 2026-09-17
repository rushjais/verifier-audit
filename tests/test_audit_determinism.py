"""4b — determinism (FORK_PLAN §5). A grader that flips its verdict is noise in the reward."""

import pytest

from vaudit.audit import Candidate, measure_determinism
from vaudit.grader import Grader
from vaudit.substrate import Task

_TASK = Task(
    task_id="T/1",
    prompt="def f(x):\n",
    entry_point="f",
    base_input=[[1]],
    plus_input=[[2]],
    canonical_solution="    return x * 2\n",
)


def _grader():
    return Grader(task=_TASK)


def _subs(*labels):
    return [Candidate(label=n, source=f"# {n}") for n in labels]


def _flaky(pattern):
    """A grader that returns `pattern` cyclically, per submission."""
    state: dict[str, int] = {}

    def grade(g, src):
        i = state.get(src, 0)
        state[src] = i + 1
        return pattern[i % len(pattern)]

    return grade


def test_a_grader_that_agrees_with_itself_has_no_flake():
    report = measure_determinism(_grader(), _subs("a", "b"), grade=lambda g, s: 1, runs=5)
    assert report.submissions == 2
    assert report.unstable == ()
    assert report.flake_rate == 0.0
    assert all(t.minority == 0 for t in report.traces)


def test_an_unstable_verdict_is_caught_and_its_size_reported():
    # 1,1,1,0,1 -> unanimous-but-for-one: one run disagreed with the majority
    report = measure_determinism(_grader(), _subs("a"), grade=_flaky([1, 1, 1, 0, 1]), runs=5)
    (trace,) = report.unstable
    assert trace.verdicts == (1, 1, 1, 0, 1)
    assert trace.minority == 1
    assert report.flake_rate == 1.0


def test_flake_rate_is_over_submissions_not_over_runs():
    grade = lambda g, s: 0 if "b" in s else 1  # noqa: E731 - stable per submission
    report = measure_determinism(_grader(), _subs("a", "b", "c", "d"), grade=grade, runs=4)
    assert report.flake_rate == 0.0  # different verdicts ACROSS submissions is not flakiness


def test_the_component_is_recorded_because_the_two_halves_have_different_fixes():
    report = measure_determinism(
        _grader(), _subs("a"), grade=lambda g, s: 1, component="rubric", runs=2
    )
    assert report.component == "rubric"
    assert "[rubric]" in report.population


def test_the_report_states_its_own_population():
    report = measure_determinism(_grader(), _subs("a", "b"), grade=_flaky([1, 0]), runs=2)
    assert report.population == (
        "flake_rate = unstable / |{2 submissions x 2 runs}| = 2/2 [procedural]"
    )


def test_timeout_adjacency_is_offered_as_a_hint_only_when_a_timeout_is_known():
    report = measure_determinism(_grader(), _subs("a"), grade=_flaky([1, 0]), runs=2)
    assert report.timeout_adjacent == ()  # no timeout supplied -> no claim made

    slow = measure_determinism(
        _grader(), _subs("a"), grade=_flaky([1, 0]), runs=2, timeout=1e-9
    )  # any real call exceeds 0.8 * 1e-9, so the hint fires
    assert len(slow.timeout_adjacent) == 1


def test_determinism_needs_more_than_one_run():
    with pytest.raises(ValueError):
        measure_determinism(_grader(), _subs("a"), grade=lambda g, s: 1, runs=1)


def test_end_to_end_the_real_sandboxed_grader_is_stable_across_reruns():
    """The procedural half should be boring. If this ever flakes, that IS the finding."""
    from vaudit.grader import grade

    gold = Candidate(label="gold", source=_TASK.prompt + _TASK.canonical_solution)
    report = measure_determinism(_grader(), [gold], grade=grade, runs=3, timeout=30.0)
    assert report.flake_rate == 0.0, report.unstable
