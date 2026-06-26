"""Append-only journal writer.

Every mutation of the materialised state (an object created, a status changed, a link added) must
also append exactly one journal event here, INSIDE the caller's transaction. The event is linked
to its predecessor by ``prev_hash`` and sealed with ``event_hash`` (see ``hashchain``), giving a
tamper-evident chain. The journal is the audit source of truth; the ``objects``/``links`` tables
are the fast materialised view. We never replay the journal on startup — but we can always verify
it.
"""
from __future__ import annotations

import sqlite3

from ..storage.sqlite import canonical_json, new_id, now_iso
from . import hashchain


def next_tick(conn: sqlite3.Connection) -> int:
    """The next monotonic tick = (max tick so far) + 1, or 0 for an empty journal."""
    row = conn.execute("SELECT MAX(tick) FROM journal_events").fetchone()
    return 0 if row is None or row[0] is None else int(row[0]) + 1


def append_event(
    conn: sqlite3.Connection,
    event_type: str,
    *,
    actor: str | None = None,
    object_id: str | None = None,
    payload: dict | None = None,
    tick: int | None = None,
) -> dict:
    """Append one event to the hash chain. The CALLER owns the transaction (so the event and the
    state change it records commit or roll back together). Returns the stored event as a dict.

    The hashed core is exactly ``{id, tick, event_type, actor, object_id, payload, created_at}`` —
    identical to what ``hashchain.verify_chain`` recomputes. Keep the two in lockstep.
    """
    eid = new_id("evt")
    tk = next_tick(conn) if tick is None else tick
    created_at = now_iso()
    payload = payload or {}
    prev = hashchain.head_hash(conn)
    core = {"id": eid, "tick": tk, "event_type": event_type, "actor": actor,
            "object_id": object_id, "payload": payload, "created_at": created_at}
    ehash = hashchain.event_hash(prev, core)
    conn.execute(
        "INSERT INTO journal_events "
        "(id, tick, event_type, actor, object_id, payload_json, prev_hash, event_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (eid, tk, event_type, actor, object_id, canonical_json(payload), prev, ehash, created_at),
    )
    return {**core, "prev_hash": prev, "event_hash": ehash}
