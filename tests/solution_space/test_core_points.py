"""(a) Deriving real StateVectors from Layer-9 objects, and building points from a live core."""
from __future__ import annotations

from joni.solution_space.core_points import points_from_core, state_vector_from_object


class _Enum:
    def __init__(self, v):
        self.value = v


class _Prov:
    def __init__(self, sources):
        self.source_ids = tuple(sources)


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_state_vector_derivation_maps_the_nine_axes():
    o = _Obj(id="c1", topic="sepsis", confidence_or_support=0.8, created_tick=5,
             status=_Enum("confirmed"), authority=_Enum("trusted"),
             provenance=_Prov(("s1", "s2")), derived_from=("x",))
    sv = state_vector_from_object(o, conflict_count=2, current_tick=10)
    assert len(sv) == 9
    assert all(0.0 <= x <= 1.0 for x in sv)
    assert sv[1] == 2 / 5.0        # contradiction_load = min(2,5)/5
    assert sv[2] == 3 / 5.0        # anchor_density = derived_from(1) + sources(2)
    assert sv[5] == 0.8            # confidence
    assert sv[7] == 1.0           # support_state (confirmed)
    assert sv[6] == 0.0 and sv[8] == 0.0   # branch_cost / routing_state honestly unknown


def test_novelty_decays_with_age():
    young = state_vector_from_object(_Obj(id="a", created_tick=9), current_tick=10)
    old = state_vector_from_object(_Obj(id="a", created_tick=0), current_tick=49)
    assert young[4] > old[4]       # newer claim is more 'novel'


def test_points_from_core_is_fail_open_without_layer9():
    class _NoCore:
        pass
    # no desi_layer9 usable on a bare object -> [] (the read-only source never crashes)
    assert points_from_core(_NoCore()) == []
