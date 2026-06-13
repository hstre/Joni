"""The renderer - where the two views are produced together.

Given a prompt, the renderer reads Layer 9 deterministically, composes a first-person
**brief** grounded entirely in state, routes it for phrasing, and emits a ``Response``
carrying *both* views:

  * Conversation View - the brief, phrased in voice: the seemingly autonomous figure.
  * Epistemic View - the exact claims, goals, memory, operator, trigger, reviewer and
    ledger event behind it: why the figure said that.

The content is decided here by rules; a model only gives the brief a mouth. So the
personhood is always one click away from being dissolved into its receipts.
"""

from __future__ import annotations

from .memory import recall
from .model_client import ModelClient
from .models import ClaimStatus, EpistemicTrace, Response
from .router import Router
from .state import Layer9


def _tokens(text: str) -> set[str]:
    return {w.strip(".,;:!?'\"()").lower() for w in text.split() if len(w) > 3}


def _best_topic(state: Layer9, prompt: str) -> str | None:
    """The topic whose claims best match the prompt (deterministic)."""
    q = _tokens(prompt)
    best, best_score = None, 0
    for topic in state.topics():
        text = topic + " " + " ".join(c.text for c in state.claims_on(topic))
        score = len(q & _tokens(text))
        # Tie-break on topic name keeps it replay-stable.
        if score > best_score or (score == best_score and best is None and score > 0):
            best, best_score = topic, score
    return best or (state.topics()[0] if state.topics() else None)


def respond(state: Layer9, router: Router, model: ModelClient, prompt: str) -> Response:
    topic = _best_topic(state, prompt)

    # Gather the grounding state for this topic.
    on_topic = state.claims_on(topic) if topic else []
    active = sorted(
        (c for c in on_topic if c.status in {ClaimStatus.ACTIVE, ClaimStatus.CONFIRMED}),
        key=lambda c: (-c.support, c.id),
    )
    rejected = sorted(
        (c for c in on_topic if c.status is ClaimStatus.REJECTED and c.history),
        key=lambda c: -c.last_changed_tick,
    )
    goals = sorted(state.active_goals(), key=lambda g: (-g.priority, g.id))
    prefs = [p for p in state.preferences.values() if p.subject == topic or topic in p.subject]
    episodes = recall(state, prompt or (topic or ""), limit=2)

    # Compose the first-person brief - grounded, deterministic.
    lines: list[str] = []
    claim_refs: list[str] = []
    trace_operator = trace_trigger = trace_ledger = None
    reviewed_by = "deterministic"

    if active:
        c = active[0]
        lines.append(f"On {topic}, I currently hold that {c.text.lower()}.")
        claim_refs.append(c.id)

    if rejected:
        r = rejected[0]
        last = r.history[-1]
        lines.append(
            f"I used to think {r.text.lower()}, but I have since rejected that "
            f"({last.trigger}, reviewed by {last.reviewed_by})."
        )
        claim_refs.append(r.id)
        trace_operator, trace_trigger = last.operator, last.trigger
        trace_ledger, reviewed_by = last.ledger_id, last.reviewed_by

    if goals:
        g = goals[0]
        lines.append(f"It matters to me because I'm working toward: {g.text.lower()}.")

    if prefs:
        p = prefs[0]
        lines.append(f"For what it's worth, I {p.stance} {p.subject}.")

    if episodes:
        lines.append(f"I remember: {episodes[0].summary.lower()}.")

    if not lines:
        lines.append("I don't have a settled view on that yet - nothing in my state speaks to it.")

    brief = " ".join(lines)

    # Route the phrasing. A turn that reports an opinion change is the 'hard' case.
    route = router.route(needs_language=True, hard=bool(rejected))
    router.charge(route)
    if route.cost:
        # Phrasing spend is itself audited - under its own operator, not the cause's.
        from .models import Operator
        state.record(Operator.VOICE_RENDER, "voice phrasing", refs=tuple(claim_refs),
                     reviewed_by=route.model_name, cost=route.cost)
    voice = f"{state.name}, a local-first operative identity; plain, candid, first person"
    conversation = model.phrase(brief, voice=voice)

    trace = EpistemicTrace(
        utterance=conversation,
        claims=tuple(claim_refs),
        goals=tuple(g.id for g in goals[:1]),
        memory=tuple(ep.id for ep in episodes),
        operator=trace_operator,
        trigger=trace_trigger,
        reviewed_by=reviewed_by if trace_ledger else route.model_name,
        ledger_event=trace_ledger,
        routed_to=route.tier,
    )
    return Response(conversation=conversation, epistemic=trace)
