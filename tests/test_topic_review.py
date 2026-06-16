"""Stage 3: an LLM judges whether a candidate topic actually belongs - a lexical filter cannot.
Non-authoritative: an 'invalid' verdict sheds only the topic's 0-support claims, through the gate;
a supported idea is kept. Captured + cached + bounded. Off by default."""

import desi_layer9 as l9
from joni.autonomy import model_call, topic_review
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    cs = CoreState(l9.Layer9())
    out = topic_review.review_topics(cs, {}, _Proto(), 1)
    assert out == {"reviewed": 0, "rejected_topics": 0, "retired_claims": 0}


def test_llm_sheds_a_junk_topic_but_keeps_supported_claims(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))

    def fake(profile, system, user):
        # Granite calls the off-domain botanical topic junk, the on-domain one valid.
        return '{"valid": false, "reason": "off-domain botanical term"}' \
            if "laxiflora" in user else '{"valid": true, "reason": "on-domain"}'
    monkeypatch.setattr(model_call, "_complete", fake)

    cs = CoreState(l9.Layer9())
    cs.learn("laxiflora is a grass species", "laxiflora")          # 0-support junk
    cs.learn("more about laxiflora leaves", "laxiflora")           # 0-support junk
    cs.learn("alignment matters for safety", "alignment")          # on-domain (>=2 claims)
    cs.learn("alignment needs careful evaluation", "alignment")
    before = len(cs.active_claims())
    out = topic_review.review_topics(cs, {}, _Proto(), 1)
    assert out["reviewed"] == 2 and out["rejected_topics"] == 1     # both judged; laxiflora junk
    assert out["retired_claims"] == 2                               # its two 0-support claims gone
    assert "laxiflora" not in cs.topics()                          # drained from the topic list
    assert "alignment" in cs.topics()                             # the valid topic kept
    assert len(cs.active_claims()) == before - 2


def test_verdict_is_cached_so_a_topic_is_judged_once(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    calls = []

    def fake(profile, system, user):
        calls.append(1)
        return '{"valid": true, "reason": "ok"}'
    monkeypatch.setattr(model_call, "_complete", fake)

    cs = CoreState(l9.Layer9())
    for i in range(2):
        cs.learn(f"routing claim {i}", "routing")
    ext: dict = {}
    topic_review.review_topics(cs, ext, _Proto(), 1)
    n1 = len(calls)
    topic_review.review_topics(cs, ext, _Proto(), 2)               # same topic, already judged
    assert len(calls) == n1                                        # not re-called
    assert ext["topic_llm_seen"]["routing"] == "valid"


def test_a_supported_junk_topic_claim_is_not_shed(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete",
                        lambda p, s, u: '{"valid": false, "reason": "junk"}')
    cs = CoreState(l9.Layer9())
    c1 = cs.learn("cotton is a fibre", "cotton")                  # 0-support -> will be shed
    c2 = cs.learn("cotton grows in fields", "cotton")            # will earn support -> kept
    sup = cs.learn("an external corroborating note", "other")
    cs.corroborate(c2, cs.core.get(sup), relation="supports")    # c2 now has support
    out = topic_review.review_topics(cs, {}, _Proto(), 1)
    assert out["rejected_topics"] == 1                            # model called cotton junk
    assert cs.core.get(c2).status.value != "rejected"           # the supported claim survives
    assert cs.core.get(c1).status.value == "rejected"           # the 0-support one is shed
