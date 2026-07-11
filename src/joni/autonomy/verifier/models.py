"""Verifier data model - the structured, auditable shape of a verification.

The dimensions are Joni's translation of the clinical spec into his domain (paper -> Auftrag):
module_fit, evidence_grounding, consistency, alternatives, error_safety, impact,
info_needed, reasoning_stability, hard_constraint_compliance, overclaim_risk. Plausibility and
evidence are kept SEPARATE on purpose - a proposal can be eloquent and internally coherent yet rest
on weak evidence, and the data model must show that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The verifier's continuous 0..1 dimensions (Joni domain). Order is stable for audit/eval.
DIMENSIONS = (
    "module_fit",                 # does the method really map onto the named non-core module?
    "evidence_grounding",         # grounded in the real method/full text, not abstract plausibility
    "consistency",                # internal logical consistency of the proposed change
    "alternatives",              # considered simpler/existing routes, or that it may not apply
    "error_safety",               # risk of the change - stays non-core, cannot degrade Joni
    "impact",                     # measurable benefit if adopted
    "info_needed",                # more evidence/full text needed (HIGH = need more; inverted)
    "reasoning_stability",        # how stable the justification is across repetitions
    "hard_constraint_compliance",  # non-core only, never the protected core (rules-for-logic)
    "overclaim_risk",             # convincing-but-unsupported (HIGH = worse, a cost not a credit)
)

# Dimensions where a HIGHER score is WORSE (they are risks/needs, not merits).
_INVERTED = frozenset({"info_needed", "overclaim_risk"})


def is_inverted(name: str) -> bool:
    return name in _INVERTED


@dataclass
class VerificationDimension:
    name: str
    score: float                  # mean over repetitions, 0..1
    variance: float = 0.0         # spread over repetitions (0 = perfectly stable)
    rationale: str = ""


@dataclass
class VerificationRedFlag:
    type: str                     # e.g. "touches_core", "unfalsifiable_acceptance", "could_degrade"
    severity: str                 # "low" | "medium" | "high"
    explanation: str = ""


@dataclass
class VerificationResult:
    escalated: bool
    escalation_reasons: list[str] = field(default_factory=list)
    dimensions: dict[str, VerificationDimension] = field(default_factory=dict)
    aggregate_score: float = 0.0
    confidence: float = 0.0        # 1 - mean variance; low when the run was unstable
    red_flags: list[VerificationRedFlag] = field(default_factory=list)
    action: str = "file"           # file | read_full_text | run_additional_pass | human_review | abstain  # noqa: E501
    veto: str = ""                 # the veto rule that fired, if any
    reps: int = 0
    audit: dict = field(default_factory=dict)
