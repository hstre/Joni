"""Strengthening Joni's *own* ideas - honestly.

A self-invented hypothesis starts as a weak candidate (support 0.4) and used to just sit
there. An idea does not get stronger by repetition; it gets stronger by surviving evidence
and challenge. Four mechanisms, all peripheral, gate-mediated and auditable - and none of
them ever *confirms* anything (that still needs an independent human):

  1. **Active testing** - the hypothesis is turned into a search query, and existing
     claims are tested against it via the DESi Semantic Layer: a governed *supports*
     attaches evidence (the idea earns weight); a governed *contradictory/tension* opens a
     conflict (the idea is challenged), never smoothed away.
  2. **Earned ladder** - a hypothesis is promoted candidate -> ACTIVE (a *working* idea,
     not a fact) only once it has >=2 independent governed supports and no open hard
     contradiction.
  3. **Adversarial self-challenge** - Joni looks for the strongest counter to his own idea;
     surviving scrutiny is recorded as earned, being contradicted demotes it.
  4. **Kevin vetting (advisory only)** - the idea is run through Kevin's epistemic selection
     (coherence / testability / connectivity / "not just pretty"). The verdict is **recorded
     as advice and shown**, but it never decides anything: Kevin must never decide. Promotion
     is settled by the deterministic ladder (mechanisms 1-2) and a human still confirms.

Bounded per cycle and deduped, so it works through the hypotheses over time.
"""

from __future__ import annotations

import os

from desi_layer9 import SemanticDecision
from desi_layer9.semantics import adapter, lexical_overlap
from desi_layer9.semantics.ports import NullSemanticLayer

from ..conflict import _content

# #132 - when the deterministic Semantic Layer returns 'insufficient' it decides nothing, so ideas
# never earn support and development stays at 0 (the 'degenerating' stall). A gated LLM relation
# judge renders the decision in that case, so an idea can EARN support from REAL evidence (the
# claim's own source/provenance, not the LLM's say-so). Promotion still needs >=2 INDEPENDENT
# supports and a human still confirms - the LLM only judges the relation, never auto-activates.
_REL_SYS = (
    "You judge the logical relation between an agent's working HYPOTHESIS and an existing CLAIM. "
    "Answer with exactly ONE word: SUPPORTS (the claim is evidence FOR the hypothesis), "
    "CONTRADICTS "
    "(evidence AGAINST it), or UNRELATED. Judge meaning, be strict; if unsure, answer UNRELATED."
)


def _llm_judge_budget() -> int:
    """How many LLM relation judgments strengthen may make this cycle (0 = off). Opt-out via
    JONI_STRENGTHEN_LLM=0; gated like every model arm (needs the semantic-proposals layer)."""
    from . import projection
    if not (projection.enabled() and os.getenv("JONI_STRENGTHEN_LLM", "1") != "0"):
        return 0
    return max(0, int(os.getenv("JONI_STRENGTHEN_LLM_MAX", "2")))


def _llm_relation(h_text: str, c_text: str, *, budget, runs_per_week: int,
                  cycle: int) -> str | None:
    """'supports' | 'contradicts' | 'unrelated' | None (model/budget unavailable). Captured."""
    from . import model_call, model_profile
    from .config import paths
    out, _cap = model_call.call(
        model_profile.profile("joni-hard"), _REL_SYS,
        f"HYPOTHESIS: {h_text}\nCLAIM: {c_text}\n\nRelation? SUPPORTS / CONTRADICTS / UNRELATED.",
        run_id=f"joni-c{cycle}-strrel", store_dir=paths().model_calls,
        escalation_reason="strengthen-relation-judge", budget=budget, runs_per_week=runs_per_week)
    if not out:
        return None
    t = out.strip().upper()
    if "SUPPORT" in t:
        return "supports"
    if "CONTRADICT" in t:
        return "contradicts"
    if "UNRELATED" in t:
        return "unrelated"
    return None


