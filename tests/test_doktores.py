"""Doktores' self-improvement review: read a paper / OpenClaw extension and, when it could
concretely improve a NON-CORE module, file an Auftrag an Claude. Never the core, never self-applied.
Uses Joni's own captured model (stubbed here); cadence- and dedup-bounded."""

import desi_layer9 as l9
from joni.autonomy import doktores, model_call
from joni.autonomy.core_state import CoreState, seed_core
from joni.autonomy.sources import Item


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _paper(key="arxiv:p1", source="arxiv"):
    return Item(source, key.split(":")[-1], "A better source-coverage method for research agents",
                f"https://example.org/{key}", "We present a retrieval method that broadens topic "
                "coverage for autonomous reading agents.")


def _online(monkeypatch, tmp_path, reply, scout=()):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: reply)
    # deterministic: no real network scouting unless a test asks for it
    monkeypatch.setattr(doktores, "_scout", lambda queries: list(scout))


_APPLICABLE = (
    '{"applicable": true, "component_key": "reader-sources", '
    '"title": "Erweitere meine Leseschicht um die Coverage-Methode", '
    '"motivation": "Das Paper beschreibt eine Retrieval-Methode fuer mehr Themenabdeckung.", '
    '"desired": "Setze die Methode in sources.py/reader.py als zusätzliche Query-Strategie um.", '
    '"acceptance": "Ein Lauf bringt zu zuvor barren Topics mindestens ein nützliches Item."}'
)
_INAPPLICABLE = '{"applicable": false}'
_CORE_TARGET = '{"applicable": true, "component_key": "operators", "title": "x", "desired": "y"}'


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    assert doktores.review(CoreState(seed_core()), {}, _Proto(), 3, items=[_paper()]) == []


def test_applicable_source_becomes_a_non_core_auftrag(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, _APPLICABLE)
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()])
    assert len(new) == 1
    order = new[0]
    assert order["component_key"] == "reader-sources"
    assert order["touches_core"] is False              # invariant: never the protected core
    assert order["addressed_to"] == "Claude" and order["found_by"] == "doktores"
    assert order in ext["commissions"]                 # filed through the commission channel
    assert ext["doktores_review"][-1]["applicable"] is True


def test_inapplicable_source_files_nothing_but_is_logged(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, _INAPPLICABLE)
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()])
    assert new == []
    assert ext["doktores_review"][-1]["applicable"] is False


def test_a_core_target_is_refused(monkeypatch, tmp_path):
    # The model naming a protected-core module (not on the _EXTENSIBLE allowlist) is dropped.
    _online(monkeypatch, tmp_path, _CORE_TARGET)
    ext: dict = {}
    assert doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()]) == []


def test_only_papers_and_extensions_are_reviewed(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, _APPLICABLE)
    forum = Item("hackernews", "h1", "a thread", "https://news.ycombinator.com/item?id=h1", "chat")
    assert doktores.review(CoreState(seed_core()), {}, _Proto(), 3, items=[forum]) == []


def test_scouted_module_relevant_paper_is_reviewed(monkeypatch, tmp_path):
    # Doktores scouts targeted literature even when the topic-fetch passed nothing reviewable.
    scouted = _paper("arxiv:scout1")
    _online(monkeypatch, tmp_path, _APPLICABLE, scout=[scouted])
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[])
    assert len(new) == 1 and new[0]["component_key"] == "reader-sources"
    assert ext["doktores_review"][-1]["title"].startswith("A better source-coverage")


def _with_hypothesis(cs, text="local routing bounds memory consolidation", topic="memory"):
    parent = cs.learn("routing is local at serving time", topic, source_id="arxiv:seed")
    cs.hypothesize(text, topic, parents=[parent])
    return cs


def test_research_brings_evidence_to_a_hypothesis_as_a_source(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, "Latency budgets do bound consolidation in long-run agents.",
            scout=[_paper("arxiv:h1")])
    cs = _with_hypothesis(CoreState(seed_core()))
    ext: dict = {}
    out = doktores.research_hypotheses(cs, ext, _Proto(), 3, budget=None)
    assert out["researched"] == 1 and out["evidence"] == 1
    assert out["hypothesis"] in ext["doktores_hyp_researched"]      # marked, won't re-research
    # the finding entered as a real claim (a SOURCE, never confirmed)
    got = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if "bound consolidation" in getattr(c, "text", "")]
    assert got and got[0].status is not l9.Status.CONFIRMED


def test_research_irrelevant_paper_adds_no_source(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, "NONE", scout=[_paper("arxiv:h2")])
    cs = _with_hypothesis(CoreState(seed_core()))
    ext: dict = {}
    out = doktores.research_hypotheses(cs, ext, _Proto(), 3, budget=None)
    assert out["researched"] == 0 and out["evidence"] == 0
    # still marked researched (it was examined), so Doktores moves on next time
    assert ext["doktores_hyp_researched"]


def test_research_no_op_without_hypotheses(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, "x", scout=[_paper("arxiv:h3")])
    assert doktores.research_hypotheses(CoreState(seed_core()), {}, _Proto(), 3)["researched"] == 0


def test_cadence_and_dedup(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, _APPLICABLE)
    ext: dict = {}
    assert len(doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()])) == 1
    # same cycle window -> cadence no-op (default JONI_DOKTORES_EVERY=4)
    p2 = [_paper("arxiv:p2")]
    assert doktores.review(CoreState(seed_core()), ext, _Proto(), 4, items=p2) == []
    # past the cadence, but the SAME source was already reviewed -> not re-examined
    out = doktores.review(CoreState(seed_core()), ext, _Proto(), 20, items=[_paper()])
    assert out == []
