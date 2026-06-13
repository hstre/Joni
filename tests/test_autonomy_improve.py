import pytest

from joni.autonomy import governance
from joni.autonomy.improve import apply_peripheral, derive, judge
from joni.autonomy.sources import Item, MockFetcher
from joni.seed import seed_identity


def test_judge_matches_existing_topic():
    s = seed_identity()
    item = Item("arxiv", "1", "Better model routing for local agents",
                "http://x", "cheap routing wins")
    rel = judge(s, item)
    assert rel.relevant
    assert rel.topic == "routing"


def test_judge_flags_a_new_topic():
    s = seed_identity()
    item = Item("arxiv", "2", "Calibration of agents", "http://x",
                "a study of calibration")
    rel = judge(s, item)
    assert rel.relevant and rel.new_topic == "calibration"


def test_derive_splits_peripheral_and_core():
    s = seed_identity()
    items = MockFetcher().fetch(["privacy", "routing", "memory", "drift"], limit=5)
    judged = [(it, judge(s, it)) for it in items]
    judged = [(it, r) for it, r in judged if r.relevant]
    imps = derive(s, judged)
    kinds = {i.kind for i in imps}
    assert "track_topic" in kinds        # peripheral self-improvement
    assert "core_change" in kinds        # the conflict-operator paper -> ask
    core = next(i for i in imps if i.kind == "core_change")
    assert not core.autonomous           # must not be self-applied


def test_apply_peripheral_tracks_a_new_topic():
    s = seed_identity()
    ext = {}
    item = Item("arxiv", "3", "Calibration of agents", "http://x", "calibration study")
    rel = judge(s, item)
    imp = derive(s, [(item, rel)])[0]
    assert imp.kind == "track_topic"
    refs = apply_peripheral(s, ext, imp)
    assert "calibration" in ext["topics_added"]
    assert refs["claim"] in s.claims
    assert any(c.topic == "calibration" for c in s.claims.values())


def test_apply_peripheral_refuses_core_change():
    s = seed_identity()
    from joni.autonomy.improve import Improvement
    core = Improvement("core_change", "x", "operator", "needs logic", "k", "u")
    with pytest.raises(governance.CoreChangeBlocked):
        apply_peripheral(s, {}, core)
