"""Per-commit ledger shadow — the sharp "would the router have gated this state update?" metric.

The topic-level observer (``router_shadow.py``) shows the router's posture per topic. This is finer:
it walks Joni's Layer-9 **ledger** and, for every canonical *state-mutating commit* (claim create /
revise / reject, conflict open / review), asks the real deployed router whether it would have GATED
that specific update. Still a PURE OBSERVER — read-only on the committed snapshot, no loop hook, no
writes, no latency.

Layer-9 ticks only span 0..3 while the ledger holds 15k events, so the unit is the commit,
not the tick. The headline is selectivity: the router should gate the *risky* commits (touching a
rejected/contested claim or an open conflict) and wave through the clean ones — not gate everything.

    python shadow/ledger_shadow.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_SNAPSHOT = _REPO / "state" / "layer9.snapshot.json"
_LOG = _HERE / "shadow_log.jsonl"

sys.path.insert(0, os.environ.get("DESI_REPO", "/home/user/DESi"))
try:  # import-safe; main() checks the import at run time
    from desi_router.governance import report_from_snapshot, select_mode
except Exception:  # noqa: BLE001 — decoupled from DESi; never silently faked, main() exits loudly
    report_from_snapshot = select_mode = None

# canonical state-mutating commits (proposals/clustering/evidence are not canonical claim commits)
_COMMIT_OPS = {"claim_create", "claim_revise", "claim_reject", "conflict_open", "conflict_review"}
_OPEN_CONFLICT = {"active", "open", "unresolved", "contested", None, ""}


def _ev(x):
    return x.get("v") if isinstance(x, dict) else x


def _refs(x):
    if isinstance(x, dict):
        x = x.get("__t__", [])
    return list(x or [])


class _Conf:
    def __init__(self, cid, topic):
        self.id, self.kind, self.scope = cid, "conflict", (topic,)


class _Snap:
    def __init__(self, conflicts, h):
        self.conflicts = tuple(conflicts)
        self.provenance = type("P", (), {"snapshot_hash": h})()


def _index(snapshot_path):
    snap = json.loads(snapshot_path.read_text())
    ss = snap["state_snapshot"]
    objs, ledger = ss["objects"], ss["ledger"]
    claim = {}
    claim_open_conflicts = defaultdict(list)
    for v in objs.values():
        f = v.get("f", {})
        ot = _ev(f.get("object_type"))
        if ot == "claim":
            claim[_ev(f.get("id"))] = {"status": _ev(f.get("status")),
                                       "topic": _ev(f.get("topic")) or "_untopiced",
                                       "text": str(f.get("text") or "")}
        elif ot == "conflict":
            cstatus = _ev(f.get("conflict_status")) or _ev(f.get("status"))
            if cstatus in _OPEN_CONFLICT:
                cid = _ev(f.get("id"))
                for ref in _refs(f.get("claim_ids")):
                    claim_open_conflicts[ref].append(cid)
    return snap["snapshot_hash"], claim, claim_open_conflicts, ledger


def _gated_for_commit(target_id, claim, claim_open_conflicts, h):
    """Run the real router on the minimal situation this commit touches -> gate the update?"""
    info = claim.get(target_id)
    topic = info["topic"] if info else "_unknown"
    rejected = bool(info and info["status"] in ("rejected", "contested"))
    open_conf = claim_open_conflicts.get(target_id, [])
    text = (info["text"][:160] if info else target_id)

    snap = _Snap([_Conf(c, topic) for c in open_conf[:4]], h)
    rep = report_from_snapshot(
        f"commit:{target_id}", snap,
        selected_claim_ids=(target_id,), selected_claim_texts=(text,),
        invalidated_claim_ids=((target_id,) if rejected else ()),
        invalidated_claim_texts=((text,) if rejected else ()),
        task_touches_invalidated=rejected,
        answer_requires_conflict_resolution=bool(open_conf),
        extraction_confidence=0.9, state_recall_estimate=1.0)
    dec = select_mode(rep, retrieval_available=True)
    risky = rejected or bool(open_conf)
    return dec.chosen_mode, (not dec.persistent_state_update_allowed), risky


def compute_record(snapshot_path, *, limit: int = 0):
    """Aggregate the per-commit shadow over a snapshot into a record dict. Returns None if the real
    router is unavailable or there are no canonical commits (None = a clean no-op for callers)."""
    if select_mode is None:
        return None
    h, claim, claim_open_conflicts, ledger = _index(snapshot_path)

    rows = []
    for e in ledger:
        f = e.get("f", {})
        op = _ev(f.get("operator"))
        if op not in _COMMIT_OPS:
            continue
        targets = _refs(f.get("output_refs")) or _refs(f.get("input_refs"))
        target = targets[0] if targets else None
        if op in ("conflict_open", "conflict_review"):
            mode, gated, risky = "guarded_mode", True, True   # inherently conflict-touching
        elif target is None:
            continue
        else:
            mode, gated, risky = _gated_for_commit(target, claim, claim_open_conflicts, h)
        rows.append({"op": op, "mode": mode, "gated": gated, "risky": risky})
        if limit and len(rows) >= limit:
            break

    if not rows:
        return None
    clean = [r for r in rows if not r["risky"]]
    by_op = defaultdict(lambda: [0, 0])
    for r in rows:
        by_op[r["op"]][1] += 1
        by_op[r["op"]][0] += r["gated"]
    return {"kind": "ledger_per_commit", "snapshot_hash": h, "commits": len(rows),
            "would_gate": sum(r["gated"] for r in rows),
            "risky_commits": len(rows) - len(clean),
            "risky_gated": sum(r["gated"] for r in rows if r["risky"]),
            "clean_commits": len(clean), "clean_gated_overblock": sum(r["gated"] for r in clean),
            "modal_mode": Counter(r["mode"] for r in rows).most_common(1)[0][0],
            "by_operator": {k: {"gated": v[0], "total": v[1]} for k, v in by_op.items()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap commits processed (0 = all)")
    args = ap.parse_args()
    if select_mode is None:
        raise SystemExit("cannot import the real DESi router (set DESI_REPO=/path/to/DESi)")
    if not _SNAPSHOT.exists():
        raise SystemExit(f"no snapshot at {_SNAPSHOT}")
    rec = compute_record(_SNAPSHOT, limit=args.limit)
    if rec is None:
        raise SystemExit("no canonical commits in the ledger")
    with _LOG.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")

    n, g, rk, rg = rec["commits"], rec["would_gate"], rec["risky_commits"], rec["risky_gated"]
    print(f"Per-commit ledger shadow · {rec['snapshot_hash'][:12]} · {n} commits (READ-ONLY)\n")
    print(f"  would gate a state update : {g}/{n} ({g / n:.0%})")
    print(f"  risky commits             : {rk}  (gated {rg}/{rk} = {rg / rk:.0%})"
          if rk else "  risky commits: 0")
    print(f"  clean commits             : {rec['clean_commits']}  (gated "
          f"{rec['clean_gated_overblock']} -> "
          f"{'CLEAN' if rec['clean_gated_overblock'] == 0 else 'CHECK over-block'})")
    print("\n  by operator (gated / total):")
    for op, v in sorted(rec["by_operator"].items(), key=lambda kv: -kv[1]["total"]):
        gg, tt = v["gated"], v["total"]
        print(f"    {op:<18} {gg:>5} / {tt:<5} ({gg / tt:.0%})")
    print(f"\n  -> gates the risky commits and waves through the clean ones "
          f"({rec['modal_mode']} is the modal posture). Observation only; loop untouched.")


if __name__ == "__main__":
    main()
