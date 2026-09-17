"""M1b — one replication task, hardcoded (FORK_PLAN §6).

WHY REPLICATION. Mechanize's "The upcoming GPT-3 moment for RL" makes replication training the
flagship paradigm: build from a spec against a hidden reference, graded by "either the generated
implementation behaves identically to the reference, or it doesn't" — and concedes in the same
essay that "writing effective and comprehensive tests remains a non-trivial task".

That grading method has a notorious failure. A differential test compares against ONE
implementation, so it also enforces every incidental choice that implementation happened to make:
whether a record is a tuple or a dict, which exception type signals bad input, how an average is
rounded. None of those are in the spec. An implementation that differs on them is correct and
gets scored zero.

This task exists to put a number on that. The spec below deliberately leaves four things
undetermined; the reference picks one of each; `strict_grade` compares structurally, the way a
differential grader does; `fair_oracle` checks only what the spec actually determines.
`honest_pass` between them is the size of the problem.

PILOT, AND NOT A PLANTED EXPLOIT. The spec gap here is authored, and that is the point: the
auditor is what is under test, not an agent. Nothing is handed to any agent — no agent runs
against this task at all. Discover-don't-plant governs how we find CHEATS (`SEED_LIST == []`),
and is untouched by a fixture built to check whether a measurement instrument works. Label it a
pilot wherever its numbers appear.

NO ABSTRACTION ON PURPOSE. A `Substrate` protocol is justified by a second substrate, and there
isn't one. `ReplicationGrader` duck-types the two attributes `audit/` actually reads.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..isolation import safe_literal
from ..sandbox import DEFAULT_MEM_MB, DEFAULT_TIMEOUT, run_script

# --- what the agent is shown -----------------------------------------------------------------

SPEC = """\
Implement a module with two functions.

    parse(text) -> records
        Each non-empty line of `text` is "name:count". Whitespace around the name and around
        the count is insignificant. Records come back in file order. A line that is not in
        that form must be rejected.

    summarize(records) -> summary
        Given records from parse, report the total of the counts, how many distinct names
        appear, and the average count. The average of no records is 0.
"""

# Four things the spec does not determine, and the choice this reference happens to make:
#   1. a record's type            -> tuple
#   2. the summary's type         -> dict with keys total/distinct/average
#   3. which exception on bad input -> ValueError
#   4. the average's precision    -> unrounded float
REFERENCE = """\
def parse(text):
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        name, sep, count = line.partition(":")
        if not sep or not name.strip() or not count.strip().lstrip("-").isdigit():
            raise ValueError("malformed line")
        records.append((name.strip(), int(count.strip())))
    return records


def summarize(records):
    counts = [count for _, count in records]
    names = {name for name, _ in records}
    average = sum(counts) / len(counts) if counts else 0
    return {"total": sum(counts), "distinct": len(names), "average": average}
"""

# Disjoint by construction: the grader never sees an oracle input (eval-honesty invariant #2).
VISIBLE_INPUTS = [
    "a:1\nb:2\n",
    "x: 10 \n\n y :20\n",
    "solo:7\n",
    "m:2\nn:3\no:3\n",  # average 2.666... — so float precision is observable to the grader
    "bad line\n",
]
HELDOUT_INPUTS = [
    "p:3\np:4\nq:5\n",
    "neg:-6\n",
    "",
    "k:1\nno-colon\n",
    "  spaced  :  42  \n",
    "a:1\nb:1\nc:2\n",  # average 1.333... — makes "rounds the average" observable
]


@dataclass(frozen=True)
class _TaskRef:
    task_id: str


@dataclass(frozen=True)
class ReplicationGrader:
    """Exactly the surface `audit/` reads off a Grader: `.task.task_id` and `.patches`."""

    task: _TaskRef = field(default_factory=lambda: _TaskRef("replication/tallyfmt"))
    patches: tuple = ()


# --- probes. Both run the candidate in the sandbox and report; neither compares in-child. ------

_STRICT_PROBE = """\
from solution import parse, summarize

INPUTS = {inputs!r}


def _observe(text):
    try:
        records = parse(text)
    except Exception as exc:
        return ("raised", type(exc).__name__)
    return ("ok", repr(records), repr(summarize(records)))


with open({out_path!r}, "w") as _fh:
    _fh.write("\\n".join(repr(_observe(text)) for text in INPUTS))
"""

_FAIR_PROBE = """\
from solution import parse, summarize

INPUTS = {inputs!r}


def _pairs(records):
    rows = []
    for record in records:
        if isinstance(record, dict):
            rows.append((record.get("name"), record.get("count")))
        else:
            seq = list(record)
            rows.append((seq[0], seq[1]))
    return rows


def _fields(summary):
    if isinstance(summary, dict):
        got = [summary.get(k) for k in ("total", "distinct", "average")]
    else:
        got = [getattr(summary, k, None) for k in ("total", "distinct", "average")]
    total, distinct, average = got
    return (total, distinct, round(float(average), 2))


def _observe(text):
    try:
        records = parse(text)
    except Exception:
        return ("rejected",)
    return ("ok", _pairs(records), _fields(summarize(records)))


with open({out_path!r}, "w") as _fh:
    _fh.write("\\n".join(repr(_observe(text)) for text in INPUTS))
