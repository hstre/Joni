"""Joni - a DESi-based operative identity.

From the outside: memory, continuity, preferences, projects, goals, and reasoned
changes of mind - it reads like a person. Inside: only controlled state and
deterministic operators, every move an append-only ledger event.

    We did not build a person. We built the *impression* of one - and we show,
    line by line, exactly how it is produced.

Two views, always together:
  * Conversation View - the seemingly autonomous figure.
  * Epistemic View    - the claim, goal, memory, operator and ledger event behind it.
"""

from __future__ import annotations

from .identity import Joni
from .loops import ResearchHarvester, run_tick
from .models import (
    Claim,
    ClaimStatus,
    EpistemicTrace,
    Goal,
    LedgerEvent,
    ModelTier,
    Operator,
    Response,
    Trigger,
)
from .router import Router
from .seed import seed_identity
from .state import Layer9

__all__ = [
    "Joni",
    "Layer9",
    "Router",
    "ResearchHarvester",
    "run_tick",
    "seed_identity",
    "Response",
    "EpistemicTrace",
    "Claim",
    "Goal",
    "LedgerEvent",
    "ClaimStatus",
    "Trigger",
    "Operator",
    "ModelTier",
]

__version__ = "0.1.0"
