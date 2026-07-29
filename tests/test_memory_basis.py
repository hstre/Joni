"""Die Grundlagenpruefung: hat eine Episode gesagt, woher sie ihr Wissen hat?

Der Anlass ist ein echter Fall, kein konstruierter. Am 29.07.2026 wurde in einer Sitzung fuenfmal
ueber Dokumente geurteilt, die nie geoeffnet worden waren - die Grundlage war jedes Mal eine
Namensaehnlichkeit: ein Repository-Modul namens ``layer9_v2`` fuer das Papier *Layer 9*, eine
Related-Work-Zeile fuer eine Abhaengigkeit, ein Wortstamm fuer eine Werksfamilie. Die vorherigen
Korrekturen standen dabei sichtbar im Verlauf.

Daraus folgt die Bauentscheidung, die diese Tests festhalten: **Ein Gedaechtnis haette das nicht
verhindert - das Gedaechtnis war da.** Was fehlte, war ein Feld und eine Regel darauf. Und der
Vorgabewert dieses Feldes muss ``UNDECLARED`` sein, nicht ``READ``: sonst behauptet jede unmarkierte
Episode, ihre Quelle gelesen zu haben, und die Pruefung findet nichts.
"""
from joni.memory import basis_report, inferred, undeclared
from joni.models import Basis, MemoryEpisode
from joni.persistence import from_dict, to_dict
from joni.state import Layer9


def _ep(state: Layer9, summary: str, *, basis: Basis = Basis.UNDECLARED,
        sources: tuple[str, ...] = ()) -> MemoryEpisode:
    ep = MemoryEpisode(id=state.next_id("M"), tick=state.tick, kind="learned",
                       summary=summary, basis=basis, sources=sources)
    state.memory.append(ep)
    return ep


# ── Der Vorgabewert ist die eigentliche Entscheidung ────────────────────────────────────────────

def test_vorgabe_ist_undeclared_nicht_read():
    """Waere READ die Vorgabe, ginge jede unmarkierte Episode als gelesen durch."""
    assert MemoryEpisode(id="M-1", tick=0, kind="learned", summary="x").basis is Basis.UNDECLARED


# ── Die Regel selbst: Quelle genannt, Grundlage nicht ───────────────────────────────────────────

def test_quelle_ohne_grundlage_faellt_auf():
    s = Layer9()
    _ep(s, "Das Layer-9-Papier faellt unter die Widerlegungen.", sources=("SSRN-6694758",))
    assert [e.id for e in undeclared(s)] == ["M-1"]


def test_gelesene_quelle_faellt_nicht_auf():
    s = Layer9()
    _ep(s, "Layer 9 nennt SPL als tragend.", basis=Basis.READ, sources=("SSRN-6694758",))
    assert undeclared(s) == []


def test_ohne_quelle_keine_pflicht():
    """Eine Episode ueber den eigenen Zustand behauptet ueber keine aeussere Quelle."""
    s = Layer9()
    _ep(s, "Budget diese Woche bei 0,26 EUR.")
    assert undeclared(s) == []


def test_erschlossen_ist_kein_fehler_aber_abrufbar():
    """Erschliessen ist erlaubt. Es muss nur auffindbar sein statt im Fliesstext zu verschwinden."""
    s = Layer9()
    _ep(s, "Vermutlich dieselbe Werksfamilie.", basis=Basis.INFERRED, sources=("SSRN-6277002",))
    assert undeclared(s) == []
    assert [e.id for e in inferred(s)] == ["M-1"]


# ── Der reale Fall, als Test ────────────────────────────────────────────────────────────────────

def test_der_fall_vom_29_juli():
    """Vier Behauptungen ueber ungelesene Dokumente, eine ueber ein gelesenes.

    Nur die vier ungedeckten duerfen auffallen - die gelesene nicht, sonst waere die Regel
    eine Rauschquelle statt einer Pruefung.
    """
    s = Layer9()
    _ep(s, "Layer-9-Papier von den Messungen erfasst.", sources=("SSRN-6694758",))
    _ep(s, "Alexandria gehoert zum widerlegten Rahmen.", sources=("SSRN-6277002",))
    _ep(s, "PES ist Grundlage von DESi.", sources=("SSRN-6272258",))
    _ep(s, "Das Modul layer9_v2 setzt das Papier um.", sources=("SSRN-6694758",))
    _ep(s, "SPL-Formalismus haelt; die Bruecke zur Sprache nicht.",
        basis=Basis.READ, sources=("SSRN-6395042",))

    auffaellig = [e.id for e in undeclared(s)]
    assert auffaellig == ["M-1", "M-2", "M-3", "M-4"]
    assert "M-5" not in auffaellig


# ── Persistenz ──────────────────────────────────────────────────────────────────────────────────

def test_altbestand_wird_undeclared_nicht_read():
    """Alte Zustaende duerfen nicht nachtraeglich zu gelesenen Quellen erklaert werden."""
    alt = {"schema": 1, "memory": [
        {"id": "M-1", "tick": 0, "kind": "learned", "summary": "alt", "refs": []}]}
    s = from_dict(alt)
    assert s.memory[0].basis is Basis.UNDECLARED
    assert s.memory[0].sources == ()


def test_rundlauf_erhaelt_grundlage_und_quellen():
    s = Layer9()
    _ep(s, "gelesen", basis=Basis.READ, sources=("SSRN-6395042", "docs/spl.md"))
    zurueck = from_dict(to_dict(s))
    assert zurueck.memory[0].basis is Basis.READ
    assert zurueck.memory[0].sources == ("SSRN-6395042", "docs/spl.md")


# ── Der Bericht ─────────────────────────────────────────────────────────────────────────────────

def test_bericht_zaehlt_und_nennt():
    s = Layer9()
    _ep(s, "a", sources=("X",))
    _ep(s, "b", basis=Basis.READ, sources=("Y",))
    _ep(s, "c", basis=Basis.INFERRED, sources=("Z",))
    r = basis_report(s)
    assert r["episodes"] == 3
    assert r["by_basis"] == {"undeclared": 1, "read": 1, "inferred": 1}
    assert r["undeclared_with_sources"] == ["M-1"]
    assert r["inferred"] == ["M-3"]
