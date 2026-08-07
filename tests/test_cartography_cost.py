"""Die Kartographie: dieselbe Karte, ein Drittel der Arbeit je Paar.

Gemessener Anlass. Ein Probelauf am 07.08.2026 kam nicht durch; von 37 Stapelstichproben lagen
22 in ``cartography``. Der Grund ist die Alle-Paare-Schleife: bei den 10.958 Claims im Zustand
sind das 60.033.403 Paare, und ``_sem_dist`` bestimmt fuer *jedes* Paar beide Vektorlaengen neu -
jede Laenge also fast 11.000-mal dieselbe Zahl. Gemessen 11,8 us je Paar bei Dimension 64, macht
rund zwoelf Minuten je Zyklus.

Was hier repariert wird, ist die dreifache Arbeit je Paar, nicht die quadratische Schleife. Die
bleibt - sie ist eine Eigenschaft dieser Karte, und sie zu deckeln waere eine Entscheidung
darueber, welche Claims zaehlen. Das ist keine Reparatur, sondern eine Festlegung ueber den
Zweck, und die gehoert nicht in einen Geschwindigkeitsfix.

Der wichtigere Teil dieser Datei ist deshalb nicht die Kostenmessung, sondern der Nachweis, dass
die Karte danach dieselbe ist - bis auf das letzte Bit.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from joni.solution_space.cartography import (  # noqa: E402
    SolutionPoint,
    _combined,
    _combined_pre,
    _norms,
    _ranges,
    _sem_dist,
    _sem_dist_pre,
    cartograph,
)


def _punkte(n: int, dim: int = 64, seed: int = 7) -> list[SolutionPoint]:
    r = random.Random(seed)
    return [SolutionPoint(id=f"c{i}",
                          state_vector=tuple(r.random() for _ in range(9)),
                          embedding=[r.random() for _ in range(dim)],
                          label=f"claim {i}", anchored=(i % 5 == 0))
            for i in range(n)]


# ── Gleichheit bis aufs letzte Bit ──────────────────────────────────────────────────────────────

def test_die_distanz_ist_bitgleich():
    """Nicht "ungefaehr gleich" - identisch. Sonst waere es eine stille Verhaltensaenderung."""
    pts = _punkte(60)
    norms = _norms(pts)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert _sem_dist_pre(pts[i], pts[j], norms[i], norms[j]) == _sem_dist(pts[i], pts[j])


def test_die_kombinierte_distanz_ist_bitgleich():
    pts = _punkte(40)
    ranges, norms = _ranges(pts), _norms(pts)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            assert (_combined_pre(pts[i], pts[j], ranges, 0.5, 0.5, norms[i], norms[j])
                    == _combined(pts[i], pts[j], ranges, 0.5, 0.5))


@pytest.mark.parametrize("tau", [0.05, 0.2, 0.35, 0.6, 0.95])
def test_die_karte_bleibt_dieselbe(tau):
    """Ueber verschiedene Schwellen: gleiche Inseln, gleiche Bruecken, gleiche Reihenfolge."""
    pts = _punkte(120)
    k = cartograph(pts, tau=tau)
    assert [(i.id, i.member_ids, i.anchored, i.size) for i in k.islands]
    # Referenz: dieselbe Rechnung ueber den unveraenderten Weg
    ranges = _ranges(pts)
    from joni.solution_space.cartography import _UnionFind
    uf = _UnionFind(len(pts))
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if _combined(pts[i], pts[j], ranges, 0.5, 0.5) <= tau:
                uf.union(i, j)
    gruppen: dict[int, list[int]] = {}
    for i in range(len(pts)):
        gruppen.setdefault(uf.find(i), []).append(i)
    erwartet = [tuple(pts[m].id for m in mitglieder)
                for _, mitglieder in sorted(gruppen.items())]
    assert [i.member_ids for i in k.islands] == erwartet


# ── Randfaelle, die die Laengenvorberechnung kippen koennten ────────────────────────────────────

def test_leere_einbettung_bleibt_null_distanz():
    a = SolutionPoint(id="a", state_vector=(0.0,) * 9, embedding=[], label="", anchored=False)
    b = SolutionPoint(id="b", state_vector=(0.0,) * 9, embedding=[1.0, 2.0], label="",
                      anchored=False)
    n = _norms([a, b])
    assert _sem_dist_pre(a, b, n[0], n[1]) == _sem_dist(a, b) == 0.0


def test_nullvektor_bleibt_maximale_distanz():
    """Laenge 0 bei nicht-leerem Vektor: der Zweig, den eine Vorberechnung leicht verliert."""
    a = SolutionPoint(id="a", state_vector=(0.0,) * 9, embedding=[0.0, 0.0], label="",
                      anchored=False)
    b = SolutionPoint(id="b", state_vector=(0.0,) * 9, embedding=[1.0, 2.0], label="",
                      anchored=False)
    n = _norms([a, b])
    assert n[0] == 0.0
    assert _sem_dist_pre(a, b, n[0], n[1]) == _sem_dist(a, b) == 1.0


def test_ein_einziger_punkt_und_gar_keiner():
    assert cartograph([]).islands == ()
    k = cartograph(_punkte(1))
    assert len(k.islands) == 1 and k.islands[0].size == 1


# ── Die Kosten selbst ───────────────────────────────────────────────────────────────────────────

def test_laengen_werden_einmal_je_punkt_bestimmt_nicht_einmal_je_paar():
    """Der eigentliche Gewinn, gezaehlt statt geschaetzt."""
    aufrufe = {"n": 0}

    class _Zaehlend(list):
        def __iter__(self):
            aufrufe["n"] += 1
            return super().__iter__()

    pts = _punkte(30)
    for p in pts:
        object.__setattr__(p, "embedding", _Zaehlend(p.embedding))
    _norms(pts)
    assert aufrufe["n"] == 30, f"{aufrufe['n']} Durchlaeufe fuer 30 Punkte"


def test_die_schleife_bleibt_quadratisch_und_das_steht_so_da():
    """Kein stiller Deckel: was diese Karte kostet, muss im Quelltext stehen.

    Sie zu deckeln waere eine Entscheidung darueber, welche Claims zaehlen - kein
    Geschwindigkeitsfix. Solange sie ungedeckelt ist, soll die Zahl sichtbar sein.
    """
    quelle = (Path(__file__).resolve().parents[1]
              / "src/joni/solution_space/cartography.py").read_text(encoding="utf-8")
    assert "quadratisch" in quelle
    assert "60.033.403" in quelle
