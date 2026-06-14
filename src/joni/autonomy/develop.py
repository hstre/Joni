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


def _semantic_rev() -> str:
    """A tag for the current semantic measure, so a model change re-measures the backlog."""
    try:
        from . import embeddings
        if embeddings.available():
            return embeddings.info()["revision"]
    except Exception:  # noqa: BLE001
        pass
    return "none"


def develop(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
            max_links: int = 2, max_backfill: int = 3) -> dict:
    layer = layer or NullSemanticLayer()
    rev = _semantic_rev()
    linked = set(extensions.get("linked", []))
    annotated = set(extensions.get("semantic_backfilled", []))   # "pair@rev" with a semantic record
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
            annotated.add(f"{key}@{rev}")                 # measured under this semantic rev
            acted = _act_on(cs, proto, cycle, a, b, sc)
            new_links += acted
            if acted:
                break
    extensions["linked"] = sorted(linked)[-1000:]

    backfilled = _backfill_legacy(cs, extensions, proto, cycle, linked, annotated, layer,
                                  max_backfill, rev)

    reviewed = 0
    for x in cs.core.open_conflicts():
        if x.conflict_status.value == "open":
            cs.review_conflict(x.id)
            reviewed += 1
            proto.record(cycle, "developed", f"opened review of contradiction {x.id}")

    return {"links": new_links, "conflicts_reviewed": reviewed, "backfilled": backfilled}


def _backfill_legacy(cs, extensions, proto, cycle, linked, done, layer, limit, rev) -> int:
    """Give already-linked pairs a Layer-9 semantic record under the current measure.

    The backlog was linked by lexical overlap under the old logic - with no governed
    semantic decision. We retroactively run the Semantic Layer over a few each cycle
    (append-only; the old link is not altered, but a contradiction/tension it now sees is
    opened honestly). Deduped by ``pair@rev`` so a *new* semantic measure (e.g. the
    embedding model coming online) re-measures the backlog once; then it goes quiet."""
    by_id = {c.id: c for c in cs.active_claims()}
    n = 0
    for key in sorted(linked):
        if n >= limit:
            break
        tag = f"{key}@{rev}"
        if tag in done:
            continue
        a_id, _, b_id = key.partition("|")
        a, b = by_id.get(a_id), by_id.get(b_id)
        if a is None or b is None:
            done.add(tag)                                 # not both live anymore - skip
            continue
        sc = adapter.analyse_pair(cs.core, a, b, layer=layer, run_id=f"joni-c{cycle}-bf")
        done.add(tag)
        n += 1
        if sc.decision.value in ("contradictory", "tension"):
            sev = "hard" if sc.decision.value == "contradictory" else "soft"
            cid = cs.open_conflict((a_id, b_id), severity=sev)
            proto.record(cycle, "developed",
                         f"backfill: Layer 9 now sees {a_id}/{b_id} {sc.decision.value} -> {cid}")
        else:
            proto.record(cycle, "developed",
                         f"backfill: {a_id}/{b_id} semantic record = {sc.decision.value}")
    extensions["semantic_backfilled"] = sorted(done)[-4000:]
    return n


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
