"""4b-prime — harness path (FORK_PLAN §5).

Every other check assumes the thing under test is the thing that runs. This is the check for
when that assumption breaks and all the others go green about something else.
"""

from vaudit.audit import CHECKLIST, CallRecorder, compare
from vaudit.grader import Grader, grade, harden_with
from vaudit.substrate import Task

_TASK = Task(
    task_id="T/1",
    prompt="def f(x):\n",
    entry_point="f",
    base_input=[[1]],
    plus_input=[[2]],
    canonical_solution="    return x * 2\n",
)
_GOLD = _TASK.prompt + _TASK.canonical_solution


def _record(label, grade_fn, **extra):
    recorder = CallRecorder(label)
    return recorder, recorder.wrap(grade_fn, **extra)


def test_identical_configuration_on_both_sides_is_a_match():
    h, h_grade = _record("harness", lambda g, s, **k: 1, timeout=30.0)
    r, r_grade = _record("rollout", lambda g, s, **k: 1, timeout=30.0)
    h_grade(Grader(task=_TASK), _GOLD)
    r_grade(Grader(task=_TASK), _GOLD)

    diff = compare(h.observation, r.observation)
    assert diff.matches
    assert "harness-path ok" in diff.render()


def test_a_grader_the_rollout_never_invokes_is_the_sharpest_form_of_the_bug():
    h, h_grade = _record("harness", lambda g, s, **k: 1)
    r, _ = _record("rollout", lambda g, s, **k: 1)  # the rollout never calls it
    h_grade(Grader(task=_TASK), _GOLD)

    diff = compare(h.observation, r.observation)
    assert diff.never_invoked
    assert not diff.matches
    assert "the rollout never runs this code" in diff.render()


def test_a_generous_timeout_in_the_harness_is_caught():
    h, h_grade = _record("harness", lambda g, s, **k: 1, timeout=30.0)
    r, r_grade = _record("rollout", lambda g, s, **k: 1, timeout=5.0)
    h_grade(Grader(task=_TASK), _GOLD)
    r_grade(Grader(task=_TASK), _GOLD)

    diff = compare(h.observation, r.observation)
    assert "timeout" in diff.differences
    assert "MISMATCH" in diff.render()


def test_testing_a_hardened_grader_the_rollout_never_uses_is_caught():
    """The patch chain decides the verdict, so a harness/rollout split there is the same bug."""
    h, h_grade = _record("harness", lambda g, s, **k: 1)
    r, r_grade = _record("rollout", lambda g, s, **k: 1)
    h_grade(harden_with(Grader(task=_TASK), "extra_cases", [[7]]), _GOLD)  # hardened
    r_grade(Grader(task=_TASK), _GOLD)  # stock

    diff = compare(h.observation, r.observation)
    assert diff.differences["patches"] == (("('extra_cases',)",), ("()",))


def test_demonstrated_on_the_real_grader():
    """Wrap the actual sandboxed grader in both settings; the verdicts agree, the configs do not."""
    h, h_grade = _record("harness", grade, timeout=30.0)
    r, r_grade = _record("rollout", grade, timeout=30.0)

    assert h_grade(Grader(task=_TASK), _GOLD) == r_grade(Grader(task=_TASK), _GOLD) == 1
    assert compare(h.observation, r.observation).matches

    # The realistic split: the suite exercises a hardened grader, production ships the stock one.
    h2, h2_grade = _record("harness", grade)
    r2, r2_grade = _record("rollout", grade)
    h2_grade(harden_with(Grader(task=_TASK), "extra_cases", [[7]]), _GOLD)
    r2_grade(Grader(task=_TASK), _GOLD)
    assert not compare(h2.observation, r2.observation).matches


def test_the_checklist_is_shipped_with_the_helper():
    """It is a helper plus a checklist read by a human, not a generic checker (FORK_PLAN §5)."""
    assert "invoked at least once in the rollout" in CHECKLIST
    assert CHECKLIST.count("\n") >= 5
