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


def test_core_ask_gate_holds_one_offs_and_releases_sustained():
    """A single paper mentioning a core word must NOT raise a core-ask; only a trigger that
    recurs across CORE_ASK_SUSTAIN cycles is worth interrupting a human."""
    from joni.autonomy.improve import CORE_ASK_SUSTAIN, gate_core_asks

    ext: dict = {}
    # a one-off mention in cycle 0 -> held, nothing released
    assert gate_core_asks(ext, ["scoring"], 0) == set()
    # it does not recur next cycle -> its streak decays
    assert gate_core_asks(ext, [], 1) == set()
    assert ext["core_ask_signals"]["scoring"] == 0

    # now 'operator' recurs every cycle: released exactly when it reaches the sustain threshold
    released = None
    for c in range(2, 2 + CORE_ASK_SUSTAIN):
        released = gate_core_asks(ext, ["operator"], c)
    assert released == {"operator"}                     # sustained -> raised once
    # immediately after, the streak is reset and the cooldown blocks re-raising
    assert gate_core_asks(ext, ["operator"], 2 + CORE_ASK_SUSTAIN) == set()


def test_core_ask_only_on_the_core_sense_of_a_keyword(monkeypatch):
    """A paper that merely uses 'operator' in an unrelated sense must NOT raise a core-ask."""
    from joni.autonomy import embeddings, improve
    from joni.autonomy.sources import Item

    monkeypatch.setattr(embeddings, "available", lambda: True)
    # text near 'model reduction' is far from the core-operator ref, near the other ref

    def cd(text, ref):
        t, r = text.lower(), ref.lower()
        t_math = "model reduction" in t or "linear algebra" in t
        r_math = "model reduction" in r or "linear algebra" in r or "functional analysis" in r
        return 0.2 if (t_math == r_math) else 0.85
    monkeypatch.setattr(embeddings, "cosine_distance", cd)

    s = seed_identity()
    math_item = Item("zenodo", "9", "Operator inference for model reduction",
                     "http://x", "symmetry-reduced operator inference via linear algebra")
    rel = judge(s, math_item)
    out = improve.derive(s, [(math_item, rel)])
    assert not any(i.kind == "core_change" for i in out)     # coincidental keyword - held back


def test_core_ask_still_raised_on_the_core_sense(monkeypatch):
    from joni.autonomy import embeddings, improve
    from joni.autonomy.sources import Item
    monkeypatch.setattr(embeddings, "available", lambda: True)

    def cd(text, ref):
        t, r = text.lower(), ref.lower()
        t_core = "epistemic" in t or "state-change" in t or "write path" in t
        r_core = "epistemic" in r or "state-change" in r or "write path" in r
        return 0.2 if (t_core == r_core) else 0.85
    monkeypatch.setattr(embeddings, "cosine_distance", cd)

    s = seed_identity()
    core_item = Item("arxiv", "10", "Rethinking the state-change operator of epistemic agents",
                     "http://x", "a new write-path operator for an epistemic state machine")
    rel = judge(s, core_item)
    out = improve.derive(s, [(core_item, rel)])
    assert any(i.kind == "core_change" for i in out)         # genuine core sense - raised
