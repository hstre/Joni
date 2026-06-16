"""Kevin, for real: a creative cross-domain transfer hypothesis over his deepseek-v4-pro profile,
entering Layer 9 as a candidate through the gate, captured, and counted as a Kevin call."""

from pathlib import Path

import desi_layer9 as l9
from joni.autonomy import kevin_llm, model_call
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_two_research_topics():
    # two topics that each earned research status: >=3 claims across >=2 independent sources
    cs = CoreState(seed_core())
    for i in range(3):
        cs.learn(f"routing claim {i} about latency and serving", "routing", source_id=f"arxiv:r{i}")
        cs.learn(f"memory claim {i} about episodic continuity", "memory", source_id=f"arxiv:m{i}")
    return cs


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    out = kevin_llm.propose(CoreState(seed_core()), {}, _Proto(), 3)
    assert out == {"kevin_calls": 0, "hypotheses": 0}


def test_kevin_proposes_cross_domain_hypothesis_via_his_own_model(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    seen = {}

    def fake(profile, system, user):
        seen["slug"] = profile.served_slug
        return '[{"text":"Routing latency budgets could bound memory consolidation",' \
               ' "topic":"routing"}]'
    monkeypatch.setattr(model_call, "_complete", fake)

    cs = _cs_with_two_research_topics()
    before = len(cs.hypotheses())
    out = kevin_llm.propose(cs, {}, _Proto(), 3)
    assert out["kevin_calls"] == 1 and out["hypotheses"] == 1
    assert seen["slug"] == "deepseek-v4-pro"                     # Kevin's own model, not Granite
    assert len(cs.hypotheses()) == before + 1                    # a candidate hypothesis, gated
    # the call is captured and counts as a Kevin call in the dashboard telemetry
    t = model_call.telemetry(Path(tmp_path) / "state" / "model_calls")
    assert t["kevin_calls"] == 1


def test_empty_truncated_call_is_a_visible_failure_not_a_silent_zero(monkeypatch, tmp_path):
    # the reasoning model out of budget returns empty content. That is a FAILED creative call:
    # no hypothesis, but recorded honestly (not a silent '0 proposals'), and cadence still applies.
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: "")   # empty content
    cs = _cs_with_two_research_topics()
    ext: dict = {}
    proto = _Proto()
    before = len(cs.hypotheses())
    out = kevin_llm.propose(cs, ext, proto, 3)
    assert out["kevin_calls"] == 1 and out["hypotheses"] == 0           # call happened, 0 produced
    assert len(cs.hypotheses()) == before                              # nothing entered the gate
    assert ext["kevin_last_cycle"] == 3                                # cadence bounds cost
    assert ext["kevin_llm"][-1]["failed"].startswith("empty")          # logged as a failure
    assert any(k == "kevin" and "NO proposal" in s for k, s in proto.events)  # visible in protocol


def test_cadence_spaces_kevin_out(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_KEVIN_EVERY", "3")
    monkeypatch.setattr(model_call, "_complete",
                        lambda p, s, u: '[{"text":"A links to B somehow","topic":"routing"}]')
    cs = _cs_with_two_research_topics()
    ext: dict = {}
    assert kevin_llm.propose(cs, ext, _Proto(), 3)["kevin_calls"] == 1
    assert kevin_llm.propose(cs, ext, _Proto(), 4)["kevin_calls"] == 0   # within cadence -> wait
    assert kevin_llm.propose(cs, ext, _Proto(), 6)["kevin_calls"] == 1   # cadence elapsed


def test_no_op_with_fewer_than_two_topics(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: "[]")
    cs = CoreState(l9.Layer9())                                 # empty core: no topics
    assert kevin_llm.propose(cs, {}, _Proto(), 3)["kevin_calls"] == 0


def test_kevin_is_not_set_on_thin_or_synthetic_topics(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: "[]")
    # two topics that DO pass research_topics (>=3 claims across >=2 sources), but whose claims
    # are all synthetic through-line bookkeeping - Kevin must NOT be set on junk to "refine".
    cs = CoreState(l9.Layer9())
    for i in range(3):
        cs.learn(f"Across my claims, 'x{i}' recurs as a through-line worth testing", "alpha",
                 source_id=f"arxiv:a{i}")
        cs.learn(f"Across my claims, 'y{i}' recurs as a through-line worth testing", "beta",
                 source_id=f"arxiv:b{i}")
    assert "alpha" in cs.research_topics() and "beta" in cs.research_topics()   # they pass #2...
    assert kevin_llm.propose(cs, {}, _Proto(), 3)["kevin_calls"] == 0           # ...but #7 blocks
