"""Fail-safe post-cycle hook for the router shadow-observer.

Called by ``run.py`` at the very end of a cycle, and ONLY when ``JONI_ROUTER_SHADOW=1``. It runs the
read-only per-commit ledger shadow over the just-written Layer-9 snapshot and appends one per-cycle
record to ``state/router_shadow.jsonl`` — a TRACKED file the loop commits each cycle, so the log
persists across jobs (capped, so it never bloats the repo). Observation-only and fully guarded: any
error, or a missing DESi router (the default with no DESi checkout on the path), is a clean no-op
that never affects the cycle.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def run_after_cycle(repo_root, cycle, *, keep: int = 500) -> dict | None:
    """Append a per-cycle router-shadow record to state/router_shadow.jsonl (tracked, so the loop's
    `git add state` persists it; capped to the last ``keep`` records). Returns it, or None on any
    no-op. Never raises — observation must not break a cycle."""
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
        log = root / "state" / "router_shadow.jsonl"
        lines = log.read_text().splitlines() if log.exists() else []
        lines.append(json.dumps(rec))
        log.write_text("\n".join(lines[-keep:]) + "\n")
        return rec
    except Exception:                         # noqa: BLE001 — must never break a cycle
        return None
