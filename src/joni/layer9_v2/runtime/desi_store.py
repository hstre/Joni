"""SQLite persistence backend for the desi_layer9 ``Layer9`` — a drop-in for ``persistence.save``/
``load`` that materialises state instead of replaying the journal on every load.

WHY: the committed JSON store derives state by replaying the whole journal on load (a fresh job's
full replay stopped finishing inside a cycle). This backend stores the kernel's OWN captured
snapshot (objects + ledger + tick/seq/minter) as indexed rows plus the journal as the retained
audit log, so ``load`` is a SELECT + ``snapshot.restore`` — no replay. It reuses
``snapshot.capture``/``restore`` and ``snapshot_hash``/``verify_chain`` verbatim, so the
reconstructed state is byte-for-byte the kernel's own (same snapshot hash, same chain). Nothing in
the desi_layer9 kernel is modified.

It is OFF by default; ``core_state`` selects it only when ``JONI_PERSISTENCE=sqlite``. The JSON
journal remains the portable, git-committed source; this is the fast local runtime store.
"""
from __future__ import annotations

import json
from pathlib import Path

from desi_layer9 import snapshot
from desi_layer9.core import JournalEntry
from desi_layer9.hashing import snapshot_hash, verify_chain

from ..storage.sqlite import connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv      (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS journal (idx INTEGER PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS objects (id  TEXT    PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger  (idx INTEGER PRIMARY KEY, data TEXT NOT NULL);
"""


def _open(path: str | Path):
    conn = connect(path)
    conn.executescript(SCHEMA)
    return conn


def save(state, path: str | Path) -> Path:
    """Materialise ``state`` into the SQLite store, transactionally. The journal is kept verbatim as
    the audit log; objects/ledger are the captured materialised view; kv holds the meta + the
    snapshot hash this state seals to (so ``load`` can verify it restored the exact state)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = snapshot.capture(state)            # kernel's own data-only snapshot (objects+ledger)
    conn = _open(path)
    try:
        with conn:                            # one transaction: all-or-nothing
            conn.execute("DELETE FROM kv")
            conn.execute("DELETE FROM journal")
            conn.execute("DELETE FROM objects")
            conn.execute("DELETE FROM ledger")
            conn.executemany("INSERT INTO kv (key, value) VALUES (?, ?)", [
                ("schema_version", json.dumps(snap["version"])),
                ("tick", json.dumps(snap["tick"])),
                ("seq", json.dumps(snap["seq"])),
                ("minter_counters", json.dumps(snap["minter_counters"])),
                ("snapshot_hash", json.dumps(snapshot_hash(state))),
            ])
            conn.executemany("INSERT INTO journal (idx, data) VALUES (?, ?)",
                             [(i, json.dumps(e.to_dict(), ensure_ascii=False))
                              for i, e in enumerate(state.journal)])
            conn.executemany("INSERT INTO objects (id, data) VALUES (?, ?)",
                             [(oid, json.dumps(o, ensure_ascii=False))
                              for oid, o in snap["objects"].items()])
            conn.executemany("INSERT INTO ledger (idx, data) VALUES (?, ?)",
                             [(i, json.dumps(ev, ensure_ascii=False))
                              for i, ev in enumerate(snap["ledger"])])
    finally:
        conn.close()
    return path


def load(path: str | Path, *, verify: bool = True):
    """Reconstruct the ``Layer9`` from the materialised rows — a SELECT, never a replay. Returns
    None if the store does not exist yet (so the caller can fall back / bootstrap)."""
    path = Path(path)
    if not path.exists():
        return None
    conn = _open(path)
    try:
        kv = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM kv")}
        if not kv:
            return None
        snap = {
            "version": kv["schema_version"],
            "tick": kv["tick"],
            "seq": kv["seq"],
            "minter_counters": kv["minter_counters"],
            "objects": {oid: json.loads(d)
                        for oid, d in conn.execute("SELECT id, data FROM objects")},
            "ledger": [json.loads(d)
                       for (d,) in conn.execute("SELECT data FROM ledger ORDER BY idx")],
        }
        journal = [JournalEntry.from_dict(json.loads(d))
                   for (d,) in conn.execute("SELECT data FROM journal ORDER BY idx")]
    finally:
        conn.close()
    state = snapshot.restore(snap, journal, tick=int(kv.get("tick", 0)))
    if verify:
        recorded = kv.get("snapshot_hash")
        if recorded and snapshot_hash(state) != recorded:
            raise ValueError("sqlite restore snapshot hash mismatch - store corrupted")
        ok, problems = verify_chain(state)
        if not ok:
            raise ValueError("ledger chain broken on load: " + "; ".join(problems))
    return state
