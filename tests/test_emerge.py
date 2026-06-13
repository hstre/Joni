"""Emergent self-development: new structure precipitates from Joni's own recurring net."""

import desi_layer9 as l9
from joni.autonomy import emerge
from joni.autonomy.core_state import CoreState


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


def test_a_cross_topic_lens_is_stored_as_a_candidate_method():
    cs = _cs_with_recurrence()
    out = emerge.emerge(cs, {}, _Proto())
    assert out["method"] == "calibration"
    m = cs.core.all(l9.ObjectType.METHOD)[0]
    assert m.status is l9.Status.CANDIDATE         # for Kevin to trial; never promoted here
    assert m.name == "calibration-as-a-lens"
    assert set(m.applicable_to) >= {"routing", "privacy", "drift"}


def test_a_within_topic_cluster_yields_a_higher_order_synthesis():
    cs = CoreState(l9.Layer9())
    for i in range(3):
        cs.learn(f"latency budgets shape routing choice number {i}", "routing")
    out = emerge.emerge(cs, {}, _Proto())
    assert out["synthesis"] == 1
    syn = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if c.status is l9.Status.CANDIDATE and c.derived_from
           and c.text.startswith("Across my")]
    assert syn and syn[0].derived_from            # derived from the cluster it abstracts


def test_quiet_when_nothing_recurs():
    cs = CoreState(l9.Layer9())
    cs.learn("a one-off observation about onboarding", "ux")
    out = emerge.emerge(cs, {}, _Proto())
    assert out == {"topic": None, "synthesis": 0, "method": None}
