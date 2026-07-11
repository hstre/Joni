"""Verifier configuration - env-driven, no hardcoded thresholds. Safe, conservative defaults.

Default mode is ``shadow`` (observe, change nothing). ``enforce`` lets the verifier's action decide;
``off`` disables it entirely. Every threshold is tunable so behaviour is configuration, not code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_MODES = ("shadow", "enforce", "off")


@dataclass(frozen=True)
class VerifierConfig:
    mode: str                       # "shadow" | "enforce" | "off"
    reps: int                       # repeated evaluations per verification (variance reduction)
    margin_threshold: float         # min gap to treat a decision as clearly settled
    disagreement_threshold: float   # per-dimension spread above which the decision is "unstable"
    instability_threshold: float    # reasoning-stability variance above which we distrust the run
    evidence_floor: float           # below this evidence-grounding score, never auto-accept
    fit_floor: float                # below this module-fit score, never auto-accept
    max_cost_eur: float             # hard per-verification budget; over it -> defined fallback
    use_logprobs: bool              # try a logit-expectation score; falls back to numeric if absent

    @property
    def enabled(self) -> bool:
        return self.mode != "off"


def load() -> VerifierConfig:
    mode = os.getenv("JONI_VERIFIER_MODE", "shadow").strip().lower()
    if mode not in _MODES:
        mode = "shadow"
    if os.getenv("JONI_VERIFIER", "1") == "0":          # hard off-switch
        mode = "off"

    def _f(name: str, default: str) -> float:
        try:
            return float(os.getenv(name, default))
        except ValueError:
            return float(default)

    return VerifierConfig(
        mode=mode,
        reps=max(1, int(os.getenv("JONI_VERIFIER_REPS", "3"))),
        margin_threshold=_f("JONI_VERIFIER_MARGIN", "0.15"),
        disagreement_threshold=_f("JONI_VERIFIER_DISAGREEMENT", "0.20"),
        instability_threshold=_f("JONI_VERIFIER_INSTABILITY", "0.15"),
        evidence_floor=_f("JONI_VERIFIER_EVIDENCE_FLOOR", "0.35"),
        fit_floor=_f("JONI_VERIFIER_FIT_FLOOR", "0.40"),
        max_cost_eur=_f("JONI_VERIFIER_MAX_COST_EUR", "0.05"),
        use_logprobs=os.getenv("JONI_VERIFIER_USE_LOGPROBS", "0") == "1",
    )
