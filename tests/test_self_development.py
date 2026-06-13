"""Joni keeps restructuring his own state - even with no new input - honestly."""

import desi_layer9 as l9
from joni.autonomy import develop
from joni.autonomy.core_state import CoreState
from semantic_stub import StubSemanticLayer


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_corroborating_claims():
    # enough shared vocabulary to fire the cheap lexical trigger, but not near-identical
    cs = CoreState(l9.Layer9())
    cs.learn("cheap local routing keeps latency low", "routing")
    cs.learn("cheap local routing improves decision quality", "routing")
    return cs


def test_develop_links_related_claims_only_via_the_semantic_layer():
    cs = _cs_with_corroborating_claims()
    out = develop.develop(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["links"] >= 1
    links = cs.core.all(l9.ObjectType.EVIDENCE_LINK)
    assert links
    # the link is unreviewed and candidate - it never confirms anything
    assert all(el.review_status == "unreviewed" for el in links)
    assert all(el.status is l9.Status.CANDIDATE for el in links)


def test_without_a_semantic_layer_no_link_is_asserted():
    # Governance: lexical overlap alone must never assign a relation.
    cs = _cs_with_corroborating_claims()
    out = develop.develop(cs, {}, _Proto())                # default = NullSemanticLayer
    assert out["links"] == 0
    assert cs.core.all(l9.ObjectType.EVIDENCE_LINK) == []
    # but the analysis IS recorded as an append-only annotation (insufficient evidence)
    clusters = cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)
    assert clusters and clusters[0].decision is l9.SemanticDecision.INSUFFICIENT


def test_develop_does_not_relink_the_same_pair():
    cs = _cs_with_corroborating_claims()
    ext = {}
    develop.develop(cs, ext, _Proto(), layer=StubSemanticLayer())
    before = cs.evidence_links()
    develop.develop(cs, ext, _Proto(), layer=StubSemanticLayer())   # same pair -> nothing new
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


def test_backfill_gives_legacy_links_a_semantic_record():
    # a pair "linked" under the old lexical logic, with no semantic annotation yet
    cs = _cs_with_corroborating_claims()
    a, b = cs.active_claims()[0].id, cs.active_claims()[1].id
    ext = {"linked": [f"{a}|{b}"], "semantic_backfilled": []}
    out = develop.develop(cs, ext, _Proto(), layer=StubSemanticLayer())
    assert out["backfilled"] >= 1
    clusters = cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)
    assert clusters and set(clusters[0].members) == {a, b}   # the backlog pair is now recorded
    # and it is not re-analysed next cycle
    before = len(clusters)
    develop.develop(cs, ext, _Proto(), layer=StubSemanticLayer())
    assert len(cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)) == before


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
