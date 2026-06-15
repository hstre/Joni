"""Invention - Joni making something up himself, not only reacting to sources.

Joni recombines insights from two different topics into a new conjecture - the same
cross-domain transfer Kevin is built on, done internally. The result is an honest
**hypothesis**: a CANDIDATE claim derived from the two parent claims, never activated or
confirmed automatically. A guess stays a guess until it earns support.

Bounded and self-limiting: at most one new hypothesis per cycle, and at most one per pair
of topics (deduped), so it explores the combinations of what Joni knows and then goes
quiet until new topics appear.
"""

from __future__ import annotations

from . import quality
from .emerge import _is_synthetic


def invent(cs, extensions: dict, proto, cycle: int = 0) -> dict:
    invented = set(extensions.get("invented", []))      # topic pairs already tried

    # strongest active claim per topic - but only over MEANINGFUL topics and REAL claims. A
    # bridge built on Joni's own bookkeeping ("'about' keeps recurring...") or on a junk token
    # topic is exactly the noise the review flagged, so it is excluded here.
    by_topic: dict[str, object] = {}
    for c in cs.active_claims():
        if not c.topic or _is_synthetic(c.text) or not quality.is_meaningful_term(c.topic):
            continue
        cur = by_topic.get(c.topic)
        if cur is None or (c.confidence_or_support, c.id) > (cur.confidence_or_support, cur.id):
            by_topic[c.topic] = c

    # Only bridge topics that earned the status of a research direction (>=3 claims across >=2
    # independent sources). A hypothesis spanning two one-source word clusters is exactly the
    # noise the review flagged - Joni invents fewer, but better-grounded, cross-domain leaps.
    research = set(cs.research_topics())
    topics = sorted(t for t in by_topic if t in research)
    made = 0
    for i, ta in enumerate(topics):
        if made:
            break
        for tb in topics[i + 1:]:
            key = f"{ta}|{tb}"
            if key in invented:
                continue
            a, b = by_topic[ta], by_topic[tb]
            text = (f"Hypothesis: the pattern behind '{a.text}' (from {ta}) might also "
                    f"apply to {tb}.")
            cs.hypothesize(text, f"{ta}+{tb}", parents=(a.id, b.id))
            invented.add(key)
            made += 1
            proto.record(cycle, "invented",
                         f"new hypothesis bridging {ta} x {tb} (candidate, derived from "
                         f"{a.id}+{b.id})")
            break

    extensions["invented"] = sorted(invented)[-500:]
    return {"hypotheses": made}
