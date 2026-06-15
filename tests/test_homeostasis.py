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


def test_retire_junk_topics_drains_stopword_and_compound_topics():
    cs = CoreState(seed_core())
    cs.learn("'about' keeps recurring, tracking it as a topic", "about")        # stopword topic
    cs.learn("a bridge claim", "alignment+memory")                             # compound topic
    keep = cs.learn("routing reduces latency", "routing")                      # good topic
    ext = {"topics_added": ["about", "alignment+memory", "calibration"]}
    out = homeostasis.retire_junk_topics(cs, ext, _Proto())
    assert out["retired_claims"] >= 2
    topics = cs.topics()
    assert "about" not in topics and "alignment+memory" not in topics          # junk drained
    assert "routing" in topics                                                  # good kept
    assert cs.core.get(keep).status.value == "active"
    assert ext["topics_added"] == ["calibration"]                              # self-added pruned


def test_retire_keeps_a_junk_topic_claim_that_earned_support():
    cs = CoreState(seed_core())
    a = cs.learn("a real cross idea", "alignment+memory")
    ev = cs.learn("supporting evidence", "alignment+memory")
    cs.corroborate(a, cs.core.get(ev), relation="supports")                    # 'a' earned support
    homeostasis.retire_junk_topics(cs, {}, _Proto())
    assert cs.core.get(a).status.value == "active"     # ugly topic, but a real idea -> kept


def test_retire_junk_methods_sheds_off_domain_candidates(monkeypatch):
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: True)
    off = ("c++", "coding", "guidelines", "devops", "frontend")

    def cd(probe, anchor):
        p_off = any(k in probe.lower() for k in off)
        a_off = any(k in anchor.lower() for k in off)
        return 0.15 if (p_off == a_off) else 0.9
    monkeypatch.setattr(embeddings, "cosine_distance", cd)

    cs = CoreState(seed_core())
    junk = cs.propose_method(name="CppCoreGuidelines", summary="C++ coding guidelines",
                             applicable_to=("routing",), origin="github")
    good = cs.propose_method(name="routing-as-a-lens", summary="model routing for agents",
                             applicable_to=("routing",), origin="joni:emergent")
    ext: dict = {}
    out = homeostasis.retire_junk_methods(cs, ext, _Proto())
    assert out["retired_methods"] == 1
    assert cs.core.get(junk).status is l9.Status.REJECTED          # off-domain -> shed
    assert cs.core.get(good).status is l9.Status.CANDIDATE         # on-domain -> kept
    assert good in ext["methods_domain_ok"]                        # cached, won't re-embed


def test_retire_junk_methods_is_a_noop_without_an_embedder(monkeypatch):
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: False)
    cs = CoreState(seed_core())
    cs.propose_method(name="CppCoreGuidelines", summary="C++ guidelines", origin="github")
    out = homeostasis.retire_junk_methods(cs, {}, _Proto())
    assert out["retired_methods"] == 0                              # fail-open: nothing shed


def test_retire_junk_hypotheses_sheds_artifact_through_lines():
    # lexical junk subjects ('mllm' vowelless, 'modes' stopword) are shed with no embedder
    cs = CoreState(seed_core())
    p = cs.learn("a routing parent", "routing")
    j1 = cs.hypothesize("Across my routing claims, 'mllm' recurs as a through-line.",
                        "routing", parents=(p,))
    j2 = cs.hypothesize("Across my routing claims, 'modes' recurs as a through-line.",
                        "routing", parents=(p,))
    good = cs.hypothesize("Across my routing claims, 'retrieval' recurs as a through-line.",
                          "routing", parents=(p,))
    out = homeostasis.retire_junk_hypotheses(cs, {}, _Proto())
    assert out["retired_hyps"] == 2
    assert cs.core.get(j1).status is l9.Status.REJECTED
    assert cs.core.get(j2).status is l9.Status.REJECTED
    assert cs.core.get(good).status is l9.Status.CANDIDATE      # admissible subject -> kept


def test_retire_junk_hypotheses_keeps_a_supported_one():
    cs = CoreState(seed_core())
    p = cs.learn("a routing parent", "routing")
    h = cs.hypothesize("Across my routing claims, 'mllm' recurs as a through-line.",
                       "routing", parents=(p,))
    ev = cs.learn("evidence for it", "routing")
    cs.corroborate(h, cs.core.get(ev), relation="supports")     # it earned support
    out = homeostasis.retire_junk_hypotheses(cs, {}, _Proto())
    assert out["retired_hyps"] == 0
    assert cs.core.get(h).status is l9.Status.CANDIDATE          # supported -> kept even if ugly
