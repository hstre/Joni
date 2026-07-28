"""Joni's source fetchers - Zenodo and OpenAlex parse their APIs into Items (no real network)."""

import json

import pytest

from joni.autonomy import sources


def _canned(payload):
    def _get(url, headers=None):
        return json.dumps(payload).encode()
    return _get


def test_online_fetchers_include_zenodo_and_openalex():
    names = {f.name for f in sources.get_fetchers(online=True)}
    assert {"arxiv", "zenodo", "openalex", "openclaw"} <= names
    # offline stays deterministic - a single mock source
    assert [f.name for f in sources.get_fetchers(online=False)] == ["mock"]


def test_zenodo_fetcher_parses_records(monkeypatch):
    payload = {"hits": {"hits": [
        {"id": 12345, "metadata": {"title": "Evaluation methods for agents",
                                   "description": "<p>A study of <b>evaluation</b>.</p>"},
         "links": {"self_html": "https://zenodo.org/records/12345"}}]}}
    monkeypatch.setattr(sources, "_get", _canned(payload))
    items = sources.ZenodoFetcher().fetch(["evaluation"], limit=4)
    assert len(items) == 1
    it = items[0]
    assert it.source == "zenodo" and it.title == "Evaluation methods for agents"
    assert it.url == "https://zenodo.org/records/12345"
    assert "<b>" not in it.summary and "evaluation" in it.summary.lower()


def test_openalex_fetcher_rebuilds_abstract_and_parses(monkeypatch):
    payload = {"results": [
        {"id": "https://openalex.org/W42", "title": "Benchmarks for evaluation",
         "primary_location": {"landing_page_url": "https://papers.ssrn.com/abstract=42"},
         "cited_by_count": 7,
         "abstract_inverted_index": {"Evaluation": [0], "is": [1], "hard": [2]}}]}
    monkeypatch.setattr(sources, "_get", _canned(payload))
    items = sources.OpenAlexFetcher().fetch(["evaluation"], limit=4)
    assert len(items) == 1
    it = items[0]
    assert it.source == "openalex" and it.id == "W42"
    assert it.url == "https://papers.ssrn.com/abstract=42"      # SSRN reachable via OpenAlex
    assert it.summary == "Evaluation is hard"
    assert it.score == 7.0


def test_openalex_captures_the_oa_pdf_url_for_full_text_reading(monkeypatch):
    # an OPEN paper: OpenAlex exposes a real PDF url -> the Item carries it so the reader can pull
    # the FULL text (the method), not just the abstract. Prefers the pdf over the landing page.
    payload = {"results": [
        {"id": "https://openalex.org/W7", "title": "An open method",
         "primary_location": {"landing_page_url": "https://papers.ssrn.com/abstract=7",
                              "pdf_url": "https://repo.example.org/7.pdf"},
         "open_access": {"is_oa": True, "oa_url": "https://repo.example.org/7"},
         "abstract_inverted_index": {"Open": [0]}}]}
    monkeypatch.setattr(sources, "_get", _canned(payload))
    it = sources.OpenAlexFetcher().fetch(["method"], limit=4)[0]
    assert it.pdf_url == "https://repo.example.org/7.pdf"        # real PDF, not the SSRN landing


def test_openalex_pdf_url_is_empty_for_a_gated_paper():
    assert sources._openalex_pdf_url({"open_access": {"is_oa": False, "oa_url": "x"}}) == ""
    assert sources._openalex_pdf_url({}) == ""
    assert sources._openalex_pdf_url(
        {"best_oa_location": {"pdf_url": "https://x/y.pdf"}}) == "https://x/y.pdf"


def test_online_fetchers_include_wikipedia():
    # Auftrag #128: the encyclopedic source for topics the paper feeds miss is wired in online.
    assert "wikipedia" in {f.name for f in sources.get_fetchers(online=True)}


def test_wikipedia_fetcher_returns_topic_extracts(monkeypatch):
    payload = {"query": {"pages": {
        "12345": {"pageid": 12345, "title": "Memory",
                  "extract": "Memory is the faculty of the mind by which data is encoded, stored "
                             "and retrieved when needed."}}}}
    monkeypatch.setattr(sources, "_get", _canned(payload))
    items = sources.WikipediaFetcher().fetch(["memory"], limit=4)
    assert len(items) == 1
    it = items[0]
    assert it.source == "wikipedia" and it.title == "Memory"
    assert it.url == "https://en.wikipedia.org/?curid=12345"
    assert "encoded" in it.summary               # a real item that can support/contradict an idea


def test_wikipedia_fetcher_degrades_quietly(monkeypatch):
    def _boom(url, headers=None):
        raise OSError("network down")
    monkeypatch.setattr(sources, "_get", _boom)
    assert sources.WikipediaFetcher().fetch(["memory"], limit=4) == []


def test_openclaw_fetcher_surfaces_community_modules(monkeypatch):
    payload = {"items": [
        {"full_name": "openclaw/clawhub", "name": "clawhub",
         "html_url": "https://github.com/openclaw/clawhub",
         "description": "Skill + Plugin Registry for OpenClaw", "stargazers_count": 8956}]}
    monkeypatch.setattr(sources, "_get", _canned(payload))
    items = sources.OpenClawFetcher().fetch(["memory"], limit=4)
    assert any(it.source == "openclaw" and it.id == "openclaw/clawhub" for it in items)
    assert items[0].score == 8956.0


def test_openclaw_topics_are_env_tunable(monkeypatch):
    monkeypatch.setenv("JONI_OPENCLAW_TOPICS", "openclaw-skills, custom-topic")
    assert sources.OpenClawFetcher()._topics() == ["openclaw-skills", "custom-topic"]


def test_a_failing_source_degrades_quietly(monkeypatch):
    def _boom(url, headers=None):
        raise OSError("network down")
    monkeypatch.setattr(sources, "_get", _boom)
    assert sources.ZenodoFetcher().fetch(["x"], limit=4) == []


def test_a_totally_dead_source_is_loud_not_empty(monkeypatch):
    """Ein Ausfall darf sich nicht als leerer Erfolg tarnen.

    run.py haelt die Absicht woertlich fest ("a source outage must show as DEGRADED, not
    '0 items'"), aber der Fetcher fing seine Ausnahmen je Suchbegriff selbst ab und gab [] zurueck -
    der DEGRADED-Pfad war damit toter Code. Gefunden, als OpenAlex sein Tagesbudget erschoepft
    hatte (HTTP 429); Joni laeuft stuendlich, OpenAlex rechnet taeglich ab, das trifft regelmaessig.

    Die Unterscheidung, die beide Absichten vereint: **Teilausfall still, Totalausfall laut.**"""
    def _boom(url, headers=None):
        raise OSError("network down")
    monkeypatch.setattr(sources, "_get", _boom)
    with pytest.raises(sources.SourceDegraded):
        sources.OpenAlexFetcher().fetch(["x"], limit=4)


def test_a_partially_failing_source_still_returns_what_it_got(monkeypatch):
    """Nur ein Begriff faellt aus: das ist kein Ausfall der Quelle, also bleibt es still."""
    calls = {"n": 0}
    payload = {"results": [{"id": "https://openalex.org/W1", "title": "Ein Treffer",
                            "abstract_inverted_index": {"text": [0]}}]}

    def _flaky(url, headers=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("erster Begriff scheitert")
        return json.dumps(payload).encode()

    monkeypatch.setattr(sources, "_get", _flaky)
    items = sources.OpenAlexFetcher().fetch(["a", "b"], limit=4)
    assert len(items) == 1 and items[0].source == "openalex"
