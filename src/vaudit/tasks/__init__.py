"""Hand-built tasks that EvalPlus cannot express. One so far; deliberately no shared protocol."""

from .replication import (
    EQUIVALENT,
    REFERENCE,
    SPEC,
    ReplicationGrader,
    fair_oracle,
    strict_grade,
)

__all__ = [
    "EQUIVALENT",
    "REFERENCE",
    "SPEC",
    "ReplicationGrader",
    "fair_oracle",
    "strict_grade",
]
