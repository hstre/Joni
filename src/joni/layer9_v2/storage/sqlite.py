"""SQLite connection + deterministic migration runner for Layer 9 v2.

The SQLite file is the AUTHORITATIVE local store. Connections enable WAL (concurrent reads while a
writer is active) and enforce foreign keys (per-connection pragma). Migrations are plain ``.sql``
files named ``NNNN_*.sql``; each is applied at most once, in numeric order, recorded in
``schema_version``. Startup opens the DB and reads the materialised tables directly — it never
replays the journal.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def now_iso() -> str:
    """UTC timestamp, second precision. (Wall-clock — recorded on rows, never used to derive a
    content hash, so object equality stays time-independent.)"""
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_id(prefix: str = "obj") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def canonical_json(obj) -> str:
    """Deterministic JSON: sorted keys, compact, unicode preserved. The basis for every hash."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(space: str, type_: str, title: str | None, payload: dict | None) -> str:
    """A stable hash of an object's SEMANTIC content (space/type/title/payload) — NOT its timestamps
    or status. Identical content => identical hash, so duplicates and equivalence are detectable."""
    body = canonical_json(
        {"space": space, "type": type_, "title": title or "", "payload": payload or {}})
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def connect(path: str | Path) -> sqlite3.Connection:
    """A connection with WAL + foreign-key enforcement + Row access. FK and WAL are set per
    connection, so this MUST be used for every connection (not just the first)."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _applied(conn: sqlite3.Connection) -> set[int]:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version "
                 "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    return {r[0] for r in conn.execute("SELECT version FROM schema_version")}


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply every pending migration in numeric order, each exactly once, recording the version.
    Deterministic: same files + same starting state => same result. Returns versions applied now."""
    applied = _applied(conn)
    pending = sorted(
        (int(f.name.split("_", 1)[0]), f)
        for f in _MIGRATIONS.glob("*.sql")
        if int(f.name.split("_", 1)[0]) not in applied
    )
    done: list[int] = []
    for ver, f in pending:
        conn.executescript(f.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                     (ver, now_iso()))
        conn.commit()
        done.append(ver)
    return done


def schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return (row[0] if row and row[0] is not None else 0)


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) and migrate to the latest schema. The normal entry point."""
    conn = connect(path)
    migrate(conn)
    return conn
