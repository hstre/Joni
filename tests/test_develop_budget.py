"""Der Paardurchlauf: begrenzt auf die geprueften Paare, ohne dass hinten etwas aushungert.

``max_links`` deckelte, wie viele Verknuepfungen *entstehen*, nicht wie viel Arbeit dafuer getan
wird. Das ist eine Grenze, die keine ist: bei den gemessenen 3.877 lebenden Claims laeuft die
Doppelschleife ueber 7.513.626 Paare zu je 67,4 us - 8,4 Minuten, um hoechstens zwei
Verknuepfungen zu finden. In den Stapelstichproben vom 07.08.2026 war das der groesste
verbliebene Posten des Zyklus.

Ein harter Deckel waere die falsche Reparatur gewesen: er faengt jeden Zyklus vorn an, und die
hinteren Claims kaemen nie dran. Deshalb ein fortsetzbarer Zeiger. Die beiden Tests, auf die es
ankommt, sind entsprechend nicht die Kostenmessungen, sondern:

* dass ueber mehrere Zyklen **jedes** Paar einmal geprueft wird, und
* dass der Zeiger eine Claim-ID ist und keine Position - sonst zeigt er nach der ersten
  Aenderung der Liste auf etwas anderes, ohne dass es auffaellt.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("desi_layer9")
from joni.autonomy import develop as dv  # noqa: E402


@dataclass
class _Claim:
    id: str
    text: str
    topic: str = "t"


@dataclass
class _Proto:
    zeilen: list = field(default_factory=list)

    def record(self, cycle, kind, summary, **kw):
        self.zeilen.append((kind, summary))


class _Core:
    @staticmethod
    def open_conflicts():
        return []


class _CS:
    """Nur so viel Zustand, wie ``develop`` anfasst."""

    def __init__(self, n: int) -> None:
        # Absichtlich ohne Wortueberlappung: der Trigger schlaegt nie an, also entstehen keine
        # Verknuepfungen und der max_links-Ausstieg maskiert die Budgetgrenze nicht.
        self._c = [_Claim(id=f"C{i:04d}", text=f"wort{i} eigen{i}") for i in range(n)]
        self.core = _Core()

    def active_claims(self):
        return list(self._c)

    def review_conflict(self, cid):    # pragma: no cover - nicht Teil dieses Tests
        raise AssertionError


def _cs(n: int) -> _CS:
    return _CS(n)


def _lauf(cs, ext, *, budget, zyklus=0):
    return dv.develop(cs, ext, _Proto(), zyklus, max_backfill=0, max_review=0,
                      budget_seconds=budget)


# ── Die Grenze folgt aus dem Budget ─────────────────────────────────────────────────────────────

def test_die_grenze_kommt_aus_dem_zeitbudget():
    assert abs(dv.max_pairs(10.0) - 2 * dv.max_pairs(5.0)) <= 1     # Ganzzahl-Abrundung
    assert 100_000 < dv.max_pairs(10.0) < 200_000


def test_ein_kleines_budget_bricht_ab_und_sagt_es():
    cs, ext, proto = _cs(60), {}, _Proto()
    r = dv.develop(cs, ext, proto, 1, max_backfill=0, max_review=0,
                   budget_seconds=100 * dv._US_PER_PAIR)     # ~100 Paare
    assert r["budget_exhausted"] is True
    assert r["pairs_examined"] <= 120
    assert any("begrenzt" in s for _, s in proto.zeilen), "Abbruch muss im Protokoll stehen"


def test_ein_grosses_budget_laeuft_durch_und_setzt_den_zeiger_zurueck():
    cs, ext = _cs(40), {}
    r = _lauf(cs, ext, budget=10.0)
    assert r["budget_exhausted"] is False
    assert ext["develop_cursor"] == ""


# ── Der Punkt: nichts hungert aus ───────────────────────────────────────────────────────────────

def test_ueber_mehrere_zyklen_wird_jedes_paar_einmal_geprueft():
    """Der Test, der den Unterschied zwischen Zeiger und hartem Deckel misst."""
    n = 50
    erwartet = n * (n - 1) // 2
    cs, ext = _cs(n), {}
    gesamt = 0
    for z in range(40):
        r = _lauf(cs, ext, budget=60 * dv._US_PER_PAIR, zyklus=z)   # ~60 Paare je Zyklus
        gesamt += r["pairs_examined"]
        if not r["budget_exhausted"]:
            break
    assert gesamt == erwartet, f"{gesamt} von {erwartet} Paaren geprueft"


def test_ein_harter_deckel_haette_die_hinteren_nie_erreicht():
    """Gegentest: ohne Zeiger bliebe der Durchlauf in denselben ersten Claims stecken."""
    cs = _cs(50)
    gesehen = set()
    for _ in range(5):
        ext = {}                                   # kein Zeiger -> jeder Zyklus faengt vorn an
        _lauf(cs, ext, budget=60 * dv._US_PER_PAIR)
        gesehen.add(ext.get("develop_cursor"))
    assert len(gesehen) == 1, "ohne Zeiger endet jeder Zyklus an derselben Stelle"


def test_der_zeiger_ist_eine_claim_id_keine_position():
    """Eine Position waere nach der ersten Listenaenderung still falsch."""
    cs, ext = _cs(50), {}
    _lauf(cs, ext, budget=60 * dv._US_PER_PAIR)
    zeiger = ext["develop_cursor"]
    assert zeiger.startswith("C"), zeiger
    assert zeiger in {c.id for c in cs.active_claims()}


def test_nach_einem_vollen_durchlauf_faengt_er_von_vorn_an():
    """Sonst kaemen neu hinzugekommene Claims nie dran."""
    cs, ext = _cs(20), {"develop_cursor": "C0018"}
    r = _lauf(cs, ext, budget=10.0)
    assert r["budget_exhausted"] is False
    assert ext["develop_cursor"] == ""


def test_der_zeiger_ueberlebt_eine_veraenderte_liste():
    """Claims kommen zwischen Zyklen dazu - der Zeiger muss trotzdem sinnvoll weitersetzen."""
    cs, ext = _cs(50), {"develop_cursor": "C0024"}
    cs._c.insert(0, _Claim(id="C0000x", text="neu dazu"))
    r = _lauf(cs, ext, budget=60 * dv._US_PER_PAIR)
    assert r["pairs_examined"] > 0


# ── Und die Verknuepfungslogik bleibt, wie sie war ──────────────────────────────────────────────

def test_max_links_greift_weiterhin(monkeypatch):
    """Die Budgetgrenze darf den bestehenden Ausstieg nicht ersetzen, nur ergaenzen."""
    class _Entscheidung:
        value = "unrelated"

    class _Sc:
        decision = _Entscheidung()
        semantic_layer = "test"
        semantic_layer_version = "0"

    gerufen = {"n": 0}

    def _fake(*a, **k):
        gerufen["n"] += 1
        return _Sc()

    cs = _cs(30)
    for c in cs._c:
        c.text = "gleicher text ueberall gleich"
    monkeypatch.setattr(dv.adapter, "analyse_pair", _fake)
    r = dv.develop(cs, {}, _Proto(), 0, max_links=2, max_backfill=0, max_review=0,
                   budget_seconds=10.0)
    assert r["links"] == 0            # 'unrelated' erzeugt keine Verknuepfung
    assert gerufen["n"] > 0           # aber der Pfad wurde durchlaufen
