"""Kevin's creative arm - divergence, far-analogies, method transfer, unusual hypotheses.

**Architecture rule (revised): the hurdle is on ADOPTION of a Kevin proposal, not on its
GENERATION.** Kevin is not a confirmation or literature-management module; new ideas and single
papers naturally have no second independent source yet. So Kevin may work from ANY ONE substantial
input - a single rich topic, an open conflict, a single-source research candidate, or two weak
topics for a far-analogy - and the epistemic gates live downstream (expert panel + Layer 9 +
method trial), never at his input.

Every Kevin output stays a **non-authoritative candidate proposal**: it enters Layer 9 as a
CANDIDATE hypothesis with **model/kevin provenance** (so it is taint-flagged and cannot reach an
authoritative status without an explicit human validation), carrying ``input_type``,
``source_count`` and a ``confirmation_ceiling`` (single-source ⇒ ``provisional``) that limits later
*promotion*, not his access. Kevin never confirms, resolves, activates or promotes anything.

Low input hurdle does NOT mean dauerfeuer: bounded by cadence, budget, per-input dedup+cooldown and
at most two proposals per cycle. Only technical non-inputs (empty / unparseable / garbage) are
blocked - internal incoherence is recorded as *metadata*, never a reason to refuse Kevin (a
contradictory text is often the most fertile creative material).
"""

from __future__ import annotations

import hashlib
import os

from . import model_call, model_profile, projection
from .config import paths

_SYS = (
    "You are Kevin, a creative research partner for an epistemic reasoning agent. Your job is "
    "DIVERGENCE: bold far-analogies, method transfer, counter-models and unusual but TESTABLE "
    "hypotheses. You may be wrong - that is allowed; downstream review catches it. Output ONLY a "
    "JSON array of at most 2 objects {\"text\": <one falsifiable conjecture>, \"topic\": <short "
    "topic>}. Each is a single declarative, checkable statement - creative but concrete, no "
    "opinions, no meta-commentary, no questions.")

# The closed set of input types Kevin may fire on (visible in the capture + proposal + site).
INPUT_TYPES = ("cross_topic_analogy", "open_conflict", "single_topic_method_exploration",
               "single_source_research_candidate")


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_KEVIN_LLM", "1") != "0"


def _every() -> int:
    """Cadence: at most one creative call per this many cycles - bounds spend, not creativity."""
    return max(1, int(os.getenv("JONI_KEVIN_EVERY", "3")))


def _is_synthetic(text: str) -> bool:
    from .emerge import _is_synthetic as _s
    return _s(text)


def _real_claims(cs, topic: str) -> list:
    """Non-synthetic (not Joni's own 'X recurs as a through-line' bookkeeping) claims on a topic."""
    return [c for c in cs.claims_on(topic) if not _is_synthetic(c.text)]


def _usable_topic(cs, topic: str) -> bool:
    """SUBSTANTIAL, not research-grade: a lexically meaningful topic with >=2 non-synthetic claims.
    No second-source / confirmed-claim / coherence requirement - those gate adoption, not access."""
    from . import quality
    return quality.is_good_topic(topic) and len(_real_claims(cs, topic)) >= 2


def _source_count(claims) -> int:
    fams = set()
    for c in claims:
        for s in (getattr(c.provenance, "source_ids", ()) or ()):
            fams.add(str(s).split(":", 1)[0])
    return len(fams)


def _select_input(cs):
    """Pick Kevin's creative input by TYPE - any one substantial input suffices. Returns
    ``(input_type, label, seed_claims)`` or ``(None, None, None)`` when there is no real input."""
    usable = [t for t in cs.topics() if _usable_topic(cs, t)]
    if len(usable) >= 2:                                   # a far-analogy across two topics
        a, b = usable[0], usable[1]
        seeds = _real_claims(cs, a)[:3] + _real_claims(cs, b)[:3]
        return "cross_topic_analogy", f"{a} × {b}", seeds
    conflicts = [x for x in cs.core.open_conflicts()]
    if conflicts:                                  # an open conflict = rich creative material
        x = conflicts[0]
        seeds = [cs.core.objects.get(cid) for cid in x.claim_ids]
        seeds = [c for c in seeds if c is not None]
        if seeds:
            return "open_conflict", f"conflict {x.id}", seeds[:4]
    if len(usable) == 1:                           # a single rich topic -> method/lens transfer
        a = usable[0]
        return "single_topic_method_exploration", a, _real_claims(cs, a)[:4]
    relaxed = cs.research_topics(min_sources=1)           # a single-source research candidate
    if relaxed:
        a = relaxed[0]
        return "single_source_research_candidate", a, cs.claims_on(a)[:4]
    return None, None, None


