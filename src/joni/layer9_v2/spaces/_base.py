"""Generic object access shared by the three spaces (method / content / question).

The three spaces are NOT three tables — they are one ``objects`` table partitioned by the ``space``
column, plus thin typed wrappers (``methods``/``contents``/``questions``) that pin ``space`` and
offer space-appropriate helpers. This keeps storage uniform (one link table, one overlay model, one
journal) while the public API still refuses to mix a method with a claim.

Reads are plain SELECTs. Writes go through ``put_object`` / ``set_status``, which — in ONE
transaction — update the materialised row, append a hash-chained journal event, and (for status
changes) record a ``status_history`` row. There is no write path that skips the journal.
"""
from __future__ import annotations

import json
import sqlite3

from ..journal import events
from ..storage.sqlite import content_hash, new_id, now_iso

SPACES = ("method", "content", "question")


def _row_to_object(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["payload"] = json.loads(d.pop("payload_json") or "{}")
    return d


def get_object(conn: sqlite3.Connection, object_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM objects WHERE id = ?", (object_id,)).fetchone()
    return _row_to_object(row) if row else None


def list_objects(
    conn: sqlite3.Connection,
    *,
    space: str | None = None,
    type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """List objects with optional, index-backed filters. No journal replay — a direct SELECT."""
    where, params = [], []
    for col, val in (("space", space), ("type", type), ("status", status)):
        if val is not None:
            where.append(f"{col} = ?")
            params.append(val)
    sql = "SELECT * FROM objects"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at, id"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return [_row_to_object(r) for r in conn.execute(sql, params)]


def put_object(
    conn: sqlite3.Connection,
    *,
    space: str,
    type: str,
    title: str | None = None,
    payload: dict | None = None,
    status: str = "active",
    object_id: str | None = None,
    actor: str | None = None,
) -> dict:
    """Insert a new object (or replace one by id), journalled atomically. Returns the stored object.

    The caller owns the transaction boundary (use ``with conn:``). ``content_hash`` is derived from
    semantic fields only, so re-putting identical content yields the same hash regardless of time.
    """
    if space not in SPACES:
        raise ValueError(f"unknown space {space!r}; expected one of {SPACES}")
    oid = object_id or new_id("obj")
    payload = payload or {}
    ts = now_iso()
    chash = content_hash(space, type, title, payload)
    existing = get_object(conn, oid)
    version = (existing["version"] + 1) if existing else 1
    created_at = existing["created_at"] if existing else ts
    conn.execute(
        "INSERT INTO objects (id, space, type, title, payload_json, status, created_at, "
        "updated_at, version, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET space=excluded.space, type=excluded.type, "
        "title=excluded.title, payload_json=excluded.payload_json, status=excluded.status, "
        "updated_at=excluded.updated_at, version=excluded.version, "
        "content_hash=excluded.content_hash",
        (oid, space, type, title, _dumps(payload), status, created_at, ts, version, chash),
    )
    events.append_event(
        conn, "object_created" if not existing else "object_updated",
        actor=actor, object_id=oid,
        payload={"space": space, "type": type, "version": version, "content_hash": chash},
    )
    return get_object(conn, oid)  # type: ignore[return-value]


def set_status(
    conn: sqlite3.Connection,
    object_id: str,
    new_status: str,
    *,
    reason: str | None = None,
    evidence_ref: str | None = None,
    actor: str | None = None,
) -> dict:
    """Transition status, recording a status_history row + a journal event atomically."""
    obj = get_object(conn, object_id)
    if obj is None:
        raise KeyError(object_id)
    old = obj["status"]
    ts = now_iso()
    conn.execute(
        "UPDATE objects SET status = ?, updated_at = ?, version = version + 1 WHERE id = ?",
        (new_status, ts, object_id))
    conn.execute(
        "INSERT INTO status_history (id, object_id, old_status, new_status, reason, "
        "evidence_ref, actor, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id("sh"), object_id, old, new_status, reason, evidence_ref, actor, ts),
    )
    events.append_event(
        conn, "status_changed", actor=actor, object_id=object_id,
        payload={"old": old, "new": new_status, "reason": reason},
    )
    return get_object(conn, object_id)  # type: ignore[return-value]


def _dumps(payload: dict) -> str:
    # Stored compactly but NOT canonicalised — the canonical form is reserved for hashing.
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
