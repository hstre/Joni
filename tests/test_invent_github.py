"""Joni invents his own cross-topic hypotheses, and GitHub is a source."""

import desi_layer9 as l9
from joni.autonomy import invent, sources
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_two_topics():
    # two topics that each earned research status (>=3 claims across >=2 independent sources),
    # so invention may bridge them - a one-source word cluster is no longer a research direction.
    cs = CoreState(l9.Layer9())
    for i in range(3):
        cs.learn(f"cheap local models handle most turns {i}", "routing", source_id=f"arxiv:r{i}")
        cs.learn(f"episodic memory preserves continuity {i}", "memory", source_id=f"arxiv:m{i}")
    return cs


def test_a_cross_topic_bridge_is_held_as_a_pattern_hint_not_a_hypothesis():
    # Priority 3 at the source: a bare "pattern behind X might also apply to Y" bridge is lexical
    # recurrence, so it is filed as a pattern hint - NOT minted as a candidate hypothesis.
    cs = _cs_two_topics()
    ext: dict = {}
    out = invent.invent(cs, ext, _Proto())
    assert out["hypotheses"] == 0 and out["pattern_hints"] == 1    # a hint, not a hypothesis
    assert cs.hypotheses() == []                                   # nothing minted into the graph
    assert ext.get("invent_pattern_hints")                        # the bridge is recorded


def test_invention_dedupes_per_topic_pair():
    cs = _cs_two_topics()
    ext: dict = {}
    invent.invent(cs, ext, _Proto())
    assert len(ext.get("invent_pattern_hints", [])) == 1
    invent.invent(cs, ext, _Proto())                      # same topic pair -> nothing new
    assert len(ext.get("invent_pattern_hints", [])) == 1


def test_a_hypothesis_is_never_confirmed_automatically():
    cs = _cs_two_topics()
    invent.invent(cs, {}, _Proto())
    assert not [c for c in cs.core.all(l9.ObjectType.CLAIM)
                if c.status is l9.Status.CONFIRMED]


def test_github_is_an_online_source():
    names = {f.name for f in sources.get_fetchers(online=True)}
    assert "github" in names
    assert {"arxiv", "hackernews", "huggingface"} <= names
    # offline still uses only the deterministic mock
    assert {f.name for f in sources.get_fetchers(online=False)} == {"mock"}


def test_cycle_reports_invention(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.delenv("JONI_ONLINE", raising=False)
    from joni.autonomy.run import one_cycle
    summary = one_cycle()
    assert "invented" in summary
    assert "hypotheses" in (tmp_path / "docs" / "index.html").read_text()
