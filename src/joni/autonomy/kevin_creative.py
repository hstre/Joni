"""Run Kevin's REAL orchestrator (``kevin.orchestrator.Kevin``) inside Joni.

This is the actual product, not Joni's lightweight ``kevin_llm`` arm: Kevin's Dirigent routes
the full pass - DESi predicts WHERE the solution spaces are (blind-spot coverage = the
'probability islands'),
the wild brother (the LLM) varies inside the under-worked regions, Layer-9 methods discipline the
wildest variants, and epistemic selection keeps only the coherent / testable / connected ones.

The SELECTED candidates enter Layer 9 as NON-AUTHORITATIVE kevin/model-origin hypotheses (taint-
flagged, ``requires_review``); Kevin never confirms, resolves, activates or promotes. Boundary kept:
LLM for language, rules for logic - every score/verdict is Kevin's engine, not the LLM.

Runs ONLY with a real LLM client (``KEVIN_USE_REAL_LLM=1`` + a key) so no MockLLM candidate can ever
enter the authoritative core; a clean no-op otherwise. Cadence- and count-bounded.
"""

from __future__ import annotations

import os


def enabled() -> bool:
    """On only when a REAL Kevin LLM client is configured - the MockLLM must never seed the
    authoritative core. ``JONI_KEVIN_ORCHESTRATOR=0`` force-disables."""
    return (os.getenv("JONI_KEVIN_ORCHESTRATOR", "1") != "0"
            and os.getenv("KEVIN_USE_REAL_LLM") == "1")


def _every() -> int:
    return max(1, int(os.getenv("JONI_KEVIN_ORCH_EVERY", "6")))


def _known_approaches(cs) -> tuple[str, ...]:
    """What Joni has already worked - the method affinities on the shelf. DESi scores the blind
    spots as the axes these do NOT cover, so Kevin probes where the room actually is."""
    import desi_layer9 as l9
    affs = {a for m in cs.core.all(l9.ObjectType.METHOD)
            for a in (getattr(m, "applicable_to", ()) or ())}
    return tuple(sorted(affs)) or ("similarity baseline", "frequency counting")


def _problem_from(cs):
    """Build a Kevin ``Problem`` from Joni's richest live material: prefer the top DESi blind-spot
    conflict, else any open conflict, else a substantial topic. Returns ``(problem, topic)`` or
    ``None`` when there is no real input."""
    from kevin.models import Problem

    from . import kevin_trial_bridge as kb

    def _claims(ids):
        return [c for c in (cs.core.objects.get(i) for i in ids) if c is not None]

    known = _known_approaches(cs)
    for isl in kb.blind_spots(cs, top_k=3):              # 1. the highest-value DESi gap
        claims = _claims(isl.get("claim_ids", []))
        if len(claims) >= 2:
            topic = getattr(claims[0], "topic", "") or "epistemics"
            stmt = (f"Reconcile or find a discriminating test between: '{claims[0].text}' vs "
                    f"'{claims[1].text}'. DESi flags the missing thinking-move: "
                    f"'{isl['missing_affinity']}'.")
            return Problem(statement=stmt, domain=topic, known_approaches=known), topic, \
                tuple(c.id for c in claims[:2])
    for x in cs.core.open_conflicts():                   # 2. any open conflict
        claims = _claims(getattr(x, "claim_ids", ()))
        if len(claims) >= 2:
            topic = getattr(claims[0], "topic", "") or "epistemics"
            stmt = (f"Reconcile or find a discriminating test between: '{claims[0].text}' vs "
                    f"'{claims[1].text}'.")
            return Problem(statement=stmt, domain=topic, known_approaches=known), topic, \
                tuple(c.id for c in claims[:2])
    return None


def run(cs, extensions: dict, proto, cycle: int = 0, *, budget=None) -> dict:
    """One full Kevin creative pass on Joni's material; ingest the selected candidates as Layer-9
    candidate hypotheses. Cadence-bounded, deduped, never fatal to the cycle."""
    out = {"kevin_runs": 0, "candidates": 0, "ingested": 0}
    if not enabled():
        return out
    last = extensions.get("kevin_orch_last_cycle")
    if last is not None and cycle - last < _every():     # cadence bounds spend
        return out
    try:
        from kevin.llm_client import get_default_client
        from kevin.orchestrator import Kevin
    except Exception:  # noqa: BLE001 - kevin not installed: clean no-op
        return out
    built = _problem_from(cs)
    if built is None:
        return out
    problem, topic, parents = built
    try:
        creative = Kevin(llm=get_default_client()).run(problem, top_spaces=2)
    except Exception as exc:  # noqa: BLE001 - never let a creative pass break the cycle
        proto.record(cycle, "note", f"kevin orchestrator skipped: {exc}")
        return out

    out["kevin_runs"] = 1
    extensions["kevin_orch_last_cycle"] = cycle
    cand_by_id = {c.id: c for c in creative.candidates}
    seen = set(extensions.get("kevin_orch_seen", []))
    ingested = []
    for ev in sorted(creative.evaluations, key=lambda e: -getattr(e, "score", 0.0)):
        if getattr(ev, "verdict", None) != "promising":  # keep only what Kevin's selector promotes
            continue
        cand = cand_by_id.get(ev.candidate_id)
        text = (getattr(cand, "content", "") or "").strip()
        if not cand or not text:
            continue
        key = text[:120]
        if key in seen:                                  # per-content dedup across cycles
            continue
        seen.add(key)
        # derived from the conflict's own claims (so it shows as a hypothesis tied to that gap)
        hid = cs.hypothesize(text, topic, parents=parents, origin="kevin")
        ingested.append({"id": hid, "score": round(getattr(ev, "score", 0.0), 3),
                         "testability": round(getattr(ev, "testability", 0.0), 3)})
        if len(ingested) >= 2:                           # at most two per cycle
            break

    extensions["kevin_orch_seen"] = list(seen)[-500:]
    out["candidates"] = len(creative.candidates)
    out["ingested"] = len(ingested)
    sp = creative.space_prediction or {}
    extensions["kevin_orch"] = {
        "cycle": cycle, "domain": topic,
        "blind_spots": sp.get("blindspots") or sp.get("blind_spot_axes"),
        "seed_spaces": len(creative.spaces), "chosen": list(creative.chosen_spaces),
        "variants": len(creative.variants), "candidates": len(creative.candidates),
        "ingested": ingested}
    if ingested:
        proto.record(cycle, "kevin",
                     f"Kevin orchestrator (DESi spaces + wild brother) on '{topic}': "
                     f"{len(creative.spaces)} space(s) -> {len(creative.variants)} variant(s) -> "
                     f"{out['ingested']} promising candidate(s) ingested as non-authoritative "
                     f"hypotheses (require review)")
    return out
