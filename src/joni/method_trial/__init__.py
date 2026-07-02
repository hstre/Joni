"""Method-transfer measurement apparatus — Stage 0 (pre-registration) + Stage 1 (micro battery).

Offline, non-core, no model, never imported by the autonomous loop. See
``docs/METHOD_TRIAL_MEASUREMENT_PLAN.md`` (v2). Stage 2+ (the actual measured runs) are budget-gated
and not built here — this is the deterministic, zero-cost foundation the plan gates everything on.
"""
from . import checkers, contract, gold_micro_v1, preregistration

__all__ = ["checkers", "contract", "gold_micro_v1", "preregistration"]