_TRIGGER = 0.2          # be more eager than develop: we *want* to test ideas
_SUPPORTS_FOR_ACTIVE = 2
_INDEP_SOURCES_FOR_ACTIVE = 2   # candidate -> active needs >=2 *independent* origins (or an
#                                 external evidence card) - not claim-to-claim circularity
_MAX_INSUFFICIENT_RETRIES = 3   # a layer-absent non-judgment is retried this often, not burned


def _kevin_verdict(text: str, topic: str):
    """Kevin's epistemic-selection verdict for an idea, or None if Kevin is unavailable.

    Uses Kevin's REAL client (``get_default_client``) and only runs when one is configured
    (``KEVIN_USE_REAL_LLM=1`` + key) - the same gate as ``kevin_creative``. We never run the
    MockLLM here: a fabricated verdict shown as Kevin's advice would be a lie. Without a real
    client this is a clean no-op (None) and the deterministic ladder decides alone - Kevin's
    verdict is advisory and never gates promotion anyway.
    """
    import os
    if os.getenv("KEVIN_USE_REAL_LLM") != "1":
        return None
    try:
        from kevin.llm_client import get_default_client
        from kevin.models import Candidate, Problem
        from kevin.selector import Selector
    except Exception:  # noqa: BLE001 - Kevin is an optional vetting partner
        return None
    try:
        cand = Candidate(content=text, space_id="hyp", variant_id="h")
        ev = Selector(get_default_client()).evaluate(Problem(statement=topic or text), cand)
        return ev.verdict.value          # "promising" | "tentative" | "rejected"
    except Exception:  # noqa: BLE001
        return None


def _supports_on(cs, claim_id: str) -> int:
    from desi_layer9 import ObjectType
    return sum(1 for el in cs.core.all(ObjectType.EVIDENCE_LINK)
               if el.claim_id == claim_id and el.relation.value in ("supports", "contextualizes"))


def _hard_conflict_on(cs, claim_id: str) -> bool:
    return any(claim_id in x.claim_ids and x.severity == "hard" for x in cs.core.open_conflicts())


def _independently_supported(cs, claim_id: str) -> bool:
    """Enough independent backing to promote: >=2 distinct source families, or >=1 external
    evidence card. A pile of mutually-supporting claims from one origin is NOT enough. Uses
    CoreState.supporter_families (the single source of truth for source-independence)."""
    families, external = cs.supporter_families(claim_id)
    return len(families) >= _INDEP_SOURCES_FOR_ACTIVE or external >= 1


