"""Query-based literature synthesis: condense several fetched papers on a topic into one SOURCE
feed item (candidate, never confirmed). Opt-in, non-core, deduped per (topic, source-set)."""

import desi_layer9 as l9
from joni.autonomy import model_call, synthesis
from joni.autonomy.core_state import CoreState, seed_core
from joni.autonomy.sources import Item


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _items(topic):
    return [Item("arxiv", "p1", f"A study of {topic} in agents", "https://x",
                 f"{topic} improves recall in long runs"),
            Item("arxiv", "p2", f"More results on {topic}", "https://y",
                 f"a second {topic} finding worth noting")]


def _cs(topic="memory"):
    cs = CoreState(seed_core())
    cs.learn(f"{topic} is something I track", topic, source_id="s0")
    return cs


def _on(monkeypatch, tmp_path, reply, *, on=True):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_LITERATURE_SYNTHESIS", "1" if on else "0")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: reply)


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.delenv("JONI_LITERATURE_SYNTHESIS", raising=False)
    out = synthesis.synthesize(_cs(), {}, _Proto(), 1, items=_items("memory"))
    assert out == {"synthesized": 0}


def test_synthesizes_one_source_from_several_papers(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path, "Recent work finds memory consolidation aids long-run recall.")
    cs, ext = _cs("memory"), {}
    out = synthesis.synthesize(cs, ext, _Proto(), 1, items=_items("memory"))
    assert out["synthesized"] == 1 and out["topic"] == "memory" and out["sources"] == 2
    # it entered as a real claim on the topic (a SOURCE, candidate - never confirmed)
    got = [c for c in cs.core.all(l9.ObjectType.CLAIM) if "consolidation" in getattr(c, "text", "")]
    assert got and got[0].status is not l9.Status.CONFIRMED
    assert ext["synthesis_log"][-1]["topic"] == "memory"


def test_needs_at_least_two_papers(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path, "x")
    one = [_items("memory")[0]]
    assert synthesis.synthesize(_cs("memory"), {}, _Proto(), 1, items=one)["synthesized"] == 0


def test_same_paper_set_is_not_re_synthesized(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path, "Recent work finds memory consolidation aids recall.")
    cs, ext = _cs("memory"), {}
    assert synthesis.synthesize(cs, ext, _Proto(), 1, items=_items("memory"))["synthesized"] == 1
    # past the cadence, the SAME (topic, source-set) is deduped -> nothing new
    assert synthesis.synthesize(cs, ext, _Proto(), 20, items=_items("memory"))["synthesized"] == 0
