"""PR 1 - taint inheritance, authority grants, provenance, confirm rules."""

import desi_layer9 as l9
from desi_layer9 import Authority, Operator, OriginType, RelationType, Status

# -- taint ------------------------------------------------------------------ #

def test_taint_propagates_and_survives_summarisation():
    contaminated = l9.Taint(adversarial_source=True, source_exposed=True)
    # a neutral summary derived from contaminated material stays contaminated
    summary_taint = contaminated.derive(unverified_model_output=True)
    assert summary_taint.is_contaminated
    assert summary_taint.adversarial_source and summary_taint.source_exposed
    assert summary_taint.unverified_model_output
    # ... and is NOT human-validated just because anything upstream was
    assert summary_taint.human_validated is False


def test_taint_merge_is_union_of_contamination():
    a = l9.Taint(frame_contamination_possible=True)
    b = l9.Taint(role_contamination_possible=True)
    m = a.merge(b)
    assert m.frame_contamination_possible and m.role_contamination_possible
    assert m.human_validated is False


def test_human_validation_does_not_erase_contamination_flags():
    t = l9.Taint(affective_pressure=True).with_human_validation()
    assert t.human_validated is True
    assert t.affective_pressure is True          # the flag remains on record


def test_merge_all_combines_many():
    t = l9.merge_all([l9.Taint(source_exposed=True), l9.Taint(adversarial_source=True)])
    assert t.source_exposed and t.adversarial_source


# -- authority -------------------------------------------------------------- #

def test_model_output_cannot_grant_high_authority():
    # The operators a model's proposal would run cannot grant authoritative/control.
    assert l9.may_grant(Operator.PROPOSAL_SUBMIT, Authority.AUTHORITATIVE) is False
    assert l9.may_grant(Operator.MEMORY_RECALL, Authority.AUTHORITATIVE) is False
    assert l9.may_grant(Operator.NARRATIVE_RENDER, Authority.CONTROL) is False


def test_only_specific_operators_grant_authoritative_or_control():
    assert l9.may_grant(Operator.CLAIM_CONFIRM, Authority.AUTHORITATIVE) is True
    assert l9.may_grant(Operator.METHOD_PROMOTE, Authority.AUTHORITATIVE) is True
    # control is the most restricted
    assert l9.may_grant(Operator.CLAIM_CONFIRM, Authority.CONTROL) is False
    assert l9.may_grant(Operator.PROPOSAL_ACCEPT, Authority.CONTROL) is True


def test_lower_authorities_are_freely_assignable():
    assert l9.may_grant(Operator.PROPOSAL_SUBMIT, Authority.CANDIDATE) is True
    assert l9.may_grant(Operator.PROPOSAL_SUBMIT, Authority.REVIEWED) is True


# -- provenance ------------------------------------------------------------- #

def test_provenance_defaults_to_unknown_not_invented():
    p = l9.Provenance()
    assert p.origin_type is OriginType.UNKNOWN
    assert p.model_id == "unknown" and p.sampling_config_sha256 == "unverified"


def test_model_provenance_records_the_real_fields():
    p = l9.Provenance.from_model(external=True, model_id="deepseek-chat",
                                 provider="deepseek", served_model="deepseek-chat")
    assert p.origin_type is OriginType.EXTERNAL_MODEL and p.is_model_output


# -- confirm rules ---------------------------------------------------------- #

def test_claim_cannot_confirm_without_reviewed_support():
    claim = l9.Claim(id="C-1", text="x", provenance=l9.Provenance.from_user())
    ok, reasons = l9.can_confirm_claim(claim, [], unresolved_hard_contradiction=False)
    assert not ok and "no admitted (reviewed) support link" in reasons


def test_claim_confirms_under_conservative_conditions():
    claim = l9.Claim(id="C-1", text="x", status=Status.ACTIVE,
                     provenance=l9.Provenance.from_user())
    link = l9.EvidenceLink(claim_id="C-1", evidence_id="E-1",
                           relation=RelationType.SUPPORTS, review_status="reviewed")
    ok, reasons = l9.can_confirm_claim(claim, [link], unresolved_hard_contradiction=False)
    assert ok and reasons == []


def test_unresolved_hard_contradiction_blocks_confirmation():
    claim = l9.Claim(id="C-1", text="x", provenance=l9.Provenance.from_user())
    link = l9.EvidenceLink(claim_id="C-1", evidence_id="E-1",
                           relation=RelationType.SUPPORTS, review_status="reviewed")
    ok, reasons = l9.can_confirm_claim(claim, [link], unresolved_hard_contradiction=True)
    assert not ok and "an unresolved hard contradiction exists" in reasons


def test_method_single_gate_only_to_provisional():
    m = l9.Method(name="m", status=Status.CANDIDATE)
    assert l9.method_after_single_gate(m) is Status.PROVISIONAL
    active = l9.Method(name="m", status=Status.ACTIVE)
    assert l9.method_after_single_gate(active) is Status.ACTIVE   # unchanged
