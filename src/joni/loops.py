"""Research harvester + improvement loop - how Joni changes over time.

A ``tick`` is one unit of lived time. Every tick is deterministic and fully audited:
it harvests a finding, detects contradictions, resolves them (the justified opinion
changes), advances a goal, and periodically forms a preference, starts or abandons a
project, and proposes a self-improvement. Run many ticks and you get an identity that
visibly evolves - drops ideas, picks up new ones, makes progress - while every step
remains a ledger event you can point at.

The "research" is a deterministic, seeded bank, not a live model: the demonstrator's
claim is about *structure*, so its inputs are fixed and replayable. (A real Research
Harvester would feed findings in here; the loop downstream is unchanged.)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .conflict import detect_conflicts, weaker_claim
from .models import ClaimStatus, LedgerEvent, ProjectStatus
from .operators import (
    abandon_project,
    advance_goal,
    assert_claim,
    form_preference,
    resolve_conflict,
    start_project,
)
from .router import Router
from .state import Layer9

# A deterministic bank of findings per topic. Some are framed to contradict an
# earlier belief (overlapping wording, opposite polarity) so opinion change is real.
DEFAULT_FINDINGS: dict[str, list[tuple[str, float]]] = {
    "privacy": [
        ("Local-first models do not keep data private without an audit ledger", 0.78),
        ("Running inference on-box keeps prompts off third-party servers", 0.7),
    ],
    "routing": [
        ("Cheap local models handle most turns without quality loss", 0.72),
        ("Escalating only hard turns to an API cuts cost sharply", 0.7),
    ],
    "memory": [
        ("Append-only episodic memory beats summarisation for continuity", 0.74),
        ("Recall by token overlap is enough without embeddings for small state", 0.62),
    ],
    "drift": [
        ("Unbounded self-modification drifts without an explicit ledger", 0.8),
        ("Bounded operators make every change reviewable", 0.71),
    ],
}


@dataclass
class ResearchHarvester:
    """Feeds deterministic findings, one per topic per visit. Replay-stable."""

    findings: dict[str, list[tuple[str, float]]] = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_FINDINGS.items()}
    )
    _cursor: dict[str, int] = field(default_factory=dict)

    def next_for(self, topic: str) -> tuple[str, float] | None:
        items = self.findings.get(topic)
        if not items:
            return None
        i = self._cursor.get(topic, 0)
        if i >= len(items):
            return None
        self._cursor[topic] = i + 1
        return items[i]


def run_tick(state: Layer9, router: Router, harvester: ResearchHarvester) -> list[LedgerEvent]:
    """Advance the identity by one tick. Returns the ledger events produced."""
    state.tick += 1
    start_index = len(state.ledger)

    topics = state.topics() or list(DEFAULT_FINDINGS.keys())
    topic = topics[(state.tick - 1) % len(topics)]

    # 1. Research harvest -> a new claim (the language of belief is fixed data here).
    finding = harvester.next_for(topic)
    if finding is not None:
        text, support = finding
        route = router.route(needs_language=False)
        assert_claim(state, text, topic, support=support, status=ClaimStatus.ACTIVE,
                     reviewed_by=route.model_name)

    # 2. Detect contradictions the new claim may have created.
    detect_conflicts(state)

    # 3. Resolve every open conflict - the justified opinion changes. A contradiction
    #    is a "hard" judgement, so it is routed to a capable reviewer and charged.
    for conflict in list(state.open_conflicts()):
        loser = weaker_claim(state, conflict)
        route = router.route(needs_language=True, hard=True)
        router.charge(route)
        resolve_conflict(state, conflict.id, reject=loser, reviewed_by=route.model_name,
                         cost=route.cost)

    # 4. Advance the highest-priority active goal a little.
    goals = sorted(state.active_goals(), key=lambda g: (-g.priority, g.id))
    if goals:
        advance_goal(state, goals[0].id, by=0.2)

    # 5. Every 3rd tick, crystallise a preference from a confirmed/active claim.
    if state.tick % 3 == 0:
        live = sorted(state.active_claims(), key=lambda c: (-c.support, c.id))
        if live:
            top = live[0]
            form_preference(state, top.topic, "prefers", strength=top.support,
                            formed_from=(top.id,))

    # 6. Every 4th tick, start a project on the current strongest topic (creativity /
    #    self-proposed improvement); abandon projects whose topic lost all support.
    if state.tick % 4 == 0 and topics:
        start_project(state, f"Deepen work on {topic}", topic)
    for project in list(state.active_projects()):
        supported = any(
            c.status in {ClaimStatus.ACTIVE, ClaimStatus.CONFIRMED} and c.topic == project.topic
            for c in state.claims.values()
        )
        if not supported and project.status is ProjectStatus.ACTIVE:
            abandon_project(state, project.id)

    return state.ledger[start_index:]


def live(state: Layer9, router: Router, harvester: ResearchHarvester, *, ticks: int) -> None:
    """Run many ticks - the weeks-long evolving instance, compressed."""
    for _ in range(ticks):
        run_tick(state, router, harvester)
