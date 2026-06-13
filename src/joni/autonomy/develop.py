"""Self-development - how Joni keeps restructuring himself, even at "0 new".

Joni's protected core is frozen, so he does not rewrite his own logic. But his *epistemic*
state is his to organise - through Layer 9, and with the **DESi Semantic Layer** as the
authority on whether two claims actually relate.

The old rule let word-overlap decide ``supports`` vs ``contextualizes``. That is exactly
the interpretation that must not live in Joni. Now:

    lexical overlap (cheap trigger only)
        -> Layer 9 semantic adapter (DESi FrameDetector / LogicalAuditor / FrameTensionRouter)
        -> governed decision: duplicate | supports | complementary | tension | contradictory
           | unrelated | insufficient
        -> Joni acts on the *governed* decision (links, or opens a conflict), never on the
           overlap.

If the Semantic Layer is unavailable the decision is *insufficient* and Joni makes no link -
he never falls back to lexical overlap for a verdict. Every analysis is recorded by Layer 9
as an append-only annotation; the claims are never touched.
"""

from __future__ import annotations

from desi_layer9 import SemanticDecision
from desi_layer9.semantics import adapter, lexical_overlap
from desi_layer9.semantics.ports import NullSemanticLayer

_TRIGGER = 0.3      # cheap lexical trigger; below this we do not even ask the Semantic Layer


def develop(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
            max_links: int = 2) -> dict:
    layer = layer or NullSemanticLayer()
    linked = set(extensions.get("linked", []))
    live = sorted(cs.active_claims(), key=lambda c: c.id)

    new_links = 0
    for i, a in enumerate(live):
        if new_links >= max_links:
            break
        for b in live[i + 1:]:
            if a.topic != b.topic or a.topic == "":
                continue
            key = f"{a.id}|{b.id}"
            if key in linked:
                continue
            trigger = lexical_overlap(a.text, b.text)
            if trigger < _TRIGGER:
                continue                                  # cheap trigger only - never a verdict
            sc = adapter.analyse_pair(cs.core, a, b, layer=layer, lexical_trigger=trigger,
                                      run_id=f"joni-c{cycle}")
            linked.add(key)
            acted = _act_on(cs, proto, cycle, a, b, sc)
            new_links += acted
            if acted:
                break
    extensions["linked"] = sorted(linked)[-1000:]

    reviewed = 0
    for x in cs.core.open_conflicts():
        if x.conflict_status.value == "open":
            cs.review_conflict(x.id)
            reviewed += 1
            proto.record(cycle, "developed", f"opened review of contradiction {x.id}")

    return {"links": new_links, "conflicts_reviewed": reviewed}


def _act_on(cs, proto, cycle, a, b, sc) -> int:
    """Act on Layer 9's governed decision. Returns 1 if a link was drawn, else 0."""
    d = sc.decision
    src = f"DESi {sc.semantic_layer}@{sc.semantic_layer_version}"
    if d is SemanticDecision.SUPPORTS:
        cs.corroborate(a.id, b, relation="supports")
        proto.record(cycle, "developed", f"linked {a.id} <-> {b.id} (supports · {src})")
        return 1
    if d is SemanticDecision.COMPLEMENTARY:
        cs.corroborate(a.id, b, relation="contextualizes")
        proto.record(cycle, "developed", f"linked {a.id} <-> {b.id} (complementary · {src})")
        return 1
    if d is SemanticDecision.CONTRADICTORY:
        cid = cs.open_conflict((a.id, b.id), severity="hard")
        proto.record(cycle, "developed", f"{src} found {a.id} vs {b.id} contradictory -> {cid}")
        return 0
    if d is SemanticDecision.TENSION:
        cid = cs.open_conflict((a.id, b.id), severity="soft")
        proto.record(cycle, "developed", f"{src} found frame tension {a.id}/{b.id} -> {cid}")
        return 0
    # duplicate / unrelated / insufficient: recorded by Layer 9, no link asserted.
    proto.record(cycle, "developed", f"{a.id}/{b.id}: {d.value} - no link ({src})")
    return 0
