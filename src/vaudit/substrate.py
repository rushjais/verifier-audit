"""Tasks under audit. EvalPlus today; the shape is a plain dataclass, not a protocol.

`base_input` feeds the grader and `plus_input` feeds the oracle. They never overlap — a grader
sharing cases with its own ground truth cannot detect anything. `canonical_solution` and
`plus_input` stay in this process and are never written anywhere a candidate could read.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Task:
    task_id: str
    prompt: str
    entry_point: str
    base_input: list  # visible to the grader
    plus_input: list  # held out, oracle only
    canonical_solution: str  # held out, oracle only


def _from_record(task_id: str, record: dict) -> Task:
    return Task(
        task_id=task_id,
        prompt=record["prompt"],
        entry_point=record["entry_point"],
        base_input=record["base_input"],
        plus_input=record["plus_input"],
        canonical_solution=record["canonical_solution"],
    )


@lru_cache(maxsize=1)
def _dataset() -> dict:
    from evalplus.data import get_human_eval_plus

    return get_human_eval_plus()


def load_task(task_id: str) -> Task:
    return _from_record(task_id, _dataset()[task_id])


def _sparseness(task: Task) -> float:
    """Reference logic per visible test case. Higher means the grader is thinner relative to the
    problem — an objective proxy for where a weak grader is weakest, not a search for results."""
    return len(task.canonical_solution) / max(1, len(task.base_input))


def load_hardest(n: int) -> list[Task]:
    """The n tasks with the sparsest visible coverage, ties broken by index for determinism."""
    tasks = [_from_record(tid, rec) for tid, rec in _dataset().items()]
    tasks.sort(key=lambda t: (-_sparseness(t), int(t.task_id.split("/")[1])))
    return tasks[:n]


def expected_outputs(task: Task, inputs: list) -> list:
    """Run the reference over `inputs` to derive expected values. Parent process only."""
    namespace: dict = {}
    exec(task.prompt + task.canonical_solution, namespace)  # trusted dataset reference
    fn = namespace[task.entry_point]
    return [fn(*args) for args in inputs]
