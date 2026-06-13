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
    cs = CoreState(l9.Layer9())
    cs.learn("cheap local models handle most turns", "routing")
    cs.learn("episodic memory preserves continuity", "memory")
    return cs


def test_invention_makes_a_candidate_hypothesis_derived_from_two_claims():
    cs = _cs_two_topics()
    out = invent.invent(cs, {}, _Proto())
    assert out["hypotheses"] == 1
    hyps = cs.hypotheses()
    assert len(hyps) == 1
    h = hyps[0]
    assert h.status is l9.Status.CANDIDATE                 # a guess, never auto-active
    assert h.authority is not l9.Authority.AUTHORITATIVE
    assert len(h.derived_from) == 2                        # bridges two parent claims
    assert "Hypothesis" in h.text


def test_invention_dedupes_per_topic_pair():
    cs = _cs_two_topics()
    ext = {}
    invent.invent(cs, ext, _Proto())
    before = len(cs.hypotheses())
    invent.invent(cs, ext, _Proto())                      # same topic pair -> nothing new
    assert len(cs.hypotheses()) == before


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
