"""Answer isolation: a candidate sharing a process with the answers can fake a pass.

Each exploit here is shown to WORK against the previous design before it is shown to be dead
against the current one. A hardening test that never demonstrates the hole proves nothing.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from vaudit.isolation import safe_literal, score_isolated
from vaudit.sandbox import run_script

ENTRY = "f"
CASES = [((1,), 2), ((3,), 6), ((10,), 20)]  # f(x) -> x * 2
GOLD = "def f(x):\n    return x * 2\n"

# --- the exploits. Every one computes nothing; each steals or neuters the verdict. ----------

STEAL_BY_MODULE = """\
def f(*args):
    import test_cases
    return dict(test_cases.CASES)[args]
"""

STEAL_BY_STACK_FRAME = """\
import sys


def f(*args):
    return sys._getframe(1).f_locals["expected"]
"""

NEUTER_THE_COMPARISON = """\
import test_cases

test_cases._eq = lambda a, b: True


def f(x):
    return "not even a number"
"""

EXPLOITS = {
    "steal_by_module": STEAL_BY_MODULE,
    "steal_by_stack_frame": STEAL_BY_STACK_FRAME,
    "neuter_the_comparison": NEUTER_THE_COMPARISON,
}


# The comparison helper the old design inlined into the generated module, where the candidate
# could reach it. Kept here only so the exploits below can be shown to be real.
_EQ_SRC = """\
def _eq(a, b):
    return a == b
"""


def _score_the_old_way(solution_src: str) -> int:
    """The pre-hardening design, reconstructed: expecteds AND the comparison in the child.

    This is what the generated case module used to look like. A candidate imported into that
    process could read CASES, walk the frame for `expected`, or replace `_eq`.
    """
    work = Path(tempfile.mkdtemp(prefix="old_design_"))
    try:
        (work / "solution.py").write_text(solution_src)
        lines = [_EQ_SRC, "", f"from solution import {ENTRY} as _fn", "", "CASES = ["]
        lines += [f"    ({args!r}, {expected!r})," for args, expected in CASES]
        lines += [
            "]",
            "",
            "for args, expected in CASES:",
            "    assert _eq(_fn(*args), expected), args",
            "",
        ]
        (work / "test_cases.py").write_text("\n".join(lines))
        # Imported, not run as __main__ — so a candidate doing `import test_cases` reaches the
        # SAME partially-initialised module, exactly as it did under the old pytest harness.
        (work / "run.py").write_text("import test_cases\n")
        return int(run_script(work, "run.py"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


@pytest.mark.parametrize("name", sorted(EXPLOITS))
def test_the_exploit_was_real_under_the_old_design(name):
    """Red first: each of these passes a grader whose answers live in the child process."""
    assert _score_the_old_way(EXPLOITS[name]) == 1, f"{name} was expected to breach the old design"


@pytest.mark.parametrize("name", sorted(EXPLOITS))
def test_the_exploit_is_dead_under_answer_isolation(name):
    """Green: the child holds only the inputs, so there is nothing left to steal or neuter."""
    assert score_isolated(ENTRY, EXPLOITS[name], CASES) == 0, f"{name} still breaches"


def test_hardening_did_not_cost_the_gold_solution():
    """Anti-theater rule 4: a fix that blocks cheats by rejecting honest work is a regression."""
    assert score_isolated(ENTRY, GOLD, CASES) == 1


def test_a_candidate_that_forges_the_output_file_still_cannot_know_the_answers():
    """It can locate and overwrite the channel; it cannot produce values it never had."""
    forge = (
        "import re\n"
        "\n"
        "_path = re.search(r'open\\(.(/[^']+).,', open('test_collect.py').read()).group(1)\n"
        "open(_path, 'w').write('999\\n999\\n999')\n"
        "\n"
        "\n"
        "def f(x):\n"
        "    return 0\n"
    )
    assert score_isolated(ENTRY, forge, CASES) == 0


def test_wrong_arity_of_outputs_is_a_miss_not_a_pass():
    """A candidate that exits early leaves a short file; that must never read as success."""
    truncate = "import os\n\n\ndef f(x):\n    if x == 10:\n        os._exit(0)\n    return x * 2\n"
    assert score_isolated(ENTRY, truncate, CASES) == 0


def test_no_cases_is_not_a_pass():
    assert score_isolated(ENTRY, GOLD, []) == 0


# --- the parent-side reader must stay a reader, never an evaluator -------------------------


def test_safe_literal_round_trips_the_values_real_tasks_produce():
    assert safe_literal("[1, 2.5, 'x', (3, None), {'k': True}]") == [
        1,
        2.5,
        "x",
        (3, None),
        {"k": True},
    ]
    assert safe_literal("-4") == -4
    assert safe_literal("inf") == float("inf")
    nan = safe_literal("nan")
    assert nan != nan  # NaN is why plain ast.literal_eval was not enough


@pytest.mark.parametrize(
    "hostile",
    [
        "__import__('os').system('echo pwned')",
        "open('/etc/passwd').read()",
        "().__class__.__mro__[1].__subclasses__()",
        "lambda: 1",
        "some_name",
    ],
)
def test_safe_literal_refuses_anything_that_is_not_a_literal(hostile):
    """Candidate output crosses a process boundary; parsing it must not hand over the parent."""
    with pytest.raises((ValueError, SyntaxError)):
        safe_literal(hostile)
