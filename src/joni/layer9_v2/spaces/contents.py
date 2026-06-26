"""Content Space — WHAT is worked on.

Claims, evidence, sources, conflicts, decisions, proposals, invalidated/superseded claims,
semantic clusters, narrative summaries. Content is the body of knowledge. Whether a piece of
content is relevant/trusted to a given user or project is NOT stored here — it lives in overlays.
Content links to methods (``generated_by``), to questions (``answers``/``belongs_to_question``),
and to other content (``supports``/``contradicts``/``derives_from``/``supersedes``/``invalidates``).
"""
from __future__ import annotations

import sqlite3

from . import _base

SPACE = "content"

CONTENT_TYPES = (
    "claim", "evidence", "evidence_link", "source", "conflict", "decision", "proposal",
    "semantic_cluster", "self_model_claim", "narrative_summary", "preference",
)


def put_content(conn: sqlite3.Connection, *, type: str, title: str | None = None,
                payload: dict | None = None, status: str = "active",
                object_id: str | None = None, actor: str | None = None) -> dict:
    return _base.put_object(conn, space=SPACE, type=type, title=title, payload=payload,
                            status=status, object_id=object_id, actor=actor)


def get_content(conn: sqlite3.Connection, object_id: str) -> dict | None:
    obj = _base.get_object(conn, object_id)
    return obj if obj and obj["space"] == SPACE else None


def list_contents(conn: sqlite3.Connection, *, type: str | None = None,
                  status: str | None = None, limit: int | None = None) -> list[dict]:
    return _base.list_objects(conn, space=SPACE, type=type, status=status, limit=limit)
