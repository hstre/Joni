"""Hash-chained journal: every event carries ``prev_hash`` and an ``event_hash`` computed over
``prev_hash + canonical(core)``. Tamper-evidence: changing any past event breaks every later hash.
"""
from __future__ import annotations

import hashlib
import json

from ..storage.sqlite import canonical_json

GENESIS = "0" * 64


def event_core(row_or_dict) -> dict:
    """The canonical, hashed core of an event (everything that defines it, minus the hash itself).
    Accepts a sqlite3.Row or a dict so the writer and the verifier hash exactly the same shape."""
    g = (lambda k: row_or_dict[k]) if not isinstance(row_or_dict, dict) else row_or_dict.get
    payload = g("payload")
    if isinstance(payload, str):
        payload = json.loads(payload)
    elif payload is None:
        payload = json.loads(g("payload_json")) if _has(row_or_dict, "payload_json") else {}
    return {"id": g("id"), "tick": g("tick"), "event_type": g("event_type"), "actor": g("actor"),
            "object_id": g("object_id"), "payload": payload, "created_at": g("created_at")}


def _has(row, key) -> bool:
    try:
        return row[key] is not None or True
    except (KeyError, IndexError):
        return False


def event_hash(prev_hash: str, core: dict) -> str:
    return hashlib.sha256((prev_hash + canonical_json(core)).encode("utf-8")).hexdigest()


def head_hash(conn) -> str:
    """The hash of the most recent event, or GENESIS for an empty journal."""
    row = conn.execute(
        "SELECT event_hash FROM journal_events ORDER BY tick DESC, rowid DESC LIMIT 1").fetchone()
    return row[0] if row else GENESIS


def verify_chain(conn) -> tuple[bool, int | None]:
    """Scan the journal in order, recomputing each hash. Returns (ok, first_bad_tick)."""
    prev = GENESIS
    for r in conn.execute("SELECT * FROM journal_events ORDER BY tick, rowid"):
        core = {"id": r["id"], "tick": r["tick"], "event_type": r["event_type"],
                "actor": r["actor"], "object_id": r["object_id"],
                "payload": json.loads(r["payload_json"]), "created_at": r["created_at"]}
        if r["prev_hash"] != prev or event_hash(prev, core) != r["event_hash"]:
            return False, r["tick"]
        prev = r["event_hash"]
    return True, None
