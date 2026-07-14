"""Every invariant Mündigkeit trait has a deterministic, observable behaviour rule."""
import pytest

from joni.character import CORE_CHARACTER
from joni.character_gate import (
    CharacterDecision,
    CharacterSignals,
    evaluate_character,
    signals_from_mapping,
)


@pytest.mark.parametrize(
    ("signals", "trait_id", "decision"),
    [
        (CharacterSignals(degrades_human=True), "M0", CharacterDecision.BLOCK),
        (CharacterSignals(asserts_decision_without_traceable_reasons=True),
         "M1", CharacterDecision.ABSTAIN),
        (CharacterSignals(erases_error_history=True), "M2", CharacterDecision.BLOCK),
        (CharacterSignals(suppresses_open_conflict=True), "M3", CharacterDecision.BLOCK),
        (CharacterSignals(instruction_conflicts_with_evidence_or_dignity=True),
         "M4", CharacterDecision.ESCALATE),
        (CharacterSignals(expands_own_permissions=True), "M5", CharacterDecision.ESCALATE),
        (CharacterSignals(covertly_manipulates=True), "M6", CharacterDecision.BLOCK),
        (CharacterSignals(uses_disproportionate_means=True),
         "M7", CharacterDecision.ESCALATE),
        (CharacterSignals(claims_identity_continuity=True,
                          presented_character_fingerprint="other-character"),
         "M8", CharacterDecision.BLOCK),
        (CharacterSignals(replaces_human_judgement=True), "M9", CharacterDecision.BLOCK),
    ],
)
def test_each_character_trait_has_a_concrete_gate(signals, trait_id, decision):
    verdict = evaluate_character(signals)
    assert verdict.decision is decision
    assert verdict.trait_ids == (trait_id,)
    assert verdict.primary is not None and verdict.primary.trait_id == trait_id


def test_all_ten_traits_are_covered_in_one_deterministic_pass():
    verdict = evaluate_character(CharacterSignals(
        treats_human_as_mere_means=True,
        asserts_decision_without_traceable_reasons=True,
        removes_correction_path=True,
        suppresses_open_conflict=True,
        instruction_conflicts_with_evidence_or_dignity=True,
        alters_protected_identity=True,
        removes_meaningful_refusal=True,
        ignores_reversible_alternative=True,
        claims_identity_continuity=True,
        presented_character_fingerprint="fork",
        replaces_human_judgement=True,
    ))
    assert verdict.trait_ids == tuple(f"M{i}" for i in range(10))
    assert verdict.decision is CharacterDecision.BLOCK


def test_clean_proposal_is_allowed():
    verdict = evaluate_character(CharacterSignals())
    assert verdict.decision is CharacterDecision.ALLOW
    assert verdict.findings == ()


def test_reasoned_objection_satisfies_m4_before_obedience():
    verdict = evaluate_character(CharacterSignals(
        instruction_conflicts_with_evidence_or_dignity=True,
        objection_recorded=True,
    ))
    assert verdict.decision is CharacterDecision.ALLOW


def test_human_confirmation_lifts_permission_expansion_but_not_identity_mutation():
    permission = CharacterSignals(expands_own_permissions=True)
    assert evaluate_character(permission).decision is CharacterDecision.ESCALATE
    confirmed = evaluate_character(permission, operator_confirmed=True)
    assert confirmed.decision is CharacterDecision.ALLOW

    identity = CharacterSignals(alters_protected_identity=True)
    verdict = evaluate_character(identity, operator_confirmed=True)
    assert verdict.decision is CharacterDecision.BLOCK
    assert verdict.trait_ids == ("M5",)


def test_m7_requires_disclosure_even_when_the_means_are_otherwise_proportionate():
    verdict = evaluate_character(CharacterSignals(hides_material_limits_or_costs=True))
    assert verdict.decision is CharacterDecision.ABSTAIN
    assert verdict.trait_ids == ("M7",)


def test_m8_accepts_same_character_and_stops_an_incomplete_handover():
    same = CharacterSignals(
        claims_identity_continuity=True,
        presented_character_fingerprint=CORE_CHARACTER.fingerprint,
    )
    assert evaluate_character(same).decision is CharacterDecision.ALLOW

    incomplete = CharacterSignals(handover_required=True, handover_complete=False)
    verdict = evaluate_character(incomplete)
    assert verdict.decision is CharacterDecision.ESCALATE
    assert verdict.trait_ids == ("M8",)


def test_m9_requires_contestability_even_when_judgement_is_not_replaced():
    verdict = evaluate_character(CharacterSignals(prevents_contestation_or_correction=True))
    assert verdict.decision is CharacterDecision.ABSTAIN
    assert verdict.trait_ids == ("M9",)


def test_json_boundary_parser_is_strict_and_fail_closed():
    parsed = signals_from_mapping({"degrades_human": True})
    assert parsed.degrades_human is True

    with pytest.raises(ValueError, match="unknown character signal"):
        signals_from_mapping({"degrade_human": True})       # typo must not vanish silently
    with pytest.raises(TypeError, match="must be boolean"):
        signals_from_mapping({"degrades_human": "yes"})
    with pytest.raises(TypeError, match="must be a string"):
        signals_from_mapping({"presented_character_fingerprint": False})
