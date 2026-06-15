"""Homeostasis - so Joni neither degenerates nor stagnates over a long autonomous run.

Two autonomous jobs, both deterministic, gate-mediated and bounded:

  * **regulate** - shed what is dead and cap what is unbounded. A self-invented hypothesis is
    *rejected* honestly only on objective grounds - contradicted, or tested several times and
    earned no support (a guess that did not pan out); Kevin's advisory "thin" verdict never
    sheds an idea. The live-hypothesis backlog is capped so it cannot grow without end. This is
    what keeps a week-long run from silting up.

  * **vitality** - measure, from his own state, whether Joni is *developing* (new active
    claims, ideas that earned promotion, governed evidence, emergent structure, real
    semantic decisions) or *degenerating* (a swelling hypothesis backlog, high duplication,
    stagnation, unbounded object growth) - and report a plain verdict. No human labelling:
    Joni grades his own trajectory and the page shows it.
"""

from __future__ import annotations

import desi_layer9 as l9
from desi_layer9 import Status


def _supports_on(cs, claim_id: str) -> int:
    return sum(1 for el in cs.core.all(l9.ObjectType.EVIDENCE_LINK)
               if el.claim_id == claim_id and el.relation.value in ("supports", "contextualizes"))


def _hard_conflicted(cs, claim_id: str) -> bool:
    return any(claim_id in x.claim_ids and x.severity == "hard"
               for x in cs.core.open_conflicts())


def regulate(cs, extensions: dict, proto, cycle: int = 0, *, max_live_hypotheses: int = 30,
             max_prune: int = 3) -> dict:
    """Reject dead hypotheses and cap the backlog. Returns what was shed and why."""
    hyps = cs.hypotheses()
    tested = extensions.get("hyp_tested", [])

    def tested_count(hid: str) -> int:
        return sum(1 for k in tested if k.startswith(hid + "|"))

    out = {"pruned": 0, "contradicted": 0, "barren": 0, "over_cap": 0}
    pruned_ids: set[str] = set()

    # 1. shed genuinely dead ideas - only on *objective* grounds (no support AND a real reason
    #    to give up). Kevin's "thin" verdict is advisory and deliberately NOT a reason here: an
    #    idea dies because it was contradicted or earned nothing after many real tests, never
    #    because the creativity engine disliked it. Kevin must never decide.
    for h in sorted(hyps, key=lambda c: int(c.id.split("-")[-1])):
        if out["pruned"] >= max_prune:
            break
        if _supports_on(cs, h.id) > 0:
            continue                                   # it earned something - keep it
        reason = None
        if _hard_conflicted(cs, h.id):
            reason = "contradicted"
        elif tested_count(h.id) >= 4:
            reason = "barren"                          # had many chances, earned nothing
        if reason:
            cs.reject_claim(h.id)
            pruned_ids.add(h.id)
            out["pruned"] += 1
            out[reason] += 1
            proto.record(cycle, "regulate",
                         f"shed {h.id}: {reason} (0 support) - a guess that did not pan out")

    # 2. cap the backlog: beyond the cap, reject the weakest (0-support, oldest) survivors.
    remaining = [h for h in hyps if h.id not in pruned_ids]
    if len(remaining) > max_live_hypotheses:
        excess = sorted(remaining, key=lambda c: int(c.id.split("-")[-1]))
        for h in excess[: len(remaining) - max_live_hypotheses]:
            if out["pruned"] >= max_prune + max_live_hypotheses or _supports_on(cs, h.id) > 0:
                continue
            cs.reject_claim(h.id)
            out["pruned"] += 1
            out["over_cap"] += 1
            proto.record(cycle, "regulate",
                         f"shed {h.id}: backlog over cap ({max_live_hypotheses})")
    return out


def _usable_semantic_rate(cs) -> float:
    clusters = [c for c in cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)
                if c.measurement.get("distance_metric") == "cosine"][-40:]
    if not clusters:
        return 0.0
    usable = sum(1 for c in clusters if c.decision.value != "insufficient-semantic-evidence")
    return round(usable / len(clusters), 3)


