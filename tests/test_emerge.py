"""Emergent self-development: new structure precipitates from Joni's own recurring net."""

import desi_layer9 as l9
from joni.autonomy import emerge, model_call
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


def test_a_recurring_cross_topic_term_becomes_a_tracked_topic(monkeypatch):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)   # lexical-only mode: no gate
    cs = _cs_with_recurrence()
    ext: dict = {}
    out = emerge.emerge(cs, ext, _Proto())
    assert out["topic"] == "calibration"
    assert "calibration" in cs.topics()            # now tracked in its own right
    assert "calibration" in ext["emerged_topics"]


def test_emergent_topic_is_not_re_emitted(monkeypatch):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    cs = _cs_with_recurrence()
    ext: dict = {}
    emerge.emerge(cs, ext, _Proto())
    before = len(cs.topics())
    out2 = emerge.emerge(cs, ext, _Proto())        # same recurrence -> not re-added
    assert out2["topic"] is None
    assert len(cs.topics()) == before


def test_a_term_recurring_across_too_few_topics_is_not_a_topic(monkeypatch):
    # the entire junk graveyard was minted at exactly 2 topics - that bar is gone.
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    cs = CoreState(l9.Layer9())
    cs.learn("calibration improves routing decisions", "routing")
    cs.learn("calibration matters for privacy budgets", "privacy")
    cs.learn("better calibration helps routing again", "routing")   # 3 claims, only 2 topics
    out = emerge.emerge(cs, {}, _Proto())
    assert out["topic"] is None


def test_the_topic_gate_judges_a_candidate_before_it_is_minted(monkeypatch, tmp_path):
    # with the semantic layer on, a generic recurring word is judged by the Granite topic
    # gatekeeper BEFORE the mint: invalid -> never minted, finalised, and protocolled.
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete",
                        lambda p, s, u: '{"valid": false, "reason": "generic word"}')
    cs = _cs_with_recurrence()
    ext: dict = {}
    proto = _Proto()
    out = emerge.emerge(cs, ext, proto)
    assert out["topic"] is None
    assert "calibration" not in cs.topics()
    assert "calibration" in ext["emerged_topics"]              # a real verdict: never re-asked
    assert ext["topic_llm_seen"]["calibration"] == "invalid"   # shared cache with the review
    assert any("rejected by the topic gate" in s for k, s in proto.events if k == "emerged")


def test_a_gate_approved_candidate_mints_and_records_its_mint_cycle(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete",
                        lambda p, s, u: '{"valid": true, "reason": "a real concept"}')
    cs = _cs_with_recurrence()
    ext: dict = {}
    out = emerge.emerge(cs, ext, _Proto(), cycle=7)
    assert out["topic"] == "calibration"
    assert ext["emerged_topic_cycle"]["calibration"] == 7      # the orphan drain's grace anchor
    assert ext["topic_llm_seen"]["calibration"] == "valid"


def test_a_failed_gate_call_burns_nothing_the_candidate_is_retried(monkeypatch, tmp_path):
    # no verdict is not a verdict: the mint is withheld, but the term stays un-finalised so a
    # later cycle (with the model back) can still judge it.
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    def _down(p, s, u):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(model_call, "_complete", _down)
    cs = _cs_with_recurrence()
    ext: dict = {}
    out = emerge.emerge(cs, ext, _Proto())
    assert out["topic"] is None
    assert "calibration" not in ext.get("emerged_topics", [])  # not burned
    monkeypatch.setattr(model_call, "_complete",
                        lambda p, s, u: '{"valid": true, "reason": "ok"}')
    out2 = emerge.emerge(cs, ext, _Proto())                    # the model is back
    assert out2["topic"] == "calibration"


def test_a_cross_topic_lens_is_stored_as_a_candidate_method_only_when_eligible():
    cs = _cs_with_recurrence()
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())   # Layer 9: eligible
    assert out["method"] == "calibration"
    m = cs.core.all(l9.ObjectType.METHOD)[0]
    assert m.status is l9.Status.CANDIDATE         # for Kevin to trial; never promoted here
    assert m.name == "calibration-as-a-lens"
    assert set(m.applicable_to) >= {"routing", "privacy", "drift"}


def test_method_lens_on_a_sink_term_is_not_minted():
    # a sink/provenance bucket term is never a transferable lens - blocked at the source, the same
    # bar the synthesis move applies (operator follow-up: garbage/sink lenses like gatemem).
    cs = CoreState(l9.Layer9())
    cs.learn("gatemem improves routing decisions", "routing")
    cs.learn("gatemem matters for privacy budgets", "privacy")
    cs.learn("gatemem shapes drift detection", "drift")
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["method"] is None


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


def test_a_non_judgment_cluster_is_retried_then_synthesises_when_eligible():
    """A layer-absent 'insufficient' must not mark a cluster done forever: when the
    Semantic Layer comes back, the same cluster can still earn a synthesis."""
    cs = CoreState(l9.Layer9())
    cs.learn("latency budgets shape routing choices", "routing")
    cs.learn("memory pressure changes how routing is decided", "routing")
    cs.learn("load spikes shift routing toward cheaper paths", "routing")
    ext: dict = {}
    # 1) layer absent -> the cluster gets only a non-judgment, not finalised
    out1 = emerge.emerge(cs, ext, _Proto())                  # NullSemanticLayer -> insufficient
    assert out1["synthesis"] == 0
    assert not ext.get("synthesized")                        # cluster NOT permanently marked done
    assert ext.get("emerge_insufficient")                    # queued for retry
    # 2) the layer is available -> the same cluster now yields a higher-order synthesis
    out2 = emerge.emerge(cs, ext, _Proto(), layer=StubSemanticLayer())
    assert out2["synthesis"] == 1


def test_synthesis_blocked_when_two_cluster_claims_live_contradict():
    # a synthesis must be over a majority-compatible cluster (operator point 3): if two of its
    # claims are in a LIVE conflict, it is not minted even when Layer 9 would clear it.
    cs = CoreState(l9.Layer9())
    a = cs.learn("latency budgets shape routing choices", "routing")
    b = cs.learn("memory pressure changes how routing is decided", "routing")
    cs.learn("load spikes shift routing toward cheaper paths", "routing")
    cs.open_conflict([a, b])                                  # two cluster claims contradict
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["synthesis"] == 0


def test_synthesis_over_a_sink_topic_is_not_minted():
    # a drain/sink topic is undifferentiated - not a real basis for a through-line (point 3)
    cs = CoreState(l9.Layer9())
    cs.learn("latency budgets shape routing choices", "forum")
    cs.learn("memory pressure changes how routing is decided", "forum")
    cs.learn("load spikes shift routing toward cheaper paths", "forum")
    out = emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["synthesis"] == 0


def test_synthesis_wording_is_neutral_and_still_detected_as_synthetic():
    # B1: no 'single underlying factor' causal claim; still starts 'Across my' so the core's
    # synthetic detector keeps excluding it from the vocabulary.
    cs = CoreState(l9.Layer9())
    cs.learn("latency budgets shape routing choices", "routing")
    cs.learn("memory pressure changes how routing is decided", "routing")
    cs.learn("load spikes shift routing toward cheaper paths", "routing")
    emerge.emerge(cs, {}, _Proto(), layer=StubSemanticLayer())
    syn = [c for c in cs.core.all(l9.ObjectType.CLAIM) if c.text.startswith("Across my")]
    assert syn and "single underlying factor" not in syn[0].text
    assert emerge._is_synthetic(syn[0].text)
