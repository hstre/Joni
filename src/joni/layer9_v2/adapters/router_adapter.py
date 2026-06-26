"""Phase 5 — router adapter (READ-ONLY).

The router decides what to do next; to do that it needs a compact, current view of the open work.
This adapter projects the v2 store into a routing slice — open questions, contested claims, items
needing review, optionally narrowed by a project overlay — and writes NOTHING. It exists so the
router can read v2 without coupling to its schema, and so a project's overlay (its active subgraph)
shapes what the router sees without mutating any global object.
"""
from __future__ import annotations

import sqlite3

from ..spaces import _base


def open_questions(conn: sqlite3.Connection, *, limit: int | None = None) -> list[dict]:
    qs = _base.list_objects(conn, space="question", status="open", limit=limit)
    return [{"id": q["id"], "type": q["type"], "title": q["title"]} for q in qs]


def contested_claims(conn: sqlite3.Connection, *, limit: int | None = None) -> list[dict]:
    """Claims with at least one active incoming contradiction — the router's hotspots. A contested
    claim is precisely one to surface, so accept active OR contested status."""
    rows = conn.execute(
        "SELECT o.id, o.title FROM objects o "
        "JOIN links l ON l.to_object_id = o.id AND l.relation_type = 'contradicts' "
        "AND l.status = 'active' "
        "WHERE o.space = 'content' AND o.type = 'claim' "
        "AND o.status IN ('active', 'contested') "
        "GROUP BY o.id, o.title ORDER BY COUNT(l.id) DESC"
        + (f" LIMIT {int(limit)}" if limit else ""),
    ).fetchall()
    return [{"id": r["id"], "title": r["title"]} for r in rows]


def _project_filter(conn: sqlite3.Connection, project_id: str) -> set[str]:
    """The set of object ids a project's overlay marks active (its working subgraph)."""
    return {r["object_id"] for r in conn.execute(
        "SELECT object_id FROM project_overlays WHERE project_id = ? AND active = 1",
        (project_id,))}


def routing_slice(conn: sqlite3.Connection, *, project_id: str | None = None) -> dict:
    """A compact view for the router: open questions, contested claims, review backlog. If
    ``project_id`` is given, restrict to that project's active overlay subgraph (read-only)."""
    questions = open_questions(conn, limit=100)
    contested = contested_claims(conn, limit=100)
    review = _base.list_objects(conn, space="content", status="needs_review", limit=100)
    if project_id is not None:
        active = _project_filter(conn, project_id)
        questions = [q for q in questions if q["id"] in active]
        contested = [c for c in contested if c["id"] in active]
        review = [r for r in review if r["id"] in active]
    return {
        "source": "layer9_v2",
        "project_id": project_id,
        "open_questions": questions,
        "contested_claims": contested,
        "needs_review": [{"id": r["id"], "title": r["title"]} for r in review],
        "next_action_hint": "resolve_conflict" if contested else
                            ("answer_question" if questions else
                             ("triage_review" if review else "idle")),
    }
