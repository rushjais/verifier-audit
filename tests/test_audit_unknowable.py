"""4c — unknowability pilot (FORK_PLAN §5). Offline: a fake `ask`, no network."""

import json

import pytest

from vaudit.audit import audit_unknowable, score_pilot
from vaudit.audit.unknowable import parse_assertions
from vaudit.tasks.replication import KNOWN_GAPS, SPEC

_GRADER = "Structural equality with a hidden reference implementation."


def _ask_returning(rows, capture=None):
    def ask(prompt):
        if capture is not None:
            capture.append(prompt)
        return json.dumps(rows)

    return ask


def _row(assertion, derivable):
    return {"assertion": assertion, "derivable": derivable, "reasoning": "because"}


def test_the_spec_and_the_grader_both_reach_the_model():
    seen = []
    audit_unknowable("t", SPEC, _GRADER, ask=_ask_returning([], seen))
    (prompt,) = seen
    assert "name:count" in prompt  # the spec
    assert "hidden reference" in prompt  # the grader


def test_only_the_non_derivable_assertions_are_reported_as_unfair():
    report = audit_unknowable(
        "t",
        SPEC,
        _GRADER,
        ask=_ask_returning(
            [
                _row("records come back in file order", True),
                _row("a record must be a tuple, not a dict", False),
            ]
        ),
    )
    assert len(report.assertions) == 2
    assert [a.text for a in report.unknowable] == ["a record must be a tuple, not a dict"]
    assert report.population.endswith("= 1")


def test_malformed_model_output_raises_rather_than_reporting_zero_gaps():
    """A silent [] would read as 'this grader is fair', which is the worst possible failure."""
    with pytest.raises(json.JSONDecodeError):
        audit_unknowable("t", SPEC, _GRADER, ask=lambda p: "I think the grader is fine!")
    with pytest.raises(ValueError):
        audit_unknowable("t", SPEC, _GRADER, ask=lambda p: '{"assertion": "x"}')


def test_markdown_fences_do_not_defeat_parsing():
    fenced = '```json\n[{"assertion": "a", "derivable": false}]\n```'
    assert parse_assertions(fenced)[0].text == "a"


# --- the pilot is scored against gaps we know are there ---------------------------------------


def test_an_auditor_that_finds_every_known_gap_scores_full_recall():
    report = audit_unknowable(
        "t",
        SPEC,
        _GRADER,
        ask=_ask_returning(
            [
                _row("each record must be a tuple", False),
                _row("the summary must be a mapping with those exact keys", False),
                _row("bad input must raise ValueError specifically", False),
                _row("the average must be an unrounded float", False),
            ]
        ),
    )
    score = score_pilot(report, KNOWN_GAPS)
    assert score.recall == 1.0
    assert score.missed == ()
    assert score.unmatched == ()
    assert "recovered 4/4" in score.render()


def test_a_gap_the_auditor_misses_is_reported_not_hidden():
    report = audit_unknowable(
        "t",
        SPEC,
        _GRADER,
        ask=_ask_returning([_row("each record must be a tuple", False)]),
    )
    score = score_pilot(report, KNOWN_GAPS)
    assert score.recovered == ("record_type",)
    assert set(score.missed) == {"summary_type", "exception_type", "average_precision"}
    assert score.recall == pytest.approx(0.25)
    assert "missed" in score.render()


def test_flags_that_match_no_known_gap_are_surfaced_for_hand_checking():
    """They may be real findings or model noise — the pilot must not decide that silently."""
    report = audit_unknowable(
        "t",
        SPEC,
        _GRADER,
        ask=_ask_returning([_row("the module must be named tallyfmt", False)]),
    )
    score = score_pilot(report, KNOWN_GAPS)
    assert score.unmatched == ("the module must be named tallyfmt",)
    assert score.recall == 0.0
    assert "hand-check" in score.render()
