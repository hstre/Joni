"""Persistence - how Joni lives on across restarts.

The whole of Layer 9 (claims with their full status history, goals, preferences,
projects, episodic memory, conflicts, the append-only ledger, the id counters and the
tick) is serialised to a single JSON document and reloaded verbatim. Because ids are
sequential and there is no PRNG, a reloaded identity is byte-for-byte the same self
that was saved - it simply continues.

This is what turns the "weeks-long local instance" from a metaphor into a file: run
``joni.live(...)`` today, save, and the same identity - same memories, same rejected
ideas, same goals in progress - resumes tomorrow.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    Claim,
    ClaimStatus,
    Conflict,
    Goal,
    GoalStatus,
    Horizon,
    LedgerEvent,
    MemoryEpisode,
    Operator,
    Preference,
    Project,
    ProjectStatus,
    Transition,
    Trigger,
)
from .state import Layer9

SCHEMA = 1


def default_state_path() -> Path:
    """Where a persisted identity lives. Override with ``JONI_STATE``."""
    import os

    env = os.getenv("JONI_STATE")
    return Path(env) if env else Path.home() / ".joni" / "state.json"


# --------------------------------------------------------------------------- #
# Serialise
# --------------------------------------------------------------------------- #


def _transition(t: Transition) -> dict:
    return {
        "from_status": t.from_status.value, "to_status": t.to_status.value,
        "trigger": t.trigger.value, "operator": t.operator.value, "tick": t.tick,
        "reviewed_by": t.reviewed_by, "ledger_id": t.ledger_id,
    }


def to_dict(state: Layer9) -> dict:
    return {
        "schema": SCHEMA,
        "name": state.name,
        "tick": state.tick,
        "counters": dict(state._counters),
        "claims": [
            {
                "id": c.id, "text": c.text, "topic": c.topic, "status": c.status.value,
                "support": c.support, "created_tick": c.created_tick,
                "last_changed_tick": c.last_changed_tick,
                "history": [_transition(t) for t in c.history],
            }
            for c in state.claims.values()
        ],
        "goals": [
            {"id": g.id, "text": g.text, "horizon": g.horizon.value, "status": g.status.value,
             "priority": g.priority, "progress": g.progress, "created_tick": g.created_tick}
            for g in state.goals.values()
        ],
        "preferences": [
            {"id": p.id, "subject": p.subject, "stance": p.stance, "strength": p.strength,
             "formed_from": list(p.formed_from), "created_tick": p.created_tick}
            for p in state.preferences.values()
        ],
        "projects": [
            {"id": p.id, "title": p.title, "topic": p.topic, "status": p.status.value,
             "created_tick": p.created_tick}
            for p in state.projects.values()
        ],
        "memory": [
            {"id": m.id, "tick": m.tick, "kind": m.kind, "summary": m.summary,
             "refs": list(m.refs)}
            for m in state.memory
        ],
        "conflicts": [
            {"id": x.id, "claim_a": x.claim_a, "claim_b": x.claim_b, "kind": x.kind,
             "tick": x.tick, "resolved": x.resolved}
            for x in state.conflicts.values()
        ],
        "ledger": [
            {"id": e.id, "tick": e.tick, "operator": e.operator.value, "summary": e.summary,
             "refs": list(e.refs), "reviewed_by": e.reviewed_by, "cost": e.cost}
            for e in state.ledger
        ],
    }


# --------------------------------------------------------------------------- #
# Deserialise
# --------------------------------------------------------------------------- #


def from_dict(d: dict) -> Layer9:
    state = Layer9(name=d.get("name", "Joni"), tick=int(d.get("tick", 0)))
    state._counters = {k: int(v) for k, v in d.get("counters", {}).items()}

    for c in d.get("claims", []):
        claim = Claim(
            id=c["id"], text=c["text"], topic=c["topic"], status=ClaimStatus(c["status"]),
            support=c["support"], created_tick=c["created_tick"],
            last_changed_tick=c["last_changed_tick"],
            history=[
                Transition(
                    from_status=ClaimStatus(t["from_status"]),
                    to_status=ClaimStatus(t["to_status"]),
                    trigger=Trigger(t["trigger"]), operator=Operator(t["operator"]),
                    tick=t["tick"], reviewed_by=t["reviewed_by"], ledger_id=t["ledger_id"],
                )
                for t in c.get("history", [])
            ],
        )
        state.claims[claim.id] = claim

    for g in d.get("goals", []):
        state.goals[g["id"]] = Goal(
            id=g["id"], text=g["text"], horizon=Horizon(g["horizon"]),
            status=GoalStatus(g["status"]), priority=g["priority"], progress=g["progress"],
            created_tick=g["created_tick"],
        )

    for p in d.get("preferences", []):
        state.preferences[p["id"]] = Preference(
            id=p["id"], subject=p["subject"], stance=p["stance"], strength=p["strength"],
            formed_from=tuple(p.get("formed_from", ())), created_tick=p["created_tick"],
        )

    for p in d.get("projects", []):
        state.projects[p["id"]] = Project(
            id=p["id"], title=p["title"], topic=p["topic"],
            status=ProjectStatus(p["status"]), created_tick=p["created_tick"],
        )

    for m in d.get("memory", []):
        state.memory.append(MemoryEpisode(
            id=m["id"], tick=m["tick"], kind=m["kind"], summary=m["summary"],
            refs=tuple(m.get("refs", ())),
        ))

    for x in d.get("conflicts", []):
        state.conflicts[x["id"]] = Conflict(
            id=x["id"], claim_a=x["claim_a"], claim_b=x["claim_b"], kind=x["kind"],
            tick=x["tick"], resolved=x["resolved"],
        )

    for e in d.get("ledger", []):
        state.ledger.append(LedgerEvent(
            id=e["id"], tick=e["tick"], operator=Operator(e["operator"]), summary=e["summary"],
            refs=tuple(e.get("refs", ())), reviewed_by=e["reviewed_by"], cost=e["cost"],
        ))

    return state


# --------------------------------------------------------------------------- #
# File I/O
# --------------------------------------------------------------------------- #


def save(state: Layer9, path: Path | str | None = None) -> Path:
    path = Path(path) if path else default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_dict(state), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(path: Path | str | None = None) -> Layer9 | None:
    path = Path(path) if path else default_state_path()
    if not path.exists():
        return None
    return from_dict(json.loads(path.read_text(encoding="utf-8")))
