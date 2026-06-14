"""From reading to self-improvement - under the DESi rule.

Joni reads what the sources return, judges relevance deterministically (cheapest tier,
free), and turns what advances him into improvements. Governance then splits them:

  * peripheral improvements (track a new topic, note a capability) he builds into
    himself autonomously - data-level changes that never touch protected logic;
  * anything that would require changing the core (a new operator, a different router
    algorithm) becomes an **ask** - recorded, raised as a GitHub issue by the workflow,
    and left for a human. Joni never self-applies it.

All deterministic: relevance is token overlap with Joni's current topics; the core/
peripheral split is a fixed rule. No model is needed to decide what he may do.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import ClaimStatus, Trigger
from ..operators import assert_claim, form_preference
from ..state import Layer9
from . import governance
from .sources import Item

# Salient terms that, if seen and not already tracked, are worth tracking as a topic.
NEW_TOPIC_HINTS = frozenset({
    "calibration", "retrieval", "quantization", "quantisation", "alignment",
    "provenance", "caching", "evaluation", "benchmarking", "distillation",
})

# Terms implying a change would touch core *logic* - ask-only, never self-applied.
CORE_TRIGGERS = frozenset({
    "operator", "operators", "scoring", "router algorithm", "deterministic core",
    "conflict resolution", "ledger format", "state machine",
})


def _content(text: str) -> set[str]:
    return {w.strip(".,;:!?'\"()").lower() for w in text.split() if len(w) > 3}


@dataclass
class Relevance:
    relevant: bool
    topic: str | None        # matched existing topic
    new_topic: str | None    # a salient untracked term, if any


def judge(state: Layer9, item: Item) -> Relevance:
    """Deterministic relevance: does this touch what Joni already works on?"""
    text = _content(item.title + " " + item.summary)
    known = state.topics()
    best, best_overlap = None, 0
    for topic in known:
        overlap = len(text & _content(topic + " " + " ".join(
            c.text for c in state.claims_on(topic))))
        if overlap > best_overlap:
            best, best_overlap = topic, overlap
    new_topic = next((t for t in sorted(text & NEW_TOPIC_HINTS) if t not in known), None)
    return Relevance(relevant=bool(best_overlap) or new_topic is not None,
                     topic=best if best_overlap else None, new_topic=new_topic)


@dataclass
class Improvement:
    kind: str            # track_topic | note_capability | core_change
    title: str
    target: str
    rationale: str
    source_key: str
    source_url: str

    @property
    def autonomous(self) -> bool:
        return governance.is_autonomous(self.kind)


def derive(state: Layer9, judged: list[tuple[Item, Relevance]]) -> list[Improvement]:
    """Derive at most a few improvements from this run's relevant reading."""
    out: list[Improvement] = []
    seen_kinds: set[str] = set()

    for item, rel in judged:
        blob = (item.title + " " + item.summary).lower()

        # Core asks take priority - we must never quietly self-apply these.
        if any(trigger in blob for trigger in CORE_TRIGGERS):
            out.append(Improvement(
                "core_change", item.title,
                next((t for t in CORE_TRIGGERS if t in blob), "core"),
                "reading suggests a change to protected core logic - needs human approval",
                item.key, item.url))
            continue

        if rel.new_topic and "track_topic" not in seen_kinds:
            out.append(Improvement(
                "track_topic", rel.new_topic, rel.new_topic,
                f"recurring untracked term '{rel.new_topic}' worth following",
                item.key, item.url))
            seen_kinds.add("track_topic")

    # One capability note per run if any HN/routing-flavoured item showed up.
    routing = next((i for i, r in judged if "rout" in (i.title + i.summary).lower()), None)
    if routing is not None:
        out.append(Improvement(
            "note_capability", "frugal model routing", "router-note",
            "external corroboration that cheap-first routing with adequacy checks pays off",
            routing.key, routing.url))
    return out


# Which protected component each core trigger touches, and what changing it would risk.
_COMPONENT = {
    "operator": "a Layer-9 operator (the closed set of state-change actions)",
    "operators": "a Layer-9 operator (the closed set of state-change actions)",
    "scoring": "the deterministic scoring / belief-weighing logic",
    "router algorithm": "the DESi routing logic (which model is chosen)",
    "deterministic core": "the deterministic core engine",
}
_RISK = {
    "operator": "high — operators are the only write path; a change affects every state mutation",
    "operators": "high — operators are the only write path; a change affects every state mutation",
    "scoring": "high — changes how beliefs are weighed and could shift every verdict",
    "router algorithm": "medium-high — changes model routing and cost behaviour",
    "deterministic core": "high — changes the engine that replay depends on",
}


def structured_ask(imp: Improvement, cycle: int) -> dict:
    """A structured core-ask for a human: which component, what change, evidence, risk, and
    whether it is just an observation or a concrete request. ``derive`` only ever produces
    an *observation* (a reading suggests something), never a worked-out change, so we say so
    honestly - a human turns it into a request."""
    component = _COMPONENT.get(imp.target, "protected core logic")
    return {
        "kind": imp.kind, "cycle": cycle,
        "request_type": "observation",          # an idea raised, not a worked-out change request
        "component": component, "target": imp.target,
        "proposed_change": (f"A source touches '{imp.target}'. Adopting its idea would change "
                            f"{component} — the concrete change is not specified; a human must "
                            "design it."),
        "evidence": {"source_title": imp.title[:200], "source_url": imp.source_url,
                     "source_key": imp.source_key},
        "risk": _RISK.get(imp.target, "high — touches protected core logic"),
        "rationale": imp.rationale,
        "source_url": imp.source_url,           # kept for backward compatibility
    }


def apply_peripheral(state: Layer9, extensions: dict, imp: Improvement) -> dict:
    """Build a peripheral improvement into Joni himself. Returns ledger refs.

    Raises if asked to apply a non-autonomous (core) kind - that path must go through
    an ask, never here.
    """
    if not imp.autonomous:
        raise governance.CoreChangeBlocked(
            f"refusing to self-apply core-touching improvement: {imp.kind}")

    if imp.kind == "track_topic":
        claim = assert_claim(
            state, f"{imp.target} is worth tracking as a topic", imp.target,
            support=0.55, status=ClaimStatus.ACTIVE, trigger=Trigger.RESEARCH_HARVEST,
            reviewed_by="deterministic")
        extensions.setdefault("topics_added", [])
        if imp.target not in extensions["topics_added"]:
            extensions["topics_added"].append(imp.target)
        return {"claim": claim.id, "topic": imp.target}

    if imp.kind == "note_capability":
        pref = form_preference(state, imp.target, "values", strength=0.6,
                               reviewed_by="deterministic")
        extensions.setdefault("notes", [])
        extensions["notes"].append({"note": imp.rationale, "source": imp.source_url})
        return {"preference": pref.id}

    return {}
