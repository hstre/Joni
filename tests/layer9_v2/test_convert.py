"""The converter CLI: produces a populated, chain-verified SQLite db from a legacy snapshot."""
from __future__ import annotations

import json

from joni.layer9_v2 import convert
from joni.layer9_v2.journal import hashchain
from joni.layer9_v2.storage import sqlite as S


def _enum(v):
    return {"__e__": "E", "v": v}


def _obj(oid, otype, **extra):
    return {"__c__": "X", "f": {"id": oid, "object_type": _enum(otype),
                                "status": _enum("active"), **extra}}


# Self-contained snapshot (3 objects, 3 link sources) — no cross-test-module import.
SYNTH = {"state_snapshot": {"objects": {
    "C-1": _obj("C-1", "claim", topic="a"),
    "C-2": _obj("C-2", "claim", topic="b"),
    "E-1": _obj("E-1", "evidence", derived_from={"__t__": ["C-1"]}),
    "EL-1": _obj("EL-1", "evidence_link", claim_id="C-1", evidence_id="E-1", relation="supports"),
    "X-1": _obj("X-1", "conflict", claim_ids={"__t__": ["C-1", "C-2"]}),
}}}


def _write_snap(tmp_path):
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(SYNTH), encoding="utf-8")
    return p


def test_convert_builds_a_populated_db(tmp_path):
    db = tmp_path / "out.sqlite"
    rep = convert.convert(_write_snap(tmp_path), db)
    assert db.exists()
    assert rep.imported == rep.total > 0
    assert rep.links == 3
    conn = S.open_db(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == rep.imported
        assert conn.execute("SELECT COUNT(*) FROM links").fetchone()[0] == rep.links
        ok, _ = hashchain.verify_chain(conn)
        assert ok
    finally:
        conn.close()


def test_convert_is_idempotent(tmp_path):
    """Re-running over the same snapshot adds nothing (idempotent upserts)."""
    db = tmp_path / "out.sqlite"
    snap = _write_snap(tmp_path)
    convert.convert(snap, db)
    conn = S.open_db(db)
    objs1 = conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
    links1 = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    conn.close()
    convert.convert(snap, db)                       # second pass, same file
    conn = S.open_db(db)
    try:
        assert conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == objs1
        assert conn.execute("SELECT COUNT(*) FROM links").fetchone()[0] == links1
    finally:
        conn.close()


def test_reset_rebuilds_from_scratch(tmp_path):
    db = tmp_path / "out.sqlite"
    snap = _write_snap(tmp_path)
    convert.convert(snap, db)
    rep = convert.convert(snap, db, reset=True)     # wipe + rebuild
    conn = S.open_db(db)
    try:
        # exactly one import event after a reset (not two accumulated)
        n = conn.execute("SELECT COUNT(*) FROM journal_events WHERE event_type='legacy_import'") \
            .fetchone()[0]
        assert n == 1
        assert conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == rep.imported
    finally:
        conn.close()


def test_main_entrypoint_returns_zero(tmp_path):
    db = tmp_path / "out.sqlite"
    rc = convert.main(["--source", str(_write_snap(tmp_path)), "--db", str(db), "--reset"])
    assert rc == 0
    assert db.exists()


def test_missing_source_is_a_clean_error(tmp_path):
    rc = convert.main(["--source", str(tmp_path / "nope.json"), "--db", str(tmp_path / "x.sqlite")])
    assert rc == 2