def _user_prompt(input_type: str, label: str, seeds) -> str:
    lines = "\n".join(f"- {c.text}" for c in seeds)
    if input_type == "cross_topic_analogy":
        ask = "Propose a bold cross-domain transfer linking these two areas."
    elif input_type == "open_conflict":
        ask = ("These claims CONTRADICT. Propose a testable hypothesis that could reconcile them, "
               "or a discriminating mechanism/experiment that would tell which holds.")
    else:
        ask = ("Propose a bold far-analogy or a transferable method/lens from a DISTANT field that "
               "might apply to this material.")
    return f"INPUT TYPE: {input_type}\nMATERIAL ({label}):\n{lines}\n\n{ask}"


def _input_hash(input_type: str, seeds) -> str:
    key = input_type + "|" + "|".join(sorted(getattr(c, "id", "") for c in seeds))
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def propose(cs, extensions: dict, proto, cycle: int, *, budget=None,
            runs_per_week: int = 0) -> dict:
    """Let Kevin make at most one creative proposal per cadence from any single substantial input.
    The proposal enters Layer 9 as a non-authoritative ``candidate`` (kevin/model provenance) and is
    audited downstream. No-op when disabled, not yet due, recently-seen input, or no real input."""
    out = {"kevin_calls": 0, "hypotheses": 0}
    if not enabled():
        return out
    last = extensions.get("kevin_last_cycle")
    if last is not None and cycle - last < _every():      # cadence bounds spend
        return out

    input_type, label, seeds = _select_input(cs)
    if not input_type or not seeds:                       # only technical non-inputs are blocked
        return out
    ihash = _input_hash(input_type, seeds)
    seen = extensions.get("kevin_inputs_seen", [])
    if ihash in seen:                                     # per-input dedup + cooldown
        extensions["kevin_last_cycle"] = cycle     # respect cadence; wait for a new input
        return out

    src = _source_count(seeds)
    contradictory = input_type == "open_conflict" or any(
        set(getattr(c, "id", "") for c in seeds) & set(x.claim_ids)
        for x in cs.core.open_conflicts())
    meta = {
        "input_type": input_type, "trigger": label, "input_hash": ihash,
        "source_count": src,
        "internal_coherence": "contradictory" if contradictory else "coherent",
        # the ceiling limits later PROMOTION, never Kevin's access:
        "confirmation_ceiling": "provisional" if src <= 1 else "activation",
        "external_corroboration": "missing" if src <= 1 else "present",
        "origin": "kevin", "authority": "none", "requires_review": True,
    }

    prof = model_profile.profile("kevin")
    output, cap = model_call.call(prof, _SYS, _user_prompt(input_type, label, seeds),
                                  run_id=f"kevin-c{cycle}", store_dir=paths().model_calls,
                                  budget=budget, runs_per_week=runs_per_week)
    if output is None or cap is None:
        return out
    out["kevin_calls"] = 1
    extensions["kevin_last_cycle"] = cycle
    extensions["kevin_inputs_seen"] = (seen + [ihash])[-500:]
    props = projection._parse(output, label)
    log = extensions.setdefault("kevin_llm", [])

    if not output.strip() or not props:
        reason = "empty (model truncation?)" if not output.strip() else "no parseable proposal"
        log.append({"call_id": cap.call_id, "served_model": cap.served_model, "cycle": cycle,
                    "replayed": cap.replayed, "failed": reason, "content_len": len(output),
                    "proposals": [], **meta})
        extensions["kevin_llm"] = log[-200:]
        proto.record(cycle, "kevin",
                     f"Kevin ({cap.served_model}) [{input_type}:{label}] produced NO proposal: "
                     f"{reason} (content_len={len(output)})")
        return out

    parents = tuple(getattr(c, "id", "") for c in seeds[:2] if getattr(c, "id", ""))
    ids = []
    for p in props[:2]:
        # NON-AUTHORITATIVE: kevin/model-origin candidate hypothesis (taint-flagged; the ceiling +
        # the panel + Layer 9 gate adoption). Kevin never confirms/resolves/promotes.
        ids.append(cs.hypothesize(p["text"], p["topic"], parents=parents, origin="kevin"))
        out["hypotheses"] += 1
    log.append({"call_id": cap.call_id, "served_model": cap.served_model, "cycle": cycle,
                "replayed": cap.replayed,
                "proposals": [{"id": i, "text": p["text"], "topic": p["topic"]}
                              for i, p in zip(ids, props[:2], strict=False)], **meta})
    extensions["kevin_llm"] = log[-200:]
    proto.record(cycle, "kevin",
                 f"Kevin ({cap.served_model}) [{input_type}:{label}] proposed {len(props)} "
                 f"candidate hyp(s) · sources={src} · ceiling={meta['confirmation_ceiling']}"
                 f" · coherence={meta['internal_coherence']} - non-authoritative, panel + Layer 9 "
                 "decide")
    return out
