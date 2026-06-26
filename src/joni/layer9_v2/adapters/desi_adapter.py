"""Phase 4 — DESi adapter (READ-ONLY).

DESi is the diagnostician: given the current epistemic state it reports mode, integrity, conflicts.
This adapter projects the v2 store into the plain dict "slice" DESi-style reasoning consumes — it
NEVER writes, and it pulls only from the materialised tables (fast SELECTs, no journal replay).

It is deliberately decoupled from the DESi package: it returns a stable, documented dict rather than
importing DESi types, so the two repos can evolve independently. "DESi diagnoses, the router acts,
Layer-9 stays authority" — this adapter is the read port into that authority.
"""
from __future__ import annotations

import sqlite3

from ..graph import traversal
from ..spaces import _base

# A claim that is contested is still a LIVE claim — both statuses count as "in play" for reasoning.
LIVE_CLAIM_STATUSES = ("active", "contested")


def claim_slice(conn: sqlite3.Connection, *, limit: int | None = None) -> list[dict]:
    """Every live (active or contested) claim with its support/contradiction counts and the methods
    that produced it. The unit DESi reasons over: a claim plus the evidence pressure on it."""
    out = []
    claims = [c for c in _base.list_objects(conn, space="content", type="claim", limit=limit)
              if c["status"] in LIVE_CLAIM_STATUSES]
    for claim in claims:
        cid = claim["id"]
        supports = traversal.supporting_evidence(conn, cid)
        against = traversal.contradicting(conn, cid)
        out.append({
            "id": cid,
            "title": claim["title"],
            "status": claim["status"],
            "support_count": len([s for s in supports if s]),
            "contradiction_count": len([c for c in against if c]),
            "methods": [m["id"] for m in traversal.methods_for(conn, cid)],
        })
    return out


def state_integrity(conn: sqlite3.Connection) -> dict:
    """A coarse integrity read DESi can gate on: counts by space/status + open conflicts."""
    counts: dict[str, dict[str, int]] = {}
    for r in conn.execute("SELECT space, status, COUNT(*) n FROM objects GROUP BY space, status"):
        counts.setdefault(r["space"], {})[r["status"]] = r["n"]
    conflicts = _base.list_objects(conn, space="content", type="conflict", status="active")
    review = _base.list_objects(conn, space="content", status="needs_review")
    return {
        "counts": counts,
        "open_conflicts": len(conflicts),
        "needs_review": len(review),
        "integrity_ok": len(review) == 0,
    }


def desi_report(conn: sqlite3.Connection) -> dict:
    """A DESi-report-shaped read slice: integrity + a bounded claim slice. Read-only."""
    integ = state_integrity(conn)
    return {
        "source": "layer9_v2",
        "integrity": integ,
        "claims": claim_slice(conn, limit=200),
        "mode_hint": "contested" if integ["open_conflicts"] else
                     ("insufficient" if not integ["counts"] else "ok"),
    }
