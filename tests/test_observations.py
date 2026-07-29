"""Die Invarianten der v3-Zuständigkeitsteilung - jede aus einem gemessenen Fehlschlag.

Getestet wird nicht, ob eine Klassifikation *richtig* ist (das misst ``run_observations.py`` gegen
Gold), sondern ob die Schicht ihre Zuständigkeit einhält: keine Urteile, keine terminale Wirkung
unsicherer Beobachtungen, keine stille Unterdrückung der besseren Quelle.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BRIDGE = Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge"
sys.path.insert(0, str(_BRIDGE))

obs = pytest.importorskip("observations")
pol = pytest.importorskip("policy")
ent = pytest.importorskip("entailment")


def _struct(**kw):
    base = {"text": "t", "subject": "wheel", "object": "alpine", "relation": "has_property",
            "modality": "asserted", "quantifier": "singular", "scope_level": "instance"}
    base.update(kw)
    agreement = tuple((f, 1.0) for f in
                      ("subject", "object", "relation", "modality", "quantifier",
                       "scope_level", "conditions"))
    return ent.Structure(agreement=agreement, **base)


# ── Zuständigkeit: es wird klassifiziert, nicht geurteilt ───────────────────────────────────────

def test_keine_beobachtung_traegt_ein_verdikt():
    """Kein Beobachtungstyp darf ein Verdikt-Wort führen - sonst ist die Trennung nur Kosmetik."""
    verdicts = {"entailed", "partially_entailed", "compatible_not_entailed", "contradicted",
                "insufficient"}
    for name in obs.OBSERVATIONS:
        assert name.lower() not in verdicts


def test_prozessbeobachtungen_haben_keine_konfidenz():
    """Klasse A schätzt nichts. Eine Konfidenz dort wäre eine erfundene Unsicherheit."""
    items = obs.process_observations(model_verdict="entailed", agreement=1.0, k=5,
                                     evidence=[{"source_id": "e1", "text": "x"}])
    for o in items:
        assert o.observation_class == obs.PROCESS
        assert o.confidence is None
        assert not o.parser_dependent


def test_semantische_beobachtung_traegt_konfidenz_und_herkunft():
    claim = _struct(quantifier="universal")
    ev = [_struct(quantifier="singular")]
    items = obs.semantic_observations(claim, ev)
    widening = [o for o in items if o.type == "QUANTIFIER_WIDENING"]
    assert widening, "Quantorenerweiterung wurde nicht klassifiziert"
    assert widening[0].confidence is not None
    assert widening[0].source == obs.DETERMINISTIC
    assert widening[0].parser_dependent


def test_reichweitenverengung_wird_als_verengung_gefuehrt():
    """TEST-026: eine Verengung (class → instance) ist ein normaler Schluss, keine Erweiterung.

    Die alte Kontrolle las jede Differenz als Eskalation und stufte deshalb ein korrektes
    `entailed` herab. Die Richtung MUSS im Detail stehen.
    """
    items = obs.semantic_observations(_struct(scope_level="instance"),
                                      [_struct(scope_level="class")])
    scope = [o for o in items if o.type == "SCOPE_CHANGE"]
    assert scope and scope[0].detail["direction"] == "narrowed"


def test_unbekannte_feldzustimmung_gilt_als_null_nicht_als_eins():
    """Unbekannte Verlässlichkeit ist keine hohe - sonst wandert Unwissen als Sicherheit durch."""
    naked = ent.Structure(text="t", subject="a", object="b", quantifier="universal")
    items = obs.semantic_observations(naked, [ent.Structure(text="e", subject="a", object="b")])
    for o in items:
        if o.confidence is not None:
            assert o.confidence == 0.0


# ── Policy: die Invarianten der Governance-Schicht ──────────────────────────────────────────────

def test_klasse_b_kann_nichts_abschliessen():
    """Die tragende Invariante: unsichere Beobachtung ⇒ Aufmerksamkeit, nie Konsequenz."""
    p = pol.Policy(name="t", rules={"QUANTIFIER_WIDENING": pol.HOLD}, min_confidence=0.0)
    d = p.decide([obs.Observation("QUANTIFIER_WIDENING", {}, confidence=1.0)])
    assert d.action == pol.REQUEST_REVIEW
    assert any("QUANTIFIER_WIDENING" in a for a in d.advisory_only)


def test_klasse_a_darf_abschliessen():
    d = pol.MSCE_L2_L3_V1.decide(
        obs.process_observations(model_verdict="entailed", agreement=0.4, k=5, evidence=[]))
    assert d.action == pol.HOLD


def test_modellquelle_wird_nicht_vom_konfidenzfilter_verschluckt():
    """Die Modellquelle liefert keine Konfidenzzahl und ist der gemessen bessere Zweig (0.727).

    Ein Filter, der `None` als 0.0 liest, hätte sie still unterdrückt - und die Policy wäre auf dem
    schwachen Zweig sitzengeblieben, ohne dass es jemand merkt.
    """
    d = pol.MSCE_L2_L3_V1.decide(obs.model_transformations(["modal_strengthening"]))
    assert d.action == pol.REQUEST_REVIEW
    assert d.reasons


def test_deterministischer_zweig_loest_in_der_startpolicy_nichts_aus():
    """Gemessen 0.25 mikro-F1 bei 10 Falschpositiven - er darf messen, nicht auslösen."""
    det = [obs.Observation(t, {}, confidence=1.0) for t in
           ("QUANTIFIER_WIDENING", "MODALITY_CHANGE", "SCOPE_CHANGE", "CONDITION_DROPPED",
            "ENTITY_MISMATCH", "CAUSAL_UPGRADE")]
    assert pol.MSCE_L2_L3_V1.decide(det).action == pol.PERSIST


def test_ohne_beobachtung_bleibt_es_beim_default():
    assert pol.MSCE_L2_L3_V1.decide([]).action == pol.PERSIST


def test_niedrige_konfidenz_wird_beratend_statt_wirksam():
    p = pol.Policy(name="t", rules={"MODALITY_CHANGE": pol.REQUEST_REVIEW}, min_confidence=0.6)
    d = p.decide([obs.Observation("MODALITY_CHANGE", {}, confidence=0.2)])
    assert d.action == pol.PERSIST
    assert d.advisory_only
