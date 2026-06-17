"""Governance-core hardening (full-review fixes). Each test asserts a documented Layer-9 invariant
that the code did NOT actually enforce before:

  1. operational state is written THROUGH the gate (was a direct, ungated core.objects write),
  2. taint actually BLOCKS promotion to authoritative - HUMAN_VALIDATE is the only override,
  3. sampling_provenance is covered by the chain hash (was forgeable without breaking the chain),
  4. repair() refuses a broken chain instead of re-blessing it.
"""

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9.enums import Authority, Status
from desi_layer9.provenance import Provenance


def _model(operator, payload, ptype=PT.METHOD_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="kevin",
                            provenance=Provenance.from_model(external=True,
                                                             model_id="deepseek-v4-pro"), **kw)


def _op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


# -- Fix 1: operational state goes through the gate ------------------------- #
def test_operational_state_is_gated_not_a_bypass():
    core = l9.Layer9()
    d = core.submit(_op(OP.OPERATIONAL_STATE, {"metrics": {"x": 1}}))
    assert d.accepted
    os_ = core.all(l9.ObjectType.OPERATIONAL_STATE)[-1]
    assert os_.authority is Authority.AUTHORITATIVE
    assert os_.ledger_event and os_.ledger_event.startswith("L9-")   # ledger event -> replayable
    # a MODEL may NOT write operational state (it grants authority)
    assert not core.submit(_model(OP.OPERATIONAL_STATE, {"metrics": {"x": 2}})).accepted


# -- Fix 2: taint blocks promotion; HUMAN_VALIDATE is the only override ------ #
def _provisional_tainted_method(core):
    core.submit(_model(OP.METHOD_PROPOSE, {"name": "m", "summary": "s", "applicable_to": ["x"]}))
    m = core.all(l9.ObjectType.METHOD)[-1]
    assert m.taint.is_contaminated and not m.taint.human_validated      # model output -> tainted
    core.submit(_op(OP.METHOD_PROMOTE, {}, ptype=PT.METHOD_PROPOSAL, target_objects=(m.id,)))
    for i in range(3):
        core.submit(_op(OP.METHOD_TRIAL_RECORD, {"success": True, "run_id": f"r{i}"},
                        ptype=PT.METHOD_PROPOSAL, target_objects=(m.id,)))
    return m


def test_contaminated_method_cannot_be_activated_without_human_validation():
    core = l9.Layer9()
    m = _provisional_tainted_method(core)
    d = core.submit(_op(OP.METHOD_PROMOTE, {}, ptype=PT.METHOD_PROPOSAL, target_objects=(m.id,)))
    assert not d.accepted                                # blocked: contaminated, not validated
    assert core.objects[m.id].status is Status.PROVISIONAL
    # a human validates it explicitly -> now it may activate (the flag stays on record)
    assert core.submit(_op(OP.HUMAN_VALIDATE, {}, target_objects=(m.id,))).accepted
    assert core.objects[m.id].taint.human_validated and core.objects[m.id].taint.is_contaminated
    d2 = core.submit(_op(OP.METHOD_PROMOTE, {}, ptype=PT.METHOD_PROPOSAL, target_objects=(m.id,)))
    assert d2.accepted and core.objects[m.id].status is Status.ACTIVE


def test_a_model_cannot_human_validate():
    core = l9.Layer9()
    m = _provisional_tainted_method(core)
    assert not core.submit(_model(OP.HUMAN_VALIDATE, {}, target_objects=(m.id,))).accepted


def test_contaminated_claim_cannot_be_confirmed_until_validated():
    link = l9.EvidenceLink(claim_id="C-1", evidence_id="E-1",
                           relation=l9.RelationType.SUPPORTS, review_status="reviewed")
    tainted = l9.Claim(id="C-1", text="x", status=Status.ACTIVE,
                       provenance=Provenance.from_user(),
                       taint=l9.Taint(unverified_model_output=True))
    ok, reasons = l9.can_confirm_claim(tainted, [link], unresolved_hard_contradiction=False)
    assert not ok and any("contaminated" in r for r in reasons)
    validated = l9.Claim(id="C-1", text="x", status=Status.ACTIVE,
                         provenance=Provenance.from_user(),
                         taint=l9.Taint(unverified_model_output=True).with_human_validation())
    ok2, _ = l9.can_confirm_claim(validated, [link], unresolved_hard_contradiction=False)
    assert ok2


# -- Fix 3: sampling_provenance is tamper-evident in the chain -------------- #
def test_sampling_provenance_is_covered_by_the_chain_hash():
    from desi_layer9.hashing import event_canonical, verify_chain
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x"}, ptype=PT.CLAIM_PROPOSAL))
    ev = core._ledger[-1]                                           # white-box: the stored event
    before = event_canonical(ev)
    ev.sampling_provenance = {"model": "forged", "temperature": 9}   # forge the provenance
    assert event_canonical(ev) != before                            # it IS in the canonical form
    ok, problems = verify_chain(core)
    assert not ok and problems                                      # tampering breaks the chain


# -- Fix 4: repair refuses a broken chain instead of re-blessing it --------- #
def test_repair_is_a_noop_on_a_clean_state(tmp_path):
    from desi_layer9 import persistence
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x"}, ptype=PT.CLAIM_PROPOSAL))
    p = tmp_path / "s.json"
    persistence.save(core, p)
    assert persistence.repair(p) is False                          # clean -> nothing to repair


def test_repair_refuses_a_broken_chain(tmp_path, monkeypatch):
    import pytest

    from desi_layer9 import persistence
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x"}, ptype=PT.CLAIM_PROPOSAL))
    p = tmp_path / "s.json"
    persistence.save(core, p)
    # force the load to fail AND the chain to look broken: repair must hard-stop, not re-seal.
    monkeypatch.setattr(persistence, "from_doc",
                        lambda doc, verify=True: (_ for _ in ()).throw(ValueError("x"))
                        if verify else core)
    monkeypatch.setattr(persistence, "verify_chain", lambda s: (False, ["tampered"]))
    with pytest.raises(ValueError, match="refusing to repair"):
        persistence.repair(p)
