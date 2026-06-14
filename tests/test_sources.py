"""Joni's source fetchers - Zenodo and OpenAlex parse their APIs into Items (no real network)."""

import json

from joni.autonomy import sources


def _canned(payload):
    def _get(url, headers=None):
        return json.dumps(payload).encode()
    return _get


def test_online_fetchers_include_zenodo_and_openalex():
    names = {f.name for f in sources.get_fetchers(online=True)}
    assert {"arxiv", "zenodo", "openalex"} <= names
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


def test_a_failing_source_degrades_quietly(monkeypatch):
    def _boom(url, headers=None):
        raise OSError("network down")
    monkeypatch.setattr(sources, "_get", _boom)
    assert sources.ZenodoFetcher().fetch(["x"], limit=4) == []
    assert sources.OpenAlexFetcher().fetch(["x"], limit=4) == []
