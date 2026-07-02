"""The end-to-end solution-space pipeline: cartograph (A) -> deep-method operators (B).

Composes the two built bricks into the loop the operator described: map the product space, find the
UNREACHED islands and the BRIDGE candidates between solution spaces, and for each ask the
deep-method operator layer which method (with its Kernfrage) to try. Deterministic, no LLM.

This is the MVP of the whole vision on whatever points the caller supplies (synthetic today; real
StateVectors + embeddings once the data capture is wired). It reuses Baustein B by turning each
geometric gap into a duck-typed gap target B already understands (id / kind / severity).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .cartography import Cartography, cartograph
from .operators import DeepMethodProposal, propose_operators


@dataclass(frozen=True)
class _GapTarget:
    """A cartographer gap in the shape Baustein B consumes (same attrs as a DESi ConflictGap)."""

    id: str
    kind: str
    severity: str = "soft"
    unresolved_since: int = 0


@dataclass(frozen=True)
class _GapSnapshot:
    conflicts: tuple = ()
    provenance: object = None


@dataclass(frozen=True)
class ReachPlan:
    """What the pipeline produced: the map, and — per unreached island / bridge — the ranked deep
    methods to try, each carrying its Kernfrage as the concrete operator."""

    cartography: Cartography
    proposals: tuple[DeepMethodProposal, ...]
    provenance: dict = field(default_factory=dict)

    def by_target(self) -> dict[str, list[DeepMethodProposal]]:
        out: dict[str, list[DeepMethodProposal]] = {}
        for p in self.proposals:
            out.setdefault(p.target, []).append(p)
        return out


def _targets(cart: Cartography) -> list[_GapTarget]:
    targets: list[_GapTarget] = []
    for isl in cart.unanchored_islands:                     # unreached regions — the hard gaps
        targets.append(_GapTarget(id=isl, kind="unanchored_island", severity="hard"))
    for b in cart.bridges:                                  # candidate connections — softer
        targets.append(_GapTarget(id=f"{b.island_a}~{b.island_b}", kind="bridge_candidate",
                                  severity="soft"))
    return targets


def plan(points, *, top_k_per_gap: int = 3, deep_trials=(), **cartography_kwargs) -> ReachPlan:
    """Cartograph ``points`` (Baustein A) then propose deep-method operators (Baustein B) for every
    unreached island and bridge candidate. Returns a :class:`ReachPlan`. Deterministic; empty points
    -> an empty plan."""
    cart = cartograph(points, **cartography_kwargs)
    snap = _GapSnapshot(conflicts=tuple(_targets(cart)))
    proposals = propose_operators(snap, deep_trials=deep_trials, top_k_per_gap=top_k_per_gap)
    n_points = len(points) if hasattr(points, "__len__") else -1
    return ReachPlan(cartography=cart, proposals=tuple(proposals),
                     provenance={"n_points": n_points,
                                 "n_islands": len(cart.islands),
                                 "n_unanchored": len(cart.unanchored_islands),
                                 "n_bridges": len(cart.bridges)})
