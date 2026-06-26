"""Phase 2 — legacy import: space mapping, single summary event, unknown→needs_review, real file."""
from __future__ import annotations

import json
from pathlib import Path

from joni.layer9_v2.adapters import legacy_import
from joni.layer9_v2.journal import hashchain
from joni.layer9_v2.storage import sqlite as S

# A tiny snapshot in the legacy custom-serialisation form (__c__/f/__e__/__t__).
SYNTH = {
    "snapshot_hash": "x", "tick": 3,
    "state_snapshot": {"objects": {
        "C-1": {"__c__": "Claim", "f": {
            "id": "C-1", "object_type": {"__e__": "ObjectType", "v": "claim"},
            "status": {"__e__": "Status", "v": "active"}, "topic": "privacy",
            "text": "privacy is tracked", "derived_from": {"__t__": []}}},
        "M-1": {"__c__": "Method", "f": {
            "id": "M-1", "object_type": {"__e__": "ObjectType", "v": "method"},
            "status": {"__e__": "Status", "v": "active"}, "text": "verifier-v2"}},
        "Z-1": {"__c__": "Mystery", "f": {
            "id": "Z-1", "object_type": {"__e__": "ObjectType", "v": "weird_new_type"},
            "status": {"__e__": "Status", "v": "active"}, "text": "???"}},
    }},
}


def test_decode_flattens_custom_serialisation():
    f = legacy_import.decode(SYNTH["state_snapshot"]["objects"]["C-1"])
    assert f["object_type"] == "claim"
    assert f["status"] == "active"
    assert f["derived_from"] == []


def test_import_maps_spaces_and_flags_unknown(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SYNTH), encoding="utf-8")
    conn = S.open_db(tmp_path / "t.sqlite")
    rep = legacy_import.import_snapshot(conn, snap)
    assert rep.total == 3 and rep.imported == 3
    spaces = {r["id"]: r["space"] for r in conn.execute("SELECT id, space FROM objects")}
    assert spaces["C-1"] == "content"
    assert spaces["M-1"] == "method"
    assert spaces["Z-1"] == "content"                       # unknown lands in content...
    z = conn.execute("SELECT type, status FROM objects WHERE id='Z-1'").fetchone()
    assert z["type"] == "unknown_legacy" and z["status"] == "needs_review"   # ...but flagged
    assert rep.needs_review == 1 and rep.unknown_types == {"weird_new_type": 1}


def test_import_writes_one_summary_event_not_per_object(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SYNTH), encoding="utf-8")
    conn = S.open_db(tmp_path / "t.sqlite")
    legacy_import.import_snapshot(conn, snap)
    evs = conn.execute("SELECT event_type FROM journal_events").fetchall()
    assert len(evs) == 1 and evs[0]["event_type"] == "legacy_import"
    ok, _ = hashchain.verify_chain(conn)
    assert ok


def test_import_preserves_legacy_id_and_payload(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SYNTH), encoding="utf-8")
    conn = S.open_db(tmp_path / "t.sqlite")
    legacy_import.import_snapshot(conn, snap)
    import json as _j
    row = conn.execute("SELECT payload_json FROM objects WHERE id='C-1'").fetchone()
    payload = _j.loads(row["payload_json"])
    assert payload["legacy_id"] == "C-1"
    assert payload["legacy_type"] == "claim"
    assert payload["fields"]["topic"] == "privacy"


def test_real_snapshot_imports_if_present(tmp_path):
    """Guarded: only runs where the real 22k-object snapshot is checked out. Confirms the import
    completes, every object maps to a valid space, and the chain still verifies."""
    real = Path(__file__).resolve().parents[2] / "state" / "layer9.snapshot.json"
    if not real.exists():
        import pytest
        pytest.skip("real snapshot not present")
    conn = S.open_db(tmp_path / "real.sqlite")
    rep = legacy_import.import_snapshot(conn, real)
    assert rep.imported == rep.total > 0
    bad = conn.execute("SELECT COUNT(*) FROM objects WHERE space NOT IN "
                       "('method','content','question')").fetchone()[0]
    assert bad == 0
    ok, _ = hashchain.verify_chain(conn)
    assert ok
