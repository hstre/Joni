"""Der Commonsense-Regelbestand: die Eigenschaften, die ihn von OpenCyc unterscheiden sollen.

Geprüft wird nicht, ob die Regeln *wahr* sind - das ist eine inhaltliche Frage. Geprüft wird, ob
sie die drei zugesagten Eigenschaften haben: versioniert, prüfbar, mit Anwendungsgrenzen. Und die
eine strukturelle Zusage: eine Regel darf ein Verdikt nie auf `entailed` heben.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "msce_bridge"))

cs = pytest.importorskip("commonsense")


@pytest.mark.parametrize("rule", cs.RULES, ids=lambda r: r.id)
def test_every_rule_states_where_it_does_not_apply(rule):
    """Ohne Anwendungsgrenze keine Regel - das ist der Unterschied zu einer Faustformel."""
    assert rule.boundary.strip(), f"{rule.id} hat keine Grenze"
    assert len(rule.boundary) > 40, f"{rule.id}: Grenze zu vage"


@pytest.mark.parametrize("rule", cs.RULES, ids=lambda r: r.id)
def test_every_rule_carries_its_own_examples(rule):
    """Prüfbarkeit heisst: die Regel bringt Positiv- UND Negativfall selbst mit."""
    assert rule.applies_to, f"{rule.id} hat keinen Positivfall"
    assert rule.does_not_apply_to, f"{rule.id} hat keinen Negativfall"


@pytest.mark.parametrize("rule", cs.RULES, ids=lambda r: r.id)
def test_every_rule_names_the_measurement_that_motivated_it(rule):
    """Die Regeln stammen aus gemessenen Fehlschlaegen, nicht aus Vermutung."""
    assert rule.motivated_by.strip()


def test_a_defeasible_rule_can_never_produce_entailed():
    """Die tragende strukturelle Zusage.

    Ohne sie waere der Regelbestand ein Werkzeug, um Claims durchzuwinken - genau der Fehler,
    den die externe Blind-Evaluation an drei Faellen zugleich aufgedeckt hat."""
    app = cs.apply_rule("dependency-chain", about="A hängt von B ab")
    assert app is not None and app.defeasible is True
    assert cs.cap_verdict("entailed", [app]) == "partially_entailed"
    # schwaechere Verdikte bleiben unberuehrt
    assert cs.cap_verdict("compatible_not_entailed", [app]) == "compatible_not_entailed"
    assert cs.cap_verdict("contradicted", [app]) == "contradicted"


def test_without_any_rule_a_verdict_is_untouched():
    assert cs.cap_verdict("entailed", []) == "entailed"


def test_the_absence_rule_licenses_nothing():
    """Diese eine Regel VERBIETET einen Schluss, statt einen zu erlauben - sie ist strikt."""
    r = cs.BY_ID["absence-is-not-refutation"]
    assert r.defeasible is False
    assert "gar nichts" in r.licenses


def test_the_dependency_rule_encodes_the_DEV012_distinction():
    """DEV-011 gilt, DEV-012 nicht - der Unterschied ist, ob das Fehlende DIE vorausgesetzte
    Entitaet ist. Genau daran ging der Auditor mit 'entailed' vorbei."""
    r = cs.BY_ID["dependency-chain"]
    assert "DIESELBE Entität" in r.licenses
    assert any("C ist" in ex for ex in r.does_not_apply_to)
    assert "DEV-012" in r.motivated_by


def test_an_application_never_claims_to_upgrade():
    app = cs.apply_rule("containment-transitivity", about="Ulm/BW/Deutschland")
    assert app.to_dict()["upgrades_verdict"] is False


def test_unknown_rule_ids_yield_nothing_rather_than_a_default():
    assert cs.apply_rule("gibt-es-nicht", about="x") is None


def test_the_rulebase_is_versioned_and_fingerprinted():
    fp = cs.rulebase_fingerprint()
    assert len(fp) == 16 and fp == cs.rulebase_fingerprint()      # stabil
    assert all(r.version for r in cs.RULES)
    assert len({r.id for r in cs.RULES}) == len(cs.RULES)         # IDs eindeutig
