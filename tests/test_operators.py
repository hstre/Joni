import pytest

from joni.models import ClaimStatus, Operator, Trigger
from joni.operators import (
    assert_claim,
    open_conflict,
    resolve_conflict,
    revise_opinion,
)
from joni.state import Layer9


def test_assert_claim_audits_from_birth():
    s = Layer9()
    c = assert_claim(s, "local-first keeps data private", "privacy", support=0.5)
    assert c.id == "C-1"
    assert s.claims["C-1"].status is ClaimStatus.TENTATIVE
    # one ledger event + one memory episode
    assert any(e.operator is Operator.CLAIM_ASSERT and "C-1" in e.refs for e in s.ledger)
    assert any(ep.refs and "C-1" in ep.refs for ep in s.memory)


def test_revise_opinion_records_transition_and_history():
    s = Layer9()
    c = assert_claim(s, "x", "t", status=ClaimStatus.ACTIVE)
    transition, event = revise_opinion(
        s, c.id, ClaimStatus.REJECTED, trigger=Trigger.SELF_REVIEW
    )
    assert s.claims[c.id].status is ClaimStatus.REJECTED
    assert transition.from_status is ClaimStatus.ACTIVE
    assert transition.to_status is ClaimStatus.REJECTED
    assert transition.ledger_id == event.id
    assert s.claims[c.id].history[-1] is transition
    # a "changed_mind" episode was recorded
    assert any(ep.kind == "changed_mind" for ep in s.memory)


def test_no_op_revision_is_rejected():
    s = Layer9()
    c = assert_claim(s, "x", "t", status=ClaimStatus.ACTIVE)
    with pytest.raises(ValueError):
        revise_opinion(s, c.id, ClaimStatus.ACTIVE, trigger=Trigger.SELF_REVIEW)


def test_resolve_conflict_reproduces_the_worked_example_fields():
    """The 'I have since abandoned this idea' trace, field for field."""
    s = Layer9()
    keep = assert_claim(s, "audit ledgers prevent drift", "drift", status=ClaimStatus.ACTIVE)
    drop = assert_claim(s, "drift needs no ledger", "drift", status=ClaimStatus.ACTIVE)
    x = open_conflict(s, keep.id, drop.id, "negation")

    transition, event = resolve_conflict(s, x.id, reject=drop.id, reviewed_by="granite-micro")

    assert s.conflicts[x.id].resolved is True
    assert s.claims[drop.id].status is ClaimStatus.REJECTED
    assert transition.from_status is ClaimStatus.ACTIVE
    assert transition.to_status is ClaimStatus.REJECTED
    assert transition.trigger is Trigger.CONTRADICTORY_EVIDENCE
    assert transition.operator is Operator.CONFLICT_RESOLUTION
    assert transition.reviewed_by == "granite-micro"
    assert transition.ledger_id == event.id
    assert event.reviewed_by == "granite-micro"


def test_ledger_ids_are_sequential_and_replay_stable():
    s = Layer9()
    assert_claim(s, "a", "t")
    assert_claim(s, "b", "t")
    ledger_ids = [e.id for e in s.ledger]
    assert ledger_ids == sorted(ledger_ids, key=lambda x: int(x.split("-")[1]))
    assert ledger_ids[0] == "L9-1"
