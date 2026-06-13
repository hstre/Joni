"""Core data model for Joni.

Joni is a DESi-based **operative identity**. From the outside it reads like a
person: it has memory, autobiographical continuity, recognisable preferences, its
own projects, long-term goals, and it changes its mind for stated reasons. Inside
there is no "person" - only controlled state and deterministic operators.

The whole point is the inversion of the usual trick:

    Do not simulate a person and then mystify it. Show, mechanically, how the
    *impression* of personhood is produced - and make every apparently personal
    trait technically dissolvable.

So everything here is plain, inspectable data. Following the ecosystem rule
(DESi / AleXiona): **LLM for language, rules for logic.** A model may phrase the
outer voice; it never owns state. Every state change is a deterministic operator
that writes an append-only ledger event - the receipts behind the personality.

Design invariants borrowed from DESi:
  * Closed enumerations - statuses, triggers and operators are fixed sets.
  * Sequential, replay-stable ids (C-184, G-12, L9-7741) assigned by counters in a
    deterministic order - no PRNG anywhere.
  * Append-only audit - the ledger records what happened; it is never rewritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# --------------------------------------------------------------------------- #
# Closed enumerations
# --------------------------------------------------------------------------- #


class ClaimStatus(StrEnum):
    """The lifecycle of a belief. Opinion change = a status transition, audited."""

    TENTATIVE = "tentative"      # held, but lightly
    ACTIVE = "active"            # currently believed and acted on
    CONFIRMED = "confirmed"      # corroborated by independent support
    REJECTED = "rejected"        # given up - "I have since abandoned this"
    SUPERSEDED = "superseded"    # replaced by a better claim


class Trigger(StrEnum):
    """Why a transition happened. Every opinion change names one of these."""

    USER_INPUT = "user_input"
    SUPPORTING_EVIDENCE = "supporting_evidence"
    CONTRADICTORY_EVIDENCE = "contradictory_evidence"
    SELF_REVIEW = "self_review"
    IMPROVEMENT_LOOP = "improvement_loop"
    RESEARCH_HARVEST = "research_harvest"


class Operator(StrEnum):
    """The closed set of deterministic operators that may change state.

    These are the *only* ways the identity can move. Each application is one ledger
    event. No operator is an LLM call.
    """

    CLAIM_ASSERT = "claim_assert"
    OPINION_REVISE = "opinion_revise"
    CONFLICT_RESOLUTION = "conflict_resolution"
    GOAL_ADOPT = "goal_adopt"
    GOAL_ADVANCE = "goal_advance"
    GOAL_DROP = "goal_drop"
    PREFERENCE_FORM = "preference_form"
    PROJECT_START = "project_start"
    PROJECT_ABANDON = "project_abandon"
    MEMORY_RECORD = "memory_record"
    VOICE_RENDER = "voice_render"   # phrasing the outer voice (audits any model spend)


class GoalStatus(StrEnum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    SHIPPED = "shipped"
    ABANDONED = "abandoned"


class Horizon(StrEnum):
    SHORT = "short"
    LONG = "long"


class ModelTier(StrEnum):
    """Where a unit of cognition is routed - cheapest capable tier first."""

    DETERMINISTIC = "deterministic"        # no model at all - pure rules
    LOCAL_SMALL = "local_small"            # e.g. a granite-micro style local model
    LOCAL_SPECIALIST = "local_specialist"  # a local model tuned for a task
    EXTERNAL_API = "external_api"          # a strong API model, on demand only


# --------------------------------------------------------------------------- #
# State records
# --------------------------------------------------------------------------- #


@dataclass
class Transition:
    """One audited change to a claim's status - the unit of 'changing one's mind'."""

    from_status: ClaimStatus
    to_status: ClaimStatus
    trigger: Trigger
    operator: Operator
    tick: int
    reviewed_by: str            # which model/tier signed off (e.g. "granite-micro")
    ledger_id: str              # the L9-#### event this transition is recorded as


@dataclass
class Claim:
    """A typed, status-bearing belief. The atom the personality is built from."""

    id: str                     # C-###
    text: str
    topic: str
    status: ClaimStatus = ClaimStatus.TENTATIVE
    support: float = 0.5        # [0,1] internal support, NOT a probability
    created_tick: int = 0
    last_changed_tick: int = 0
    history: list[Transition] = field(default_factory=list)


@dataclass
class Goal:
    id: str                     # G-###
    text: str
    horizon: Horizon = Horizon.LONG
    status: GoalStatus = GoalStatus.ACTIVE
    priority: float = 0.5
    progress: float = 0.0       # [0,1]
    created_tick: int = 0


@dataclass
class Preference:
    """A recognisable like/dislike - traceable to the claims that formed it."""

    id: str                     # PR-###
    subject: str
    stance: str                 # e.g. "prefers", "avoids"
    strength: float = 0.5
    formed_from: tuple[str, ...] = ()   # claim ids
    created_tick: int = 0


@dataclass
class Project:
    id: str                     # P-###
    title: str
    topic: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    created_tick: int = 0


@dataclass
class MemoryEpisode:
    """An autobiographical episode - the continuity the outside reads as 'a life'."""

    id: str                     # M-###
    tick: int
    kind: str                   # e.g. "learned", "changed_mind", "started_project"
    summary: str
    refs: tuple[str, ...] = ()  # ids of claims/goals/projects involved


@dataclass
class Conflict:
    id: str                     # X-###
    claim_a: str
    claim_b: str
    kind: str                   # e.g. "negation", "stance_opposition"
    tick: int
    resolved: bool = False


@dataclass
class LedgerEvent:
    """An append-only audit record. The receipts behind every apparent trait."""

    id: str                     # L9-####
    tick: int
    operator: Operator
    summary: str
    refs: tuple[str, ...] = ()
    reviewed_by: str = "deterministic"
    cost: float = 0.0           # routing cost charged for this event, if any


# --------------------------------------------------------------------------- #
# The dual view
# --------------------------------------------------------------------------- #


@dataclass
class EpistemicTrace:
    """The Epistemic View of a single utterance.

    This is the whole thesis in one object: given something Joni 'said', exactly
    which internal causes produced it - so the personhood never has to be taken on
    faith. Mirrors the user's worked example for "I have since abandoned this idea".
    """

    utterance: str
    claims: tuple[str, ...] = ()        # claim ids in play
    goals: tuple[str, ...] = ()         # goal ids in play
    memory: tuple[str, ...] = ()        # memory episode ids recalled
    operator: Operator | None = None    # the operator that drove a change, if any
    trigger: Trigger | None = None
    reviewed_by: str = "deterministic"
    ledger_event: str | None = None     # the L9-#### behind it
    routed_to: ModelTier = ModelTier.DETERMINISTIC


@dataclass
class Response:
    """What Joni returns: the apparent person, plus the receipts.

    ``conversation`` is the Conversation View (the seemingly autonomous figure).
    ``epistemic`` is the Epistemic View (why it behaved that way). Two windows onto
    the same event - never one without the other.
    """

    conversation: str
    epistemic: EpistemicTrace
