"""Router and budget control - which tier handles a unit of cognition, at what cost.

Deterministic. Cheapest capable tier first; a strong external API model is used only
when a task genuinely needs it *and* the budget allows. Every routed operation is
charged, and the charge rides along into the ledger - so "Joni used a strong model
here" is an audited fact with a price, not a vibe.

The model *name* a route resolves to (e.g. ``granite-micro``, ``deepseek-chat``) is
what appears as ``reviewed_by`` on a ledger event and in the epistemic trace.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ModelTier


@dataclass(frozen=True)
class ModelSpec:
    name: str
    tier: ModelTier
    cost: float            # charged per routed call


# Local tiers are free (they run on-box); only the external API costs budget.
REGISTRY: dict[ModelTier, ModelSpec] = {
    ModelTier.DETERMINISTIC: ModelSpec("deterministic", ModelTier.DETERMINISTIC, 0.0),
    ModelTier.LOCAL_SMALL: ModelSpec("granite-micro", ModelTier.LOCAL_SMALL, 0.0),
    ModelTier.LOCAL_SPECIALIST: ModelSpec("local-specialist", ModelTier.LOCAL_SPECIALIST, 0.0),
    ModelTier.EXTERNAL_API: ModelSpec("deepseek-chat", ModelTier.EXTERNAL_API, 0.002),
}


@dataclass
class RouteDecision:
    tier: ModelTier
    model_name: str
    cost: float
    reason: str


class Router:
    """Deterministic tier selection under a budget."""

    def __init__(self, budget: float = 1.0) -> None:
        self.budget = budget
        self.spent = 0.0

    def remaining(self) -> float:
        return round(self.budget - self.spent, 4)

    def route(self, *, needs_language: bool, hard: bool = False) -> RouteDecision:
        """Pick a tier.

        * No language needed -> pure rules (DETERMINISTIC), free.
        * Language, ordinary -> a local small model, free.
        * Language, hard, and budget available -> the external API model.
        * Language, hard, but out of budget -> degrade to the local specialist.
        """
        if not needs_language:
            return self._decide(ModelTier.DETERMINISTIC, "no language required")
        if not hard:
            return self._decide(ModelTier.LOCAL_SMALL, "routine phrasing handled locally")
        if self.remaining() >= REGISTRY[ModelTier.EXTERNAL_API].cost:
            return self._decide(ModelTier.EXTERNAL_API, "hard task within budget")
        return self._decide(ModelTier.LOCAL_SPECIALIST, "hard task but budget exhausted")

    def charge(self, decision: RouteDecision) -> float:
        self.spent = round(self.spent + decision.cost, 4)
        return decision.cost

    @staticmethod
    def _decide(tier: ModelTier, reason: str) -> RouteDecision:
        spec = REGISTRY[tier]
        return RouteDecision(tier=tier, model_name=spec.name, cost=spec.cost, reason=reason)
