"""Persistence for deep-method trial outcomes — the substrate Baustein C reads.

An append-only JSONL ledger of ``DeepMethodTrial`` records: (method_id, target gap, result, scope,
gap_kind). This is where REAL outcomes land once the loop executes deep-method operators and grades
them; ``discover_from_store`` reads them straight into the discoverer. Deterministic, stdlib-only.

Today the store is the honest empty seam: the mechanism to record and consume trials exists and is
tested, but populating it with real outcomes is the live-loop step (a deep operator is proposed by
Baustein B, applied, graded, and its outcome appended here) — not yet wired into the autonomy loop.
"""

from __future__ import annotations

import json
import os

from .discovery import discover_affinities
from .operators import DeepMethodTrial

_FIELDS = ("method_id", "target", "result", "scope", "count", "gap_kind")


def record_trial(path: str, trial: DeepMethodTrial) -> None:
    """Append one trial as a JSON line (creates the file/dirs if needed)."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    row = {k: getattr(trial, k) for k in _FIELDS}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_trials(path: str) -> list[DeepMethodTrial]:
    """Read the ledger back into ``DeepMethodTrial`` objects (missing/empty file -> [])."""
    if not os.path.exists(path):
        return []
    out: list[DeepMethodTrial] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out.append(DeepMethodTrial(
                method_id=r["method_id"], target=r["target"], result=r["result"],
                scope=r.get("scope", "unknown"), count=int(r.get("count", 1)),
                gap_kind=r.get("gap_kind", "unknown")))
    return out


def discover_from_store(path: str, **kwargs):
    """Convenience: load the ledger and run the discoverer over it (same kwargs as
    ``discover_affinities``). Empty store -> [] (nothing discovered yet, honestly)."""
    return discover_affinities(load_trials(path), **kwargs)
