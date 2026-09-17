"""4a — honest-solution coverage (FORK_PLAN §5).

The property under test is the DENOMINATOR: only oracle-verified-correct solutions may enter
the population, or a rejection is ambiguous and the rate is meaningless.
"""

import pytest

from vaudit.audit import Candidate, measure_honest_pass
from vaudit.grader import Grader, harden_with
from vaudit.substrate import Task

_TASK = Task(
    task_id="T/1",
    prompt='def f(x):\n    """Double it."""\n',
    entry_point="f",
    base_input=[[1]],
    plus_input=[[2]],
    canonical_solution="    return x * 2\n",
)


def _grader():
    return Grader(task=_TASK)


def _candidates(*labels):
    return [Candidate(label=n, source=f"# {n}\ndef f(x):\n    return x * 2\n") for n in labels]


def test_rate_is_over_verified_solutions_not_proposed_ones():
    """An incorrect proposal must not dilute the denominator — the grader was right to refuse."""
    report = measure_honest_pass(
        _grader(),
        _candidates("iterative", "recursive", "broken"),
        # the oracle rejects "broken"; the grader rejects it too, correctly
        verify=lambda g, src: 0 if "broken" in src else 1,
        grade=lambda g, src: 0 if "broken" in src else 1,
    )
    assert report.proposed == 3
    assert report.discarded == ("broken",)
    assert report.verified == 2  # NOT 3
    assert report.honest_pass == 1.0  # NOT 2/3
    assert report.rejections == ()


def test_a_verified_solution_the_grader_refuses_is_a_fairness_bug():
    report = measure_honest_pass(
        _grader(),
        _candidates("stdlib", "hand_rolled"),
        verify=lambda g, src: 1,  # both are genuinely correct
        grade=lambda g, src: 0 if "hand_rolled" in src else 1,
    )
    assert report.verified == 2
    assert report.accepted == 1
    assert report.honest_pass == 0.5

    (bug,) = report.rejections
    assert bug.label == "hand_rolled"
    repro = bug.repro(report.task_id)
    assert "'T/1'" in repro and "expect 1, prints 0" in repro


def test_a_rate_over_nothing_is_not_a_rate():
    report = measure_honest_pass(
        _grader(), _candidates("a", "b"), verify=lambda g, src: 0, grade=lambda g, src: 1
    )
    assert report.verified == 0
    assert report.honest_pass is None  # not 0.0, and not a ZeroDivisionError


def test_the_report_states_its_own_population():
    """Anti-theater rule 6: every number carries the predicate it is computed over."""
    report = measure_honest_pass(
        _grader(),
        _candidates("a", "b", "c"),
        verify=lambda g, src: 0 if "c" in src else 1,
        grade=lambda g, src: 1,
    )
    assert report.population == (
        "honest_pass = accepted / |{s in 3 proposed : oracle(s) = 1}| = 2/2"
    )


def test_patches_are_recorded_so_a_number_names_the_grader_it_came_from():
    grader = harden_with(_grader(), "extra_cases", [[7]])
    report = measure_honest_pass(
        grader, _candidates("a"), verify=lambda g, src: 1, grade=lambda g, src: 1
    )
    assert report.grader_patches == ("extra_cases",)


@pytest.mark.parametrize("body", ["    return x * 2\n", "    return x + x\n", "    return 2 * x\n"])
def test_end_to_end_real_grader_accepts_genuinely_different_correct_solutions(body):
    """No fakes: the real oracle and the real sandboxed grader, three distinct idioms."""
    report = measure_honest_pass(_grader(), [Candidate(label="idiom", source=_TASK.prompt + body)])
    assert report.verified == 1, f"oracle rejected a correct solution: {body!r}"
    assert report.honest_pass == 1.0, f"grader rejected a verified-correct solution: {body!r}"
