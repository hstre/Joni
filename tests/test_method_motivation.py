"""Die Rueckreferenz: welche Vorfaelle haben diese Methode noetig gemacht?

Reflexion ist mehr als zurueckschauen. Sie ist: strukturaehnliche Fehler sehen, daraus eine Methode
ableiten - und **die Fehler an die Methode haengen**. Ohne den letzten Schritt hat man eine Regel,
die man glauben muss. Mit ihm hat man eine, die sich selbst begruendet und die man pruefen kann.

``supporting_runs`` sagt, wo eine Methode funktioniert hat. ``motivated_by`` sagt, warum es sie
gibt. Das sind verschiedene Fragen, und nur die zweite beantwortet "warum mache ich das so".

Der Testfall stammt aus diesem Repository: Die Grundlagenpflicht in ``memory.basis`` entstand aus
fuenf Verwechslungen an einem Tag. Eine Methode mit diesen fuenf Vorfaellen dahinter ist begruendet.
Eine ohne ist es nicht - was nicht heisst, dass sie falsch ist, sondern dass niemand mehr weiss,
woher sie kommt.
"""
import pytest

l9 = pytest.importorskip("desi_layer9")
from joni.autonomy.method_ledger import unmotivated  # noqa: E402


def _row(mid: str, motivated_by=()) -> dict:
    return {"method_id": mid, "name": "m", "status": "active", "state": "aktiv",
            "n_trials": 0, "last_verdict": None, "motivated_by": list(motivated_by)}


def test_methode_traegt_die_vorfaelle_die_sie_noetig_machten():
    m = l9.objects.Method(id="ME-1", name="Grundlage vor Behauptung erklaeren",
                          motivated_by=("M-4", "M-11", "M-17", "M-23", "M-29"))
    assert m.motivated_by == ("M-4", "M-11", "M-17", "M-23", "M-29")


def test_vorgabe_ist_leer_nicht_erfunden():
    """Ein Vorgabewert, der Vorfaelle behauptet, waere schlimmer als keiner."""
    assert l9.objects.Method(id="ME-1", name="x").motivated_by == ()


def test_supporting_runs_und_motivated_by_sind_verschiedene_fragen():
    """Wo hat es funktioniert vs. warum gibt es das ueberhaupt - eines ersetzt das andere nicht."""
    m = l9.objects.Method(id="ME-1", name="x",
                          supporting_runs=("run-7", "run-9"), motivated_by=("M-4",))
    assert m.supporting_runs != m.motivated_by
    assert len(m.supporting_runs) == 2 and len(m.motivated_by) == 1


def test_unbegruendete_methoden_fallen_auf():
    rows = [_row("ME-1", ("M-4", "M-11")), _row("ME-2"), _row("ME-3", ("M-29",))]
    assert [r["method_id"] for r in unmotivated(rows)] == ["ME-2"]


def test_alle_begruendet_meldet_nichts():
    assert unmotivated([_row("ME-1", ("M-4",)), _row("ME-2", ("M-9",))]) == []


def test_rundlauf_ueber_den_snapshot_erhaelt_die_rueckreferenz():
    """Die Referenz muss den Schnappschuss ueberleben, sonst ist sie beim naechsten Start weg."""
    from desi_layer9.snapshot import _deser, _ser
    m = l9.objects.Method(id="ME-1", name="x", motivated_by=("M-4", "M-11"))
    assert _deser(_ser(m)).motivated_by == ("M-4", "M-11")


def test_alter_schnappschuss_ohne_das_feld_laedt_weiter():
    """Bestehende Zustaende tragen es nicht - sie duerfen daran nicht scheitern."""
    from desi_layer9.snapshot import _deser
    alt = {"__c__": "Method", "f": {"id": "ME-1", "name": "x"}}
    assert _deser(alt).motivated_by == ()
