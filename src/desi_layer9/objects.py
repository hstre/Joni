"""The concrete Layer-9 object classes.

Each extends ``EpistemicObject`` (common governance metadata) with its own fields.
Crucially, a ``Claim`` does **not** contain its own evidence: claims, ``Evidence`` and
``EvidenceLink`` are separate objects, so support is auditable and a claim can only be
confirmed under explicit conditions (see ``rules.can_confirm_claim``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .base import EpistemicObject
from .enums import (
    ConflictStatus,
    MemoryKind,
    ObjectType,
    Operator,
    ProposalType,
    RelationType,
)


@dataclass
class Claim(EpistemicObject):
    object_type: ObjectType = ObjectType.CLAIM
    text: str = ""
    topic: str = ""


@dataclass
class Evidence(EpistemicObject):
    object_type: ObjectType = ObjectType.EVIDENCE
    content: str = ""
    kind: str = "statement"       # statement | measurement | document | observation | ...
    source_id: str | None = None  # -> Source.id


@dataclass
class EvidenceLink(EpistemicObject):
    """A typed relation between a claim and a piece of evidence - itself audited."""

    object_type: ObjectType = ObjectType.EVIDENCE_LINK
    claim_id: str = ""
    evidence_id: str = ""
    relation: RelationType = RelationType.SUPPORTS
    strength: float = 0.5
    review_status: str = "unreviewed"   # unreviewed | reviewed | disputed


@dataclass
class Constraint(EpistemicObject):
    object_type: ObjectType = ObjectType.CONSTRAINT
    text: str = ""
    kind: str = "hard"            # hard | soft


@dataclass
class Goal(EpistemicObject):
    object_type: ObjectType = ObjectType.GOAL
    text: str = ""
    horizon: str = "long"         # short | long
    priority: float = 0.5
    progress: float = 0.0


@dataclass
class Preference(EpistemicObject):
    object_type: ObjectType = ObjectType.PREFERENCE
    subject: str = ""
    stance: str = "prefers"
    strength: float = 0.5
    formed_from: tuple[str, ...] = ()   # claim ids


@dataclass
class Project(EpistemicObject):
    object_type: ObjectType = ObjectType.PROJECT
    title: str = ""
    topic: str = ""


@dataclass
class Method(EpistemicObject):
    """A reusable thinking move. Versioned; promoted only after trial + review."""

    object_type: ObjectType = ObjectType.METHOD
    name: str = ""
    summary: str = ""
    steps: tuple[str, ...] = ()
    origin: str = "unknown"
    applicable_to: tuple[str, ...] = ()
    contraindications: tuple[str, ...] = ()
    success_count: int = 0
    failure_count: int = 0
    trial_count: int = 0
    supporting_runs: tuple[str, ...] = ()
    failed_runs: tuple[str, ...] = ()
    parent_methods: tuple[str, ...] = ()
    version: int = 1
    superseded_by: str | None = None


@dataclass
class MemoryEpisode(EpistemicObject):
    object_type: ObjectType = ObjectType.MEMORY_EPISODE
    kind: MemoryKind = MemoryKind.EPISODIC
    summary: str = ""
    refs: tuple[str, ...] = ()
    source_event: str | None = None     # the ledger event that produced it
    importance: float = 0.5
    retrieval_weight: float = 0.5       # salience; NOT epistemic status
    last_recalled_tick: int = 0
    recall_count: int = 0


@dataclass
class Conflict(EpistemicObject):
    """An incompatibility that may persist - there is no forced narrative smoothing."""

    object_type: ObjectType = ObjectType.CONFLICT
    conflict_status: ConflictStatus = ConflictStatus.OPEN
    kind: str = "contradiction"
    severity: str = "soft"        # soft | hard
    claim_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    resolution: str | None = None
    resolution_reason: str | None = None


@dataclass
class Source(EpistemicObject):
    object_type: ObjectType = ObjectType.SOURCE
    uri: str = ""
    title: str = ""
    kind: str = "web"             # web | paper | dataset | conversation | ...
    retrieved_tick: int = 0


@dataclass
class Proposal(EpistemicObject):
    """The single ingress for every external/generative contribution."""

    object_type: ObjectType = ObjectType.PROPOSAL
    proposal_type: ProposalType = ProposalType.CLAIM_PROPOSAL
    payload: dict = field(default_factory=dict)
    proposer: str = "unknown"
    reason: str = ""
    expected_effect: str = ""
    risks: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    target_objects: tuple[str, ...] = ()
    requested_operator: Operator | None = None


@dataclass
class Review(EpistemicObject):
    object_type: ObjectType = ObjectType.REVIEW
    target_id: str = ""
    reviewer: str = "unknown"
    verdict: str = "neutral"      # support | reject | neutral | needs_more
    reason: str = ""
    independent: bool = False     # was the reviewer independent of the generator?


@dataclass
class Decision(EpistemicObject):
    """The gate's verdict on a proposal - the audit of what was (not) accepted."""

    object_type: ObjectType = ObjectType.DECISION
    proposal_id: str = ""
    operator: Operator | None = None
    accepted: bool = False
    new_status: str | None = None
    reason: str = ""
    rejected_fields: tuple[str, ...] = ()


@dataclass
class OperationalState(EpistemicObject):
    """Actual system data - the ground truth a narrative may describe but never override."""

    object_type: ObjectType = ObjectType.OPERATIONAL_STATE
    metrics: dict = field(default_factory=dict)   # measured counts/values, key->number


@dataclass
class SelfModelClaim(EpistemicObject):
    """A claim Joni makes *about itself* - provisional and evidence-bearing, not a fact."""

    object_type: ObjectType = ObjectType.SELF_MODEL_CLAIM
    text: str = ""
    evidence: tuple[str, ...] = ()        # supporting object ids
    counterevidence: tuple[str, ...] = ()


@dataclass
class NarrativeSummary(EpistemicObject):
    """A verbal compression. Read-only over state; can never write OperationalState."""

    object_type: ObjectType = ObjectType.NARRATIVE_SUMMARY
    text: str = ""
    basis: tuple[str, ...] = ()           # the object ids it summarises
