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

from desi_layer9 import SemanticDecision
from desi_layer9.semantics import adapter, lexical_overlap
from desi_layer9.semantics.ports import NullSemanticLayer

from ..conflict import _content

_TRIGGER = 0.2          # be more eager than develop: we *want* to test ideas
_SUPPORTS_FOR_ACTIVE = 2
_MAX_INSUFFICIENT_RETRIES = 3   # a layer-absent non-judgment is retried this often, not burned


def _kevin_verdict(text: str, topic: str):
    """Kevin's epistemic-selection verdict for an idea, or None if Kevin is unavailable."""
    try:
        from kevin.llm_client import MockLLM
        from kevin.models import Candidate, Problem
        from kevin.selector import Selector
    except Exception:  # noqa: BLE001 - Kevin is an optional vetting partner
        return None
    try:
        cand = Candidate(content=text, space_id="hyp", variant_id="h")
        ev = Selector(MockLLM()).evaluate(Problem(statement=topic or text), cand)
        return ev.verdict.value          # "promising" | "tentative" | "rejected"
    except Exception:  # noqa: BLE001
        return None


def _supports_on(cs, claim_id: str) -> int:
    from desi_layer9 import ObjectType
    return sum(1 for el in cs.core.all(ObjectType.EVIDENCE_LINK)
               if el.claim_id == claim_id and el.relation.value in ("supports", "contextualizes"))


def _hard_conflict_on(cs, claim_id: str) -> bool:
    return any(claim_id in x.claim_ids and x.severity == "hard" for x in cs.core.open_conflicts())


def strengthen(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
               max_hyp: int = 2, max_tests: int = 3) -> dict:
    layer = layer or NullSemanticLayer()
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
    def _idnum(c) -> int:
        return int(c.id.split("-")[-1])
    chosen = sorted(hyps, key=lambda c: (seen_cycle.get(c.id, -1), _idnum(c)))[:max_hyp]
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
                insufficient[key] = insufficient.get(key, 0) + 1
                out["insufficient"] += 1
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
                                      contradictory=(d is SemanticDecision.CONTRADICTORY))
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

        # earned ladder: candidate -> active once the *rules* are met - enough independent
        # governed support and no open hard contradiction. Kevin's verdict is not a gate here:
        # an idea that earned its support is promoted even if Kevin called it thin.
        if (_supports_on(cs, h.id) >= _SUPPORTS_FOR_ACTIVE
                and not _hard_conflict_on(cs, h.id)):
            cs.activate_claim(h.id)
            out["promoted"] += 1
            aside = " (Kevin flagged it thin - advisory)" if h.id in hollow else ""
            proto.record(cycle, "strengthen",
                         f"idea {h.id} promoted candidate -> active (earned support, "
                         f"unchallenged) - a working idea, not confirmed{aside}")

    extensions["hyp_tested"] = sorted(tested)[-4000:]
    extensions["hyp_insufficient"] = dict(sorted(insufficient.items())[-4000:])
    extensions["hyp_hollow"] = sorted(hollow)[-1000:]
    extensions["learned_queries"] = learned[-8:]
    # keep the rotation clock only for live hypotheses (drop ids that have left the set)
    live_ids = {c.id for c in hyps}
    extensions["hyp_seen_cycle"] = {k: v for k, v in seen_cycle.items() if k in live_ids}
    return out
