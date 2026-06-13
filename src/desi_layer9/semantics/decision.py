"""Layer 9's governed decision over a DESi semantic measurement.

The measurement is DESi's; the *classification* into a governed relationship - and whether
it may drive a synthesis - is Layer 9's. Deterministic, threshold-based, fully auditable.
Lexical overlap is only ever a tie-breaker for duplication; it never decides relatedness.

    measurement (+ lexical_trigger)  ->  (SemanticDecision, SemanticState, rationale)

Fail-closed: any missing/invalid measurement is ``INSUFFICIENT`` -> human review. A model
or a high word overlap can never push a pair to ``SYNTHESIS_ELIGIBLE`` on its own.
"""

from __future__ import annotations

from ..enums import SemanticDecision, SemanticState
from .ports import SemanticMeasurement

DUP_LEXICAL = 0.80          # very high word overlap, used only to confirm a same-frame dup
DUP_PI_DISTANCE = 0.12      # if a Π/√JSD distance is present, this small means duplicate

_CONTRADICTION_AUDITS = {"logically_rejected"}


def classify(m: SemanticMeasurement, *, lexical_trigger: float = 0.0
             ) -> tuple[SemanticDecision, SemanticState, str]:
    if m.error:
        return (SemanticDecision.INSUFFICIENT, SemanticState.INSUFFICIENT_EVIDENCE,
                f"semantic layer gave no usable output: {m.error}")

    # explicit contradiction: a frame conflict or a rejected logical audit.
    rejected_audit = (m.logical_audit_a in _CONTRADICTION_AUDITS
                      or m.logical_audit_b in _CONTRADICTION_AUDITS)
    if m.frame_tension == "conflict" or rejected_audit:
        return (SemanticDecision.CONTRADICTORY, SemanticState.SYNTHESIS_REJECTED,
                "frame conflict / logical rejection - claims are opposed")

    # frame tension: hold it, do not synthesise; EN may apply.
    if m.frame_tension == "tension":
        note = " (EN recommended)" if m.en_recommended else ""
        return (SemanticDecision.TENSION, SemanticState.HUMAN_REVIEW_REQUIRED,
                "frame tension between the claims" + note)

    # cannot judge the frame on at least one side -> insufficient.
    if not m.frames_declared or m.frame_tension == "undecidable":
        return (SemanticDecision.INSUFFICIENT, SemanticState.HUMAN_REVIEW_REQUIRED,
                "frame undeclared / undecidable - not enough to decide")

    # same surface vocabulary but different frames -> not the same concept.
    if not m.frames_match:
        return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
                f"different frames ({m.frame_a} vs {m.frame_b}) despite shared words")

    # same frame, no tension, no contradiction.
    is_duplicate = (
        m.duplicate is True
        or (m.pi_distance is not None and m.pi_distance <= DUP_PI_DISTANCE)
        or (m.pi_distance is None and lexical_trigger >= DUP_LEXICAL)
    )
    if is_duplicate:
        return (SemanticDecision.DUPLICATE, SemanticState.SYNTHESIS_REJECTED,
                "same frame and near-identical - a duplicate, not a synthesis")

    if "logically_supported" in (m.logical_audit_a, m.logical_audit_b):
        return (SemanticDecision.SUPPORTS, SemanticState.SEMANTIC_MEASURED,
                "same frame, one logically supports the other")

    return (SemanticDecision.COMPLEMENTARY, SemanticState.SYNTHESIS_ELIGIBLE,
            "same frame, compatible and non-duplicate - a synthesis candidate")
