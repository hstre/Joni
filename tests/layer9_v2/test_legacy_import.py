"""Phase 2 — legacy import: space mapping, single summary event, unknown→needs_review, real file."""
from __future__ import annotations

import json
from pathlib import Path

from joni.layer9_v2.adapters import legacy_import
from joni.layer9_v2.journal import hashchain
from joni.layer9_v2.storage import sqlite as S


def _enum(v):
    return {"__e__": "E", "v": v}


def _obj(oid, otype, *, status="active", **extra):
    f = {"id": oid, "object_type": _enum(otype), "status": _enum(status)}
    f.update(extra)
    return {"__c__": "X", "f": f}


# A tiny snapshot in the legacy custom-serialisation form (__c__/f/__e__/__t__), exercising every
# link-bearing reference field the converter rebuilds.
SYNTH = {
    "snapshot_hash": "x", "tick": 3,
    "state_snapshot": {"objects": {
        "C-1": _obj("C-1", "claim", topic="privacy", text="privacy is tracked",
                    derived_from={"__t__": []}),
        "C-2": _obj("C-2", "claim", topic="surveillance", text="surveillance grows"),
        "M-1": _obj("M-1", "method", text="verifier-v2"),
        # evidence derives_from a claim → derives_from edge
        "E-1": _obj("E-1", "evidence", content="supporting note",
                    derived_from={"__t__": ["C-1"]}),
        # evidence_link with a mappable relation → supports edge
        "EL-1": _obj("EL-1", "evidence_link", claim_id="C-1", evidence_id="E-1",
                     relation="supports", strength=0.7),
        # evidence_link with an unmappable relation → counted, no edge
        "EL-2": _obj("EL-2", "evidence_link", claim_id="C-2", evidence_id="E-1",
                     relation="contextualizes"),
        # conflict over two claims → pairwise contradicts edge
        "X-1": _obj("X-1", "conflict", claim_ids={"__t__": ["C-1", "C-2"]},
                    conflict_kind="contradiction"),
        # decision pointing at a proposal that was NOT imported → dangling, skipped
        "D-1": _obj("D-1", "decision", proposal_id="PROP-missing"),
        "Z-1": _obj("Z-1", "weird_new_type", text="???"),
    }},
}
N_OBJECTS = len(SYNTH["state_snapshot"]["objects"])


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
    assert rep.total == N_OBJECTS and rep.imported == N_OBJECTS
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


def test_import_reconstructs_typed_links(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(SYNTH), encoding="utf-8")
    conn = S.open_db(tmp_path / "t.sqlite")
    rep = legacy_import.import_snapshot(conn, snap)

    def edge(src, rel, dst):
        return conn.execute(
            "SELECT 1 FROM links WHERE from_object_id=? AND relation_type=? AND to_object_id=?",
            (src, rel, dst)).fetchone() is not None

    assert edge("E-1", "derives_from", "C-1")          # from derived_from
    assert edge("E-1", "supports", "C-1")              # from evidence_link relation=supports
    assert edge("C-1", "contradicts", "C-2")           # from conflict claim_ids pairwise
    assert rep.by_relation == {"derives_from": 1, "supports": 1, "contradicts": 1}
    assert rep.links == 3
    # the 'contextualizes' relation does not map onto the closed vocab — counted, never invented
    assert rep.unmapped_relations == {"contextualizes": 1}
    # the decision points at a proposal that was never imported — skipped, not a forced edge
    assert rep.dangling_link_targets == 1
    assert not edge("D-1", "derives_from", "PROP-missing")
    ok, _ = hashchain.verify_chain(conn)               # one summary event; chain intact
    assert ok


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
