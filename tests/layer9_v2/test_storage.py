"""Phase 1 — storage foundation: migrations, pragmas, content hashing."""
from __future__ import annotations

from joni.layer9_v2.storage import sqlite as S


def test_migrate_is_idempotent_and_versioned(tmp_path):
    db = tmp_path / "t.sqlite"
    conn = S.connect(db)
    first = S.migrate(conn)
    assert first == [1]                      # migration 0001 applied
    assert S.schema_version(conn) == 1
    again = S.migrate(conn)
    assert again == []                       # nothing pending the second time
    assert S.schema_version(conn) == 1


def test_open_db_sets_wal_and_foreign_keys(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_expected_tables_exist(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"objects", "links", "user_overlays", "project_overlays",
            "status_history", "journal_events", "snapshots", "embeddings",
            "schema_version"} <= names


def test_content_hash_is_time_independent_and_semantic(tmp_path):
    a = S.content_hash("content", "claim", "t", {"x": 1, "y": 2})
    b = S.content_hash("content", "claim", "t", {"y": 2, "x": 1})  # key order must not matter
    c = S.content_hash("content", "claim", "t", {"x": 1, "y": 3})
    assert a == b
    assert a != c


def test_foreign_keys_enforced(tmp_path):
    import sqlite3
    conn = S.open_db(tmp_path / "t.sqlite")
    # a link to a non-existent object must be rejected by the FK constraint
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO links (id, from_object_id, to_object_id, relation_type, created_at) "
            "VALUES ('l1','nope','nope','supports','2026-01-01T00:00:00+00:00')")
        conn.commit()
