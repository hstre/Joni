"""Slice-quality shadow run — the three plausible-wrong-slice checks on Joni's REAL graph.

PURE OBSERVER. Reads the v2 store (built by ``joni-layer9-convert`` from Joni's snapshot), and per
slice projects it + a slice-independent graph scan into DESi's ``DesiReport``, runs the unified
``attack_slice`` (#7), and aggregates how often each of the FIVE vectors (missing opposition /
same-scope-newer / thin provenance / scope mismatch / k-unstable) FIRES on real data — the
over-caution the fixtures cannot show. It never writes Joni state and never touches the loop.

    python shadow/slice_quality_shadow.py [--db ...] [--granularity claim|topic] [--limit N]

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
    from desi_router.governance import attack_slice, report_from_snapshot
except Exception as exc:  # noqa: BLE001 — decoupled; never silently faked
    attack_slice = report_from_snapshot = None
    _IMPORT_ERR = exc


class _Snap:
    conflicts = ()
    provenance = type("P", (), {"snapshot_hash": "shadow"})()

_FIRE_KEYS = ("fires_missing_opposition", "fires_same_scope_newer", "fires_thin_provenance",
              "fires_scope_mismatch", "fires_k_unstable")


def _claim_index(conn, statuses: tuple[str, ...]) -> dict[str, dict]:
    """id -> {topic, tick, title} for every live claim (the same-scope-newer + widening pool)."""
    placeholders = ",".join("?" for _ in statuses)
    idx: dict[str, dict] = {}
    for oid, payload, title in conn.execute(
            f"SELECT id, payload_json, title FROM objects WHERE space='content' AND type='claim' "
            f"AND status IN ({placeholders})", statuses):
        f = (json.loads(payload) or {}).get("fields", {})
        idx[oid] = {"topic": f.get("topic") or "_untopiced",
                    "tick": f.get("created_tick") or 0, "title": title or ""}
    return idx


def _newer_siblings(slice_ids, idx, by_topic) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Same-topic claims NEWER than a slice claim, not in the slice (the #5 silent-staleness pool).
    Topic stands in for scope because Joni claims carry no scope tag — deliberately coarse; the run
    reports whether that over-fires."""
    sl = set(slice_ids)
    ids, texts = [], []
    for cid in slice_ids:
        meta = idx.get(cid)
        if not meta:
            continue
        for sib in by_topic.get(meta["topic"], ()):
            if sib in sl or sib in ids:
                continue
            if idx.get(sib, {}).get("tick", 0) > meta["tick"]:
                ids.append(sib)
                texts.append(idx[sib]["title"][:120])
    return tuple(ids), tuple(texts)


def _report(conn, label, slice_ids, idx, by_topic, *, with_supersession=True):
    scan = slice_scan.scan_slice(conn, slice_ids)
    if with_supersession:
        nids, ntexts = _newer_siblings(slice_ids, idx, by_topic)
        scan["newer_sibling_ids"] = nids
        scan["newer_sibling_texts"] = ntexts
    texts = tuple(idx.get(cid, {}).get("title", "")[:160] for cid in slice_ids)
    return report_from_snapshot(
        f"shadow:{label}", _Snap(),
        selected_claim_ids=tuple(slice_ids), selected_claim_texts=texts,
        extraction_confidence=0.9, state_recall_estimate=1.0, **scan)


def _decide(conn, label, slice_ids, idx, by_topic, *, wide_ids=None) -> dict:
    rep = _report(conn, label, slice_ids, idx, by_topic)
    wide = (_report(conn, f"{label}:wide", wide_ids, idx, by_topic, with_supersession=False)
            if wide_ids and tuple(wide_ids) != tuple(slice_ids) else None)
    res = attack_slice(rep, retrieval_available=True, wide_report=wide)
    fired = set(res.fired)
    return {
        "unit": label, "n": len(slice_ids),
        "fires_missing_opposition": "omitted_opposition" in fired,
        "fires_same_scope_newer": "same_scope_newer" in fired,
        "fires_thin_provenance": "thin_provenance" in fired,
        "fires_scope_mismatch": "scope_mismatch" in fired,
        "fires_k_unstable": "k_unstable" in fired,
        "survived": res.survived,
        "mode": res.decision.chosen_mode,
        "would_gate_update": not res.decision.persistent_state_update_allowed,
    }


def run(db_path: str | Path, *, granularity: str = "claim",
        statuses: tuple[str, ...] = ("active", "contested"), limit: int | None = None) -> dict:
    """Scan slices through the unified attack pass and aggregate per-vector fire-rates. ``claim``
    granularity (default) is the answer-slice level at which omitted opposition / supersession
    surface; the widened (topic) slice drives k-stability. ``statuses`` = the live set."""
    conn = S.open_db(db_path)
    try:
        idx = _claim_index(conn, statuses)
        by_topic: dict[str, list[str]] = {}
        for cid, m in idx.items():
            by_topic.setdefault(m["topic"], []).append(cid)
        if granularity == "claim":
            ids = [c for v in by_topic.values() for c in v]
            if limit:
                ids = ids[:limit]
            rows = [_decide(conn, cid, (cid,), idx, by_topic,
                            wide_ids=tuple(by_topic[idx[cid]["topic"]][:12])) for cid in ids]
        else:
            topics = sorted(by_topic, key=lambda t: (-len(by_topic[t]), t))
            if limit:
                topics = topics[:limit]
            rows = [_decide(conn, t, tuple(by_topic[t][:12]), idx, by_topic) for t in topics]
    finally:
        conn.close()
    n = len(rows) or 1
    fires = {k: sum(r[k] for r in rows) for k in _FIRE_KEYS}
    return {
        "granularity": granularity, "statuses": list(statuses), "units_scanned": len(rows),
        "fires": fires,
        "fire_rate": {k: round(v / n, 3) for k, v in fires.items()},
        "would_gate_update": sum(r["would_gate_update"] for r in rows),
        "mode_distribution": dict(Counter(r["mode"] for r in rows)),
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(_REPO / "state" / "layer9_v2.sqlite"))
    ap.add_argument("--granularity", choices=("topic", "claim"), default="claim")
    ap.add_argument("--statuses", default="active,contested",
                    help="the router's live set (comma-separated)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="emit the full per-unit rows as JSON")
    args = ap.parse_args(argv)
    if attack_slice is None:
        print(f"FATAL: could not import desi_router.governance ({_IMPORT_ERR}). "
              f"Set DESI_REPO to a checkout with the governance package.", file=sys.stderr)
        return 2
    if not Path(args.db).exists():
        print(f"FATAL: v2 store {args.db} not found — build it with `joni-layer9-convert` first.",
              file=sys.stderr)
        return 2
    statuses = tuple(s.strip() for s in args.statuses.split(",") if s.strip())
    summary = run(args.db, granularity=args.granularity, statuses=statuses, limit=args.limit)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    n = summary["units_scanned"]
    print(f"Slice-quality shadow · {n} {summary['granularity']}-slices · "
          f"live={summary['statuses']} · v2 graph · real data\n")
    print(f"  check fire-rate (signal present per {summary['granularity']}):")
    for k, v in summary["fire_rate"].items():
        print(f"    {k.replace('fires_',''):22s} {v:>6}  ({summary['fires'][k]}/{n})")
    print(f"\n  would-gate-update on {summary['would_gate_update']}/{n}")
    print(f"  mode distribution: {summary['mode_distribution']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
