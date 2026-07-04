"""Constitution — Joni's normative value root (docs/CONSTITUTION.md).

The layer above the personal store and Layer 9: a deterministic checker + priority order over
proposed actions/outputs, not a derivation machine. Phase 1: 10 principles + a wired Tier-0 gate.
"""
from .gate import (
    PRINCIPLES,
    Constitution,
    Decision,
    Principle,
    Proposal,
    Verdict,
    check,
)

__all__ = [
    "PRINCIPLES",
    "Constitution",
    "Decision",
    "Principle",
    "Proposal",
    "Verdict",
    "check",
]
