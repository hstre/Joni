"""PR 1 - status transition tables (valid and invalid)."""

import pytest

import desi_layer9 as l9
from desi_layer9 import ConflictStatus as CS
from desi_layer9 import ObjectType as OT
from desi_layer9 import Status as S


def test_valid_claim_lifecycle():
    assert l9.validate_transition(OT.CLAIM, S.CANDIDATE, S.ACTIVE)
    assert l9.validate_transition(OT.CLAIM, S.ACTIVE, S.CONFIRMED)
    assert l9.validate_transition(OT.CLAIM, S.ACTIVE, S.CONTESTED)


def test_invalid_claim_transitions_raise():
    # candidate cannot jump straight to confirmed
    with pytest.raises(l9.TransitionError):
        l9.assert_transition(OT.CLAIM, S.CANDIDATE, S.CONFIRMED)
    # rejected is terminal
    with pytest.raises(l9.TransitionError):
        l9.assert_transition(OT.CLAIM, S.REJECTED, S.ACTIVE)


def test_method_single_gate_only_reaches_provisional():
    # the table allows candidate->provisional but NOT candidate->active
    assert l9.validate_transition(OT.METHOD, S.CANDIDATE, S.PROVISIONAL)
    assert not l9.validate_transition(OT.METHOD, S.CANDIDATE, S.ACTIVE)
    # provisional -> active is allowed (after trials/review, enforced by the gate)
    assert l9.validate_transition(OT.METHOD, S.PROVISIONAL, S.ACTIVE)


def test_idempotent_noop_is_allowed():
    assert l9.validate_transition(OT.CLAIM, S.ACTIVE, S.ACTIVE)


def test_conflicts_can_persist_open_or_tolerated():
    # An open conflict need never be resolved: open->tolerated is allowed, and
    # tolerated is not forced anywhere.
    assert l9.validate_conflict_transition(CS.OPEN, CS.TOLERATED)
    assert l9.validate_conflict_transition(CS.OPEN, CS.UNDER_REVIEW)
    # resolved can reopen on new evidence
    assert l9.validate_conflict_transition(CS.RESOLVED, CS.OPEN)
    # superseded is terminal
    with pytest.raises(l9.TransitionError):
        l9.assert_conflict_transition(CS.SUPERSEDED, CS.OPEN)


def test_every_object_class_has_a_transition_table_or_default():
    for ot in OT:
        # claim-like default applies where no explicit table exists; never crashes
        assert isinstance(l9.allowed(ot, S.CANDIDATE), frozenset)
