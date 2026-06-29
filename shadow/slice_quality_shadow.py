"""Slice-quality shadow run — the three plausible-wrong-slice checks on Joni's REAL graph.

PURE OBSERVER. Reads the v2 store (built by ``joni-layer9-convert`` from Joni's snapshot), and for
each topic projects the slice (its active claims) + a slice-independent graph scan into DESi's
``DesiReport``, runs the real ``select_mode``, and aggregates: how often each check (missing
opposition / thin provenance / scope mismatch) FIRES on real data, the resulting mode distribution,
and the over-caution risk the fixtures cannot show. It never writes Joni state and never touches the
loop.

    python shadow/slice_quality_shadow.py [--db state/layer9_v2.sqlite] [--limit N]

It uses the REAL checks from the DESi repo (``DESI_REPO`` or default ``/home/user/DESi``); if the
governance module cannot be imported it exits loudly — never a silent fake.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, os.environ.get("DESI_REPO") or os.environ.get("DESI_ROOT") or "/home/user/DESi")

from joni.layer9_v2.checks import slice_scan  # noqa: E402
from joni.layer9_v2.storage import sqlite as S  # noqa: E402

try:
    from desi_router.governance import report_from_snapshot, select_mode
except Exception as exc:  # noqa: BLE001 — decoupled; never silently faked
    report_from_snapshot = select_mode = None
    _IMPORT_ERR = exc


class _Snap:
    conflicts = ()
    provenance = type("P", (), {"snapshot_hash": "shadow"})()


def topics_with_active_claims(conn) -> dict[str, list[str]]:
    """topic -> active claim ids, read straight from the materialised v2 store."""
    by_topic: dict[str, list[str]] = {}
    for oid, payload in conn.execute(
            "SELECT id, payload_json FROM objects WHERE space='content' AND type='claim' "
            "AND status='active'"):
        f = (json.loads(payload) or {}).get("fields", {})
        by_topic.setdefault(f.get("topic") or "_untopiced", []).append(oid)
    return by_topic


def shadow_for_topic(conn, topic: str, claim_ids: list[str]) -> dict:
    slice_ids = tuple(claim_ids[:12])               # the answer's working slice
    scan = slice_scan.scan_slice(conn, slice_ids)
    texts = []
    for cid in slice_ids:
        row = conn.execute("SELECT title FROM objects WHERE id=?", (cid,)).fetchone()
        texts.append((row[0] or "")[:160] if row else "")
    rep = report_from_snapshot(
        f"shadow:{topic}", _Snap(),
        selected_claim_ids=slice_ids, selected_claim_texts=tuple(texts),
        extraction_confidence=0.9, state_recall_estimate=1.0, **scan)
    dec = select_mode(rep, retrieval_available=True)
    return {
        "topic": topic, "n_active": len(claim_ids),
        "fires_missing_opposition": bool(rep.omitted_opposition_ids),
        "fires_thin_provenance": bool(rep.provenance_under_support),
        "fires_scope_mismatch": bool(rep.scope_mismatch_scopes),
        "mode": dec.chosen_mode,
        "would_gate_update": not dec.persistent_state_update_allowed,
    }


def run(db_path: str | Path, *, limit: int | None = None) -> dict:
    conn = S.open_db(db_path)
    try:
        by_topic = topics_with_active_claims(conn)
        topics = sorted(by_topic, key=lambda t: (-len(by_topic[t]), t))
        if limit:
            topics = topics[:limit]
        rows = [shadow_for_topic(conn, t, by_topic[t]) for t in topics]
    finally:
        conn.close()
    n = len(rows) or 1
    fires = {k: sum(r[k] for r in rows) for k in
             ("fires_missing_opposition", "fires_thin_provenance", "fires_scope_mismatch")}
    return {
        "topics_scanned": len(rows),
        "fires": fires,
        "fire_rate": {k: round(v / n, 3) for k, v in fires.items()},
        "would_gate_update": sum(r["would_gate_update"] for r in rows),
        "mode_distribution": dict(Counter(r["mode"] for r in rows)),
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(_REPO / "state" / "layer9_v2.sqlite"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="emit the full per-topic rows as JSON")
    args = ap.parse_args(argv)
    if select_mode is None:
        print(f"FATAL: could not import desi_router.governance ({_IMPORT_ERR}). "
              f"Set DESI_REPO to a checkout with the governance package.", file=sys.stderr)
        return 2
    if not Path(args.db).exists():
        print(f"FATAL: v2 store {args.db} not found — build it with `joni-layer9-convert` first.",
              file=sys.stderr)
        return 2
    summary = run(args.db, limit=args.limit)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"Slice-quality shadow · {summary['topics_scanned']} topics · v2 graph · real data\n")
    print("  check fire-rate (how often the signal is present on real topics):")
    for k, v in summary["fire_rate"].items():
        print(f"    {k.replace('fires_',''):22s} {v:>6}  ({summary['fires'][k]} topics)")
    g, n = summary["would_gate_update"], summary["topics_scanned"]
    print(f"\n  would-gate-update on {g}/{n} topics")
    print(f"  mode distribution: {summary['mode_distribution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
