"""Joni regulates himself: sheds dead ideas, caps the backlog, grades his own vitality."""

import desi_layer9 as l9
from joni.autonomy import homeostasis
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _hyp(cs, text="Hypothesis: routing relates to memory", topic="routing"):
    p = cs.learn("a parent claim about routing", topic)
    return cs.hypothesize(text, topic, parents=(p,))


def test_kevins_thin_verdict_alone_does_not_shed_an_idea():
    """Kevin must never decide: a Kevin-flagged ('hollow') idea is NOT deleted on Kevin's word.
    It is shed only on objective grounds (contradicted, or barren after many real tests)."""
    cs = CoreState(seed_core())
    h = _hyp(cs)
    ext = {"hyp_hollow": [h], "hyp_tested": [f"{h}|C-1", f"{h}|C-2"]}   # Kevin-flagged, 2 tests
    out = homeostasis.regulate(cs, ext, _Proto())
    assert out["pruned"] == 0                                     # Kevin's opinion sheds nothing
    assert cs.core.get(h).status is l9.Status.CANDIDATE          # kept - the rules decide


def test_a_barren_idea_tested_many_times_is_shed():
    cs = CoreState(seed_core())
    h = _hyp(cs)
    ext = {"hyp_tested": [f"{h}|C-{i}" for i in range(4)]}          # 4 tries, 0 support
    out = homeostasis.regulate(cs, ext, _Proto())
    assert out["pruned"] == 1 and out["barren"] == 1


def test_an_idea_that_earned_support_is_kept():
    cs = CoreState(seed_core())
    p = cs.learn("routing is local", "routing")
    h = cs.hypothesize("Hypothesis: routing is local-first", "routing", parents=(p,))
    ev = cs.learn("routing runs on device", "routing")
    cs.corroborate(h, cs.core.get(ev), relation="supports")        # it earned a support
    ext = {"hyp_hollow": [h], "hyp_tested": [f"{h}|x", f"{h}|y", f"{h}|z", f"{h}|w"]}
    out = homeostasis.regulate(cs, ext, _Proto())
    assert out["pruned"] == 0
    assert cs.core.get(h).status is l9.Status.CANDIDATE            # supported -> kept


def test_pruning_is_bounded_per_cycle():
    cs = CoreState(seed_core())
    hs = [_hyp(cs, text=f"Hypothesis number {i}") for i in range(6)]
    # barren on objective grounds: 4 real tests each, 0 support
    ext = {"hyp_tested": [f"{h}|{c}" for h in hs for c in "abcd"]}
    out = homeostasis.regulate(cs, ext, _Proto(), max_prune=3)
    assert out["pruned"] == 3                          # capped; works through over time


def test_vitality_counts_validation_not_raw_growth():
    # merely learning more claims is NOT development under the quality metric...
    cs = CoreState(seed_core())
    ext: dict = {"vitality_prev": {"supports": 0, "promoted": 0, "confirmed": 0, "objects": 0}}
    cs.learn("a new claim", "routing")
    cs.learn("another new claim", "routing")
    rec = homeostasis.vitality(cs, ext, _Proto())
    assert rec["development"] == 0                       # growth alone does not count

    # ...but new *validating* evidence does.
    cs2 = CoreState(seed_core())
    a = cs2.learn("routing reduces latency", "routing")
    b = cs2.learn("local routing cuts latency", "routing")
    cs2.corroborate(a, cs2.core.get(b), relation="supports")
    ext2: dict = {"vitality_prev": {"supports": 0, "promoted": 0, "confirmed": 0, "objects": 0}}
    rec2 = homeostasis.vitality(cs2, ext2, _Proto())
    assert rec2["development"] >= 1                      # earned support = real progress
    assert rec2["verdict"] == "developing"
    assert ext2["vitality_history"]


def test_vitality_flags_degenerating_on_a_swelling_unsupported_backlog():
    cs = CoreState(seed_core())
    for i in range(28):                                            # many unsupported hypotheses
        _hyp(cs, text=f"Hypothesis idea {i}")
    # no growth since last time -> development 0, big unsupported backlog -> degenerating
    ext = {"vitality_prev": {"active": len(cs.active_claims()), "links": 0, "promoted": 0,
                             "emergent": 0, "objects": len(cs.core.objects)}}
    rec = homeostasis.vitality(cs, ext, _Proto())
    assert rec["unsupported_hypotheses"] > 25
    assert rec["verdict"] == "degenerating"
