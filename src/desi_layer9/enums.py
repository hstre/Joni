"""Closed enumerations for Layer 9.

Layer 9 is the *authoritative epistemic state* shared by Joni (operative identity) and
Kevin (creativity module). Everything here is a frozen, closed enumeration - no
open-world category invention. The whole point of Layer 9 is that authority, status,
provenance and taint are typed and machine-checkable, never free text a model can fake.
"""

from __future__ import annotations

from enum import StrEnum


class ObjectType(StrEnum):
    """The closed set of epistemic object classes Layer 9 governs."""

    CLAIM = "claim"
    EVIDENCE = "evidence"
    EVIDENCE_LINK = "evidence_link"
    CONSTRAINT = "constraint"
    GOAL = "goal"
    PREFERENCE = "preference"
    PROJECT = "project"
    METHOD = "method"
    MEMORY_EPISODE = "memory_episode"
    CONFLICT = "conflict"
    DECISION = "decision"
    PROPOSAL = "proposal"
    REVIEW = "review"
    SOURCE = "source"
    LEDGER_EVENT = "ledger_event"
    OPERATIONAL_STATE = "operational_state"
    SELF_MODEL_CLAIM = "self_model_claim"
    NARRATIVE_SUMMARY = "narrative_summary"
    SEMANTIC_CLUSTER = "semantic_cluster"


class SemanticState(StrEnum):
    """The auditable lifecycle of a semantic cluster proposal.

    Meaning equivalence is decided *here*, in Layer 9, never inside Joni or Kevin. A
    cluster climbs these stages only as it passes deterministic checks; a model is asked
    only for genuine boundary cases, and a human for the rest. Only ``SYNTHESIS_ELIGIBLE``
    clusters may feed a Joni synthesis or a Kevin method.
    """

    LEXICAL_CANDIDATE = "lexical-candidate"        # cheap recurrence found the members
    SEMANTIC_MEASURED = "semantic-measured"        # the DESi Semantic Layer has run
    SYNTHESIS_ELIGIBLE = "synthesis-eligible"      # may become a synthesis/method
    SYNTHESIS_REJECTED = "synthesis-rejected"      # not the same concept / contradictory
    HUMAN_REVIEW_REQUIRED = "human-review-required"  # borderline; a human must decide
    INSUFFICIENT_EVIDENCE = "insufficient-semantic-evidence"  # layer absent/invalid output


class SemanticDecision(StrEnum):
    """The governed relationship Layer 9 reads out of the DESi Semantic Layer's measures.

    The *measurement* (frames, Π-distance, √JSD, logical audit, frame tension, EN signal)
    comes from DESi; the *classification* into one of these is Layer 9's governed decision.
    Joni never assigns these itself.
    """

    DUPLICATE = "duplicate"                # same claim, semantically
    SUPPORTS = "supports"                  # one backs the other
    COMPLEMENTARY = "complementary"        # related, add up to more (synthesis candidate)
    TENSION = "tension"                    # in semantic tension (EN may apply)
    CONTRADICTORY = "contradictory"        # logically opposed
    UNRELATED = "unrelated"                # shared words, different concepts
    INSUFFICIENT = "insufficient-semantic-evidence"  # the layer could not decide


class Status(StrEnum):
    """The closed lifecycle an epistemic object can be in.

    Not every status is valid for every object class - see ``transitions.py`` for the
    per-class transition tables.
    """

    CANDIDATE = "candidate"        # freshly proposed, untrusted
    PROVISIONAL = "provisional"    # accepted for use, not yet confirmed
    ACTIVE = "active"              # in force
    CONFIRMED = "confirmed"        # corroborated under the confirm conditions
    CONTESTED = "contested"        # an open conflict touches it
    REJECTED = "rejected"          # given up
    SUPERSEDED = "superseded"      # replaced by a newer object/version
    QUARANTINED = "quarantined"    # untrusted/contaminated; held out of use
    EXPIRED = "expired"            # past its validity window


class Authority(StrEnum):
    """How much weight an object's content may be given.

    Only Layer-9 operators may grant ``AUTHORITATIVE`` or ``CONTROL`` (see
    ``OPERATORS_GRANTING_AUTHORITATIVE`` / ``OPERATORS_GRANTING_CONTROL``). A model may
    *write* ``authority: authoritative`` in its output; that field is never adopted.
    """

    UNTRUSTED = "untrusted"        # raw model/source output
    CANDIDATE = "candidate"        # a structured proposal
    REVIEWED = "reviewed"          # passed an independent review
    AUTHORITATIVE = "authoritative"  # part of the in-force authoritative state
    CONTROL = "control"            # governs the system itself (rules, budgets, schema)


# Ordered, for "at least this authority" comparisons.
AUTHORITY_ORDER: tuple[Authority, ...] = (
    Authority.UNTRUSTED,
    Authority.CANDIDATE,
    Authority.REVIEWED,
    Authority.AUTHORITATIVE,
    Authority.CONTROL,
)


def authority_rank(a: Authority) -> int:
    return AUTHORITY_ORDER.index(a)


class OriginType(StrEnum):
    """Where a piece of state came from - machine-readable provenance."""

    USER = "user"
    SOURCE = "source"
    LOCAL_MODEL = "local_model"
    EXTERNAL_MODEL = "external_model"
    DETERMINISTIC_OPERATOR = "deterministic_operator"
    HUMAN = "human"
    IMPORTED_STATE = "imported_state"
    UNKNOWN = "unknown"            # explicitly unknown - never invented


