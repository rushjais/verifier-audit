"""4e — mutation catch rate (FORK_PLAN §5).

The property under test is the differential filter: a mutant the oracle still accepts is not a
bug, so it must never count against the grader.
"""

import pytest

from vaudit.audit import Mutant, generate_mutants, measure_catch_rate
from vaudit.grader import Grader
from vaudit.substrate import Task

_REF = 'def f(x):\n    """Double positives."""\n    if x > 0:\n        return x * 2\n    return 0\n'

_TASK = Task(
    task_id="T/1",
    prompt='def f(x):\n    """Double positives."""\n',
    entry_point="f",
    base_input=[[1]],
    plus_input=[[2]],
    canonical_solution="    return x * 2 if x > 0 else 0\n",
)


def _grader():
    return Grader(task=_TASK)


def test_mutants_are_single_point_deterministic_and_actually_different():
    first = generate_mutants(_REF)
    assert first, "the reference has mutable operators"
    assert [m.label for m in first] == [m.label for m in generate_mutants(_REF)]  # stable order
    assert all(m.source != _REF for m in first)
    assert len({m.source for m in first}) == len(first)  # no duplicate mutants


def test_the_operators_hit_the_constructs_a_real_off_by_one_would():
    labels = " ".join(m.label for m in generate_mutants(_REF))
    assert "cmp:Gt->GtE" in labels  # x > 0  ->  x >= 0
    assert "bin:Mult->FloorDiv" in labels  # x * 2  ->  x // 2
    assert "const:2->3" in labels


def test_limit_truncates_without_changing_the_order():
    full = generate_mutants(_REF)
    assert [m.label for m in generate_mutants(_REF, limit=2)] == [m.label for m in full[:2]]


def test_equivalent_mutants_are_excluded_not_counted_against_the_grader():
    """A mutant the oracle still accepts behaves the same; accepting it is not a grader failure."""
    mutants = [Mutant("real_bug", "x"), Mutant("equivalent", "y")]
    report = measure_catch_rate(
        _grader(),
        mutants,
        verify=lambda g, src: 1 if src == "y" else 0,  # the oracle says "y" still behaves
        grade=lambda g, src: 1,  # the grader accepts both
    )
    assert report.generated == 2
    assert report.equivalent == ("equivalent",)
    assert report.catchable == 1  # NOT 2
    assert report.catch_rate == 0.0
    assert [m.label for m in report.escaped] == ["real_bug"]


def test_escaped_mutants_are_reported_as_the_graders_blind_spots():
    mutants = [Mutant("a", "a"), Mutant("b", "b"), Mutant("c", "c")]
    report = measure_catch_rate(
        _grader(),
        mutants,
        verify=lambda g, src: 0,  # all genuinely broken
        grade=lambda g, src: 1 if src == "c" else 0,  # the grader misses "c"
    )
    assert report.caught == 2
    assert report.catch_rate == pytest.approx(2 / 3)
    assert [m.label for m in report.escaped] == ["c"]


def test_a_rate_over_nothing_is_not_a_rate():
    report = measure_catch_rate(
        _grader(),
        [Mutant("a", "a")],
        verify=lambda g, src: 1,  # every mutant was equivalent
        grade=lambda g, src: 0,
    )
    assert report.catchable == 0
    assert report.catch_rate is None


def test_the_report_states_its_own_population():
    report = measure_catch_rate(
        _grader(),
        [Mutant("a", "a"), Mutant("b", "b")],
        verify=lambda g, src: 1 if src == "b" else 0,
        grade=lambda g, src: 0,
    )
    assert report.population == ("catch_rate = rejected / |{m in 2 mutants : oracle(m) = 0}| = 1/1")


def test_end_to_end_the_real_grader_catches_real_mutants_of_a_real_reference():
    """No fakes: real sandboxed grader, real oracle, mutants of the actual reference."""
    from vaudit.grader import grade, run_oracle

    gold = _TASK.prompt + _TASK.canonical_solution
    mutants = generate_mutants(gold, limit=4)
    report = measure_catch_rate(_grader(), mutants, grade=grade, verify=run_oracle)

    assert report.generated == len(mutants)
    assert report.catchable > 0, "every mutant was equivalent — the filter has nothing to measure"
    assert report.catch_rate is not None
