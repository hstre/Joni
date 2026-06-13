"""Emergent self-development: new structure precipitates from Joni's own recurring net."""

import desi_layer9 as l9
from joni.autonomy import emerge
from joni.autonomy.core_state import CoreState
from semantic_stub import StubSemanticLayer


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_recurrence():
    """'calibration' recurs across three different topics; build that net."""
    cs = CoreState(l9.Layer9())
    cs.learn("calibration improves routing decisions", "routing")
    cs.learn("calibration matters for privacy budgets", "privacy")
    cs.learn("calibration of drift detectors reduces false alarms", "drift")
    return cs


def test_a_recurring_cross_topic_term_becomes_a_tracked_topic():
    cs = _cs_with_recurrence()
    ext: dict = {}
    out = emerge.emerge(cs, ext, _Proto())
    assert out["topic"] == "calibration"
    assert "calibration" in cs.topics()            # now tracked in its own right
    assert "calibration" in ext["emerged_topics"]


def test_emergent_topic_is_not_re_emitted():
    cs = _cs_with_recurrence()
    ext: dict = {}
    emerge.emerge(cs, ext, _Proto())
    before = len(cs.topics())
    out2 = emerge.emerge(cs, ext, _Proto())        # same recurrence -> not re-added
    assert out2["topic"] is None
    assert len(cs.topics()) == before


def test_a_cross_topic_lens_is_stored_as_a_candidate_method_only_when_eligible():
    cs = _cs_with_recurrence()
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())   # Layer 9: eligible
    assert out["method"] == "calibration"
    m = cs.core.all(l9.ObjectType.METHOD)[0]
    assert m.status is l9.Status.CANDIDATE         # for Kevin to trial; never promoted here
    assert m.name == "calibration-as-a-lens"
    assert set(m.applicable_to) >= {"routing", "privacy", "drift"}


def test_no_method_for_kevin_when_layer9_does_not_clear_the_cluster():
    cs = _cs_with_recurrence()
    # different frames -> Layer 9 says 'unrelated' -> no method, no synthesis.
    out = emerge.emerge(cs, {}, _Proto(),
                        layer=StubSemanticLayer(frame_a="empirical_causal",
                                                frame_b="information_theoretic"))
    assert out["method"] is None
    assert cs.core.all(l9.ObjectType.METHOD) == []
    # the rejected analysis is still recorded for inspection
    assert cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)


def test_a_within_topic_cluster_yields_a_higher_order_synthesis_when_eligible():
    cs = CoreState(l9.Layer9())
    cs.learn("latency budgets shape routing choices", "routing")
    cs.learn("memory pressure changes how routing is decided", "routing")
    cs.learn("load spikes shift routing toward cheaper paths", "routing")
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["synthesis"] == 1
    syn = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if c.status is l9.Status.CANDIDATE and c.derived_from
           and c.text.startswith("Across my")]
    assert syn and syn[0].derived_from            # derived from the cluster it abstracts


def test_quiet_when_nothing_recurs():
    cs = CoreState(l9.Layer9())
    cs.learn("a one-off observation about onboarding", "ux")
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out == {"topic": None, "synthesis": 0, "method": None}
