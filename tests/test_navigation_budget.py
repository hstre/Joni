"""Die Navigation darf nicht 27 Minuten fuer eine beratende Zeile brauchen.

Gemessen am 07.08.2026: ``top_agenda_line`` baut aus allen 10.958 Claims Loesungspunkte und
vergleicht sie paarweise - 60.033.403 Paare, 27 Minuten je Zyklus. Das Ergebnis ist *eine* Zeile
im Protokoll, die nichts entscheidet und den Kern nicht anfasst ("Non-authoritative, never
mutates the core", sagt der Aufrufer selbst).

Zwei Entscheidungen stecken in der Reparatur, und beide werden hier festgehalten:

1. **Abgelehnt, nicht gekuerzt.** Eine Auswahl waere eine Festlegung darueber, welche Claims in
   die Karte gehoeren - das ist eine Aussage ueber ihren Zweck und hat in einer Kostenbremse
   nichts zu suchen. Das Modul sieht fuer fehlende Daten ohnehin ein leeres, klar
   gekennzeichnetes Ergebnis vor; hier gilt dasselbe.
2. **Sichtbar, nicht still.** Eine leere Zeile saehe aus wie "nichts zu tun" und hiesse
   "nicht nachgesehen". Der Unterschied ist derselbe wie zwischen UNDECLARED und NONE.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("desi_layer9")
from joni.autonomy import navigation_view as nv  # noqa: E402


class _Kern:
    """Ein Kern, der nur sagt, wie viele Claims er haette."""

    def __init__(self, n: int) -> None:
        self._n = n
        self.gefragt = 0

    def count(self, object_type=None):
        self.gefragt += 1
        return self._n

    def all(self, object_type):        # wuerde bei n=200.000 Minuten kosten
        raise AssertionError("all() darf bei ueberschrittener Grenze nicht aufgerufen werden")


# ── Die Grenze folgt aus dem Budget, nicht aus einer gegriffenen Zahl ────────────────────────────

def test_die_grenze_kommt_aus_dem_zeitbudget():
    """Verdoppeltes Budget -> rund wurzel-zwei-mal so viele Punkte (quadratische Kosten)."""
    a, b = nv.max_points(5.0), nv.max_points(20.0)
    assert b > a
    assert 1.9 < b / a < 2.1, f"{a} -> {b}"


def test_die_grenze_ist_plausibel_gross():
    n = nv.max_points()
    paare = n * (n - 1) // 2
    assert 500 < n < 3000, n
    assert paare * 6.2e-6 <= nv.NAV_BUDGET_SECONDS * 1.05


# ── Ablehnen statt kuerzen ──────────────────────────────────────────────────────────────────────

def test_zu_grosser_zustand_wird_abgelehnt_nicht_gekuerzt():
    kern = _Kern(10958)
    rep = nv.run_navigation(kern)
    assert rep["available"] is False
    assert rep["agenda"] == []
    assert rep["n_claims"] == 10958
    assert "60,033,403" in rep["skipped"] or "60033403" in rep["skipped"]


def test_die_teure_arbeit_wird_gar_nicht_erst_begonnen():
    """``all()`` wirft im Doppel - die Ablehnung muss davor greifen, nicht danach."""
    nv.run_navigation(_Kern(50_000))          # wuerde sonst die Zusicherung ausloesen


def test_kleiner_zustand_laeuft_normal_weiter():
    """Die Bremse darf nicht der Normalfall werden."""
    kern = _Kern(50)
    rep = nv.run_navigation(kern)
    assert "skipped" not in rep


# ── Sichtbar, nicht still ───────────────────────────────────────────────────────────────────────

def test_die_ablehnung_steht_in_der_protokollzeile():
    zeile = nv.top_agenda_line(_Kern(10958))
    assert zeile, "Eine leere Zeile saehe aus wie 'nichts zu tun'"
    assert "uebersprungen" in zeile
    assert "10958" in zeile


def test_ohne_agenda_bleibt_die_zeile_leer():
    """Der Unterschied, auf den es ankommt: nichts gefunden ist nicht dasselbe wie nicht gesucht."""
    class _Leer(_Kern):
        def all(self, object_type):
            return []
    assert nv.top_agenda_line(_Leer(3)) == ""


def test_ein_budget_null_haelt_alles_an_und_sagt_es():
    zeile = nv.top_agenda_line(_Kern(10), budget_seconds=0.0)
    assert "uebersprungen" in zeile