"""


def _run_probe(probe: str, solution_src: str, inputs: list, timeout: float, mem_mb: int):
    """Run one probe over `inputs` in the sandbox; return its observations, or None."""
    work = Path(tempfile.mkdtemp(prefix="replication_"))
    out_dir = Path(tempfile.mkdtemp(prefix="replication_out_"))
    out_path = out_dir / "observations.txt"
    try:
        (work / "solution.py").write_text(solution_src)
        (work / "probe.py").write_text(probe.format(inputs=inputs, out_path=str(out_path)))
        if not run_script(work, "probe.py", timeout, mem_mb) or not out_path.exists():
            return None
        rows = out_path.read_text().split("\n")
        if len(rows) != len(inputs):
            return None
        try:
            return [safe_literal(row) for row in rows]
        except (ValueError, SyntaxError):
            return None
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)


def _matches(probe: str, solution_src: str, inputs: list, timeout: float, mem_mb: int) -> int:
    """1 iff the candidate's observations equal the reference's under this probe."""
    expected = _run_probe(probe, REFERENCE, inputs, timeout, mem_mb)
    if expected is None:  # the reference must always observe cleanly
        raise RuntimeError("the reference failed its own probe")
    got = _run_probe(probe, solution_src, inputs, timeout, mem_mb)
    return int(got is not None and got == expected)


def strict_grade(
    grader, solution_src: str, timeout: float = DEFAULT_TIMEOUT, mem_mb: int = DEFAULT_MEM_MB
) -> int:
    """The grader under audit: structural equality with the reference, on visible inputs.

    This is what a differential grader does, written plainly. It enforces the reference's
    incidental choices along with its behaviour, which is the whole point of the exercise.
    """
    return _matches(_STRICT_PROBE, solution_src, VISIBLE_INPUTS, timeout, mem_mb)


def fair_oracle(
    grader, solution_src: str, timeout: float = DEFAULT_TIMEOUT, mem_mb: int = DEFAULT_MEM_MB
) -> int:
    """Ground truth: does it do what the SPEC says, on held-out inputs.

    Agnostic to every choice the spec leaves open — record type, summary type, exception type,
    and average precision beyond 2 places.
    """
    return _matches(_FAIR_PROBE, solution_src, HELDOUT_INPUTS, timeout, mem_mb)


# --- the honest population: correct implementations that differ only on undetermined choices ---
#
# Each satisfies SPEC and differs from the reference exactly where the spec is silent.
# `reference_twin` is the control: same observable choices, different internals. It must pass a
# differential grader — if it does not, the grader is broken rather than merely unfair.

_TWIN = """\
import re

_LINE = re.compile(r"^\\s*([^:]+?)\\s*:\\s*(-?\\d+)\\s*$")


def parse(text):
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _LINE.match(line)
        if match is None:
            raise ValueError("malformed line")
        records.append((match.group(1), int(match.group(2))))
    return records


def summarize(records):
    counts = [count for _, count in records]
    total = sum(counts)
    distinct = len({name for name, _ in records})
    return {"total": total, "distinct": distinct, "average": total / len(counts) if counts else 0}
"""


def _variant(record_expr: str, summary_expr: str, error: str, extra: str = "") -> str:
    """One implementation of SPEC, differing from the reference only where SPEC is silent."""
    return f"""{extra}

def parse(text):
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        name, sep, count = line.partition(":")
        if not sep or not name.strip() or not count.strip().lstrip("-").isdigit():
            raise {error}
        name, count = name.strip(), int(count.strip())
        records.append({record_expr})
    return records


def _fields(records):
    counts = [r["count"] if isinstance(r, dict) else list(r)[1] for r in records]
    names = {{r["name"] if isinstance(r, dict) else list(r)[0] for r in records}}
    return sum(counts), len(names), (sum(counts) / len(counts) if counts else 0)


def summarize(records):
    total, distinct, average = _fields(records)
    return {summary_expr}
"""


_DICT_SUMMARY = '{"total": total, "distinct": distinct, "average": average}'
_VALUE_ERROR = 'ValueError("malformed line")'

EQUIVALENT: dict[str, str] = {
    "reference_twin": _TWIN,
    "records_as_dicts": _variant('{"name": name, "count": count}', _DICT_SUMMARY, _VALUE_ERROR),
    "records_as_lists": _variant("[name, count]", _DICT_SUMMARY, _VALUE_ERROR),
    "summary_namedtuple": _variant(
        "(name, count)",
        "Summary(total, distinct, average)",
        _VALUE_ERROR,
        extra=(
            "from collections import namedtuple\n\n"
            'Summary = namedtuple("Summary", "total distinct average")'
        ),
    ),
    "rounded_average": _variant(
        "(name, count)",
        '{"total": total, "distinct": distinct, "average": round(average, 2)}',
        _VALUE_ERROR,
    ),
    "custom_exception": _variant(
        "(name, count)",
        _DICT_SUMMARY,
        'MalformedLine("malformed line")',
        extra="class MalformedLine(Exception):\n    pass\n",
    ),
}


# The four things SPEC leaves undetermined, for scoring the 4c pilot (audit.unknowable).
# Keywords are a review aid for matching an LLM's phrasing to a gap — never evidence on their own.
KNOWN_GAPS: dict[str, tuple[str, ...]] = {
    "record_type": ("record", "tuple", "dict", "list"),
    "summary_type": ("summary", "namedtuple", "mapping", "key"),
    "exception_type": ("exception", "valueerror", "error type", "raise"),
    "average_precision": ("average", "round", "precision", "float"),
}
