"""Phase 4/5 — DESi + router read slices are read-only and shaped as documented."""
from __future__ import annotations

from joni.layer9_v2.adapters import desi_adapter, router_adapter
from joni.layer9_v2.graph import links
from joni.layer9_v2.spaces import _base, contents, overlays, questions
from joni.layer9_v2.storage import sqlite as S


def _seed(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    with conn:
        claim = contents.put_content(conn, type="claim", title="contested claim")
        ev = contents.put_content(conn, type="evidence", title="for")
        against = contents.put_content(conn, type="evidence", title="against")
        q = questions.put_question(conn, type="research_question", title="open q")
        links.add_link(conn, ev["id"], "supports", claim["id"])
        links.add_link(conn, against["id"], "contradicts", claim["id"])
    return conn, claim, q


def test_desi_report_is_read_only_and_counts_pressure(tmp_path):
    conn, claim, _ = _seed(tmp_path)
    before = conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
    rep = desi_adapter.desi_report(conn)
    after = conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
    assert after == before                                  # no writes
    row = next(c for c in rep["claims"] if c["id"] == claim["id"])
    assert row["support_count"] == 1 and row["contradiction_count"] == 1
    assert rep["source"] == "layer9_v2"


def test_router_slice_flags_contested_and_open_questions(tmp_path):
    conn, claim, q = _seed(tmp_path)
    sl = router_adapter.routing_slice(conn)
    assert claim["id"] in [c["id"] for c in sl["contested_claims"]]
    assert q["id"] in [x["id"] for x in sl["open_questions"]]
    assert sl["next_action_hint"] == "resolve_conflict"


def test_contested_status_claims_still_surface(tmp_path):
    """A claim that conflict-resolution moved to status 'contested' is exactly what the router and
    DESi must surface — they must not be filtered out by an 'active'-only status check. (This is the
    real-data case: legacy conflicts mark their claims 'contested', not 'active'.)"""
    conn = S.open_db(tmp_path / "t.sqlite")
    with conn:
        a = contents.put_content(conn, type="claim", title="contested A")
        b = contents.put_content(conn, type="claim", title="contested B")
        links.add_link(conn, a["id"], "contradicts", b["id"])
        _base.set_status(conn, b["id"], "contested", reason="in conflict")
    sl = router_adapter.routing_slice(conn)
    assert b["id"] in [c["id"] for c in sl["contested_claims"]]
    assert sl["next_action_hint"] == "resolve_conflict"
    # DESi's claim slice includes the contested claim with its contradiction pressure counted
    rep = desi_adapter.desi_report(conn)
    row = next(c for c in rep["claims"] if c["id"] == b["id"])
    assert row["contradiction_count"] == 1


def test_router_slice_respects_project_overlay(tmp_path):
    conn, claim, q = _seed(tmp_path)
    # project P1 only activates the question, not the contested claim
    with conn:
        overlays.set_project_overlay(conn, project_id="P1", object_id=q["id"], active=True)
    sl = router_adapter.routing_slice(conn, project_id="P1")
    assert [x["id"] for x in sl["open_questions"]] == [q["id"]]
    assert sl["contested_claims"] == []                     # filtered out by the overlay
    assert sl["next_action_hint"] == "answer_question"
