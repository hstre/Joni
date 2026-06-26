"""Converter CLI — bring Joni's legacy Layer-9 data into the v2 SQLite store.

Usage::

    python -m joni.layer9_v2.convert                  # snapshot -> state/layer9_v2.sqlite
    python -m joni.layer9_v2.convert --source PATH --db PATH
    python -m joni.layer9_v2.convert --reset               # rebuild the db from scratch
    python -m joni.layer9_v2.convert --verify              # re-open and verify the journal chain

It reads the materialised **snapshot** (not the live journal — no replay), opens/creates the target
SQLite database, migrates it to the latest schema, imports every object into its space, rebuilds the
typed links, and prints the import report. The source file is never modified, and this never touches
the running Layer-9. Re-running is safe: objects/links use idempotent upserts, so a second run over
the same snapshot adds nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .adapters import legacy_import
from .journal import hashchain
from .storage import sqlite as S

DEFAULT_SOURCE = "state/layer9.snapshot.json"
DEFAULT_DB = "state/layer9_v2.sqlite"


def convert(source: str | Path, db: str | Path, *,
            reset: bool = False) -> legacy_import.ImportReport:
    """Open/create ``db``, migrate, and import ``source`` into it. Returns the import report."""
    source, db = Path(source), Path(db)
    if not source.exists():
        raise FileNotFoundError(f"source snapshot not found: {source}")
    if reset:
        for p in (db, Path(f"{db}-wal"), Path(f"{db}-shm")):
            p.unlink(missing_ok=True)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = S.open_db(db)
    try:
        return legacy_import.import_snapshot(conn, source)
    finally:
        conn.close()


def _verify(db: str | Path) -> bool:
    conn = S.open_db(db)
    try:
        ok, bad = hashchain.verify_chain(conn)
        n = conn.execute("SELECT COUNT(*) FROM objects").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        print(f"db {db}: {n} objects, {m} links, chain {'OK' if ok else f'BROKEN at tick {bad}'}")
        return ok
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="joni-layer9-convert", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help=f"legacy snapshot (default {DEFAULT_SOURCE})")
    ap.add_argument("--db", default=DEFAULT_DB, help=f"target SQLite file (default {DEFAULT_DB})")
    ap.add_argument("--reset", action="store_true", help="delete and rebuild the target db first")
    ap.add_argument("--verify", action="store_true",
                    help="only verify an existing db's journal chain")
    args = ap.parse_args(argv)

    if args.verify:
        return 0 if _verify(args.db) else 1

    try:
        rep = convert(args.source, args.db, reset=args.reset)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(legacy_import.import_report_text(rep))
    print(f"-> wrote {args.db}")
    ok, bad = _chain_status(args.db)
    print(f"   journal chain: {'OK' if ok else f'BROKEN at tick {bad}'}")
    return 0 if ok else 1


def _chain_status(db: str | Path) -> tuple[bool, int | None]:
    conn = S.open_db(db)
    try:
        return hashchain.verify_chain(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
