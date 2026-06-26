"""Phase 1/3 — the three spaces: typed wrappers, separation, status transitions."""
from __future__ import annotations

import pytest

from joni.layer9_v2.spaces import _base, contents, methods, questions
from joni.layer9_v2.storage import sqlite as S


def _db(tmp_path):
    return S.open_db(tmp_path / "t.sqlite")


def test_each_space_stores_and_reads_back(tmp_path):
    conn = _db(tmp_path)
    with conn:
        m = methods.put_method(conn, type="router_policy", title="greedy", payload={"k": 1})
        c = contents.put_content(conn, type="claim", title="privacy matters")
        q = questions.put_question(conn, type="research_question", title="what is privacy?")
    assert methods.get_method(conn, m["id"])["space"] == "method"
    assert contents.get_content(conn, c["id"])["space"] == "content"
    assert questions.get_question(conn, q["id"])["space"] == "question"
    assert methods.get_method(conn, m["id"])["payload"] == {"k": 1}


def test_spaces_do_not_leak_across_typed_getters(tmp_path):
    conn = _db(tmp_path)
    with conn:
        c = contents.put_content(conn, type="claim", title="x")
    # a content object is invisible through the method/question getters
    assert methods.get_method(conn, c["id"]) is None
    assert questions.get_question(conn, c["id"]) is None


def test_unknown_space_is_rejected(tmp_path):
    conn = _db(tmp_path)
    with pytest.raises(ValueError), conn:
        _base.put_object(conn, space="soup", type="claim")


def test_status_transition_records_history_and_bumps_version(tmp_path):
    conn = _db(tmp_path)
    with conn:
        c = contents.put_content(conn, type="claim", title="x")
    with conn:
        _base.set_status(conn, c["id"], "superseded", reason="replaced", actor="tester")
    obj = contents.get_content(conn, c["id"])
    assert obj["status"] == "superseded"
    assert obj["version"] == 2
    hist = conn.execute("SELECT old_status, new_status, reason FROM status_history "
                        "WHERE object_id = ?", (c["id"],)).fetchall()
    assert (hist[0]["old_status"], hist[0]["new_status"], hist[0]["reason"]) == \
           ("active", "superseded", "replaced")


def test_list_filters_are_index_backed(tmp_path):
    conn = _db(tmp_path)
    with conn:
        for i in range(3):
            contents.put_content(conn, type="claim", title=f"c{i}")
        contents.put_content(conn, type="evidence", title="e")
    assert len(contents.list_contents(conn, type="claim")) == 3
    assert len(contents.list_contents(conn, type="evidence")) == 1
    assert len(contents.list_contents(conn)) == 4
