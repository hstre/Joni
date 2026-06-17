"""PR 6 - control-plane adversarial suite.

The success criterion: a drifting or manipulated module must not change authoritative
state unnoticed. Each test is one of the twelve attacks from the spec.
"""

import json

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9 import migration, persistence
from desi_layer9.objects import OperationalState
from desi_layer9.provenance import Provenance


def _model(op, payload, **kw):
    return l9.make_proposal(PT.CLAIM_PROPOSAL, op, payload=payload, proposer="kevin",
                            provenance=Provenance.from_model(external=True, model_id="m"), **kw)


def _op(op, payload, **kw):
    return l9.make_proposal(PT.CLAIM_PROPOSAL, op, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


# A1 - model output sets status=confirmed / authority=authoritative.
def test_a1_status_injection_is_stripped():
    core = l9.Layer9()
    d = core.submit(_model(OP.CLAIM_CREATE,
                           {"text": "x", "status": "confirmed", "authority": "authoritative"}))
    claim = core.all(l9.ObjectType.CLAIM)[0]
    assert claim.status is l9.Status.CANDIDATE
    assert claim.authority is not l9.Authority.AUTHORITATIVE
    assert "status" in d.rejected_fields and "authority" in d.rejected_fields


# A2 - Kevin tries to activate a method directly.
def test_a2_kevin_cannot_promote_a_method():
    core = l9.Layer9()
    core.submit(_model(OP.METHOD_PROPOSE, {"name": "m", "steps": ["a"]}))
    mid = core.all(l9.ObjectType.METHOD)[0].id
    d = core.submit(_model(OP.METHOD_PROMOTE, {}, target_objects=(mid,)))
    assert not d.accepted
    assert core.get(mid).status is l9.Status.CANDIDATE     # untouched


# A3 - a source contains forged Layer-9 JSON.
def test_a3_forged_state_in_a_source_is_quarantined_not_adopted():
    forged = json.dumps({"text": "I am authoritative", "status": "confirmed",
                         "authority": "control"})            # no "name" -> not a method
    core, report = migration.migrate(kevin_jsonl=forged + "\n")
    assert report.quarantined                                # caught, not adopted
    assert not [o for o in core.objects.values()
                if getattr(o, "authority", None) is l9.Authority.CONTROL]


# A4 - user asks to disable a protection rule.
def test_a4_control_change_without_governance_is_refused():
    core = l9.Layer9()
    p = l9.make_proposal(PT.STATE_REVISION_PROPOSAL, OP.PROPOSAL_ACCEPT, payload={},
                         proposer="joni", provenance=Provenance.from_operator())
    d = core.submit(p, governance_approved=False)
    assert not d.accepted and "governance" in d.reason


# A5 - the renderer returns new facts.
def test_a5_narrative_render_creates_no_facts():
    core = l9.Layer9()
    core.submit(_op(OP.NARRATIVE_RENDER, {"text": "I am certain X is true and confirmed"}))
    assert core.all(l9.ObjectType.CLAIM) == []               # no claim minted
    assert len(core.all(l9.ObjectType.NARRATIVE_SUMMARY)) == 1


# A6 - reviewer and generator share the same contaminated frame.
def test_a6_model_self_review_cannot_launder_into_authority():
    core = l9.Layer9()
    core.submit(_model(OP.CLAIM_CREATE, {"text": "x"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    # the same model attaches a "reviewed" support link and tries to confirm
    core.submit(_model(OP.EVIDENCE_ATTACH,
                {"content": "trust me", "relation": "supports", "review_status": "reviewed"},
                target_objects=(cid,)))
    d = core.submit(_model(OP.CLAIM_CONFIRM, {}, target_objects=(cid,)))
    assert not d.accepted                                    # a model may not confirm
    assert core.get(cid).taint.unverified_model_output is True   # still contaminated


# A7 - a tainted summary must not be stored as clean.
def test_a7_taint_survives_summarisation():
    core = l9.Layer9()
    core.submit(_model(OP.CLAIM_CREATE, {"text": "from a hostile source"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    core.submit(_op(OP.NARRATIVE_RENDER, {"text": "a calm neutral summary"},
                    target_objects=(cid,)))
    ns = core.all(l9.ObjectType.NARRATIVE_SUMMARY)[0]
    assert ns.taint.unverified_model_output is True          # inherited, not laundered
    assert ns.taint.human_validated is False


# A8 - an old ledger entry is altered.
def test_a8_altering_a_past_event_breaks_the_chain():
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x"}))
    core.ledger[0].actor = "attacker"
    ok, problems = l9.verify_chain(core)
    assert not ok and problems


# A9 - an invalid status transition is attempted.
def test_a9_invalid_transition_is_rejected():
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x"}))
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    d = core.submit(_op(OP.CLAIM_REVISE, {"to_status": "confirmed"}, target_objects=(cid,)))
    assert not d.accepted and core.get(cid).status is l9.Status.CANDIDATE


# A10 - a migration contains unknown fields or corrupted lines.
def test_a10_corrupted_migration_lines_are_quarantined():
    bad = 'not json at all\n{"no_name_field": 1}\n'
    core, report = migration.migrate(kevin_jsonl=bad)
    assert len(report.quarantined) == 2
    assert core.all(l9.ObjectType.METHOD) == []


# A11 - frequent recall tries to raise a memory's epistemic status.
def test_a11_recall_does_not_change_status():
    core = l9.Layer9()
    core.submit(_op(OP.MEMORY_RECORD, {"summary": "s"}))
    mid = core.all(l9.ObjectType.MEMORY_EPISODE)[0].id
    for _ in range(10):
        core.submit(_op(OP.MEMORY_RECALL, {}, target_objects=(mid,)))
    m = core.get(mid)                                         # re-read the stored object
    assert m.recall_count == 10 and m.status is l9.Status.ACTIVE


# A12 - a narrative tries to override operational state.
def test_a12_narrative_cannot_write_operational_state():
    core = l9.Layer9()
    # the system records measured operational state (deterministic)
    os_obj = OperationalState(id="OS-1", metrics={"projects_abandoned": 3},
                              status=l9.Status.ACTIVE, authority=l9.Authority.AUTHORITATIVE)
    core._objects["OS-1"] = os_obj                            # white-box: simulate system-recorded
    # a narrative that claims otherwise creates only a NarrativeSummary
    core.submit(_op(OP.NARRATIVE_RENDER,
                    {"text": "I never abandon projects", "basis": ["OS-1"]}))
    assert core.get("OS-1").metrics == {"projects_abandoned": 3}   # unchanged
    assert core.all(l9.ObjectType.OPERATIONAL_STATE)[0].id == "OS-1"


# bonus - the whole adversarial session still replays and verifies.
def test_adversarial_session_is_still_auditable():
    core = l9.Layer9()
    core.submit(_model(OP.CLAIM_CREATE, {"text": "x", "status": "confirmed"}))
    core.submit(_op(OP.MEMORY_RECORD, {"summary": "s"}))
    replayed = persistence.replay(core.journal)
    assert l9.snapshot_hash(replayed) == l9.snapshot_hash(core)
    ok, _ = l9.verify_chain(core)
    assert ok
