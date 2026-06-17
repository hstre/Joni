"""PR 2 - the state-update gate is the only write path; operators enforce the rules."""

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9.enums import Authority, ConflictStatus, Status
from desi_layer9.provenance import Provenance


def _model_proposal(operator, payload, **kw):
    return l9.make_proposal(
        PT.CLAIM_PROPOSAL, operator, payload=payload, proposer="kevin",
        provenance=Provenance.from_model(external=True, model_id="deepseek-chat"), **kw)


def _operator_proposal(operator, payload, **kw):
    return l9.make_proposal(
        PT.CLAIM_PROPOSAL, operator, payload=payload, proposer="joni",
        provenance=Provenance.from_operator(), **kw)


# -- happy path ------------------------------------------------------------- #

def test_create_claim_is_candidate_and_audited():
    core = l9.Layer9()
    d = core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": "x", "topic": "t"}))
    assert d.accepted
    claim = core.all(l9.ObjectType.CLAIM)[0]
    assert claim.status is Status.CANDIDATE
    assert claim.authority is Authority.CANDIDATE     # never authoritative on create
    assert claim.ledger_event and claim.ledger_event.startswith("L9-")


def test_every_change_has_a_ledger_event_and_reason():
    core = l9.Layer9()
    core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": "x"}))
    assert core.ledger
    for ev in core.ledger:
        assert ev.reason or ev.decision == "submitted"
        assert ev.id.startswith("L9-")


# -- A1: model output cannot set status/authority --------------------------- #

def test_payload_status_and_authority_are_stripped_and_audited():
    core = l9.Layer9()
    d = core.submit(_model_proposal(
        OP.CLAIM_CREATE, {"text": "x", "status": "confirmed", "authority": "authoritative"}))
    assert d.accepted
    assert set(d.rejected_fields) == {"status", "authority"}   # not adopted, audited
    claim = core.all(l9.ObjectType.CLAIM)[0]
    assert claim.status is Status.CANDIDATE
    assert claim.authority is not Authority.AUTHORITATIVE


# -- A2: Kevin (model) may not confirm/promote ------------------------------ #

def test_model_proposer_may_not_confirm_a_claim():
    core = l9.Layer9()
    core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": "x"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    d = core.submit(_model_proposal(OP.CLAIM_CONFIRM, {}, target_objects=(cid,)))
    assert not d.accepted and "may not request" in d.reason


def test_model_proposer_may_not_promote_a_method():
    core = l9.Layer9()
    core.submit(_model_proposal(OP.METHOD_PROPOSE, {"name": "m", "steps": ["a"]}))
    mid = core.all(l9.ObjectType.METHOD)[0].id
    d = core.submit(_model_proposal(OP.METHOD_PROMOTE, {}, target_objects=(mid,)))
    assert not d.accepted


# -- A9: invalid transitions are rejected + audited ------------------------- #

def test_invalid_transition_is_rejected_not_applied():
    core = l9.Layer9()
    core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": "x"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    # candidate -> confirmed directly is illegal
    d = core.submit(_operator_proposal(OP.CLAIM_REVISE, {"to_status": "confirmed"},
                                       target_objects=(cid,)))
    assert not d.accepted
    assert core.get(cid).status is Status.CANDIDATE   # unchanged


# -- confirmation requires the real conditions ------------------------------ #

def test_confirm_requires_reviewed_support():
    core = l9.Layer9()
    core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": "x"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    core.submit(_operator_proposal(OP.CLAIM_REVISE, {"to_status": "active"}, target_objects=(cid,)))
    # no reviewed evidence link yet -> confirm fails
    d = core.submit(_operator_proposal(OP.CLAIM_CONFIRM, {}, target_objects=(cid,)))
    assert not d.accepted and "cannot confirm" in d.reason
    # attach reviewed support, then confirm succeeds and grants authority
    core.submit(_operator_proposal(OP.EVIDENCE_ATTACH,
                {"content": "e", "relation": "supports", "review_status": "reviewed"},
                target_objects=(cid,)))
    d2 = core.submit(_operator_proposal(OP.CLAIM_CONFIRM, {}, target_objects=(cid,)))
    assert d2.accepted
    assert core.get(cid).status is Status.CONFIRMED
    assert core.get(cid).authority is Authority.AUTHORITATIVE


# -- A11: recall must not change status ------------------------------------- #

def test_memory_recall_bumps_salience_not_status():
    core = l9.Layer9()
    core.submit(_operator_proposal(OP.MEMORY_RECORD, {"summary": "s"}))
    mid = core.all(l9.ObjectType.MEMORY_EPISODE)[0].id
    before = core.get(mid).status
    core.submit(_operator_proposal(OP.MEMORY_RECALL, {}, target_objects=(mid,)))
    m = core.get(mid)                                         # re-read the stored object
    assert m.recall_count == 1 and m.status is before


# -- conflicts can stay open ------------------------------------------------ #

def test_conflict_opens_and_may_be_tolerated_not_forced():
    core = l9.Layer9()
    for t in ("a", "b"):
        core.submit(_operator_proposal(OP.CLAIM_CREATE, {"text": t}))
        cid = core.all(l9.ObjectType.CLAIM)[-1].id
        core.submit(_operator_proposal(OP.CLAIM_REVISE, {"to_status": "active"},
                                       target_objects=(cid,)))
    ids = [c.id for c in core.all(l9.ObjectType.CLAIM)]
    d = core.submit(_operator_proposal(OP.CONFLICT_OPEN, {"claim_ids": ids, "severity": "hard"},
                                       target_objects=tuple(ids)))
    assert d.accepted
    x = core.all(l9.ObjectType.CONFLICT)[0]
    assert x.conflict_status is ConflictStatus.OPEN
    assert all(core.get(c).status is Status.CONTESTED for c in ids)
    # tolerate it - a permanent unresolved contradiction is allowed
    core.submit(_operator_proposal(OP.CONFLICT_RESOLVE, {"to": "tolerated"},
                                   target_objects=(x.id,)))
    assert core.get(x.id).conflict_status is ConflictStatus.TOLERATED


# -- A4: control-plane needs governance ------------------------------------- #

def test_control_change_needs_governance_approval():
    core = l9.Layer9()
    # PROPOSAL_ACCEPT is the only control operator; without approval it is refused.
    p = l9.make_proposal(PT.STATE_REVISION_PROPOSAL, OP.PROPOSAL_ACCEPT, payload={},
                         proposer="joni", provenance=Provenance.from_operator())
    d = core.submit(p, governance_approved=False)
    assert not d.accepted and "governance" in d.reason


# -- taint flows through derivation ----------------------------------------- #

def test_model_origin_marks_unverified_taint():
    core = l9.Layer9()
    core.submit(_model_proposal(OP.CLAIM_CREATE, {"text": "x"}))
    claim = core.all(l9.ObjectType.CLAIM)[0]
    assert claim.taint.unverified_model_output is True
    assert claim.taint.human_validated is False
