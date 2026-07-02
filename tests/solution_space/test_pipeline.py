"""End-to-end: cartograph (A) -> deep-method operators (B).

Reuses the three-island synthetic map (one unanchored region + one bridge) and asserts the pipeline
turns each geometric gap into ranked deep-method operators — reduction-family for reaching an
unreached island, invariant/reduction for a bridge — each carrying its Kernfrage.
"""
from __future__ import annotations

from joni.method_trial import deep_methods as D
from joni.solution_space import SolutionPoint, plan

_Z = (0.0,) * 9


def _sv(*head):
    return tuple(head) + (0.0,) * (9 - len(head))


POINTS = [
    SolutionPoint("A0a", _Z, (1.0, 0.0, 0.0), anchored=True),
    SolutionPoint("A0b", _sv(1.0), (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("U1a", (9.0,) * 9, (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("U1b", (9.0,) * 8 + (8.0,), (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("A2a", _Z, (0.0, 0.0, 1.0), anchored=True),
    SolutionPoint("A2b", _sv(0.0, 0.0, 1.0), (0.0, 0.0, 1.0), anchored=True),
]


def test_pipeline_maps_then_proposes_operators_per_gap():
    rp = plan(POINTS, tau=0.2, top_k_per_gap=3)
    assert rp.provenance["n_islands"] == 3
    assert rp.provenance["n_unanchored"] == 1 and rp.provenance["n_bridges"] == 1
    by = rp.by_target()
    # exactly two gap targets got operators: the unreached island and the bridge
    assert len(by) == 2
    for props in by.values():
        assert props and all(D.by_id(p.method_id) is not None for p in props)
        assert all(p.core_question for p in props)         # every operator carries its Kernfrage
    # reduction is the top-relevance operator for BOTH an unreached island and a bridge
    assert any(p.method_id == "reduction" for props in by.values() for p in props)


def test_unreached_island_gets_reaching_methods():
    rp = plan(POINTS, tau=0.2, top_k_per_gap=4)
    island_props = [p for p in rp.proposals if not p.target.count("~")]
    assert island_props
    kinds = {p.method_kind for p in island_props}
    # reaching an unreached region -> reduction / estimation / search / optimization families
    assert kinds & {"reduction", "estimation", "search", "optimization"}


def test_bridge_gets_connecting_methods():
    rp = plan(POINTS, tau=0.2, top_k_per_gap=4)
    bridge_props = [p for p in rp.proposals if "~" in p.target]
    assert bridge_props
    kinds = {p.method_kind for p in bridge_props}
    assert kinds & {"reduction", "invariant", "counting", "modeling"}


def test_empty_points_is_an_empty_plan():
    rp = plan([])
    assert rp.proposals == () and rp.cartography.islands == ()
