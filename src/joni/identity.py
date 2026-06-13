"""Joni - the operative identity.

Wraps Layer 9, the router, the research harvester and the voice model into one
object that (a) lives over ticks and (b) answers in two views at once. It owns no
hidden state - everything it 'is' sits in ``self.state`` and the append-only ledger.

    joni = Joni()
    joni.live(ticks=8)                 # weeks, compressed: it evolves, audited
    r = joni.respond("what's your take on privacy?")
    print(r.conversation)              # the apparent person
    print(r.epistemic)                 # the receipts
"""

from __future__ import annotations

from .loops import ResearchHarvester, run_tick
from .model_client import ModelClient, get_default_model
from .models import LedgerEvent, Response
from .renderer import respond as _respond
from .router import Router
from .seed import seed_identity
from .state import Layer9


class Joni:
    def __init__(
        self,
        *,
        model: ModelClient | None = None,
        budget: float = 1.0,
        state: Layer9 | None = None,
        harvester: ResearchHarvester | None = None,
    ) -> None:
        self.state = state or seed_identity()
        self.router = Router(budget=budget)
        self.harvester = harvester or ResearchHarvester()
        self.model = model or get_default_model()

    # -- living over time --------------------------------------------------- #
    def tick(self) -> list[LedgerEvent]:
        """Advance one unit of lived time. Returns this tick's ledger events."""
        return run_tick(self.state, self.router, self.harvester)

    def live(self, *, ticks: int) -> None:
        for _ in range(ticks):
            self.tick()

    # -- the dual view ------------------------------------------------------ #
    def respond(self, prompt: str) -> Response:
        return _respond(self.state, self.router, self.model, prompt)

    # -- introspection ------------------------------------------------------ #
    def snapshot(self) -> dict:
        s = self.state
        return {
            "name": s.name,
            "tick": s.tick,
            "claims": {"total": len(s.claims), "active": len(s.active_claims())},
            "goals": len(s.active_goals()),
            "projects": len(s.active_projects()),
            "preferences": len(s.preferences),
            "memory": len(s.memory),
            "open_conflicts": len(s.open_conflicts()),
            "ledger_events": len(s.ledger),
            "spend": s.total_spend(),
            "budget_remaining": self.router.remaining(),
            "topics": s.topics(),
        }
