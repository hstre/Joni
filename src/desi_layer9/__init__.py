"""desi_layer9 - the authoritative epistemic state and governance core.

Layer 9 is the single, shared, authoritative epistemic state for the ecosystem. Joni
(the operative identity) and Kevin (the creativity module) both build on it. The
governing principle:

    No LLM, creativity module or renderer may change authoritative Layer-9 state
    directly. Every change goes through a closed, validated operator and the
    state-update gate.

This package (PR 1) defines the *schema and authority model*: the closed object classes,
their common governance metadata (status, authority, machine-readable provenance,
derived-from, validity, support, taint), the proposal ingress types, and the per-class
status transition tables. The write-gate and operators (PR 2), the hash-chained ledger,
replay and migration (PR 3), and the Joni/Kevin integrations (PR 4/5) build on this.

``confidence_or_support`` is an internal support metric in [0, 1] - **not a probability**.
"""

from __future__ import annotations

from . import migration, persistence, semantics
from .base import EpistemicObject
from .core import JournalEntry, Layer9, make_proposal
from .enums import (
    AUTHORITY_ORDER,
    OPERATORS_GRANTING_AUTHORITATIVE,
    OPERATORS_GRANTING_CONTROL,
    Authority,
    ConflictKind,
    ConflictStatus,
    MemoryKind,
    ObjectType,
    Operator,
    OriginType,
    ProposalType,
    RelationType,
    SemanticDecision,
    SemanticState,
    Status,
    authority_rank,
    may_grant,
)
from .hashing import snapshot_hash, verify_chain
from .ids import IdMinter
from .ledger import LedgerEvent
from .objects import (
    Claim,
    Conflict,
    Constraint,
    Decision,
    Evidence,
    EvidenceLink,
    Goal,
    MemoryEpisode,
    Method,
    NarrativeSummary,
    OperationalState,
    Preference,
    Project,
    Proposal,
    Review,
    SelfModelClaim,
    SemanticCluster,
    Source,
)
from .provenance import Provenance
from .rules import can_confirm_claim, method_after_single_gate
from .taint import Taint, merge_all
from .transitions import (
    CONFLICT_TRANSITIONS,
    TRANSITIONS,
    TransitionError,
    allowed,
    assert_conflict_transition,
    assert_transition,
    validate_conflict_transition,
    validate_transition,
)

SCHEMA_VERSION = 1

__all__ = [
    "SCHEMA_VERSION",
    # base + metadata
    "EpistemicObject", "Provenance", "Taint", "merge_all", "IdMinter",
    # enums
    "ObjectType", "Status", "Authority", "OriginType", "RelationType",
    "ConflictStatus", "ConflictKind", "MemoryKind", "ProposalType", "Operator",
    "SemanticState", "SemanticDecision",
    "AUTHORITY_ORDER", "authority_rank", "may_grant",
    "OPERATORS_GRANTING_AUTHORITATIVE", "OPERATORS_GRANTING_CONTROL",
    # objects
    "Claim", "Evidence", "EvidenceLink", "Constraint", "Goal", "Preference",
    "Project", "Method", "MemoryEpisode", "Conflict", "Decision", "Proposal",
    "Review", "Source", "OperationalState", "SelfModelClaim", "NarrativeSummary",
    "SemanticCluster",
    # the semantic boundary (port to the DESi Semantic Layer)
    "semantics",
    # transitions + rules
    "TRANSITIONS", "CONFLICT_TRANSITIONS", "TransitionError", "allowed",
    "validate_transition", "assert_transition",
    "validate_conflict_transition", "assert_conflict_transition",
    "can_confirm_claim", "method_after_single_gate",
    # the authoritative core + gate (PR 2)
    "Layer9", "make_proposal", "LedgerEvent",
    # ledger/replay/migration (PR 3)
    "JournalEntry", "snapshot_hash", "verify_chain", "persistence", "migration",
]
