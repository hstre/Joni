"""Die epistemische Karte - wer darf was, und stimmt es noch.

Wie bei der Architekturkarte ist die tragende Eigenschaft nicht, dass die Seite huebsch ist,
sondern dass sie nichts behauptet, was sie nicht ausgerechnet hat. Die Tests hier pruefen genau
das: dass die Erlaubnistabelle aus der echten Regelfunktion kommt, dass ein nicht bestimmbarer
Operator nicht geraten wird, und dass die Aussage "ein einziges Schreibtor" aus dem Quelltext
faellt statt aus einem Docstring.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("desi_layer9")
from joni import epistemic_map as em  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
DOCS = REPO / "docs"


@pytest.fixture(scope="module")
def data() -> dict:
    return em.analyse(SRC, REPO)


# ── Frische ─────────────────────────────────────────────────────────────────────────────────────

def test_die_seite_passt_zum_quelltext(data):
    """Wenn das hier rot ist: ``python -m joni.epistemic_map``."""
    gebaut = DOCS / "flow.json"
    assert gebaut.exists(), "Die Karte wurde nie gebaut."
    assert gebaut.read_text(encoding="utf-8") == json.dumps(
        data, ensure_ascii=False, indent=1, sort_keys=True), (
        "Die epistemische Karte ist nicht mehr auf dem Stand des Quelltextes. "
        "Neu bauen: python -m joni.epistemic_map")


# ── Die Erlaubnistabelle wird gerechnet, nicht abgeschrieben ────────────────────────────────────

def test_tabelle_stimmt_mit_der_echten_regelfunktion_ueberein(data):
    """Jede Zelle wird gegen ``policy.may_request`` nachgeprueft - keine Stichprobe."""
    from desi_layer9 import policy
    from desi_layer9.enums import Operator, OriginType

    allowed = data["permissions"]["allowed"]
    for o in OriginType:
        for op in Operator:
            assert (op.value in allowed[o.value]) == policy.may_request(o, op), \
                f"{o.value} / {op.value}"


def test_eine_regelaenderung_schlaegt_auf_die_tabelle_durch(monkeypatch):
    """Der eigentliche Beweis, dass nichts abgeschrieben ist: Regel aendern, Tabelle aendert sich.

    Waere die Tabelle von Hand gepflegt, bliebe sie hier unveraendert - und genau das waere der
    Fehler, den diese Seite verhindern soll.
    """
    from desi_layer9 import policy
    vorher = em.permission_matrix()["allowed"]["human"]
    monkeypatch.setattr(policy, "may_request", lambda origin, op: False)
    nachher = em.permission_matrix()["allowed"]["human"]
    assert vorher and nachher == []


def test_erzeugende_herkuenfte_duerfen_nichts_autoritatives(data):
    """Die tragende Zusage der Regel: ein Modell darf vorschlagen, nicht bestaetigen."""
    auth = set(data["permissions"]["authoritative"])
    for origin in ("local_model", "external_model", "user", "source"):
        assert not (set(data["permissions"]["allowed"][origin]) & auth), origin


def test_der_befund_ueber_ungedecktes_vertrauen_ist_gerechnet(data):
    """Herkuenfte, die weder erzeugend noch ausdruecklich vertraut sind, aber autoritativ duerfen.

    Der Befund kam nicht vom Lesen der Regel - dort steht nur, wer gesperrt ist. Er kam vom
    Ausrechnen. Wenn jemand die Regel spaeter schliesst, muss diese Liste leer werden, und der
    Test haelt fest, dass sie das dann auch wirklich tut.
    """
    odd = data["permissions"]["trusted_by_default"]
    for o in odd:
        assert o not in ("human", "deterministic_operator")
        assert data["permissions"]["authoritative_by_origin"][o]


# ── Nichts wird geraten ─────────────────────────────────────────────────────────────────────────

def test_ein_variabler_operator_wird_nicht_geraten(tmp_path):
    """``entry.operator`` sieht aus wie ``Operator.CLAIM_CREATE``, ist aber eine Variable."""
    p = tmp_path / "joni"
    p.mkdir()
    (p / "__init__.py").write_text("", encoding="utf-8")
    (p / "a.py").write_text(
        "def f(entry):\n"
        "    make_proposal(PT.X, entry.operator, payload={}, proposer='x')\n"
        "    make_proposal(PT.X, Operator.CLAIM_CREATE, payload={}, proposer='y')\n",
        encoding="utf-8")
    sites = em.write_sites(tmp_path)
    assert [s["operator"] for s in sites] == [None, "claim_create"]
    assert [s["proposer"] for s in sites] == ["x", "y"]


def test_die_umschliessende_funktion_wird_mitgefuehrt(tmp_path):
    """Ohne sie stuende auf der Seite nur eine Datei - die Frage ist aber, *wer* schreibt."""
    p = tmp_path / "joni"
    p.mkdir()
    (p / "__init__.py").write_text("", encoding="utf-8")
    (p / "a.py").write_text(
        "def lernen():\n    make_proposal(PT.X, Operator.CLAIM_CREATE, payload={})\n",
        encoding="utf-8")
    assert em.write_sites(tmp_path)[0]["function"] == "lernen"


def test_nicht_bestimmbare_stellen_werden_ausgewiesen_nicht_verschwiegen(data):
    """Sie stehen als eigene Gruppe da - eine Karte, die hier etwas einsetzt, waere falscher."""
    assert data["totals"]["non_literal"] > 0
    assert len(data["by_operator"]["<nicht literal>"]) == data["totals"]["non_literal"]


# ── Das Schreibtor ──────────────────────────────────────────────────────────────────────────────

def test_es_gibt_genau_ein_oeffentliches_schreibtor(data):
    """Die tragende Eigenschaft des Kerns - und sie wird gemessen, nicht geglaubt."""
    assert data["gate"]["public_writers"] == ["submit"]
    assert data["gate"]["single_gate"] is True


def test_ein_zweiter_schreiber_wuerde_auffallen(tmp_path):
    """Der Test, der den vorigen erst aussagekraeftig macht: faende er nie etwas,
    waere er wertlos."""
    core = tmp_path / "desi_layer9"
    core.mkdir()
    (core / "core.py").write_text(
        "class C:\n"
        "    def submit(self, p):\n        self._objects[p.id] = p\n"
        "    def hintertuer(self, p):\n        self._objects[p.id] = p\n",
        encoding="utf-8")
    g = em.core_writers(tmp_path)
    assert g["public_writers"] == ["hintertuer", "submit"]
    assert g["single_gate"] is False


# ── Die Grenze zwischen Modell und Regel ────────────────────────────────────────────────────────

def test_der_eingebettete_kern_kann_kein_modell_erreichen(data):
    """Die tragende Zusage der ganzen Anlage - und ab jetzt eine gepruefte, keine behauptete.

    Die Stelle, die ueber Geltung entscheidet, darf nicht fragen koennen, was ein Modell davon
    haelt. Wenn dieser Test je rot wird, ist nicht der Test falsch: dann ist ein Modell in den
    Kern verdrahtet worden, und das ist eine Entscheidung, die niemand nebenbei treffen darf.
    """
    b = data["boundaries"]
    assert b["kernel_model_free"] is True
    assert b["kernel_modules"], "Ohne Kernmodule prueft der Test nichts."
    assert not (set(b["kernel_modules"]) & set(b["can_reach_model"]))


def test_die_tueren_werden_gelesen_nicht_gepflegt(tmp_path):
    """Meine von Hand geratene Tuerliste enthielt ein Modul, das gar keine Tuer ist."""
    arch = {"modules": [
        {"name": "a", "external": ["openai"], "dependents": ["b"]},
        {"name": "b", "external": ["json"], "dependents": []},
        {"name": "c", "external": ["json"], "dependents": []},
        {"name": "d", "external": ["urllib"], "dependents": []},
    ]}
    b = em.boundaries(arch)
    assert b["model_doors"] == ["a"]
    assert b["network_doors"] == ["d"]
    assert b["can_reach_model"] == ["a", "b"]      # b importiert a
    assert b["deterministic"] == ["c", "d"]
    assert b["offline"] == ["c"]                   # d spricht nach aussen, nur ohne Modell


def test_die_grenze_wird_lieber_zu_weit_als_zu_eng_gezogen(tmp_path):
    """Erreichbarkeit, nicht Aufruf: wer eine Tuer importiert, zaehlt - auch ungenutzt.

    Andersherum waere der Fehler toedlich: ein Modul faelschlich als deterministisch zu fuehren
    heisst, eine Zusage zu geben, die nicht haelt.
    """
    arch = {"modules": [
        {"name": "tuer", "external": ["openai"], "dependents": ["nutzt_nie"]},
        {"name": "nutzt_nie", "external": [], "dependents": []},
    ]}
    assert em.boundaries(arch)["deterministic"] == []


# ── Der beobachtete Zyklus ──────────────────────────────────────────────────────────────────────

def test_der_zyklus_kommt_aus_echten_ereignissen(data):
    c = data["cycle"]
    assert c["cycles"] > 100 and c["total"] > 1000
    assert all(0.0 <= e["position"] <= 1.0 for e in c["events"])
    assert all(e["in_cycles"] <= c["cycles"] for e in c["events"])


def test_kaputte_protokollzeilen_kippen_die_karte_nicht(tmp_path):
    """Ein abgeschnittener Schreibvorgang darf die Seite nicht unbaubar machen."""
    p = tmp_path / "protocol.jsonl"
    p.write_text('{"cycle":1,"kind":"a","model":"deterministic","cost_eur":0}\n'
                 'kaputt{\n'
                 '{"cycle":1,"kind":"b","model":"m","cost_eur":0.5}\n', encoding="utf-8")
    c = em.observed_cycle(p)
    assert c["total"] == 2
    assert {e["kind"] for e in c["events"]} == {"a", "b"}


def test_fehlendes_protokoll_ist_kein_absturz(tmp_path):
    assert em.observed_cycle(tmp_path / "gibtsnicht.jsonl")["cycles"] == 0


def test_die_reihenfolge_ist_die_gemessene(tmp_path):
    """Erst-Position im Zyklus, gemittelt - nicht die Reihenfolge, in der ich sie erwarte."""
    p = tmp_path / "protocol.jsonl"
    p.write_text("".join(
        json.dumps({"cycle": c, "kind": k, "model": "deterministic", "cost_eur": 0}) + "\n"
        for c in (1, 2) for k in ("erst", "mitte", "spaet")), encoding="utf-8")
    assert [e["kind"] for e in em.observed_cycle(p)["events"]] == ["erst", "mitte", "spaet"]


# ── Die Seite ───────────────────────────────────────────────────────────────────────────────────

def test_seite_ist_in_sich_geschlossen():
    h = (DOCS / "flow.html").read_text(encoding="utf-8")
    assert "<script src=" not in h and "cdn." not in h


def test_die_seite_nennt_ihre_grenze():
    """Sie zeigt keinen Kontrollfluss - und das muss draufstehen, nicht nur im Quelltext."""
    h = (DOCS / "flow.html").read_text(encoding="utf-8")
    assert "keinen Kontrollfluss" in h
    assert "Haeufigkeit ist keine Kausalitaet" in h


def test_beide_karten_verweisen_aufeinander():
    a = (DOCS / "index.html").read_text(encoding="utf-8")
    f = (DOCS / "flow.html").read_text(encoding="utf-8")
    assert "flow.html" in a and "index.html" in f


def test_der_eingebettete_datensatz_bleibt_lesbar():
    """Die ``<``-Maskierung darf gueltiges JSON nicht zerstoeren - sonst ist die Seite leer."""
    h = (DOCS / "flow.html").read_text(encoding="utf-8")
    roh = h.split("window.__FLOW__ = ", 1)[1].rsplit("</script>", 1)[0].strip().rstrip(";")
    wieder = json.loads(roh)
    assert wieder["gate"]["public_writers"] == ["submit"]
    assert wieder["cycle"]["cycles"] > 0
