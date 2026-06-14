"""Reconsolidation - Joni revisiting his own memory for links he missed, through a Kevin lens.

The ordinary ``develop`` pass only links claims *within* one topic, once. This runs
occasionally and goes wider: it borrows one of **Kevin's candidate methods** (a lens, with the
topics it applies to) and re-reads memory *across* those topics through it, letting the DESi
Semantic Layer forge governed cross-topic links (or open conflicts) that develop would never
look for.

Honest by construction: lexical overlap is only a cheap trigger; Layer 9 renders every verdict;
nothing is auto-confirmed; bounded per pass; and it shares ``develop``'s ``linked`` ledger so a
pair is examined once. It is just Joni, now and then, connecting old notes with a borrowed lens.
"""
from __future__ import annotations

import desi_layer9 as l9
from desi_layer9.semantics import adapter, lexical_overlap
from desi_layer9.semantics.ports import NullSemanticLayer

from .develop import _TRIGGER, _act_on

_EVERY = 12          # run this consolidation pass once every N cycles ("ab und zu")


def _lenses(cs) -> list:
    """Kevin's candidate methods that name >= 2 topics they apply to - the lenses to re-read
    memory through. Newest first, so fresh ideas get tried."""
    out = []
    for m in cs.core.all(l9.ObjectType.METHOD):
        topics = tuple(t for t in (getattr(m, "applicable_to", ()) or ()) if t)
        if len(topics) >= 2:
            out.append((m, topics))
    out.sort(key=lambda mt: int(mt[0].id.split("-")[-1]), reverse=True)
    return out


def reconsolidate(cs, extensions: dict, proto, cycle: int = 0, *, layer=None,
                  every: int = _EVERY, max_links: int = 2, max_pairs: int = 8) -> dict:
    """Every ``every`` cycles, re-read memory across one Kevin lens's topics for new
    cross-topic links. A no-op on other cycles or when there is no multi-topic lens yet."""
    out = {"ran": False, "lens": None, "links": 0, "pairs": 0}
    if every <= 0 or cycle % every != 0:
        return out
    layer = layer or NullSemanticLayer()
    lenses = _lenses(cs)
    if not lenses:
        return out

    # rotate through the available lenses over successive passes
    idx = int(extensions.get("reconsolidate_lens_idx", 0)) % len(lenses)
    method, topics = lenses[idx]
    extensions["reconsolidate_lens_idx"] = (idx + 1) % len(lenses)
    out["ran"] = True
    out["lens"] = getattr(method, "name", None) or method.id

    linked = set(extensions.get("linked", []))
    tset = set(topics)
    claims = [c for c in cs.active_claims() if c.topic in tset]

    # candidate CROSS-topic pairs (what develop never links), strongest lexical trigger first
    pairs = []
    for i, a in enumerate(claims):
        for b in claims[i + 1:]:
            if a.topic == b.topic:                        # develop already covers within-topic
                continue
            key = f"{a.id}|{b.id}" if a.id < b.id else f"{b.id}|{a.id}"
            if key in linked:
                continue
            trig = lexical_overlap(a.text, b.text)
            if trig >= _TRIGGER:                          # cheap trigger only - never a verdict
                pairs.append((trig, a, b, key))
    pairs.sort(key=lambda p: -p[0])

    analysed = 0
    for trig, a, b, key in pairs:
        if out["links"] >= max_links or analysed >= max_pairs:
            break
        analysed += 1
        sc = adapter.analyse_pair(cs.core, a, b, layer=layer, lexical_trigger=trig,
                                  run_id=f"joni-c{cycle}-recon")
        linked.add(key)
        out["links"] += _act_on(cs, proto, cycle, a, b, sc)
    out["pairs"] = analysed
    extensions["linked"] = sorted(linked)[-1000:]
    proto.record(cycle, "reconsolidated",
                 f"re-read memory through Kevin lens '{out['lens']}' across "
                 f"{', '.join(sorted(topics))}: {analysed} pair(s) examined, "
                 f"{out['links']} new cross-topic link(s)")
    return out
