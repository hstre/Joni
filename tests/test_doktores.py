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


def _online(monkeypatch, tmp_path, reply, scout=(), agents=(), full_text=None, ground=None):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))

    # the review is two calls: abstract triage, then (if it passed) full-text grounding. Route by
    # the grounding system prompt so a test can give a different reply for each stage.
    def complete(profile, system, user):
        return ground if (ground is not None and "FULL TEXT" in system) else reply
    monkeypatch.setattr(model_call, "_complete", complete)
    # deterministic: no real network scouting (papers OR agent repos) or PDF fetch in tests
    monkeypatch.setattr(doktores, "_scout", lambda queries: list(scout))
    monkeypatch.setattr(doktores, "_agent_scout", lambda extensions: list(agents))
    monkeypatch.setattr(doktores, "_full_text", lambda item: full_text)


_APPLICABLE = (
    '{"applicable": true, "component_key": "reader-sources", '
    '"title": "Erweitere meine Leseschicht um die Coverage-Methode", '
    '"motivation": "Das Paper beschreibt eine Retrieval-Methode fuer mehr Themenabdeckung.", '
    '"desired": "Setze die Methode in sources.py/reader.py als zusätzliche Query-Strategie um.", '
    '"acceptance": "Ein Lauf bringt zu zuvor barren Topics mindestens ein nützliches Item."}'
)
_INAPPLICABLE = '{"applicable": false}'
_CORE_TARGET = '{"applicable": true, "component_key": "operators", "title": "x", "desired": "y"}'
# what the model returns AFTER reading the full text - grounded in the real method, not the abstract
_GROUNDED = (
    '{"applicable": true, "component_key": "reader-sources", '
    '"title": "Erweitere die Leseschicht um die konkrete Retrieval-Schleife", '
    '"motivation": "Der Volltext zeigt: die Methode ist eine iterative Query-Verfeinerung mit '
    'Rueckkopplung, nicht bloss ein Ranking.", '
    '"desired": "Implementiere in reader.py die im Paper beschriebene Feedback-Schleife (Retrieve '
    '-> Rerank -> Query-Refine), Abschnitt 4.", '
    '"acceptance": "Recall@5 steigt um >=3 Punkte gegenueber der flachen Suche."}'
)


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


def test_ssrn_is_a_reviewable_source(monkeypatch, tmp_path):
    # SSRN papers (scouted via OpenAlex's SSRN slice) are reviewed like any other paper source.
    _online(monkeypatch, tmp_path, _APPLICABLE, scout=[_paper("ssrn:w1", source="ssrn")])
    new = doktores.review(CoreState(seed_core()), {}, _Proto(), 3, items=[])
    assert len(new) == 1 and new[0]["evidence"]["source"] == "ssrn"


def test_zenodo_passive_items_are_throttled(monkeypatch, tmp_path):
    # The Zenodo firehose is capped to one passive item; a scouted paper is still reviewed first.
    _online(monkeypatch, tmp_path, _INAPPLICABLE, scout=[_paper("arxiv:s1")])
    zen = [_paper(f"zenodo:z{i}", source="zenodo") for i in range(5)]
    ext: dict = {}
    doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=zen)
    reviewed = ext["doktores_review"]
    assert sum(1 for e in reviewed if e["source"] == "zenodo") <= 1
    assert any(e["source"] == "arxiv" for e in reviewed)    # the scouted paper got reviewed


def _fake_github(url, headers=None):
    import json
    return json.dumps({"items": [
        {"full_name": "acme/memory-agent", "name": "memory-agent",
         "html_url": "https://github.com/acme/memory-agent",
         "description": "Long-term memory for LLM agents via hybrid vector+graph retrieval.",
         "stargazers_count": 42},
        {"full_name": "acme/tool-agent", "name": "tool-agent",
         "html_url": "https://github.com/acme/tool-agent",
         "description": "A tool-use planning loop for autonomous agents.", "stargazers_count": 7},
    ]})


def test_agent_scout_reads_github_agent_repos_and_rotates_the_queries(monkeypatch):
    # watching how OTHER agents are built: GitHub agent repos enter as reviewable 'github' items,
    # and the query window advances each firing so fresh, active projects keep surfacing.
    from joni.autonomy import sources
    monkeypatch.delenv("JONI_DOKTORES_AGENTS", raising=False)
    monkeypatch.setattr(sources, "_get", _fake_github)
    ext: dict = {}
    items = doktores._agent_scout(ext)
    assert items and all(it.source == "github" for it in items)
    assert any(it.id == "acme/memory-agent" for it in items)   # repo full_name is the item id
    assert ext["agent_scout_idx"] == 2                          # the query window advanced
    doktores._agent_scout(ext)
    assert ext["agent_scout_idx"] == 4                          # ...and again -> fresh queries


def test_agent_scout_respects_the_off_flag(monkeypatch):
    monkeypatch.setenv("JONI_DOKTORES_AGENTS", "0")
    assert doktores._agent_scout({}) == []


def test_a_peer_agent_repo_becomes_a_non_core_auftrag(monkeypatch, tmp_path):
    # an applicable peer-agent codebase becomes an Auftrag through the SAME gate/commission channel
    # as a paper - a source to assess and adapt, never the protected core, never self-applied.
    repo = Item("github", "acme/memory-agent", "memory-agent",
                "https://github.com/acme/memory-agent",
                "Hybrid vector+graph long-term memory for LLM agents.", 42.0)
    _online(monkeypatch, tmp_path, _APPLICABLE, agents=[repo])
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[])
    assert len(new) == 1
    assert new[0]["found_by"] == "doktores" and new[0]["touches_core"] is False
    assert ext["doktores_review"][-1]["source"] == "github"    # a peer agent's code was reviewed


