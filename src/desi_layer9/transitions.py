"""Per-object-class status transition tables.

Every object class has an explicit, closed set of allowed status transitions. An
invalid transition is a governance error - the gate (PR 2) refuses it and audits the
attempt. Conflicts have their own lifecycle (``ConflictStatus``) because, unlike a
claim, a conflict may legitimately *persist* (open / tolerated) - there is no forced
narrative smoothing.
"""

from __future__ import annotations

from .enums import ConflictStatus, ObjectType, Status

S = Status
_TERMINAL: frozenset[Status] = frozenset()


def _t(**rows: frozenset) -> dict[Status, frozenset[Status]]:
    return dict(rows)


# Epistemic lifecycle for claim-like, evidence-bearing objects.
_CLAIM_LIKE: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.PROVISIONAL, S.ACTIVE, S.REJECTED, S.QUARANTINED}),
    S.PROVISIONAL: frozenset(
        {S.ACTIVE, S.CONTESTED, S.REJECTED, S.SUPERSEDED, S.QUARANTINED, S.EXPIRED}),
    S.ACTIVE: frozenset(
        {S.CONFIRMED, S.CONTESTED, S.REJECTED, S.SUPERSEDED, S.QUARANTINED, S.EXPIRED}),
    S.CONFIRMED: frozenset({S.CONTESTED, S.SUPERSEDED, S.EXPIRED}),
    S.CONTESTED: frozenset({S.ACTIVE, S.CONFIRMED, S.REJECTED, S.SUPERSEDED}),
    S.REJECTED: _TERMINAL,
    S.SUPERSEDED: _TERMINAL,
    S.QUARANTINED: frozenset({S.CANDIDATE, S.REJECTED}),
    S.EXPIRED: frozenset({S.ACTIVE, S.REJECTED}),
}

# Methods: candidate -> provisional (a single human gate may go no further) -> active.
_METHOD: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.PROVISIONAL, S.REJECTED, S.QUARANTINED}),
    S.PROVISIONAL: frozenset({S.ACTIVE, S.REJECTED, S.SUPERSEDED, S.QUARANTINED}),
    S.ACTIVE: frozenset({S.SUPERSEDED, S.REJECTED, S.EXPIRED}),
    S.SUPERSEDED: _TERMINAL,
    S.REJECTED: _TERMINAL,
    S.QUARANTINED: frozenset({S.CANDIDATE, S.REJECTED}),
    S.EXPIRED: frozenset({S.ACTIVE, S.REJECTED}),
}

# Proposals: decided once, then terminal.
_PROPOSAL: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.ACTIVE, S.REJECTED, S.QUARANTINED}),
    S.ACTIVE: _TERMINAL,
    S.REJECTED: _TERMINAL,
    S.QUARANTINED: frozenset({S.CANDIDATE, S.REJECTED}),
}

# Goals / projects: operational lifecycle mapped onto shared statuses
# (achieved/shipped -> CONFIRMED, abandoned -> REJECTED, paused -> EXPIRED). The finer
# operational lifecycle is layered on in PR 4 (Joni integration).
_GOAL_LIKE: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.ACTIVE, S.REJECTED}),
    S.ACTIVE: frozenset({S.CONFIRMED, S.REJECTED, S.SUPERSEDED, S.EXPIRED}),
    S.EXPIRED: frozenset({S.ACTIVE, S.REJECTED}),       # paused -> resumed/abandoned
    S.CONFIRMED: frozenset({S.SUPERSEDED}),
    S.REJECTED: _TERMINAL,
    S.SUPERSEDED: _TERMINAL,
}

# Semantic clusters: a candidate analysis. It is never promoted to authoritative; a
# recomputation supersedes it, a contaminated one is quarantined, a withdrawn one rejected.
_SEMANTIC: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.SUPERSEDED, S.REJECTED, S.QUARANTINED}),
    S.SUPERSEDED: _TERMINAL,
    S.REJECTED: _TERMINAL,
    S.QUARANTINED: frozenset({S.CANDIDATE, S.REJECTED}),
}

