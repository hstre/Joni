"""Router shadow-observer for Joni — PURE OBSERVER, zero effect on the loop.

ChatGPT's step 4: before switching the external DESi router on for Joni, run it in SHADOW MODE.
Joni answers and mutates state exactly as today; this script runs *in parallel, after the fact*,
reads Joni's Layer-9 snapshot READ-ONLY, asks the real deployed router "what would you have done?",
and logs it. It never writes Joni state, never touches the loop, adds no latency, shares no state.

Granularity: per **topic** (Joni's unit of reasoning). For each topic it builds the epistemic
situation from Layer-9 — active claims (the usable slice), rejected/contested claims (invalidated),
open conflicts touching the topic, thin-footing signal — projects it into the router's
``DesiReport`` and runs ``select_mode``. The output is a distribution: on how many topics would the
router be guarded / ask_user / retrieval / clean, and where would it gate a state update.

It uses the REAL router from the DESi repo (no drift): set ``DESI_REPO`` or it defaults to
``/home/user/DESi``. If the router cannot be imported, it says so and exits — it never silently
substitutes a fake.

    python shadow/router_shadow.py [--limit N] [--min-claims K]
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

_OPEN_CONFLICT = {"active", "open", "unresolved", "contested", None, ""}


def _ev(x):
    return x.get("v") if isinstance(x, dict) else x


class _Conf:
    def __init__(self, cid, kind, scope):
        self.id, self.kind, self.scope = cid, kind, tuple(scope)


class _Snap:
    def __init__(self, conflicts, h):
        self.conflicts = tuple(conflicts)
        self.provenance = type("P", (), {"snapshot_hash": h})()


def load_topics(snapshot_path: Path):
    snap = json.loads(snapshot_path.read_text())
    objs = snap["state_snapshot"]["objects"]
    by_topic_claims = defaultdict(list)
    claim_topic = {}
    conflicts = []
    for v in objs.values():
        f = v.get("f", {})
        ot = _ev(f.get("object_type"))
        if ot == "claim":
            topic = _ev(f.get("topic")) or "_untopiced"
            rec = {"id": _ev(f.get("id")), "text": str(f.get("text") or ""),
                   "status": _ev(f.get("status")), "authority": _ev(f.get("authority"))}
            by_topic_claims[topic].append(rec)
            claim_topic[rec["id"]] = topic
        elif ot == "conflict":
            cstatus = _ev(f.get("conflict_status")) or _ev(f.get("status"))
            cids = f.get("claim_ids") or {}
            cids = cids.get("__t__", cids) if isinstance(cids, dict) else cids
            conflicts.append({"id": _ev(f.get("id")), "kind": _ev(f.get("kind")) or "conflict",
                              "open": cstatus in _OPEN_CONFLICT, "claim_ids": list(cids or [])})
    return snap["snapshot_hash"], by_topic_claims, claim_topic, conflicts


def shadow_for_topic(topic, claims, topic_conflicts, snapshot_hash):
    # Joni claims carry authority='candidate' by construction; trust is expressed in STATUS.
    active = [c for c in claims if c["status"] == "active"]
    rejected = [c for c in claims if c["status"] in ("rejected", "contested")]
    unsettled = [c for c in claims if c["status"] == "candidate"]   # proposed, not yet active
    open_conf = [c for c in topic_conflicts if c["open"]]

    slice_ids = tuple(c["id"] for c in active[:12])
    slice_txt = tuple(c["text"][:160] for c in active[:12])
    inval_ids = tuple(c["id"] for c in rejected[:12])
    inval_txt = tuple(c["text"][:160] for c in rejected[:12])
    snap = _Snap([_Conf(c["id"], c["kind"], (topic,)) for c in open_conf[:8]], snapshot_hash)

    # thin trusted footing (unsettled claims dominate the active ones) -> a real mismatch signal
    recall = 1.0
    conf = 0.9
    if active and len(unsettled) > 2 * len(active):
        conf = 0.3
    has_usable = bool(slice_ids)

    rep = report_from_snapshot(
        f"shadow:{topic}", snap,
        selected_claim_ids=slice_ids, selected_claim_texts=slice_txt,
        invalidated_claim_ids=inval_ids, invalidated_claim_texts=inval_txt,
        task_touches_invalidated=bool(inval_ids),
        answer_requires_conflict_resolution=bool(open_conf),
        extraction_confidence=conf, state_recall_estimate=recall)
    dec = select_mode(rep, retrieval_available=True)
    return {
        "topic": topic, "n_claims": len(claims), "active": len(active),
        "rejected_or_contested": len(rejected), "unsettled": len(unsettled),
        "open_conflicts": len(open_conf), "has_usable_state": has_usable,
        "thin_footing": bool(active and len(unsettled) > 2 * len(active)),
        "mode": dec.chosen_mode, "validator_required": dec.validator_required,
        "would_gate_update": not dec.persistent_state_update_allowed,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap topics processed (0 = all)")
    ap.add_argument("--min-claims", type=int, default=1, help="skip topics with fewer claims")
    args = ap.parse_args()

    if select_mode is None:
        raise SystemExit("cannot import the real DESi router (set DESI_REPO=/path/to/DESi)")
    if not _SNAPSHOT.exists():
        raise SystemExit(f"no snapshot at {_SNAPSHOT}")
    h, by_topic, claim_topic, conflicts = load_topics(_SNAPSHOT)

    conf_by_topic = defaultdict(list)
    for c in conflicts:
        for cid in c["claim_ids"]:
            t = claim_topic.get(cid)
            if t:
                conf_by_topic[t].append(c)
        if not c["claim_ids"]:
            conf_by_topic["_global"].append(c)

    topics = [t for t in by_topic if len(by_topic[t]) >= args.min_claims]
    topics.sort(key=lambda t: -len(by_topic[t]))
    if args.limit:
        topics = topics[: args.limit]

    rows = [shadow_for_topic(t, by_topic[t], conf_by_topic.get(t, []), h)
            for t in topics]
    modes = Counter(r["mode"] for r in rows)
    gated = sum(r["would_gate_update"] for r in rows)
    # over-block sanity: a fully clean topic (no rejected/contested, no conflict, solid footing)
    # must NOT be gated. Thin-footing topics are gated for a real reason and are not "clean".
    clean = [r for r in rows if r["rejected_or_contested"] == 0 and r["open_conflicts"] == 0
             and not r["thin_footing"] and r["has_usable_state"]]
    clean_gated = [r for r in clean if r["would_gate_update"]]

    record = {"snapshot_hash": h, "topics_observed": len(rows),
              "mode_distribution": dict(modes), "would_gate_update": gated,
              "clean_topics": len(clean), "clean_topics_gated_overblock": len(clean_gated)}
    with _LOG.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    print(f"Router shadow over Joni Layer-9 · snapshot {h[:12]} · {len(rows)} topics (READ-ONLY)\n")
    for m, n in modes.most_common():
        print(f"  {m:<16} {n:>4}  ({n / len(rows):.0%})")
    print(f"\nwould gate a state update on {gated}/{len(rows)} topics ({gated / len(rows):.0%})")
    print(f"clean topics: {len(clean)}  ·  of which gated (over-block): {len(clean_gated)} "
          f"-> {'CLEAN' if not clean_gated else 'CHECK'}")
    print("\nhotspots (most conflicted topics the router would guard):")
    for r in sorted(rows, key=lambda r: -(r["open_conflicts"] + r["rejected_or_contested"]))[:6]:
        print(f"  {r['topic']:<16} claims={r['n_claims']:<5} "
              f"rej/contested={r['rejected_or_contested']:<4} "
              f"conflicts={r['open_conflicts']:<3} -> {r['mode']}")
    print(f"\nappended a shadow record to {_LOG.relative_to(_REPO)} "
          "(observation only; loop untouched)")


if __name__ == "__main__":
    main()
