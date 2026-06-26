"""Periodic snapshots of the materialised state.

A snapshot is a cheap integrity checkpoint: a hash over the current ``objects`` + ``links`` rows at
a given tick, plus the schema version. It is NOT a copy of the data (the SQLite file already is the
data) and NOT something we replay — it lets a reader confirm "the live tables still match the
known-good state I checkpointed at tick T" without walking the whole journal. Snapshotting is
O(rows), taken periodically, never on the hot path.
"""
from __future__ import annotations

import hashlib
import sqlite3

from .sqlite import canonical_json, new_id, now_iso, schema_version


def _state_digest(conn: sqlite3.Connection) -> str:
    """A deterministic hash over the semantic columns of objects + links (ordered by id)."""
    h = hashlib.sha256()
    for r in conn.execute("SELECT id, space, type, status, content_hash, version "
                          "FROM objects ORDER BY id"):
        h.update(canonical_json(dict(r)).encode("utf-8"))
    for r in conn.execute("SELECT id, from_object_id, to_object_id, relation_type, status, weight "
                          "FROM links ORDER BY id"):
        h.update(canonical_json(dict(r)).encode("utf-8"))
    return h.hexdigest()


def take_snapshot(conn: sqlite3.Connection, *, tick: int, snapshot_type: str = "periodic") -> dict:
    """Record a checkpoint of current state at ``tick``. Caller owns the transaction."""
    payload_hash = _state_digest(conn)
    sid = new_id("snap")
    sv = schema_version(conn)
    conn.execute(
        "INSERT INTO snapshots (id, tick, snapshot_type, payload_hash, created_at, schema_version) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (sid, tick, snapshot_type, payload_hash, now_iso(), sv),
    )
    return {"id": sid, "tick": tick, "snapshot_type": snapshot_type,
            "payload_hash": payload_hash, "schema_version": sv}


def latest_snapshot(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM snapshots ORDER BY tick DESC, rowid DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def verify_against(conn: sqlite3.Connection, snapshot_id: str) -> bool:
    """True iff current state still hashes to the recorded snapshot payload_hash."""
    row = conn.execute("SELECT payload_hash FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    if row is None:
        raise KeyError(snapshot_id)
    return row[0] == _state_digest(conn)