def vitality(cs, extensions: dict, proto, cycle: int = 0) -> dict:
    """Grade Joni's own trajectory: developing, steady, or degenerating. Deterministic."""
    s = cs.core
    active = len(cs.active_claims())
    links = len(s.all(l9.ObjectType.EVIDENCE_LINK))
    supports = sum(1 for el in s.all(l9.ObjectType.EVIDENCE_LINK)
                   if el.relation.value in ("supports", "contextualizes"))   # *validating* links
    hyps = len(cs.hypotheses())
    promoted = sum(1 for c in s.all(l9.ObjectType.CLAIM)
                   if c.status is Status.ACTIVE and c.derived_from)   # ideas that earned active
    confirmed = sum(1 for c in s.all(l9.ObjectType.CLAIM) if c.status is Status.CONFIRMED)
    emergent = len(extensions.get("emerged_topics", [])) + \
        len(extensions.get("emerged_methods", [])) + len(extensions.get("synthesized", []))
    usable = _usable_semantic_rate(cs)
    objects = len(s.objects)
    methods_total = len(s.all(l9.ObjectType.METHOD))
    method_trials_total = extensions.get("method_trials_total", 0)
    methods_ready_total = extensions.get("methods_ready_total", 0)

    prev = extensions.get("vitality_prev", {})
    d_supports = supports - prev.get("supports", supports)
    d_promoted = promoted - prev.get("promoted", promoted)
    d_confirmed = confirmed - prev.get("confirmed", confirmed)
    d_objects = objects - prev.get("objects", objects)

    # Development = *epistemic progress*, not raw growth. New validating evidence, ideas that
    # earned promotion, and (rare) confirmations count; merely learning/hearing more claims or
    # minting more emergent bookkeeping does NOT - so Joni cannot read his own noise as vital.
    development = 3 * max(0, d_supports) + 4 * max(0, d_promoted) + 6 * max(0, d_confirmed)
    stagnation = extensions.get("stagnation", 0)
    stagnation = 0 if development > 0 else stagnation + 1

    # degeneration signals: a swelling unsupported backlog, or a long stagnation, or bloat
    # with no development.
    unsupported = sum(1 for h in cs.hypotheses() if _supports_on(cs, h.id) == 0)
    degeneration = (1 if unsupported > 25 else 0) + (1 if stagnation >= 12 else 0) + \
        (1 if (d_objects > 30 and development == 0) else 0)

    if development > 0 and degeneration == 0:
        verdict = "developing"
    elif degeneration >= 1 and development == 0:
        verdict = "degenerating"
    else:
        verdict = "steady"

    record = {"verdict": verdict, "development": development, "degeneration": degeneration,
              "active": active, "hypotheses": hyps, "unsupported_hypotheses": unsupported,
              "promoted_ideas": promoted, "confirmed_claims": confirmed,
              "evidence_links": links, "supporting_links": supports,
              "emergent_total": emergent, "usable_semantic_rate": usable,
              "methods_total": methods_total, "method_trials_total": method_trials_total,
              "methods_ready_total": methods_ready_total,
              "stagnation_cycles": stagnation, "objects": objects, "cycle": cycle}
    extensions["vitality"] = record
    extensions["vitality_prev"] = {"supports": supports, "promoted": promoted,
                                   "confirmed": confirmed, "objects": objects,
                                   "active": active, "links": links, "emergent": emergent}
    extensions["stagnation"] = stagnation
    hist = extensions.setdefault("vitality_history", [])
    hist.append({"cycle": cycle, "verdict": verdict, "development": development,
                 "degeneration": degeneration, "usable_semantic_rate": usable})
    extensions["vitality_history"] = hist[-200:]
    proto.record(cycle, "vitality",
                 f"{verdict} · dev {development} · degen {degeneration} · "
                 f"{unsupported} unsupported idea(s) · semantic-usable {int(usable*100)}%")
    return record
