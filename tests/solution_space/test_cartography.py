"""Baustein A — the product-space cartographer.

Synthetic points in (9-dim governance ⊕ 3-dim semantic): three islands — one anchored solution
island, one UNANCHORED island (same topic as the first but far in governance), and a second anchored
island on a different topic. Expect: 3 islands, the middle one flagged unanchored, and a bridge
between the two same-topic-but-governance-far islands (the 'Verknüpfung zwischen Lösungsräumen').
"""
from __future__ import annotations

from joni.solution_space.cartography import SolutionPoint, cartograph

_Z = (0.0,) * 9


def _sv(*head):
    return tuple(head) + (0.0,) * (9 - len(head))


POINTS = [
    # island 0 — anchored, topic A, governance near origin
    SolutionPoint("A0a", _Z, (1.0, 0.0, 0.0), anchored=True),
    SolutionPoint("A0b", _sv(1.0), (1.0, 0.0, 0.0), anchored=False),
    # island 1 — UNANCHORED, topic A (same embedding), governance FAR across ALL axes -> bridge
    SolutionPoint("U1a", (9.0,) * 9, (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("U1b", (9.0,) * 8 + (8.0,), (1.0, 0.0, 0.0), anchored=False),
    # island 2 — anchored, topic C (orthogonal embedding), governance near origin
    SolutionPoint("A2a", _Z, (0.0, 0.0, 1.0), anchored=True),
    SolutionPoint("A2b", _sv(0.0, 0.0, 1.0), (0.0, 0.0, 1.0), anchored=True),
]


def _island_of(cart, point_id):
    return next(i for i in cart.islands if point_id in i.member_ids)


def test_three_islands_with_correct_membership():
    cart = cartograph(POINTS, tau=0.2)
    assert len(cart.islands) == 3
    assert _island_of(cart, "A0a").member_ids == ("A0a", "A0b")
    assert set(_island_of(cart, "U1a").member_ids) == {"U1a", "U1b"}
    assert _island_of(cart, "A2a").id == _island_of(cart, "A2b").id


def test_the_only_unanchored_island_is_the_candidate_region():
    cart = cartograph(POINTS, tau=0.2)
    assert len(cart.unanchored_islands) == 1
    unl = _island_of(cart, "U1a")
    assert unl.id in cart.unanchored_islands and not unl.anchored
    # the anchored islands are NOT flagged
    assert _island_of(cart, "A0a").id not in cart.unanchored_islands


def test_bridge_between_same_topic_but_governance_far_islands():
    cart = cartograph(POINTS, tau=0.2, bridge_sem_max=0.25, bridge_gov_min=0.5)
    assert len(cart.bridges) == 1
    b = cart.bridges[0]
    pair = {b.island_a, b.island_b}
    assert pair == {_island_of(cart, "A0a").id, _island_of(cart, "U1a").id}
    assert b.semantic_distance <= 0.25 and b.governance_distance >= 0.5
    # island 2 (different topic) is bridged to neither
    assert _island_of(cart, "A2a").id not in pair


def test_empty_input_is_safe():
    cart = cartograph([])
    assert cart.islands == () and cart.unanchored_islands == () and cart.bridges == ()


def test_tighter_tau_splits_more_and_looser_merges():
    loose = cartograph(POINTS, tau=0.9)          # everything within reach -> one island
    assert len(loose.islands) == 1
    tight = cartograph(POINTS, tau=0.001)         # nothing merges -> every point its own island
    assert len(tight.islands) == len(POINTS)
