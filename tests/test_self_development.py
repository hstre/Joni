"""Joni keeps restructuring his own state - even with no new input - honestly."""

import desi_layer9 as l9
from joni.autonomy import develop
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_corroborating_claims():
    cs = CoreState(l9.Layer9())
    cs.learn("cheap local models handle most routing turns well", "routing")
    cs.learn("most routing turns are handled by cheap local models", "routing")
    return cs


def test_develop_links_mutually_supporting_claims_unreviewed():
    cs = _cs_with_corroborating_claims()
    ext = {}
    out = develop.develop(cs, ext, _Proto())
    assert out["links"] >= 1
    links = cs.core.all(l9.ObjectType.EVIDENCE_LINK)
    assert links
    # the link is unreviewed and candidate - it never confirms anything
    assert all(el.review_status == "unreviewed" for el in links)
    assert all(el.status is l9.Status.CANDIDATE for el in links)


def test_develop_does_not_relink_the_same_pair():
    cs = _cs_with_corroborating_claims()
    ext = {}
    develop.develop(cs, ext, _Proto())
    before = cs.evidence_links()
    develop.develop(cs, ext, _Proto())          # same state -> nothing new to link
    assert cs.evidence_links() == before


def test_develop_engages_open_conflicts_into_review():
    cs = CoreState(l9.Layer9())
    a = cs.learn("the cause is A", "topic")
    b = cs.learn("the cause is not A", "topic")
    cs.open_conflict((a, b), severity="hard")
    out = develop.develop(cs, {}, _Proto())
    assert out["conflicts_reviewed"] == 1
    x = cs.core.all(l9.ObjectType.CONFLICT)[0]
    assert x.conflict_status.value == "under_review"   # engaged, not force-resolved


def test_develop_never_confirms_a_claim():
    cs = _cs_with_corroborating_claims()
    develop.develop(cs, {}, _Proto())
    assert not [c for c in cs.core.all(l9.ObjectType.CLAIM)
                if c.status is l9.Status.CONFIRMED]     # honest: no fake authority


def test_cycle_reports_development(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.delenv("JONI_ONLINE", raising=False)
    from joni.autonomy.run import one_cycle
    summary = one_cycle()
    assert "developed" in summary
    assert "evidence links" in (tmp_path / "docs" / "index.html").read_text()
