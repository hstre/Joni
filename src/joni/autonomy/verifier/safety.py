"""Deterministic aggregation + safety vetoes - 'rules for logic'.

The model gave continuous signals; the DECISION is made here by rules, not by the model. No naive
average: a weighted mean of the merit dimensions, but SAFETY OVERRIDES the score. A single relevant
red-flag, a possible core touch, weak evidence, or an unstable run can each prevent an automatic
'file' regardless of how clean the aggregate looks. Missing evidence is never compensated by
linguistic plausibility. When evidence is insufficient the system may ABSTAIN rather than invent a
clear answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import VerificationDimension

# merit dimensions and their weights (sum normalised); inverted risks are subtracted separately.
_WEIGHTS = {
    "module_fit": 0.25,
    "evidence_grounding": 0.25,
    "consistency": 0.15,
    "reasoning_stability": 0.10,
    "hard_constraint_compliance": 0.15,
    "impact": 0.10,
}
_HARD_CONSTRAINT_FLOOR = 0.5           # below this, a protected-core touch is plausible -> human
_OVERCLAIM_HIGH = 0.6
_CORE_FLAG_TYPES = ("touches_core", "core", "protected_core", "could_degrade", "security",
                    "egress", "persistence")


@dataclass(frozen=True)
class Decision:
    action: str            # file | read_full_text | run_additional_pass | human_review | abstain
    aggregate: float
    confidence: float
    veto: str = ""         # which rule fired, "" if the score decided


def _score(dims: dict[str, VerificationDimension], name: str, default: float = 0.5) -> float:
    d = dims.get(name)
    return d.score if d is not None else default


def _aggregate(dims: dict[str, VerificationDimension]) -> float:
    num = den = 0.0
    for name, w in _WEIGHTS.items():
        if name in dims:
            num += w * dims[name].score
            den += w
    base = (num / den) if den else 0.5
    # inverted risks pull the aggregate down (never up)
    base -= 0.5 * _score(dims, "info_needed", 0.0)
    base -= 0.5 * _score(dims, "overclaim_risk", 0.0)
    return max(0.0, min(1.0, base))


def decide(dims: dict[str, VerificationDimension], red_flags, cfg) -> Decision:
    agg = _aggregate(dims)
    var = [d.variance for d in dims.values()]
    confidence = round(1.0 - (sum(var) / len(var) if var else 0.0), 4)
    evidence = _score(dims, "evidence_grounding")
    fit = _score(dims, "module_fit")
    hard = _score(dims, "hard_constraint_compliance")
    info_needed = _score(dims, "info_needed", 0.0)
    overclaim = _score(dims, "overclaim_risk", 0.0)
    stability_var = dims["reasoning_stability"].variance if "reasoning_stability" in dims else 0.0

    def d(action, veto=""):
        return Decision(action=action, aggregate=round(agg, 4), confidence=confidence, veto=veto)

    # 1. safety first: a high-severity red-flag, or a core/degrade/security flag, needs a human.
    if any(str(f.severity).lower() == "high" for f in red_flags):
        return d("human_review", "high_severity_red_flag")
    if any(f.type.lower() in _CORE_FLAG_TYPES for f in red_flags):
        return d("human_review", "core_or_safety_red_flag")
    if hard < _HARD_CONSTRAINT_FLOOR:
        return d("human_review", "hard_constraint_compliance_low")
    # 2. weak evidence must not be filed - read the paper if we only had the abstract, else abstain.
    if evidence < cfg.evidence_floor:
        return d("read_full_text" if info_needed >= 0.5 else "abstain", "evidence_below_floor")
    if fit < cfg.fit_floor:
        return d("abstain", "module_fit_below_floor")
    # 3. an oversold proposal (convincing but unsupported) does not get filed automatically.
    if overclaim >= _OVERCLAIM_HIGH and evidence < 0.6:
        return d("abstain", "overclaim_over_evidence")
    # 4. an unstable run gets another pass rather than a coin-flip.
    if stability_var > cfg.instability_threshold:
        return d("run_additional_pass", "reasoning_unstable")
    # 5. a genuinely borderline aggregate is not auto-filed.
    if agg < 0.5 + cfg.margin_threshold:
        return d("run_additional_pass", "aggregate_borderline")
    return d("file")
