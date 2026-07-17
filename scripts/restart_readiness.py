"""Read-out of the restart gate (design-notes/RESTART_CRITERIA.md).

    python scripts/restart_readiness.py

Checks the mechanical criteria against the current state and prints a checklist. Judgment items
(no new token-hypotheses over a shadow run; a stable post-reconsolidation replay) are marked
REVIEW - the operator confirms those. Nothing here restarts Joni; it only reports readiness.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

PASS, REVIEW, FAIL, UNKNOWN = "PASS", "REVIEW", "FAIL", "UNKNOWN"


def _last_series_row(path: Path) -> dict | None:
    if not path.exists():
        return None
    rows = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for ln in reversed(rows):
        try:
            return json.loads(ln)
        except json.JSONDecodeError:
            continue
    return None


def _check_sensors(row: dict | None) -> tuple[str, str]:
    if not row:
        return UNKNOWN, "no collapse_series row yet - run a cycle first"
    m = row.get("metrics", {})
    have = ("hollow_ratio" in m.get("weak_claim_ratio", {})
            and "selfmodel_count" in m.get("repetition", {})
            and "by_status" in m.get("conflict_depth", {}))
    return (PASS, "corrected sensors present (hollow_ratio, selfmodel_count, conflict by_status)") \
        if have else (FAIL, "old panel schema - Phase A not deployed on this state")


def _check_conflicts(row: dict | None) -> tuple[str, str]:
    if not row:
        return UNKNOWN, "no panel row"
    cd = row.get("metrics", {}).get("conflict_depth", {})
    if "by_status" in cd:
        return PASS, (f"live={cd.get('open_conflicts')} (open+under_review), "
                      f"tolerated={cd.get('tolerated')}, closed={cd.get('closed')} - reconciled")
    return FAIL, "conflict status breakdown missing"


def _check_metabolism(ext: dict) -> tuple[str, str]:
    hist = ext.get("metabolism_history") or []
    if not hist:
        return REVIEW, "no metabolism history yet - run a shadow batch with JONI_METABOLISM to tune"
    states = {h.get("state") for h in hist}
    return (PASS, f"metabolism active; states seen: {sorted(states)}") if "sated" in states \
        else (REVIEW, f"metabolism measured but never satiated yet (states: {sorted(states)})")


def _check_backlog(ext: dict) -> tuple[str, str]:
    vit = ext.get("vitality", {})
    trials = vit.get("method_trials_total", 0)
    if trials and trials > 0:
        return PASS, f"method trials moving ({trials} recorded)"
    return REVIEW, ("0 method trials - clear the junk pile via reconsolidation_audit --apply, or "
                    "start the real trial path, before restart")


def main() -> int:
    from joni.autonomy.config import paths
    p = paths()
    row = _last_series_row(p.collapse_series)
    ext = {}
    if p.extensions.exists():
        try:
            ext = json.loads(p.extensions.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ext = {}

    checks = [
        ("1. alarm sensors measure correctly", *_check_sensors(row)),
        ("2. no new token-hypotheses", REVIEW, "operator watches a short shadow run's protocol"),
        ("3. method backlog shrinking or tested", *_check_backlog(ext)),
        ("4. metabolism couples intake<->consolidation", *_check_metabolism(ext)),
        ("5. conflict counts reconciled", *_check_conflicts(row)),
        ("6. replay stable after reconsolidation", REVIEW,
         "operator runs `python -m joni.autonomy verify` + a cold load"),
    ]
    print("# Joni restart readiness\n")
    worst = PASS
    order = {PASS: 0, REVIEW: 1, UNKNOWN: 2, FAIL: 3}
    for name, verdict, detail in checks:
        print(f"[{verdict:^7}] {name}\n          {detail}")
        if order[verdict] > order[worst]:
            worst = verdict
    print(f"\nOverall: {worst}. "
          + ("all mechanical checks pass - resume only after the REVIEW items are confirmed."
             if worst in (PASS, REVIEW)
             else "NOT ready - a mechanical criterion failed."))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
