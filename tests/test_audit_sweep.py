"""M1a sweep (FORK_PLAN §5). The measurement half must work before any money is spent."""

import pytest

from vaudit.audit.honest import Candidate
from vaudit.audit.sweep import TaskRow, main, measure_task, render
from vaudit.substrate import load_task


def test_a_dry_run_prices_the_sweep_and_buys_nothing(capsys):
    assert main(["--tasks", "5", "--k", "20"]) == 0
    printed = capsys.readouterr().out
    assert "100 calls" in printed and "Dry run" in printed


def test_a_missing_rate_renders_as_n_a_rather_than_a_number():
    row = TaskRow(
        task_id="T/1",
        generated=0,
        distinct_shapes=0,
        verified=0,
        discarded=0,
        honest_pass=None,
        catch_rate=None,
        flake_rate=None,
        rejections=[],
    )
    assert "n/a" in render([row])


def test_the_table_names_the_populations_its_numbers_are_over():
    row = TaskRow(
        task_id="T/1",
        generated=3,
        distinct_shapes=2,
        verified=3,
        discarded=0,
        honest_pass=0.67,
        catch_rate=0.5,
        flake_rate=0.0,
        rejections=["opus_01"],
    )
    text = render([row])
    assert "oracle-verified-correct solutions" in text
    assert "oracle-broken mutants" in text
    assert "makes" in text and "untrustworthy" in text  # the diversity caveat
    assert "opus_01" in text


@pytest.mark.slow
def test_the_whole_measurement_half_runs_on_a_real_task_with_no_api_calls():
    """Everything after generation is local. Proves the $0.35 only ever buys the solutions."""
    task = load_task("HumanEval/0")
    gold = task.prompt + task.canonical_solution
    candidates = [
        Candidate(label="gold", source=gold),
        Candidate(label="broken", source=task.prompt + "    return False\n"),
    ]

    row = measure_task(task, candidates, mutants=2)

    assert row.task_id == "HumanEval/0"
    assert row.generated == 2
    assert row.discarded == 1, "the broken one must be discarded, not counted as a rejection"
    assert row.verified == 1
    assert row.honest_pass == 1.0
    assert row.catch_rate is not None
    assert row.flake_rate == 0.0
