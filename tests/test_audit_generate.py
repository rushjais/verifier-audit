"""4a's population generator (FORK_PLAN §5). Offline: a fake create(), no network, no spend."""

from types import SimpleNamespace

import pytest

from vaudit.audit.generate import (
    DEFAULT_MODELS,
    diversity,
    estimate,
    fingerprint,
    generate_solutions,
    load_checkpoint,
)
from vaudit.substrate import Task

_TASK = Task(
    task_id="T/1",
    prompt="def f(x):\n",
    entry_point="f",
    base_input=[[1]],
    plus_input=[[2]],
    canonical_solution="    return x\n",
)


def _fake_create(calls):
    def create(**kwargs):
        calls.append(kwargs)
        n = len(calls)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text=f"```python\ndef f(x):\n    return x + {n}\n```")
            ]
        )

    return create


def test_nothing_is_bought_without_an_explicit_confirm(tmp_path, capsys):
    calls = []
    out = generate_solutions(
        _TASK, k=5, client=None, directory=tmp_path, create=_fake_create(calls)
    )
    assert calls == [], "the default path must not call the API"
    assert out == []
    printed = capsys.readouterr().out
    assert "estimated $" in printed and "confirm=True" in printed


def test_confirm_generates_and_strips_markdown_fences(tmp_path):
    calls = []
    out = generate_solutions(
        _TASK, k=3, client=None, confirm=True, directory=tmp_path, create=_fake_create(calls)
    )
    assert len(calls) == 3 and len(out) == 3
    assert all("```" not in c.source for c in out)
    assert all(c.source.startswith("def f(x):") for c in out)


def test_generation_varies_both_the_model_and_the_idiom(tmp_path):
    """Diversity is produced, not assumed — one model with one prompt gives one solution shape."""
    calls = []
    generate_solutions(
        _TASK, k=6, client=None, confirm=True, directory=tmp_path, create=_fake_create(calls)
    )
    assert len({c["model"] for c in calls}) == len(DEFAULT_MODELS)
    directives = {c["messages"][0]["content"].split("Style directive: ")[1] for c in calls}
    assert len(directives) == 6  # a different directive every time


def test_a_run_resumes_from_its_checkpoint_instead_of_restarting(tmp_path):
    """A spend cap hitting mid-sweep must cost the remainder of the run, not the run."""
    first = []
    generate_solutions(
        _TASK, k=2, client=None, confirm=True, directory=tmp_path, create=_fake_create(first)
    )
    assert len(load_checkpoint("T/1", tmp_path)) == 2

    second = []
    out = generate_solutions(
        _TASK, k=5, client=None, confirm=True, directory=tmp_path, create=_fake_create(second)
    )
    assert len(second) == 3, "only the missing three should be generated"
    assert len(out) == 5


def test_an_already_complete_task_costs_nothing_to_re_request(tmp_path):
    generate_solutions(
        _TASK, k=2, client=None, confirm=True, directory=tmp_path, create=_fake_create([])
    )
    calls = []
    out = generate_solutions(
        _TASK, k=2, client=None, confirm=True, directory=tmp_path, create=_fake_create(calls)
    )
    assert calls == [] and len(out) == 2


# --- cost ---------------------------------------------------------------------------------


def test_estimate_refuses_to_guess_at_an_unknown_models_price():
    with pytest.raises(KeyError):
        estimate(1, 1, ("claude-not-a-real-model",))


def test_estimate_scales_and_splits_across_the_model_mix():
    small, big = estimate(1, 30, DEFAULT_MODELS), estimate(10, 30, DEFAULT_MODELS)
    assert big.total == pytest.approx(small.total * 10)
    assert set(big.per_model) == set(DEFAULT_MODELS)
    assert big.calls == 300


# --- structural diversity -------------------------------------------------------------------


def test_renaming_variables_is_not_diversity():
    a = "def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n"
    b = "def f(items):\n    acc = 0\n    for i in items:\n        acc += i\n    return acc\n"
    assert fingerprint(a) == fingerprint(b)


def test_a_different_algorithm_fingerprints_differently():
    loop = "def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n"
    builtin = "def f(xs):\n    return sum(xs)\n"
    assert fingerprint(loop) != fingerprint(builtin)


def test_unparseable_source_is_never_silently_merged():
    assert fingerprint("def f(:\n").startswith("unparseable:")
    assert fingerprint("def f(:\n") != fingerprint("def g(:\n")


def test_diversity_reports_the_largest_identical_cluster():
    from vaudit.audit import Candidate

    same = "def f(xs):\n    return sum(xs)\n"
    renamed = "def f(ys):\n    return sum(ys)\n"
    other = "def f(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n"
    report = diversity(
        [
            Candidate("a", same),
            Candidate("b", renamed),  # same shape as a
            Candidate("c", other),
        ]
    )
    assert report.total == 3 and report.distinct == 2 and report.largest_cluster == 2
    assert "2/3" in report.population


def test_effort_is_only_sent_to_models_that_accept_it(tmp_path):
    """Haiku 4.5 rejects output_config.effort with a 400 — it killed the first real sweep."""
    calls = []
    generate_solutions(
        _TASK, k=6, client=None, confirm=True, directory=tmp_path, create=_fake_create(calls)
    )
    by_model = {c["model"]: c for c in calls}
    assert "output_config" not in by_model["claude-haiku-4-5"]
    assert by_model["claude-opus-5"]["output_config"] == {"effort": "low"}
    assert by_model["claude-sonnet-5"]["output_config"] == {"effort": "low"}
