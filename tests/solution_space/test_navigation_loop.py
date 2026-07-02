"""The iterative navigation loop: explore the top item, re-map, converge as gaps get anchored."""
from __future__ import annotations

from dataclasses import replace

from joni.solution_space import navigate_iteratively
from joni.solution_space.cartography import SolutionPoint

_Z = (0.0,) * 9


def _sv(*head):
    return tuple(head) + (0.0,) * (9 - len(head))


def _base_points():
    return [
        SolutionPoint("A0a", _Z, (1.0, 0.0, 0.0), anchored=True),
        SolutionPoint("A0b", _sv(1.0), (1.0, 0.0, 0.0), anchored=True),
        # two UNREACHED islands (different topics, governance-far)
        SolutionPoint("U1a", (9.0,) * 9, (1.0, 0.0, 0.0), anchored=False),
        SolutionPoint("U1b", (9.0,) * 8 + (8.0,), (1.0, 0.0, 0.0), anchored=False),
        SolutionPoint("U2a", (5.0,) * 9, (0.0, 1.0, 0.0), anchored=False),
        SolutionPoint("U2b", _sv(5.0, 5.0, 5.0, 5.0, 5.0), (0.0, 1.0, 0.0), anchored=False),
    ]


def test_loop_converges_as_exploring_anchors_the_reached_islands():
    state = {"pts": _base_points()}

    def provider():
        return list(state["pts"])

    def explore(item):
        # "reaching" an island = its candidates become known solutions -> anchor its member points
        ids = set(item.members)
        state["pts"] = [replace(p, anchored=True) if p.id in ids else p for p in state["pts"]]

    trace = navigate_iteratively(provider, explore, max_steps=10, tau=0.2)
    # it terminated (last step chose nothing) and reaching the islands left NO unreached region
    assert trace[-1].chosen is None and trace[-1].n_unreached == 0
    # it took at most a handful of steps (one per distinct gap), not the full budget
    assert len(trace) <= 6


def test_loop_terminates_and_never_re_explores_the_same_gap():
    pts = _base_points()
    # a no-op explorer never changes the map; the loop still terminates by exhausting distinct gaps
    trace = navigate_iteratively(lambda: pts, lambda item: None, max_steps=20, tau=0.2)
    assert trace[-1].chosen is None                # terminated on its own, well within the budget
    chosen = [frozenset(s.chosen.members) for s in trace if s.chosen is not None]
    assert len(chosen) == len(set(chosen))         # each distinct gap explored at most once
