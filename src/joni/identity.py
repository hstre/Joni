"""Joni - the operative identity.

Wraps Layer 9, the router, the research harvester, the creativity engine and the
voice model into one object that (a) lives over ticks, (b) answers in two views at
once, and (c) persists, so the same identity resumes after a restart. It owns no
hidden state - everything it 'is' sits in ``self.state`` and the append-only ledger.

    joni = Joni(state_path="joni.json")   # resumes if the file exists
    joni.live(ticks=8)                      # weeks, compressed: it evolves, audited
    r = joni.respond("what's your take on privacy?")
    print(r.conversation)                   # the apparent person
    print(r.epistemic)                      # the receipts
    joni.save()                             # lives on
"""

from __future__ import annotations

from pathlib import Path

from . import persistence
from .creativity import CreativityEngine, get_default_creativity
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
        creativity: CreativityEngine | None = None,
        budget: float = 1.0,
        state: Layer9 | None = None,
        harvester: ResearchHarvester | None = None,
        state_path: str | Path | None = None,
        autosave: bool = False,
    ) -> None:
        self.state_path = Path(state_path) if state_path else None
        # Resume from disk if a path was given and a saved identity exists.
        loaded = persistence.load(self.state_path) if self.state_path else None
        self.state = state or loaded or seed_identity()
        self.router = Router(budget=budget)
        self.harvester = harvester or ResearchHarvester()
        self.creativity = creativity or get_default_creativity()
        self.model = model or get_default_model()
        self.autosave = autosave and self.state_path is not None

    # -- persistence -------------------------------------------------------- #
    def save(self, path: str | Path | None = None) -> Path:
        return persistence.save(self.state, path or self.state_path)

    def _maybe_save(self) -> None:
        if self.autosave:
            self.save()

    # -- living over time --------------------------------------------------- #
    def tick(self) -> list[LedgerEvent]:
        """Advance one unit of lived time. Returns this tick's ledger events."""
        events = run_tick(self.state, self.router, self.harvester, self.creativity)
        self._maybe_save()
        return events

    def live(self, *, ticks: int) -> None:
        for _ in range(ticks):
            run_tick(self.state, self.router, self.harvester, self.creativity)
        self._maybe_save()

    # -- the dual view ------------------------------------------------------ #
    def respond(self, prompt: str) -> Response:
        r = _respond(self.state, self.router, self.model, prompt)
        self._maybe_save()
        return r

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
            "creativity": getattr(self.creativity, "name", "unknown"),
        }
