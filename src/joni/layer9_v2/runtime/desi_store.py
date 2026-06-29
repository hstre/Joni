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

# measurement.pairs is the O(members²) semantic-adapter log — stored on the object but never read.
# The committed checkpoint drops it so the cold-start artefact stays small (git-friendly).
_DEAD_MEASUREMENT_KEYS = ("pairs",)


def _strip_dead_blobs(snap: dict) -> int:
    dropped = 0
    for o in snap.get("objects", {}).values():
        f = o.get("f") if isinstance(o, dict) else None
        m = (f or {}).get("measurement") if isinstance(f, dict) else None
        d = m.get("__d__") if isinstance(m, dict) else None
        if isinstance(d, dict):
            for k in _DEAD_MEASUREMENT_KEYS:
                if k in d:
                    d.pop(k, None)
                    dropped += 1
    return dropped


def write_checkpoint(state, checkpoint_path: str | Path) -> Path:
    """Write a COMPACT, materialised cold-start checkpoint: the kernel's snapshot (dead measurement
    blobs stripped) + the snapshot hash it seals to. Loading it via ``load_via_checkpoint`` restores
    the state WITHOUT replaying the journal. Cheap (the state is already in memory)."""
    checkpoint_path = Path(checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    snap = snapshot.capture(state)
    _strip_dead_blobs(snap)
    doc = {"snapshot_hash": snapshot_hash(state), "tick": state.tick, "state_snapshot": snap}
    checkpoint_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")),
                              encoding="utf-8")
    return checkpoint_path


def load_via_checkpoint(core_json_path: str | Path, checkpoint_path: str | Path):
    """Fast cold-start: restore the committed materialised checkpoint (NO replay) and accept it ONLY
    if its hash matches the committed journal's recorded ``snapshot_hash`` AND the ledger chain
    verifies. Returns a ``Layer9`` or None — None means the caller must fall back to a full replay
    (the journal stays the source of truth; the checkpoint is a verified cache)."""
    core_json_path, checkpoint_path = Path(core_json_path), Path(checkpoint_path)
    if not checkpoint_path.exists() or not core_json_path.exists():
        return None
    try:
        doc = json.loads(core_json_path.read_text(encoding="utf-8"))
        recorded = doc.get("snapshot_hash")
        ck = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if not recorded or ck.get("snapshot_hash") != recorded:
            return None                              # stale checkpoint -> replay
        journal = [JournalEntry.from_dict(e) for e in doc.get("journal", [])]
        state = snapshot.restore(ck["state_snapshot"], journal, tick=int(doc.get("tick", 0)))
        if snapshot_hash(state) != recorded:
            return None                              # safety: restored state must match exactly
        ok, _ = verify_chain(state)
        return state if ok else None
    except Exception:  # noqa: BLE001 — a malformed checkpoint is never fatal; replay instead
        return None


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
