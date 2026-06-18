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
    ConflictKind,
    ConflictStatus,
    MemoryKind,
    ObjectType,
    Operator,
    ProposalType,
    RelationType,
    SemanticDecision,
    SemanticState,
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
class MethodTrialEvent(EpistemicObject):
    """An immutable, append-only record of ONE METHOD_TRIAL_RECORDED event.

    The verbatim payload is stored as a CANONICAL JSON string (``canonical_payload``), never a
    mutable dict, so the record cannot be altered in place and a hash over it is deterministic.
    This object is never mutated and never read by the method-promotion/discard counters -
    interpretation of the trial lives OUTSIDE Layer 9.

    ``record_authority`` vs ``epistemic_authority``: the RECORD is authoritative (Layer 9 confirms
    that this event, with this payload, was registered); the trial's epistemic VERDICT inside the
    payload is NOT thereby confirmed - so a generic reader must not read ``authority`` and treat the
    embedded ``epistemic_result`` as established science.
    """

    object_type: ObjectType = ObjectType.METHOD_TRIAL_EVENT
    schema_version: str = ""
    trial_id: str = ""
    canonical_payload: str = ""               # canonical JSON of the verbatim payload (immutable)
    record_authority: str = "authoritative"   # the registration is in-force...
    epistemic_authority: str = "none"         # ...the trial verdict is NOT core-confirmed


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
    kind: str = "contradiction"   # the detector rule that found it (free text)
    conflict_kind: ConflictKind = ConflictKind.UNQUALIFIED  # the *taxonomy* of the incompatibility
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


@dataclass
class SemanticCluster(EpistemicObject):
    """Layer 9's auditable annotation of a DESi Semantic-Layer analysis over claims.

    It is an **annotation over claims, never a rewrite of them**. It keeps three things
    cleanly separated and on the permanent record:

      1. what the DESi Semantic Layer *measured* (``measurement``: frames, Π-distance,
         √JSD, logical audit, frame tension, EN signal) - with its version;
      2. what Layer 9 *decided* from that (``decision`` + ``semantic_state``);
      3. (Joni's later synthesis is a separate object, referencing this one.)

    Append-only: a newer Semantic-Layer version emits *new* clusters; it never edits the
    originals or the claims. Always a candidate analysis - never authoritative.
    """

    object_type: ObjectType = ObjectType.SEMANTIC_CLUSTER
    members: tuple[str, ...] = ()                 # claim ids analysed (2 for a pair, N for a group)
    surface_terms: tuple[str, ...] = ()           # the lexical hooks that triggered analysis
    lexical_trigger: float = 0.0                  # the cheap overlap that nominated it
    measurement: dict = field(default_factory=dict)  # raw DESi Semantic-Layer outputs
    decision: SemanticDecision = SemanticDecision.INSUFFICIENT  # the governed relationship
    semantic_state: SemanticState = SemanticState.LEXICAL_CANDIDATE  # governance disposition
    decision_rationale: str = ""
    semantic_layer: str = "absent"                # which Semantic Layer produced the measures
    semantic_layer_version: str = "0"
