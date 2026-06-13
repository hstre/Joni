"""Layer 9 - the identity's whole controlled state.

One object holds everything the outside reads as a person: claims, goals,
preferences, projects, autobiographical memory, open conflicts, and the append-only
audit ledger. Plus the sequential id counters and the current ``tick``.

Nothing here is random. Ids are handed out by counters in a deterministic order, so
a whole life history is replayable (C-1, C-2, … exactly as DESi assigns them). The
ledger is append-only - the receipts are never rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    Claim,
    Conflict,
    Goal,
    LedgerEvent,
    MemoryEpisode,
    Operator,
    Preference,
    Project,
)


@dataclass
class Layer9:
    """The deterministic state of one operative identity."""

    name: str = "Joni"
    tick: int = 0

    claims: dict[str, Claim] = field(default_factory=dict)
    goals: dict[str, Goal] = field(default_factory=dict)
    preferences: dict[str, Preference] = field(default_factory=dict)
    projects: dict[str, Project] = field(default_factory=dict)
    memory: list[MemoryEpisode] = field(default_factory=list)
    conflicts: dict[str, Conflict] = field(default_factory=dict)
    ledger: list[LedgerEvent] = field(default_factory=list)

    # Monotonic id counters - the source of C-/G-/L9- ids. Deterministic, no PRNG.
    _counters: dict[str, int] = field(
        default_factory=lambda: {
            "C": 0, "G": 0, "PR": 0, "P": 0, "M": 0, "X": 0, "L9": 0
        }
    )

    # -- id minting --------------------------------------------------------- #
    def next_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}-{self._counters[prefix]}"

    # -- ledger (append-only) ----------------------------------------------- #
    def record(
        self,
        operator: Operator,
        summary: str,
        *,
        refs: tuple[str, ...] = (),
        reviewed_by: str = "deterministic",
        cost: float = 0.0,
    ) -> LedgerEvent:
        event = LedgerEvent(
            id=self.next_id("L9"),
            tick=self.tick,
            operator=operator,
            summary=summary,
            refs=refs,
            reviewed_by=reviewed_by,
            cost=cost,
        )
        self.ledger.append(event)
        return event

    # -- convenient read views ---------------------------------------------- #
    def active_claims(self) -> list[Claim]:
        from .models import ClaimStatus

        live = {ClaimStatus.ACTIVE, ClaimStatus.CONFIRMED}
        return [c for c in self.claims.values() if c.status in live]

    def claims_on(self, topic: str) -> list[Claim]:
        return [c for c in self.claims.values() if c.topic == topic]

    def active_goals(self) -> list[Goal]:
        from .models import GoalStatus

        return [g for g in self.goals.values() if g.status is GoalStatus.ACTIVE]

    def active_projects(self) -> list[Project]:
        from .models import ProjectStatus

        return [p for p in self.projects.values() if p.status is ProjectStatus.ACTIVE]

    def open_conflicts(self) -> list[Conflict]:
        return [x for x in self.conflicts.values() if not x.resolved]

    def topics(self) -> list[str]:
        """The identity's current subject matter, by claim count then name."""
        counts: dict[str, int] = {}
        for c in self.claims.values():
            counts[c.topic] = counts.get(c.topic, 0) + 1
        return sorted(counts, key=lambda t: (-counts[t], t))

    def total_spend(self) -> float:
        return round(sum(e.cost for e in self.ledger), 4)
