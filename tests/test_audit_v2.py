"""Entailment-Auditor v2: die sechs Invarianten aus der Architektur, erzwungen statt behauptet.

Kein Netz - die Modellschicht wird ersetzt. Geprüft wird die STRUKTUR der Governance, nicht die
Trefferquote (die misst der Dev-Satz).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge"))

v2 = pytest.importorskip("audit_v2")
ent = pytest.importorskip("entailment")


def _s(**kw):
    base = dict(text="t", subject="alpine containers", relation="has_property",
                object="musl libc", modality="asserted", quantifier="generic",
                scope_level="class")
    base.update(kw)
    return ent.Structure(**base)


# ── Invariante 1 + 2: nur abwärts, nie zu contradicted ──────────────────────────────────────────

@pytest.mark.parametrize("start", v2.LADDER)
def test_a_veto_never_moves_a_verdict_upwards(start):
    veto = v2.Veto("evidence_padding", "grund", "entailed")   # versucht zu HEBEN
    out = v2.apply_vetoes(start, [veto])
    assert v2.LADDER.index(out) >= v2.LADDER.index(start), "Veto hat heraufgestuft"


def test_no_control_can_ever_assert_contradicted():
    """Einen Widerspruch zu behaupten ist eine positive Aussage - daran sind Regeln gescheitert."""
    claim = _s(quantifier="universal")
    ev = [_s(quantifier="singular")]
    vetoes = v2.run_controls(claim, ev, verdict="entailed")
    assert vetoes, "erwartet mindestens ein Veto"
    assert all(v.downgrade_to != "contradicted" for v in vetoes)
    assert v2.apply_vetoes("entailed", vetoes) != "contradicted"


def test_contradicted_from_the_model_is_left_alone():
    """`contradicted` liegt ausserhalb der Leiter - Kontrollen fassen es nicht an."""
    assert v2.apply_vetoes("contradicted", [v2.Veto("x", "y", "insufficient")]) == "contradicted"


# ── Invariante 3: ohne Veto identisch mit dem Modellurteil ──────────────────────────────────────

def test_without_a_veto_the_model_verdict_survives_unchanged():
    assert v2.apply_vetoes("entailed", []) == "entailed"
    assert v2.apply_vetoes("partially_entailed", []) == "partially_entailed"


# ── Invariante 4: Kontrollen laufen nur auf durchlassenden Verdikten ────────────────────────────

@pytest.mark.parametrize("verdict", ["compatible_not_entailed", "insufficient", "contradicted"])
def test_controls_do_not_run_on_non_passing_verdicts(verdict):
    claim = _s(quantifier="universal")
    ev = [_s(quantifier="singular")]
    assert v2.run_controls(claim, ev, verdict=verdict) == []


# ── Die einzelnen Kontrollen, je aus einem gemessenen Fehlschlag ────────────────────────────────

def test_evidence_padding_is_registered_but_inactive():
    """Abgeschaltet, weil GEMESSEN schaedlich - nicht weil es schwer war.

    Der Kontrollkatalog war aus v1s Defektliste uebernommen, ohne zu pruefen, ob v2 diese Defekte
    erbt. Es erbt sie nicht: der Auffuell-Angriff laesst das Modellurteil unveraendert
    (compatible_not_entailed, Zustimmung 1.0 mit und ohne Auffuellung). Als Veto erzeugte die
    Kontrolle auf dem Dev-Satz drei Falschsperren und fing null Angriffe, weil ihr Entitaetsproxy
    auf Wortueberlappung beruht und legitime, nur anders formulierte Stuetzung verwirft.

    Die allgemeine Lehre: ein Kontrollkatalog muss aus den gemessenen Fehlern des Systems
    abgeleitet sein, das er bewacht - nicht aus denen seines Vorgaengers."""
    assert "evidence_padding" in v2.CONTROLS          # bleibt dokumentiert
    assert "evidence_padding" not in v2.ACTIVE_CONTROLS   # feuert aber nicht
    claim = _s(subject="binary wheels", object="musl systems")
    unrelated = [_s(subject="container images", object="base layer", quantifier="universal")]
    assert v2.run_controls(claim, unrelated, verdict="entailed") == []


def test_disabling_a_control_happens_via_the_registry_not_by_deleting_code():
    """Damit eine Wiederaktivierung eine Datenaenderung ist, keine Codeaenderung."""
    assert set(v2.ACTIVE_CONTROLS) <= set(v2.CONTROLS)
    assert v2.ACTIVE_CONTROLS, "es duerfen nicht alle Kontrollen abgeschaltet sein"


def test_epistemic_hedge_is_caught():
    """DEV-017: 'keine Hinweise gefunden' traegt keinen Sachclaim."""
    claim = _s(epistemic_hedge=False)
    hedged = [_s(epistemic_hedge=True)]
    vetoes = v2.run_controls(claim, hedged, verdict="entailed")
    assert "epistemic_hedge" in [v.control for v in vetoes]


def test_quantifier_escalation_is_caught():
    vetoes = v2.run_controls(_s(quantifier="universal"), [_s(quantifier="existential")],
                             verdict="entailed")
    assert "quantifier_escalation" in [v.control for v in vetoes]


def test_modality_escalation_is_caught():
    vetoes = v2.run_controls(_s(modality="asserted"), [_s(modality="possible")],
                             verdict="entailed")
    assert "modality_escalation" in [v.control for v in vetoes]


def test_uncovered_conjunction_downgrades():
    """§7f: ein nicht gedeckter Konjunkt darf nie als entailed durchgehen."""
    vetoes = v2.run_controls(_s(), [_s()], verdict="entailed", propositions_covered=False)
    assert "conjunction_coverage" in [v.control for v in vetoes]
    assert v2.apply_vetoes("entailed", vetoes) == "partially_entailed"


def test_a_clean_case_produces_no_veto():
    """Die Gegenprobe: passt alles, greift nichts - sonst waere v2 nur ueberstreng."""
    assert v2.run_controls(_s(), [_s()], verdict="entailed") == []


# ── Invariante 5: Herkunft ist ausgewiesen ──────────────────────────────────────────────────────

def test_the_result_attributes_every_part_to_its_origin():
    r = v2.Result(claim="c", verdict="partially_entailed", model_verdict="entailed",
                  model_agreement=1.0, vetoes=[v2.Veto("a", "b", "partially_entailed")])
    d = r.to_dict()
    assert d["provenance"]["verdict_proposed_by"] == "model"
    assert d["provenance"]["controls_can_upgrade"] is False
    assert d["downgraded"] is True
    assert d["vetoes"][0]["can_upgrade"] is False


# ── Triage: Zweitmeinung markiert, urteilt aber nicht ───────────────────────────────────────────

def test_the_second_opinion_flags_but_never_changes_the_verdict():
    """Uneinigkeit ist ein Signal fuer Pruefung - kein Urteilsverbesserer.

    Als Kombinationsregel bringt ein Ensemble nichts, zweimal gemessen: flash+pro und flash+gemma
    landen beide bei 17/20 statt 18, weil die Uneinigkeiten genau die Faelle sind, in denen einer
    richtig und einer falsch liegt. Als SIGNAL faengt dieselbe Uneinigkeit auf dem Dev-Satz zwei
    von drei Fehlern bei 10 Prozent markierter Faelle."""
    assert v2.needs_review("entailed", "compatible_not_entailed") is True
    assert v2.needs_review("entailed", "entailed") is False


def test_review_required_is_reported_separately_from_the_verdict():
    r = v2.Result(claim="c", verdict="entailed", model_verdict="entailed",
                  model_agreement=1.0, review_required=True, second_opinion="insufficient")
    d = r.to_dict()
    assert d["verdict"] == "entailed"          # unveraendert
    assert d["review_required"] is True         # aber markiert
    assert d["second_opinion"] == "insufficient"


def test_the_second_opinion_must_come_from_another_house():
    """Geschwistermodelle taugen nicht - gemessen: deepseek flash/pro waren sich bei 18 von 20
    Faellen einig, also fast nie uneinig, also als Triage blind."""
    import spl_builder as sb
    primary = sb.BUILDERS[ent.PARSER]
    second = sb.BUILDERS[v2.SECOND_OPINION]
    assert primary.split("/")[0].split("-")[0] != second.split("/")[0]
