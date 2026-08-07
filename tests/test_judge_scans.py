"""Die Bewertung darf nicht 151-mal den ganzen Speicher lesen.

Gemessener Anlass, kein vermuteter: Ein Probelauf am 07.08.2026 wurde nach 25 Minuten
abgeschnitten. Fuenf aufeinanderfolgende Stapelstichproben lagen alle an derselben Stelle -
``judge()`` -> ``claims_on()`` -> ``_live_claims()`` -> ``core.all()``. Die Ursache stand in vier
Zeilen: ``judge`` holte ``topics()`` und dann je Thema ``claims_on(topic)``, und jeder dieser
Aufrufe geht durch alle 201.195 Objekte und kopiert jeden Claim tief.

Gemessen: 0,58 s je Scan, 150 Themen, also ~80 s je Fundstueck. Der Kernel ist daran nicht
schuld - die Tiefkopie *ist* seine Schutzzusage. Schuld war, sie 151-mal zu bezahlen.

Zwei Dinge werden hier festgehalten: dass die Zahl der Scans klein bleibt, und dass das
Ergebnis dasselbe ist wie vorher. Das zweite ist das wichtigere - eine schnelle Bewertung, die
anders urteilt, waere keine Reparatur, sondern eine stille Verhaltensaenderung.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

pytest.importorskip("desi_layer9")
from joni.autonomy.improve import judge  # noqa: E402
from joni.autonomy.sources import Item  # noqa: E402


@dataclass
class _Claim:
    text: str
    topic: str


class _Zaehlend:
    """Ein Zustand, der mitzaehlt, wie oft der teure Vollscan angefasst wird."""

    def __init__(self, claims: list[_Claim]) -> None:
        self._claims = claims
        self.scans = 0

    def _live(self) -> list[_Claim]:
        self.scans += 1
        return list(self._claims)

    # -- die alte, teure Schnittstelle -------------------------------------- #
    def topics(self) -> list[str]:
        from collections import Counter
        counts = Counter(c.topic for c in self._live() if c.topic)
        return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    def claims_on(self, topic: str) -> list[_Claim]:
        return [c for c in self._live() if c.topic == topic]


class _Gruppierend(_Zaehlend):
    """Derselbe Zustand, zusaetzlich mit der gruppierten Leseform."""

    def claims_by_topic(self) -> dict[str, list[_Claim]]:
        out: dict[str, list[_Claim]] = {}
        for c in self._live():
            if c.topic:
                out.setdefault(c.topic, []).append(c)
        return out


def _welt(n_themen: int = 40) -> list[_Claim]:
    return [_Claim(text=f"claim {i} ueber thema{i % n_themen} und messung",
                   topic=f"thema{i % n_themen}")
            for i in range(400)]


def _item() -> Item:
    return Item(source="test", id="k", title="Messung von thema7 in der Praxis",
                url="https://x", summary="thema7 und die Frage der Kalibrierung")


# ── Die eigentliche Reparatur ───────────────────────────────────────────────────────────────────

def test_ein_scan_statt_einem_je_thema():
    """Der Punkt der Aenderung: die Kosten haengen nicht mehr an der Themenzahl."""
    z = _Gruppierend(_welt(n_themen=40))
    judge(z, _item())
    assert z.scans == 1, f"{z.scans} Vollscans - erwartet war einer"


def test_ohne_gruppierung_waere_es_einer_je_thema():
    """Der Gegentest: ohne ihn wuesste man nicht, ob der erste Test ueberhaupt etwas misst."""
    z = _Zaehlend(_welt(n_themen=40))
    judge(z, _item())
    assert z.scans == 41, f"{z.scans} - erwartet waren 1 + 40"


def test_mehr_themen_kosten_nicht_mehr_scans():
    schmal = _Gruppierend(_welt(n_themen=5))
    breit = _Gruppierend(_welt(n_themen=150))
    judge(schmal, _item())
    judge(breit, _item())
    assert schmal.scans == breit.scans == 1


# ── Und das Wichtigere: dasselbe Urteil ─────────────────────────────────────────────────────────

def test_das_urteil_ist_unveraendert():
    """Beide Wege muessen dasselbe liefern - sonst ist es keine Reparatur."""
    claims = _welt(n_themen=40)
    alt = judge(_Zaehlend(claims), _item())
    neu = judge(_Gruppierend(claims), _item())
    assert (alt.relevant, alt.topic, alt.new_topic) == (neu.relevant, neu.topic, neu.new_topic)


@pytest.mark.parametrize("n_themen", [1, 3, 12, 40])
def test_gleiches_urteil_ueber_verschiedene_zustaende(n_themen):
    claims = _welt(n_themen=n_themen)
    for titel in ("Messung von thema0", "voellig anderes Thema", "kalibrierung und routing"):
        it = Item(source="test", id="k", title=titel, url="https://x", summary="")
        alt = judge(_Zaehlend(claims), it)
        neu = judge(_Gruppierend(claims), it)
        assert (alt.relevant, alt.topic, alt.new_topic) == (neu.relevant, neu.topic, neu.new_topic)


def test_die_themenreihenfolge_bleibt_die_alte():
    """Bei Gleichstand gewinnt das erste Thema - die Reihenfolge ist also Teil des Ergebnisses."""
    claims = _welt(n_themen=7)
    z = _Zaehlend(claims)
    g = _Gruppierend(claims)
    by = g.claims_by_topic()
    assert sorted(by, key=lambda t: (-len(by[t]), t)) == z.topics()
    for t in z.topics():
        assert by[t] == z.claims_on(t)


def test_leerer_zustand_faellt_nicht_um():
    z = _Gruppierend([])
    r = judge(z, _item())
    assert r.topic is None
    assert z.scans == 1


def test_alte_schnittstelle_wird_weiter_bedient():
    """Ein Zustand ohne ``claims_by_topic`` muss weiter funktionieren, nur langsamer."""
    z = _Zaehlend(_welt(n_themen=6))
    assert judge(z, _item()) is not None
