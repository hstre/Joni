"""'Provenance is not a topic': the 'forum' (and reserved) sink must not manufacture conflicts.

A conflict needs two claims on the same SUBJECT. 'forum' is a platform a claim was heard ON, not
what it is ABOUT - claims land there because their subject is unknown. So a 'forum vs forum' pair
is a category error, not a contradiction. Detection must skip sink buckets, and the legacy stock of
such false conflicts must close as TOLERATED (no claim harmed), reviving any claim they stranded.
"""
from joni.autonomy import homeostasis, quality
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_is_sink_topic():
    assert quality.is_sink_topic("forum") is True
    assert quality.is_sink_topic("unsorted") is True
    assert quality.is_sink_topic("General") is True          # reserved, case-insensitive
    assert quality.is_sink_topic("routing") is False
    assert quality.is_sink_topic("") is False


def test_a_sink_pair_never_opens_a_conflict():
    cs = CoreState(seed_core())
    cs.learn("routing must always be remote", "forum")
    cs.learn("routing must never be remote", "forum")
    assert cs.detect_and_open_conflicts() == []              # both in the sink -> no contradiction


def test_a_real_topic_pair_still_opens_a_conflict():
    cs = CoreState(seed_core())
    cs.learn("routing must always be remote", "routing")
    cs.learn("routing must never be remote", "routing")
    assert len(cs.detect_and_open_conflicts()) == 1          # real subject -> real contradiction


def test_tolerate_sink_conflicts_closes_a_false_conflict_and_revives_both_claims():
    cs = CoreState(seed_core())
    a = cs.learn("routing must always be remote", "forum")
    b = cs.learn("routing must never be remote", "forum")
    cid = cs.open_conflict((a, b), severity="hard")          # a legacy false conflict, direct
    assert cs.core.get(a).status.value == "contested"
    assert cs.core.get(b).status.value == "contested"

    closed = homeostasis.tolerate_sink_conflicts(cs, _Proto(), 1)
    assert closed == 1
    assert cs.core.get(cid).conflict_status.value == "tolerated"   # closed, not resolved
    assert cs.core.get(a).status.value == "active"           # revived - not left in limbo
    assert cs.core.get(b).status.value == "active"
    # nothing was superseded/rejected - a false conflict harms no claim
    assert cs.core.get(a).status.value != "superseded"


def test_a_real_conflict_is_never_tolerated_by_the_sink_pass():
    cs = CoreState(seed_core())
    a = cs.learn("routing must always be remote", "routing")
    cs.learn("routing must never be remote", "routing")
    cs.detect_and_open_conflicts()                           # a genuine, same-subject conflict
    assert homeostasis.tolerate_sink_conflicts(cs, _Proto(), 1) == 0   # untouched
    assert cs.core.get(a).status.value == "contested"        # stays contested - it IS a dispute


def test_a_claim_still_held_by_a_real_conflict_stays_contested():
    cs = CoreState(seed_core())
    # x is in TWO conflicts: a spurious sink one and a genuine real-topic one.
    x = cs.learn("routing must always be remote", "forum")
    y = cs.learn("routing must never be remote", "forum")
    cs.open_conflict((x, y), severity="hard")                # spurious sink pair
    z = cs.learn("routing must never be remote", "routing")
    x2 = cs.learn("routing must always be remote", "routing")
    cs.detect_and_open_conflicts()                           # real conflict between z and x2
    homeostasis.tolerate_sink_conflicts(cs, _Proto(), 1)
    # the sink pair's OWN claims revive, but z/x2 (a real dispute) stay contested
    assert cs.core.get(z).status.value == "contested"
    assert cs.core.get(x2).status.value == "contested"
