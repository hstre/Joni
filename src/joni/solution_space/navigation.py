"""Navigation — turn the map into a PRIORITISED exploration agenda: where to work next, and why.

The cartographer (A) says what the terrain is; the operators (B) say which deep method to try on a
gap. Navigation adds the missing piece: a deterministic RANKING over the gaps, so the output is an
ordered worklist rather than an unordered pile. Two gap kinds, each with a principled priority:

  * **reach an unreached island** — priority rises with the island's SIZE (more candidates at
    stake) and with whether it is REACHABLE from a known anchor (a bridge to an anchor exists);
  * **build a bridge** — priority rises the more the two islands are semantically CLOSE yet
    governance-FAR (strongly 'same topic, disconnected reasoning').

Each agenda item carries the deep-method operator to try (from B) and a traceable reason. This is
the confirmed value of the pipeline (navigation + discovery), independent of the — measured-null —
idea of a method-as-prompt lever. Deterministic, no model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cartography import cartograph
from .pipeline import plan


@dataclass(frozen=True)
class NavItem:
    kind: str                              # "reach_island" | "bridge"
    target: str
    priority: float
    reason: str
    method_id: str = ""                    # the deep-method operator to try (from Baustein B)
    core_question: str = ""                # its Kernfrage

    def to_dict(self) -> dict:
        return {"kind": self.kind, "target": self.target, "priority": self.priority,
                "reason": self.reason, "method_id": self.method_id,
                "core_question": self.core_question}


@dataclass(frozen=True)
class NavigationReport:
    n_islands: int
    n_anchored: int
    n_unreached: int
    n_bridges: int
    agenda: tuple[NavItem, ...] = ()
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"n_islands": self.n_islands, "n_anchored": self.n_anchored,
                "n_unreached": self.n_unreached, "n_bridges": self.n_bridges,
                "agenda": [i.to_dict() for i in self.agenda], "params": self.params}


def navigate(points, *, top: int = 10, w_size: float = 0.5, w_reach: float = 0.5,
             **cart_kwargs) -> NavigationReport:
    """Cartograph ``points``, rank the unreached islands and bridges into an agenda, and attach the
    deep-method operator for each. Returns a :class:`NavigationReport`. Deterministic."""
    cart = cartograph(points, **cart_kwargs)
    rp = plan(points, top_k_per_gap=1, **cart_kwargs)
    # index proposals by the BARE gap id ("conflict:island_1" -> "island_1")
    by_id = {p.target.split(":", 1)[-1]: p for p in rp.proposals}

    size = {i.id: i.size for i in cart.islands}
    max_size = max(size.values(), default=1) or 1
    anchored = {i.id for i in cart.islands if i.anchored}

    # which unreached islands touch an anchored island through a bridge (i.e. are reachable)
    reachable: set[str] = set()
    for b in cart.bridges:
        if b.island_a in anchored:
            reachable.add(b.island_b)
        if b.island_b in anchored:
            reachable.add(b.island_a)

    def _op(target: str):
        p = by_id.get(target)
        return (p.method_id, p.core_question) if p else ("", "")

    items: list[NavItem] = []
    for uid in cart.unanchored_islands:
        reach = 1.0 if uid in reachable else 0.0
        prio = round(w_size * (size.get(uid, 0) / max_size) + w_reach * reach, 4)
        mid, cq = _op(uid)
        items.append(NavItem(
            kind="reach_island", target=uid, priority=prio, method_id=mid, core_question=cq,
            reason=(f"unreached region (size {size.get(uid, 0)}, "
                    f"{'reachable from an anchor' if reach else 'isolated from known ground'})")))
    for b in cart.bridges:
        prio = round((1.0 - b.semantic_distance) * b.governance_distance, 4)
        tid = f"{b.island_a}~{b.island_b}"
        mid, cq = _op(tid)
        items.append(NavItem(
            kind="bridge", target=tid, priority=prio, method_id=mid, core_question=cq,
            reason=(f"bridge: semantically close (d={b.semantic_distance}) but governance-far "
                    f"(d={b.governance_distance}) — related topic, disconnected reasoning")))

    items.sort(key=lambda x: (-x.priority, x.kind, x.target))
    return NavigationReport(
        n_islands=len(cart.islands), n_anchored=len(anchored),
        n_unreached=len(cart.unanchored_islands), n_bridges=len(cart.bridges),
        agenda=tuple(items[: max(0, top)]),
        params={"top": top, "w_size": w_size, "w_reach": w_reach, **cart.params})
