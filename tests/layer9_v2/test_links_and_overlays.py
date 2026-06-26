"""Phase 1/3 — typed links + traversal, and user/project overlays kept off the global object."""
from __future__ import annotations

import pytest

from joni.layer9_v2.graph import links, traversal
from joni.layer9_v2.spaces import contents, overlays, questions
from joni.layer9_v2.storage import sqlite as S


def _db(tmp_path):
    return S.open_db(tmp_path / "t.sqlite")


def test_typed_link_connects_spaces_and_is_idempotent(tmp_path):
    conn = _db(tmp_path)
    with conn:
        claim = contents.put_content(conn, type="claim", title="privacy matters")
        q = questions.put_question(conn, type="research_question", title="what is privacy?")
        links.add_link(conn, claim["id"], "answers", q["id"])
        links.add_link(conn, claim["id"], "answers", q["id"])      # same edge again
    rows = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
    assert rows == 1                                                # unique (from,to,relation)
    assert traversal.answers_for(conn, q["id"])[0]["id"] == claim["id"]


def test_unknown_relation_is_rejected(tmp_path):
    conn = _db(tmp_path)
    with conn:
        a = contents.put_content(conn, type="claim", title="a")
        b = contents.put_content(conn, type="claim", title="b")
    with pytest.raises(ValueError), conn:
        links.add_link(conn, a["id"], "vibes_with", b["id"])


def test_supporting_and_contradicting_evidence(tmp_path):
    conn = _db(tmp_path)
    with conn:
        claim = contents.put_content(conn, type="claim", title="c")
        ev1 = contents.put_content(conn, type="evidence", title="for")
        ev2 = contents.put_content(conn, type="evidence", title="against")
        links.add_link(conn, ev1["id"], "supports", claim["id"])
        links.add_link(conn, ev2["id"], "contradicts", claim["id"])
    assert [e["id"] for e in traversal.supporting_evidence(conn, claim["id"])] == [ev1["id"]]
    assert [e["id"] for e in traversal.contradicting(conn, claim["id"])] == [ev2["id"]]


def test_bounded_walk_is_cycle_safe(tmp_path):
    conn = _db(tmp_path)
    with conn:
        a = contents.put_content(conn, type="claim", title="a")
        b = contents.put_content(conn, type="claim", title="b")
        links.add_link(conn, a["id"], "supports", b["id"])
        links.add_link(conn, b["id"], "supports", a["id"])         # cycle
    reached = traversal.walk(conn, a["id"], relation_type="supports", max_depth=5)
    # terminates despite the cycle; start node excluded, each other node visited once
    assert {o["id"] for o in reached} == {b["id"]}


def test_overlay_is_per_user_and_not_on_global_object(tmp_path):
    conn = _db(tmp_path)
    with conn:
        claim = contents.put_content(conn, type="claim", title="contested")
        overlays.set_user_overlay(conn, user_id="alice", object_id=claim["id"],
                                  trust_level="high", personal_weight=0.9)
        overlays.set_user_overlay(conn, user_id="bob", object_id=claim["id"],
                                  trust_level="low", visibility="hidden")
    # the two users disagree about the same global object, which itself is unchanged
    alice = overlays.get_user_overlay(conn, user_id="alice", object_id=claim["id"])
    bob = overlays.get_user_overlay(conn, user_id="bob", object_id=claim["id"])
    assert alice["trust_level"] == "high"
    assert bob["visibility"] == "hidden"
    glob = contents.get_content(conn, claim["id"])
    assert "trust_level" not in glob["payload"] and "trust_level" not in glob


def test_project_overlay_upsert(tmp_path):
    conn = _db(tmp_path)
    with conn:
        claim = contents.put_content(conn, type="claim", title="x")
        overlays.set_project_overlay(conn, project_id="P1", object_id=claim["id"], active=True,
                                     project_weight=0.5)
        overlays.set_project_overlay(conn, project_id="P1", object_id=claim["id"], active=False)
    ov = overlays.get_project_overlay(conn, project_id="P1", object_id=claim["id"])
    assert ov["active"] is False
    assert conn.execute("SELECT COUNT(*) FROM project_overlays").fetchone()[0] == 1