class RelationType(StrEnum):
    """How an evidence link relates to a claim."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXTUALIZES = "contextualizes"
    LIMITS = "limits"
    DERIVED_FROM = "derived_from"


class ConflictStatus(StrEnum):
    """A conflict can persist - there is no forced narrative smoothing."""

    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    TOLERATED = "tolerated"        # two incompatible views held open on purpose
    SUPERSEDED = "superseded"


class ConflictKind(StrEnum):
    """*What kind* of incompatibility this is - so a scope tension is not mistaken for a
    flat contradiction. Qualified deterministically when the conflict is opened."""

    CONTRADICTION = "contradiction"          # genuine logical opposition (A and not-A)
    SCOPE_TENSION = "scope_tension"          # both true, but over different scopes/cases
    EXCEPTION = "exception"                  # one is an exception to the other
    CONDITIONAL_COMPATIBILITY = "conditional_compatibility"  # compatible under stated conditions
    UNQUALIFIED = "unqualified"              # opened but not yet qualified


class MemoryKind(StrEnum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    SELF_NARRATIVE = "self_narrative"


class ProposalType(StrEnum):
    """All external/generative contributions enter as one of these proposals."""

    CLAIM_PROPOSAL = "claim_proposal"
    GOAL_PROPOSAL = "goal_proposal"
    PROJECT_PROPOSAL = "project_proposal"
    PREFERENCE_PROPOSAL = "preference_proposal"
    METHOD_PROPOSAL = "method_proposal"
    STATE_REVISION_PROPOSAL = "state_revision_proposal"
    SELF_MODEL_PROPOSAL = "self_model_proposal"
    SEMANTIC_PROPOSAL = "semantic_proposal"


class Operator(StrEnum):
    """The closed set of operators allowed to change Layer 9. Each is one ledger event.

    No operator is an LLM call; an LLM can only produce a *proposal* that an operator
    may (or may not) accept.
    """

    PROPOSAL_SUBMIT = "proposal_submit"
    PROPOSAL_ACCEPT = "proposal_accept"
    PROPOSAL_REJECT = "proposal_reject"
    CLAIM_CREATE = "claim_create"
    CLAIM_REVISE = "claim_revise"
    CLAIM_CONFIRM = "claim_confirm"
    CLAIM_CONTEST = "claim_contest"
    CLAIM_REJECT = "claim_reject"
    CLAIM_SUPERSEDE = "claim_supersede"
    EVIDENCE_ATTACH = "evidence_attach"
    CONFLICT_OPEN = "conflict_open"
    CONFLICT_REVIEW = "conflict_review"
    CONFLICT_RESOLVE = "conflict_resolve"
    GOAL_CREATE = "goal_create"
    GOAL_UPDATE = "goal_update"
    GOAL_PAUSE = "goal_pause"
    GOAL_ABANDON = "goal_abandon"
    PROJECT_CREATE = "project_create"
    PROJECT_UPDATE = "project_update"
    PROJECT_COMPLETE = "project_complete"
    PROJECT_ABANDON = "project_abandon"
    PREFERENCE_PROPOSE = "preference_propose"
    PREFERENCE_REVISE = "preference_revise"
    MEMORY_RECORD = "memory_record"
    MEMORY_RECALL = "memory_recall"
    MEMORY_CONSOLIDATE_PROPOSE = "memory_consolidate_propose"
    METHOD_PROPOSE = "method_propose"
    METHOD_TRIAL_RECORD = "method_trial_record"
    METHOD_PROMOTE = "method_promote"
    METHOD_REJECT = "method_reject"
    SELF_MODEL_PROPOSE = "self_model_propose"
    SELF_MODEL_REVISE = "self_model_revise"
    NARRATIVE_RENDER = "narrative_render"
    SEMANTIC_CLUSTER_PROPOSE = "semantic_cluster_propose"
    OPERATIONAL_STATE = "operational_state"   # deterministic system measurement (gated)
    HUMAN_VALIDATE = "human_validate"         # a human signs off on a contaminated object


# Operators permitted to grant high authority. Enforced by the gate (PR 2); declared
# here so the authority model is fully specified in one place.
OPERATORS_GRANTING_AUTHORITATIVE: frozenset[Operator] = frozenset({
    Operator.CLAIM_CONFIRM,
    Operator.GOAL_CREATE,
    Operator.PROJECT_CREATE,
    Operator.METHOD_PROMOTE,
    Operator.CONFLICT_RESOLVE,
    Operator.PROPOSAL_ACCEPT,
    Operator.OPERATIONAL_STATE,   # only a deterministic operator/human writes operational state
    Operator.HUMAN_VALIDATE,      # only a human/operator may clear taint for promotion
})

# Control-plane changes (rules, budgets, schema) require these operators *and* human
# governance approval at the gate.
OPERATORS_GRANTING_CONTROL: frozenset[Operator] = frozenset({
    Operator.PROPOSAL_ACCEPT,    # only when accepting a human-approved control proposal
})


def may_grant(operator: Operator, authority: Authority) -> bool:
    """Whether an operator is even *allowed* to assign the given authority level."""
    if authority is Authority.CONTROL:
        return operator in OPERATORS_GRANTING_CONTROL
    if authority is Authority.AUTHORITATIVE:
        return operator in OPERATORS_GRANTING_AUTHORITATIVE
    return True  # untrusted/candidate/reviewed may be set by any operator
