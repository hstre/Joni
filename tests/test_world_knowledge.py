"""Weltwissens-Adapter: die Regeln, die nicht kippen dürfen.

Alle Tests laufen OHNE Netz - die HTTP-Schicht wird ersetzt. Geprüft wird nicht, ob Wikidata
richtige Daten hat, sondern ob der Adapter mit dem, was zurückkommt, ehrlich umgeht.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge"))

wk = pytest.importorskip("world_knowledge")


@pytest.fixture
def cache(tmp_path):
    return wk.Cache(tmp_path / "c.sqlite")


def test_absence_is_never_a_refutation(monkeypatch, cache):
    """Die tragende Regel: kein Treffer heisst 'hier steht nichts', nie 'es ist falsch'."""
    monkeypatch.setattr(wk, "_get_json", lambda url: {"esearchresult": {"idlist": []}})
    r = wk.find_literature("etwas ohne Fundstelle", cache=cache)
    assert r.found is False
    assert r.absence_is_not_refutation is True
    assert "KEINE Widerlegung" in r.note
    # Es darf kein Feld geben, das eine Widerlegung BEHAUPTEN koennte. Das einzige Feld mit
    # "refut" im Namen ist die Sicherung selbst.
    d = r.to_dict()
    assert "refutes" not in d and "refuted" not in d
    assert [k for k in d if "refut" in k] == ["absence_is_not_refutation"]


def test_irrelevant_hits_are_dropped_not_served(monkeypatch, cache):
    """PubMed faellt auf einzelne haeufige Woerter zurueck und liefert Unverwandtes.

    Live gemessen: die Anfrage 'xyzzy nonexistent quux flurble' ergab drei Arbeiten zu
    Wissensgraphen und Aspirin-Reaktivitaet, weil 'nonexistent' in Abstracts vorkommt. Eine
    irrelevante Zitatstelle an eine Praemisse zu heften ist schlimmer als gar keine.
    """
    monkeypatch.setattr(wk, "_get_json", lambda url: (
        {"esearchresult": {"idlist": ["1"]}} if "esearch" in url else
        {"result": {"uids": ["1"], "1": {"title": "Biologic Therapy and Aspirin Reactivity"}}}))
    r = wk.find_literature("ferritin saturation threshold anaemia", cache=cache)
    assert r.found is False
    assert "ohne inhaltlichen Bezug" in r.note or "KEINE Widerlegung" in r.note


def test_a_genuinely_related_hit_survives(monkeypatch, cache):
    monkeypatch.setattr(wk, "_get_json", lambda url: (
        {"esearchresult": {"idlist": ["33735515"]}} if "esearch" in url else
        {"result": {"uids": ["33735515"], "33735515": {
            "title": "Threshold for defining fever varies with age",
            "fulljournalname": "Nursing open", "pubdate": "2021"}}}))
    r = wk.find_literature("fever varies with age", cache=cache)
    assert r.found is True and len(r.evidence) == 1
    assert r.evidence[0].external_id == "33735515"
    assert r.evidence[0].confidence_class == "literature_reference"


def test_ambiguity_is_reported_not_resolved(monkeypatch, cache):
    """'fever' liefert als ersten Treffer ein Mixtape. Der Adapter darf nicht selbst waehlen."""
    monkeypatch.setattr(wk, "_get_json", lambda url: {"search": [
        {"id": "Q64355201", "label": "Fever", "description": "2019 mixtape"},
        {"id": "Q38933", "label": "fever", "description": "common medical sign"}]})
    r = wk.resolve_entity("fever", cache=cache)
    assert r.found is True and len(r.ambiguous_candidates) == 2
    assert "mehrdeutig" in r.note
    assert {c["id"] for c in r.ambiguous_candidates} == {"Q64355201", "Q38933"}


def test_referenced_and_unreferenced_statements_are_distinguished(monkeypatch, cache):
    """Wikidata-Aussagen sind unterschiedlich gut belegt - das muss sichtbar bleiben."""
    monkeypatch.setattr(wk, "_get_json", lambda url: {
        "P19": [{"value": {"content": "Q3012"}, "references": [{"hash": "abc"}], "qualifiers": []}],
        "P20": [{"value": {"content": "Q60"}, "references": [], "qualifiers": []}]})
    r = wk.get_claims("Q937", cache=cache)
    by_prop = {e.property_id: e for e in r.evidence}
    assert by_prop["P19"].confidence_class == "structured_referenced"
    assert by_prop["P20"].confidence_class == "structured_unreferenced"


def test_premise_evidence_never_judges_validity(monkeypatch, cache):
    monkeypatch.setattr(wk, "_get_json", lambda url: (
        {"esearchresult": {"idlist": ["1"]}} if "esearch" in url else
        {"result": {"uids": ["1"], "1": {"title": "fever threshold varies with age"}}}))
    r = wk.premise_evidence("fever threshold varies", cache=cache)
    assert r.found is True
    assert "kein Urteil" in r.note


def test_an_unreachable_source_is_not_a_finding(monkeypatch, cache):
    def _boom(url):
        raise OSError("network down")
    monkeypatch.setattr(wk, "_get_json", _boom)
    r = wk.find_literature("irgendwas", cache=cache)
    assert r.found is False and "nicht erreichbar" in r.note
    assert r.absence_is_not_refutation is True
