"""Typed links — the ONLY connective tissue between (and within) the three spaces.

A link is a directional, typed edge ``(from_object) --relation--> (to_object)``. The relation
vocabulary is closed (``RELATION_TYPES``) so the graph stays interpretable: a ``supports`` edge
means something specific and is queried differently from a ``uses_method`` edge. Adding a link is a
journalled mutation; the ``ux_links_edge`` unique index keeps (from, to, relation) idempotent.
"""
from __future__ import annotations

import json
import sqlite3

from ..journal import events
from ..storage.sqlite import new_id, now_iso

# Closed relation vocabulary (spec §relation types).
RELATION_TYPES = (
    "supports", "contradicts", "derives_from", "supersedes", "invalidates", "answers", "tests",
    "uses_method", "requires_method", "generated_by", "belongs_to_question", "blocks", "motivates",
    "cites_source",
)


def add_link(
    conn: sqlite3.Connection,
    from_object_id: str,
    relation_type: str,
    to_object_id: str,
    *,
    weight: float = 1.0,
    provenance: dict | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    actor: str | None = None,
) -> dict:
    """Create (or refresh) a typed edge, journalled. Idempotent on (from, to, relation)."""
    if relation_type not in RELATION_TYPES:
        raise ValueError(
            f"unknown relation_type {relation_type!r}; expected one of {RELATION_TYPES}")
    lid = new_id("lnk")
    ts = now_iso()
    conn.execute(
        "INSERT INTO links (id, from_object_id, to_object_id, relation_type, status, weight, "
        "provenance_json, created_at, valid_from, valid_until) "
        "VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?) "
        "ON CONFLICT(from_object_id, to_object_id, relation_type) DO UPDATE SET status='active', "
        "weight=excluded.weight, provenance_json=excluded.provenance_json, "
        "valid_from=excluded.valid_from, valid_until=excluded.valid_until",
        (lid, from_object_id, to_object_id, relation_type, weight,
         json.dumps(provenance or {}, ensure_ascii=False), ts, valid_from, valid_until),
    )
    events.append_event(conn, "link_added", actor=actor, object_id=from_object_id,
                        payload={"to": to_object_id, "relation": relation_type, "weight": weight})
    row = conn.execute(
        "SELECT * FROM links WHERE from_object_id = ? AND to_object_id = ? AND relation_type = ?",
        (from_object_id, to_object_id, relation_type),
    ).fetchone()
    return _link_row(row)


def retire_link(conn: sqlite3.Connection, from_object_id: str, relation_type: str,
                to_object_id: str, *, actor: str | None = None) -> None:
    """Mark an edge inactive (soft delete — the journal keeps the history)."""
    conn.execute(
        "UPDATE links SET status = 'retired' WHERE from_object_id = ? AND to_object_id = ? "
        "AND relation_type = ?", (from_object_id, to_object_id, relation_type))
    events.append_event(conn, "link_retired", actor=actor, object_id=from_object_id,
                        payload={"to": to_object_id, "relation": relation_type})


def out_links(conn: sqlite3.Connection, object_id: str, *, relation_type: str | None = None,
              status: str = "active") -> list[dict]:
    return _query_links(conn, "from_object_id", object_id, relation_type, status)


def in_links(conn: sqlite3.Connection, object_id: str, *, relation_type: str | None = None,
             status: str = "active") -> list[dict]:
    return _query_links(conn, "to_object_id", object_id, relation_type, status)


def _query_links(conn, column, object_id, relation_type, status) -> list[dict]:
    sql = f"SELECT * FROM links WHERE {column} = ?"
    params: list = [object_id]
    if status is not None:
        sql += " AND status = ?"
        params.append(status)
    if relation_type is not None:
        sql += " AND relation_type = ?"
        params.append(relation_type)
    sql += " ORDER BY created_at, id"
    return [_link_row(r) for r in conn.execute(sql, params)]


def _link_row(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["provenance"] = json.loads(d.pop("provenance_json") or "{}")
    return d