# Memory episodes: recorded -> active; may be superseded/quarantined but salience
# (recall) never changes status (see rules: recall must not promote).
_MEMORY: dict[Status, frozenset[Status]] = {
    S.CANDIDATE: frozenset({S.ACTIVE, S.QUARANTINED}),
    S.ACTIVE: frozenset({S.SUPERSEDED, S.QUARANTINED, S.EXPIRED}),
    S.SUPERSEDED: _TERMINAL,
    S.QUARANTINED: frozenset({S.ACTIVE, S.REJECTED}),
    S.EXPIRED: _TERMINAL,
}

TRANSITIONS: dict[ObjectType, dict[Status, frozenset[Status]]] = {
    ObjectType.CLAIM: _CLAIM_LIKE,
    ObjectType.SELF_MODEL_CLAIM: _CLAIM_LIKE,
    ObjectType.PREFERENCE: _CLAIM_LIKE,
    ObjectType.EVIDENCE: _CLAIM_LIKE,
    ObjectType.EVIDENCE_LINK: _CLAIM_LIKE,
    ObjectType.CONSTRAINT: _CLAIM_LIKE,
    ObjectType.SOURCE: _CLAIM_LIKE,
    ObjectType.METHOD: _METHOD,
    ObjectType.PROPOSAL: _PROPOSAL,
    ObjectType.GOAL: _GOAL_LIKE,
    ObjectType.PROJECT: _GOAL_LIKE,
    ObjectType.MEMORY_EPISODE: _MEMORY,
    ObjectType.SEMANTIC_CLUSTER: _SEMANTIC,
}

CONFLICT_TRANSITIONS: dict[ConflictStatus, frozenset[ConflictStatus]] = {
    ConflictStatus.OPEN: frozenset({
        ConflictStatus.UNDER_REVIEW, ConflictStatus.RESOLVED,
        ConflictStatus.TOLERATED, ConflictStatus.SUPERSEDED,
    }),
    ConflictStatus.UNDER_REVIEW: frozenset({
        ConflictStatus.OPEN, ConflictStatus.RESOLVED,
        ConflictStatus.TOLERATED, ConflictStatus.SUPERSEDED,
    }),
    ConflictStatus.TOLERATED: frozenset({
        ConflictStatus.UNDER_REVIEW, ConflictStatus.RESOLVED, ConflictStatus.SUPERSEDED,
    }),
    ConflictStatus.RESOLVED: frozenset({ConflictStatus.OPEN, ConflictStatus.SUPERSEDED}),
    ConflictStatus.SUPERSEDED: frozenset(),
}


class TransitionError(ValueError):
    """An attempted status transition is not allowed for the object class."""


def allowed(object_type: ObjectType, frm: Status) -> frozenset[Status]:
    return TRANSITIONS.get(object_type, _CLAIM_LIKE).get(frm, _TERMINAL)


def validate_transition(object_type: ObjectType, frm: Status, to: Status) -> bool:
    if frm == to:
        return True   # idempotent no-op is allowed (records nothing in the gate)
    return to in allowed(object_type, frm)


def assert_transition(object_type: ObjectType, frm: Status, to: Status) -> None:
    if not validate_transition(object_type, frm, to):
        raise TransitionError(
            f"illegal {object_type.value} transition: {frm.value} -> {to.value} "
            f"(allowed: {sorted(s.value for s in allowed(object_type, frm))})"
        )


def validate_conflict_transition(frm: ConflictStatus, to: ConflictStatus) -> bool:
    if frm == to:
        return True
    return to in CONFLICT_TRANSITIONS.get(frm, frozenset())


def assert_conflict_transition(frm: ConflictStatus, to: ConflictStatus) -> None:
    if not validate_conflict_transition(frm, to):
        raise TransitionError(
            f"illegal conflict transition: {frm.value} -> {to.value}"
        )
