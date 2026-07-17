"""One-time reconsolidation audit of Joni's accumulated state (design: point 2 of the review).

    python scripts/reconsolidation_audit.py                 # READ-ONLY: print the audit report
    python scripts/reconsolidation_audit.py --json out.json # also write the report as JSON
    python scripts/reconsolidation_audit.py --apply --yes    # operator-only: reject CLEAR junk

Default is strictly read-only: it loads the live core, classifies every topic, hypothesis and
method into junk / borderline / keep (with a reason each) and prints a bounded, grouped report.

``--apply`` (which additionally requires ``--yes``) rejects only ``junk``-verdict hypotheses and
methods, through the existing gate operators (``reject_claim`` / ``reject_method`` - append-only,
provenance preserved, no ledger rewrite). Borderline objects are never touched. Run this
deliberately, with Joni parked, and review the dry-run report first.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write the report JSON here")
    ap.add_argument("--apply", action="store_true",
                    help="operator-only: reject CLEAR junk (requires --yes)")
    ap.add_argument("--yes", action="store_true", help="confirm a real write to the core")
    args = ap.parse_args()

    from joni.autonomy import core_state, reconsolidation_audit
    from joni.autonomy.config import paths

    p = paths()
    cs = core_state.load_or_migrate(p)
    report = reconsolidation_audit.audit(cs)
    print(reconsolidation_audit.render_markdown(report))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")

    if args.apply:
        if not args.yes:
            print("\n--apply needs --yes to write to the core. Nothing changed.")
            return 2

        class _Proto:
            def record(self, *a, **k):
                pass

        done = reconsolidation_audit.apply_junk(cs, _Proto())
        core_state.save(cs, p)
        print(f"\napplied: rejected {done['hypotheses']} junk hypothesis(es) and "
              f"{done['methods']} junk method(s) (gate-mediated). Core saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
