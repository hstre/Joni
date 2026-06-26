"""Phase 6 — append-only hash-chained journal: no mutation without a journal event."""
from __future__ import annotations

from joni.layer9_v2.journal import hashchain
from joni.layer9_v2.spaces import _base, contents
from joni.layer9_v2.storage import sqlite as S


def _db(tmp_path):
    return S.open_db(tmp_path / "t.sqlite")


def test_every_mutation_appends_exactly_one_event(tmp_path):
    conn = _db(tmp_path)
    n0 = conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
    with conn:
        c = contents.put_content(conn, type="claim", title="x")     # +1 object_created
    with conn:
        _base.set_status(conn, c["id"], "retired")                  # +1 status_changed
    n1 = conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
    assert n1 - n0 == 2
    types = [r[0] for r in conn.execute("SELECT event_type FROM journal_events ORDER BY tick")]
    assert types[-2:] == ["object_created", "status_changed"]


def test_chain_verifies_and_head_advances(tmp_path):
    conn = _db(tmp_path)
    assert hashchain.head_hash(conn) == hashchain.GENESIS
    with conn:
        contents.put_content(conn, type="claim", title="a")
    h1 = hashchain.head_hash(conn)
    assert h1 != hashchain.GENESIS
    with conn:
        contents.put_content(conn, type="claim", title="b")
    assert hashchain.head_hash(conn) != h1
    ok, bad = hashchain.verify_chain(conn)
    assert ok and bad is None


def test_tampering_with_a_past_event_breaks_the_chain(tmp_path):
    conn = _db(tmp_path)
    with conn:
        contents.put_content(conn, type="claim", title="a")
        contents.put_content(conn, type="claim", title="b")
    # rewrite the payload of the first event without recomputing hashes
    first_tick = conn.execute("SELECT MIN(tick) FROM journal_events").fetchone()[0]
    conn.execute("UPDATE journal_events SET payload_json = '{\"evil\":true}' WHERE tick = ?",
                 (first_tick,))
    conn.commit()
    ok, bad = hashchain.verify_chain(conn)
    assert not ok
    assert bad == first_tick


def test_rollback_leaves_no_partial_state_or_event(tmp_path):
    conn = _db(tmp_path)
    n0 = conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
    e0 = conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
    try:
        with conn:
            contents.put_content(conn, type="claim", title="will-rollback")
            raise RuntimeError("boom")          # abort the transaction
    except RuntimeError:
        pass
    assert conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0] == n0
    assert conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0] == e0
    ok, _ = hashchain.verify_chain(conn)
    assert ok
