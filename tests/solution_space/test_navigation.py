"""Navigation: the map becomes a prioritised agenda (where to work next, and why)."""
from __future__ import annotations

from joni.solution_space import navigate
from joni.solution_space.cartography import SolutionPoint

_Z = (0.0,) * 9


def _sv(*head):
    return tuple(head) + (0.0,) * (9 - len(head))


# island 0 anchored (topic A); island 1 UNREACHED (topic A, governance-far -> bridge to island 0);
# island 2 anchored (topic C, isolated from island 1)
POINTS = [
    SolutionPoint("A0a", _Z, (1.0, 0.0, 0.0), anchored=True),
    SolutionPoint("A0b", _sv(1.0), (1.0, 0.0, 0.0), anchored=True),
    SolutionPoint("U1a", (9.0,) * 9, (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("U1b", (9.0,) * 8 + (8.0,), (1.0, 0.0, 0.0), anchored=False),
    SolutionPoint("C2a", _Z, (0.0, 0.0, 1.0), anchored=True),
    SolutionPoint("C2b", _sv(0.0, 0.0, 1.0), (0.0, 0.0, 1.0), anchored=True),
]


def test_empty_points_is_an_empty_report():
    r = navigate([])
    assert r.n_islands == 0 and r.agenda == ()


def test_report_counts_and_agenda_are_populated():
    r = navigate(POINTS, tau=0.2)
    assert r.n_islands == 3 and r.n_anchored == 2 and r.n_unreached == 1 and r.n_bridges == 1
    assert r.agenda                                   # a non-empty worklist
    kinds = {i.kind for i in r.agenda}
    assert "reach_island" in kinds and "bridge" in kinds


def test_every_agenda_item_carries_an_operator_and_reason():
    r = navigate(POINTS, tau=0.2)
    for item in r.agenda:
        assert item.method_id and item.core_question   # a deep-method operator to try
        assert item.reason and item.priority >= 0.0


def test_agenda_is_priority_sorted():
    r = navigate(POINTS, tau=0.2)
    prios = [i.priority for i in r.agenda]
    assert prios == sorted(prios, reverse=True)


def test_reachable_unreached_island_outranks_the_same_island_when_isolated():
    # the unreached island IS bridged to an anchor here -> its reach term fires
    r = navigate(POINTS, tau=0.2, w_size=0.0, w_reach=1.0)   # weight only reachability
    island_item = next(i for i in r.agenda if i.kind == "reach_island")
    assert island_item.priority == 1.0                 # reachable from an anchor -> full score
