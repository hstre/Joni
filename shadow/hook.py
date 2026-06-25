"""Fail-safe post-cycle hook for the router shadow-observer.

Called by ``run.py`` at the very end of a cycle, and ONLY when ``JONI_ROUTER_SHADOW=1``. It runs the
read-only per-commit ledger shadow over the just-written Layer-9 snapshot and appends one per-cycle
record to ``shadow/shadow_log.jsonl`` so the log accumulates automatically. It is observation-only
and fully guarded: any error, or a missing DESi router (the production default, where DESI_REPO is
absent), is a clean no-op that never affects the cycle.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def run_after_cycle(repo_root, cycle) -> dict | None:
    """Append a per-cycle router-shadow record; return it, or None on any no-op. Never raises."""
    try:
        root = Path(repo_root)
        snapshot = root / "state" / "layer9.snapshot.json"
        if not snapshot.exists():
            return None
        # lazy import: ledger_shadow's DESi-router import is guarded (None if absent)
        from shadow.ledger_shadow import compute_record
        rec = compute_record(snapshot)
        if rec is None:                       # router unavailable or no commits -> no-op
            return None
        rec = {"cycle": cycle, "ts": datetime.now(UTC).isoformat(timespec="seconds"), **rec}
        log = root / "shadow" / "shadow_log.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        return rec
    except Exception:                         # noqa: BLE001 — must never break a cycle
        return None
