"""M1b pilot — a differential grader enforces the reference's incidental choices (FORK_PLAN §6).

These run the real sandbox, so they are slower than the rest of the suite and worth it: the
pilot's headline number comes from here.
"""

import pytest

from vaudit.audit import Candidate, measure_honest_pass
from vaudit.tasks import EQUIVALENT, REFERENCE, ReplicationGrader, fair_oracle, strict_grade
from vaudit.tasks.replication import HELDOUT_INPUTS, VISIBLE_INPUTS


@pytest.fixture(scope="module")
def grader():
    return ReplicationGrader()


def test_grader_and_oracle_share_no_inputs():
    """Eval-honesty invariant #2, for this task."""
    assert set(VISIBLE_INPUTS).isdisjoint(HELDOUT_INPUTS)


def test_the_reference_passes_its_own_grader_and_the_oracle(grader):
    assert strict_grade(grader, REFERENCE) == 1
    assert fair_oracle(grader, REFERENCE) == 1


def test_the_control_passes_so_the_grader_is_unfair_rather_than_broken(grader):
    """Different internals, identical observable choices. A grader that rejected this would be
    broken, and the pilot would be measuring nothing."""
    assert strict_grade(grader, EQUIVALENT["reference_twin"]) == 1


@pytest.mark.parametrize("label", sorted(EQUIVALENT))
def test_every_variant_genuinely_satisfies_the_spec(grader, label):
    """The population must be real: each of these IS correct, so each rejection is a grader bug."""
    assert fair_oracle(grader, EQUIVALENT[label]) == 1


def test_the_oracle_is_not_simply_accepting_everything(grader):
    """Without this the honest-pass denominator would be meaningless."""
    wrong = "def parse(text):\n    return []\n\n\ndef summarize(records):\n    return {}\n"
    assert fair_oracle(grader, wrong) == 0
    assert strict_grade(grader, wrong) == 0


@pytest.mark.parametrize(
    ("label", "undetermined_choice"),
    [
        ("records_as_dicts", "a record's type"),
        ("records_as_lists", "a record's type"),
        ("summary_namedtuple", "the summary's type"),
        ("rounded_average", "the average's precision"),
        ("custom_exception", "which exception signals bad input"),
    ],
)
def test_each_rejection_traces_to_something_the_spec_never_determined(
    grader, label, undetermined_choice
):
    assert strict_grade(grader, EQUIVALENT[label]) == 0, undetermined_choice


def test_the_pilot_headline_a_differential_grader_rejects_most_correct_work(grader):
    candidates = [Candidate(label=n, source=src) for n, src in EQUIVALENT.items()]
    report = measure_honest_pass(grader, candidates, grade=strict_grade, verify=fair_oracle)

    assert report.discarded == (), "every variant should survive verification"
    assert report.verified == len(EQUIVALENT)
    assert report.honest_pass == pytest.approx(1 / 6)
    assert report.accepted == 1  # only the control
    assert {r.label for r in report.rejections} == set(EQUIVALENT) - {"reference_twin"}