def strengthen(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
               max_hyp: int = 2, max_tests: int = 3, budget=None,
               runs_per_week: int = 0) -> dict:
    layer = layer or NullSemanticLayer()
    # The reconstruction-trick plausibility ranker (Auftrag #135) refines an ambiguous conflict's
    # kind; opt-in (default off), bounded to one ranking per cycle, the weekly budget the ceiling.
    from . import plausibility
    conflict_ranker = plausibility.ranker_for(budget=budget, runs_per_week=runs_per_week,
                                              cycle=cycle, max_calls=1)
    llm_left = _llm_judge_budget()     # #132: gated LLM relation judgments left this cycle
    # Plateau lever: ideas Doktores judged internally COHERENT may mature on thinner evidence.
    coherent_ids = {e.get("hypothesis") for e in extensions.get("doktores_hyp_log", [])
                    if isinstance(e, dict) and e.get("coherent") and e.get("hypothesis")}
    hyps = cs.hypotheses()
    out = {"tested": 0, "supported": 0, "challenged": 0, "survived": 0,
           "promoted": 0, "rejected": 0, "insufficient": 0}
    if not hyps:
        return out

    tested = set(extensions.get("hyp_tested", []))
    insufficient = dict(extensions.get("hyp_insufficient", {}))
    hollow = set(extensions.get("hyp_hollow", []))
    learned = list(extensions.get("learned_queries", []))
    seen_cycle = dict(extensions.get("hyp_seen_cycle", {}))
    # Fair rotation: attend the *least-recently-strengthened* hypotheses first, so support
    # spreads across all ideas. A fixed oldest-id order let the oldest hypothesis hog the only
    # slot every cycle while the other 30 starved. Kevin's advisory verdict does NOT influence
    # the order - it must never shape outcomes, only inform.
    # Plateau-breaker: prefer hypotheses Doktores judged COHERENT so the ones that CAN mature on
    # >=1 support (the coherence lever) earn their support first - closes the coherent-but-
    # unsupported gap. Coherence is Doktores' measured verdict, not an outcome shortcut.
    def _idnum(c) -> int:
        return int(c.id.split("-")[-1])
    chosen = sorted(hyps, key=lambda c: (c.id not in coherent_ids, seen_cycle.get(c.id, -1),
                                         _idnum(c)))[:max_hyp]
    for h in chosen:
        seen_cycle[h.id] = cycle

    for h in chosen:
        # a query so Joni actively seeks outside evidence about his own idea
        terms = [w for w in _content(h.text) if len(w) > 4][:2]
        for q in (f"{h.topic} {t}".strip() for t in terms):
            if q and q not in learned:
                learned.append(q)

        # Kevin vetting - ADVISORY ONLY. Kevin's reservation is recorded (and shown), but it
        # never blocks promotion or deletes an idea; the rules decide. Kevin must never decide.
        verdict = _kevin_verdict(h.text, h.topic)
        if verdict == "rejected":
            hollow.add(h.id)
            out["rejected"] += 1
            proto.record(cycle, "strengthen",
                         f"Kevin advises {h.id} looks thin (advisory) - the rules still decide")

        # test the idea against existing claims via the Semantic Layer
        candidates = [c for c in cs.active_claims()
                      if c.id not in h.derived_from and c.id != h.id]
        candidates.sort(key=lambda c: -lexical_overlap(h.text, c.text))
        n = 0                # analyses attempted this cycle (cost bound)
        real = 0             # analyses that returned a real Layer-9 judgment
        challenged_here = False
        for c in candidates:
            if n >= max_tests:
                break
            trig = lexical_overlap(h.text, c.text)
            if trig < _TRIGGER:
                break
            key = f"{h.id}|{c.id}"
            if key in tested:
                continue
            if insufficient.get(key, 0) >= _MAX_INSUFFICIENT_RETRIES:
                tested.add(key)              # had several fair chances at a judgment - finalise
                insufficient.pop(key, None)
                continue
            n += 1
            sc = adapter.analyse_pair(cs.core, h, c, layer=layer, lexical_trigger=trig,
                                      run_id=f"joni-c{cycle}-str")
            out["tested"] += 1
            d = sc.decision
            # 'insufficient' is *not a judgment* (the layer could not decide) - never let it
            # permanently consume the pair. Retry it (bounded) on a later cycle, when the
            # Semantic Layer may render a real decision. Layer 9 still governs every support.
            if d is SemanticDecision.INSUFFICIENT:
                # #132: the deterministic layer could not decide. When a gated LLM judge is
                # available (bounded per cycle, budget-metered), let it render the relation so the
                # idea can earn support from this REAL claim (its own source is the evidence);
                # else keep the bounded-retry as before. Promotion still needs >=2 independent
                # supports; a human still confirms. The LLM judges the relation, not promotion.
                rel = None
                if llm_left > 0:
                    llm_left -= 1
                    rel = _llm_relation(h.text, c.text, budget=budget,
                                        runs_per_week=runs_per_week, cycle=cycle)
                if rel is None:
                    insufficient[key] = insufficient.get(key, 0) + 1
                    out["insufficient"] += 1
                    continue
                tested.add(key)
                insufficient.pop(key, None)
                real += 1
                if rel == "supports":
                    cs.corroborate(h.id, c, relation="supports")
                    out["supported"] += 1
                    proto.record(cycle, "strengthen",
                                 f"idea {h.id} earned support from {c.id} (LLM-judged relation; "
                                 "evidence is the claim's own source)")
                elif rel == "contradicts":
                    from .qualify import qualify_conflict
                    ck = qualify_conflict(h.text, c.text, severity="soft", ranker=conflict_ranker)
                    cid = cs.open_conflict((h.id, c.id), severity="soft", conflict_kind=ck)
                    out["challenged"] += 1
                    challenged_here = True
                    proto.record(cycle, "strengthen",
                                 f"idea {h.id} challenged by {c.id} (LLM-judged, {ck}) -> {cid}")
                continue
            tested.add(key)                  # a real Layer-9 decision was rendered
            insufficient.pop(key, None)
            real += 1
            if d in (SemanticDecision.SUPPORTS, SemanticDecision.COMPLEMENTARY):
                cs.corroborate(h.id, c, relation="supports")
                out["supported"] += 1
                proto.record(cycle, "strengthen",
                             f"idea {h.id} earned support from {c.id} ({d.value})")
            elif d in (SemanticDecision.CONTRADICTORY, SemanticDecision.TENSION):
                from .qualify import qualify_conflict
                sev = "hard" if d is SemanticDecision.CONTRADICTORY else "soft"
                ck = qualify_conflict(h.text, c.text, severity=sev,
                                      contradictory=(d is SemanticDecision.CONTRADICTORY),
                                      ranker=conflict_ranker)
                cid = cs.open_conflict((h.id, c.id), severity=sev, conflict_kind=ck)
                out["challenged"] += 1
                challenged_here = True
                proto.record(cycle, "strengthen",
                             f"idea {h.id} challenged by {c.id} ({ck}) -> {cid}")

        # adversarial self-challenge: a *real* judgment was rendered and none contradicted
        if real and not challenged_here:
            out["survived"] += 1
            proto.record(cycle, "strengthen",
                         f"idea {h.id} survived {real} challenge(s) - no contradiction found")

        # earned ladder: candidate -> active once the rules are met. Standard bar: >=2 INDEPENDENT
        # supports (distinct source families or an external card), no open hard contradiction.
        # PLATEAU LEVER (opt-out JONI_PROMOTE_ON_COHERENCE=0): an idea Doktores judged internally
        # COHERENT may mature on just >=1 independent support - thinner evidence, deliberately a
        # little into the risk, but coherence-gated, still ACTIVE not confirmed, and fully
        # reversible: a wrong call shows up as a contradiction/degeneration and homeostasis demotes
        # it, and Joni's introspection reflects it. Kevin's advisory verdict is never a gate here.
        families, external = cs.supporter_families(h.id)
        sup = _supports_on(cs, h.id)
        independent = len(families) >= _INDEP_SOURCES_FOR_ACTIVE or external >= 1
        standard = sup >= _SUPPORTS_FOR_ACTIVE and independent
        coherent = os.getenv("JONI_PROMOTE_ON_COHERENCE", "1") != "0" and h.id in coherent_ids
        lever = coherent and sup >= 1 and (len(families) >= 1 or external >= 1)
        if not _hard_conflict_on(cs, h.id) and (standard or lever):
            cs.activate_claim(h.id)
            out["promoted"] += 1
            how = ("earned >=2 independent supports" if standard
                   else "Doktores-coherent + 1 independent support")
            aside = " (Kevin flagged it thin - advisory)" if h.id in hollow else ""
            proto.record(cycle, "strengthen",
                         f"idea {h.id} promoted candidate -> active ({how}, unchallenged) - "
                         f"a working idea, not confirmed{aside}")

    extensions["hyp_tested"] = sorted(tested)[-4000:]
    extensions["hyp_insufficient"] = dict(sorted(insufficient.items())[-4000:])
    extensions["hyp_hollow"] = sorted(hollow)[-1000:]
    extensions["learned_queries"] = learned[-8:]
    # keep the rotation clock only for live hypotheses (drop ids that have left the set)
    live_ids = {c.id for c in hyps}
    extensions["hyp_seen_cycle"] = {k: v for k, v in seen_cycle.items() if k in live_ids}
    return out
