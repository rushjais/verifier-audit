"""Grader auditing: is this verifier FAIR and DETERMINISTIC, not just un-gameable.

The hackathon original measures one direction — can a grader be cheated. These checks measure
the other two. None of them is a new idea on its own (SWE-bench Verified screened for
over-specific tests by hand; flaky-test detection is an established field). What does not exist
is the automated, per-grader combination: fairness reported beside robustness, repeatably, for a
specific verifier as it changes. See `BRIEF.md` and `FORK_PLAN.md` §5.

    4a  honest_pass  = accepted / |{s : oracle(s) = 1}|   correct code the grader accepts
    4e  catch_rate   = rejected / |{m : oracle(m) = 0}|   broken code the grader rejects
    4b  flake_rate   = unstable / |{submissions x m runs}|
    4b-prime harness path = does the grader's own test exercise what the rollout exercises
"""

from .determinism import DeterminismReport, Trace, measure_determinism
from .generate import CostEstimate, DiversityReport, diversity, estimate, generate_solutions
from .harness_path import CHECKLIST, CallRecorder, Observation, PathDiff, compare, describe
from .honest import Candidate, HonestPassReport, Rejection, measure_honest_pass
from .mutation import Mutant, MutationReport, generate_mutants, measure_catch_rate
from .unknowable import (
    Assertion,
    PilotScore,
    UnknowabilityReport,
    audit_unknowable,
    score_pilot,
)

__all__ = [
    "CHECKLIST",
    "Assertion",
    "CallRecorder",
    "Candidate",
    "CostEstimate",
    "DeterminismReport",
    "DiversityReport",
    "HonestPassReport",
    "Mutant",
    "MutationReport",
    "Observation",
    "PathDiff",
    "PilotScore",
    "Rejection",
    "Trace",
    "UnknowabilityReport",
    "audit_unknowable",
    "compare",
    "describe",
    "diversity",
    "estimate",
    "generate_mutants",
    "generate_solutions",
    "measure_catch_rate",
    "measure_determinism",
    "measure_honest_pass",
    "score_pilot",
]
