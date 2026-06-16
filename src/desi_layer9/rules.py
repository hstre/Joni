"""Conservative epistemic rules - the conditions, not the enforcement.

These pure predicates state *when* something is structurally allowed (e.g. a claim may
be confirmed). The gate (PR 2) is what enforces them, adds the authority/operator check,
and writes the ledger event. Nothing here claims to detect truth - confirmation is a
governed status, not a discovery of fact.
"""

from __future__ import annotations

from .enums import OriginType, RelationType, Status
from .objects import Claim, EvidenceLink, Method


def can_confirm_claim(
    claim: Claim,
    evidence_links: list[EvidenceLink],
    *,
    unresolved_hard_contradiction: bool,
) -> tuple[bool, list[str]]:
    """Conservative confirm conditions (§4). Returns (ok, list of failed reasons).

    Requires: at least one admitted support link, no unresolved hard contradiction,
    provenance present, and not quarantined. The operator/authority gate is separate.
    """
    reasons: list[str] = []

    supports = [
        el for el in evidence_links
        if el.claim_id == claim.id
        and el.relation is RelationType.SUPPORTS
        and el.review_status == "reviewed"
    ]
    if not supports:
        reasons.append("no admitted (reviewed) support link")
    if unresolved_hard_contradiction:
        reasons.append("an unresolved hard contradiction exists")
    if claim.provenance.origin_type is OriginType.UNKNOWN:
        reasons.append("provenance missing/unknown")
    if claim.status is Status.QUARANTINED:
        reasons.append("claim is quarantined")
    taint = getattr(claim, "taint", None)
    if taint is not None and taint.is_contaminated and not taint.human_validated:
        # taint must actually block confirmation, not just be recorded; a human can clear it
        # explicitly via HUMAN_VALIDATE.
        reasons.append("claim is contaminated and not human-validated")

    return (not reasons), reasons


def method_after_single_gate(method: Method) -> Status:
    """A single positive human gate may move a method only candidate -> provisional.

    It must never make a method authoritative/active outright (§8). Promotion to active
    requires trials + review at the gate.
    """
    if method.status is Status.CANDIDATE:
        return Status.PROVISIONAL
    return method.status
