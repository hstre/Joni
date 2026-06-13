"""Self-development - how Joni keeps restructuring himself, even at "0 new".

Joni's protected core is frozen (he files an ask for core changes), so he does not
rewrite his own logic autonomously. But his *epistemic* state is his to organise, and he
should keep doing so every cycle - not sit idle when no new papers arrive.

Two honest, bounded moves, both through the gate, neither faking authority:

  * **evidence web** - link mutually-supporting active claims on a topic (as *unreviewed*
    evidence; it never confirms anything - confirmation still needs a human reviewer);
  * **engage conflicts** - move open contradictions into review rather than leaving them
    untouched (they are still never force-resolved).

This self-limits: once the live claims are consolidated, there is nothing new to link, so
it goes quiet until new claims arrive.
"""

from __future__ import annotations

from ..conflict import _overlap


def develop(cs, extensions: dict, proto, cycle: int = 0, *, max_links: int = 2) -> dict:
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
            # same topic -> at least contextualizes; strong overlap -> supports.
            relation = "supports" if _overlap(a.text, b.text) >= 0.5 else "contextualizes"
            cs.corroborate(a.id, b, relation=relation)
            linked.add(key)
            new_links += 1
            proto.record(cycle, "developed",
                         f"linked {a.id} <-> {b.id} ({relation}, unreviewed)")
            break
    extensions["linked"] = sorted(linked)[-1000:]

    reviewed = 0
    for x in cs.core.open_conflicts():
        if x.conflict_status.value == "open":
            cs.review_conflict(x.id)
            reviewed += 1
            proto.record(cycle, "developed", f"opened review of contradiction {x.id}")

    return {"links": new_links, "conflicts_reviewed": reviewed}
