"""Joni - HTTP/API surface (FastAPI).

A thin port over the identity. Its whole job is to serve the two views together:
every ``/api/respond`` returns the Conversation View *and* the Epistemic View, and
the ledger/state endpoints let the UI show the receipts behind any utterance.

    uvicorn joni.api:app --reload      # or: joni-serve

Endpoints:
    GET  /              -> the dual-pane UI
    GET  /health        -> liveness
    GET  /api/state     -> snapshot + claims/goals/projects/preferences
    GET  /api/ledger    -> the append-only audit ledger
    POST /api/respond   -> {prompt} -> conversation + epistemic trace
    POST /api/tick      -> advance one tick; return the new events + snapshot
    POST /api/live      -> {ticks} -> advance many ticks; return snapshot
    POST /api/reset     -> reseed the identity
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .identity import Joni
from .models import LedgerEvent

app = FastAPI(
    title="Joni",
    description="A DESi-based operative identity: appears like a person, stays fully "
    "dissolvable into controlled state.",
    version="0.1.0",
)

_WEB = Path(__file__).parent / "web"
_JONI = Joni()


# --------------------------------------------------------------------------- #
# Serialisation
# --------------------------------------------------------------------------- #


def _event_dict(e: LedgerEvent) -> dict:
    return {
        "id": e.id, "tick": e.tick, "operator": e.operator.value, "summary": e.summary,
        "refs": list(e.refs), "reviewed_by": e.reviewed_by, "cost": e.cost,
    }


def _state_dict() -> dict:
    s = _JONI.state
    return {
        "snapshot": _JONI.snapshot(),
        "claims": [
            {"id": c.id, "topic": c.topic, "status": c.status.value, "support": c.support,
             "text": c.text, "changes": len(c.history)}
            for c in sorted(s.claims.values(), key=lambda c: c.id)
        ],
        "goals": [
            {"id": g.id, "text": g.text, "horizon": g.horizon.value, "status": g.status.value,
             "priority": g.priority, "progress": g.progress}
            for g in sorted(s.goals.values(), key=lambda g: g.id)
        ],
        "projects": [
            {"id": p.id, "title": p.title, "topic": p.topic, "status": p.status.value}
            for p in sorted(s.projects.values(), key=lambda p: p.id)
        ],
        "preferences": [
            {"id": p.id, "subject": p.subject, "stance": p.stance, "strength": p.strength,
             "formed_from": list(p.formed_from)}
            for p in sorted(s.preferences.values(), key=lambda p: p.id)
        ],
    }


def _trace_dict(e) -> dict:
    return {
        "claims": list(e.claims),
        "goals": list(e.goals),
        "memory": list(e.memory),
        "operator": e.operator.value if e.operator else None,
        "trigger": e.trigger.value if e.trigger else None,
        "reviewed_by": e.reviewed_by,
        "ledger_event": e.ledger_event,
        "routed_to": e.routed_to.value,
    }


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #


class RespondRequest(BaseModel):
    prompt: str = Field(..., min_length=1)


class LiveRequest(BaseModel):
    ticks: int = Field(1, ge=1, le=200)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_WEB / "index.html")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "joni", "version": app.version}


@app.get("/api/state")
def state() -> dict:
    return _state_dict()


@app.get("/api/ledger")
def ledger() -> dict:
    return {"ledger": [_event_dict(e) for e in _JONI.state.ledger]}


@app.post("/api/respond")
def respond(req: RespondRequest) -> dict:
    r = _JONI.respond(req.prompt)
    return {
        "conversation": r.conversation,
        "epistemic": _trace_dict(r.epistemic),
        "snapshot": _JONI.snapshot(),
    }


@app.post("/api/tick")
def tick() -> dict:
    events = _JONI.tick()
    return {"events": [_event_dict(e) for e in events], "snapshot": _JONI.snapshot()}


@app.post("/api/live")
def live(req: LiveRequest) -> dict:
    _JONI.live(ticks=req.ticks)
    return {"snapshot": _JONI.snapshot()}


@app.post("/api/reset")
def reset() -> dict:
    global _JONI
    _JONI = Joni()
    return {"snapshot": _JONI.snapshot()}


def serve() -> None:  # pragma: no cover - entry point, exercised manually
    """``joni-serve`` - run the app with uvicorn."""
    import os

    import uvicorn

    uvicorn.run(
        "joni.api:app",
        host=os.getenv("JONI_HOST", "127.0.0.1"),
        port=int(os.getenv("JONI_PORT", "8000")),
        reload=bool(os.getenv("JONI_RELOAD")),
    )