def test_full_text_grounds_the_order_in_the_real_method_not_the_abstract(monkeypatch, tmp_path):
    # the abstract passes triage, then Doktores READS THE PAPER and re-grounds the order in the
    # actual method - the important part is in the body, not the summary.
    _online(monkeypatch, tmp_path, _APPLICABLE,
            full_text="Section 4: the method is an iterative retrieve-rerank-refine feedback loop.",
            ground=_GROUNDED)
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()])
    assert len(new) == 1
    order = new[0]
    assert "Feedback-Schleife" in order["desired_capability"]    # the grounded method, not abstract
    assert order["evidence"]["grounded_in"] == "full-text"


def test_full_text_can_refute_an_oversold_abstract(monkeypatch, tmp_path):
    # the abstract sounded applicable, but the full text shows it does not really map to a module:
    # the order is dropped (a quality gain the abstract-only review could not make).
    _online(monkeypatch, tmp_path, _APPLICABLE,
            full_text="On reading, this is a survey with no implementable method.",
            ground=_INAPPLICABLE)
    ext: dict = {}
    assert doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()]) == []


def test_no_full_text_falls_back_to_the_abstract_verdict(monkeypatch, tmp_path):
    # a source with no fetchable PDF (GitHub repo, paywalled): the abstract verdict still stands,
    # so peer-practice and closed papers are not lost - just marked as abstract-grounded.
    _online(monkeypatch, tmp_path, _APPLICABLE, full_text=None)     # no body available
    ext: dict = {}
    new = doktores.review(CoreState(seed_core()), ext, _Proto(), 3, items=[_paper()])
    assert len(new) == 1 and new[0]["evidence"]["grounded_in"] == "abstract"


def test_full_text_reads_an_ssrn_open_access_pdf_not_just_the_abstract(monkeypatch):
    # a SSRN/OpenAlex paper that HAS an open PDF: _full_text pulls the PDF BODY via the OA pdf_url,
    # not just the abstract - so SSRN papers (incl. the operator's own, when open) are read in full.
    from joni.autonomy import pdf
    monkeypatch.setattr(pdf, "available", lambda: True)
    seen = {}

    def fake_read_url(url, **kw):
        seen["url"] = url
        return type("Doc", (), {"text": "Section 3: the actual method, equations and results."})()
    monkeypatch.setattr(pdf, "read_url", fake_read_url)
    item = Item("ssrn", "w1", "My SSRN paper", "https://papers.ssrn.com/abstract=1",
                "abstract only", 0.0, "https://repo.example.org/open/w1.pdf")
    body = doktores._full_text(item)
    assert body and "actual method" in body
    assert seen["url"] == "https://repo.example.org/open/w1.pdf"    # the OA PDF, not the landing


def test_full_text_of_a_gated_paper_with_no_open_pdf_is_none(monkeypatch):
    # a truly gated SSRN paper (no open pdf, only a landing page): honestly None -> abstract stands,
    # nothing lost, but the review knows it only saw the abstract.
    from joni.autonomy import pdf
    monkeypatch.setattr(pdf, "available", lambda: True)
    item = Item("ssrn", "w2", "Gated paper", "https://papers.ssrn.com/abstract=2", "abstract",
                0.0, "")
    assert doktores._full_text(item) is None


def _with_hypothesis(cs, text="local routing bounds memory consolidation", topic="memory"):
    parent = cs.learn("routing is local at serving time", topic, source_id="arxiv:seed")
    cs.hypothesize(text, topic, parents=[parent])
    return cs


def test_assess_judges_internal_coherence_not_paper_support(monkeypatch, tmp_path):
    # A novel idea need not be backed by literature - the only bar is internal logical coherence.
    _online(monkeypatch, tmp_path, '{"coherent": true, "reason": "self-consistent and testable"}')
    cs = _with_hypothesis(CoreState(seed_core()))
    n_claims = len(list(cs.core.all(l9.ObjectType.CLAIM)))
    ext: dict = {}
    out = doktores.assess_hypotheses(cs, ext, _Proto(), 3, budget=None)
    assert out["assessed"] == 1 and out["coherent"] is True
    assert out["hypothesis"] in ext["doktores_hyp_assessed"]        # marked, won't re-assess
    assert ext["doktores_hyp_log"][-1]["coherent"] is True
    # CRITICAL: it does NOT inject any paper-evidence claim - the idea stands on its own logic
    assert len(list(cs.core.all(l9.ObjectType.CLAIM))) == n_claims


def test_assess_can_flag_an_incoherent_idea(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, '{"coherent": false, "reason": "contradicts itself"}')
    cs = _with_hypothesis(CoreState(seed_core()))
    out = doktores.assess_hypotheses(cs, {}, _Proto(), 3, budget=None)
    assert out["assessed"] == 1 and out["coherent"] is False


def test_assess_no_op_without_hypotheses(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, '{"coherent": true}')
    assert doktores.assess_hypotheses(CoreState(seed_core()), {}, _Proto(), 3)["assessed"] == 0


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
