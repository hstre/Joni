"""Layer 9's governed decision over a DESi semantic measurement.

The measurement is DESi's; the *classification* into a governed relationship - and whether
it may drive a synthesis - is Layer 9's. Deterministic, threshold-based, fully auditable.
Lexical overlap is only ever a tie-breaker for duplication; it never decides relatedness.

    measurement (+ lexical_trigger)  ->  (SemanticDecision, SemanticState, rationale)

Signal order: an explicit frame conflict / logical rejection / frame tension is a veto
first. Then, the *primary* relatedness signal is the embedding / √JSD ``pi_distance`` when
present (the real meaning-level measure); the frame match/mismatch refines it. Only when no
distance is available does it fall back to frames alone, which for thin claims fails closed
to insufficient. A model or a high word overlap can never force ``SYNTHESIS_ELIGIBLE``.
"""

from __future__ import annotations

from ..enums import SemanticDecision, SemanticState
from .ports import SemanticMeasurement

DUP_LEXICAL = 0.80          # very high word overlap, used only to confirm a same-frame dup

# Cosine/√JSD distance thresholds (experimental, to be calibrated). These are a *separate*
# measurement channel - they do not loosen any frame threshold.
DIST_DUPLICATE = 0.10       # ~identical meaning
DIST_COMPLEMENTARY = 0.30   # clearly related, non-duplicate -> a synthesis candidate
DIST_SUPPORTS = 0.45        # related enough to link, not to synthesise
DIST_BORDERLINE = 0.60      # beyond this, unrelated

_CONTRADICTION_AUDITS = {"logically_rejected"}


def classify(m: SemanticMeasurement, *, lexical_trigger: float = 0.0
             ) -> tuple[SemanticDecision, SemanticState, str]:
    if m.error:
        return (SemanticDecision.INSUFFICIENT, SemanticState.INSUFFICIENT_EVIDENCE,
                f"semantic layer gave no usable output: {m.error}")

    # explicit contradiction veto: a frame conflict or a rejected logical audit.
    rejected_audit = (m.logical_audit_a in _CONTRADICTION_AUDITS
                      or m.logical_audit_b in _CONTRADICTION_AUDITS)
    if m.frame_tension == "conflict" or rejected_audit:
        return (SemanticDecision.CONTRADICTORY, SemanticState.SYNTHESIS_REJECTED,
                "frame conflict / logical rejection - claims are opposed")

    # frame tension veto: hold it, do not synthesise; EN may apply.
    if m.frame_tension == "tension":
        note = " (EN recommended)" if m.en_recommended else ""
        return (SemanticDecision.TENSION, SemanticState.HUMAN_REVIEW_REQUIRED,
                "frame tension between the claims" + note)

    # primary signal: a meaning-level distance, if available. The embedding *cosine* distance
    # is preferred (labelled as such); the √JSD path is used only if a real projector set it.
    dist = m.cosine_distance if m.cosine_distance is not None else m.pi_distance
    if dist is not None:
        return _from_distance(m, dist)

    # no distance available -> frames alone.
    if not m.frames_declared or m.frame_tension == "undecidable":
        return (SemanticDecision.INSUFFICIENT, SemanticState.HUMAN_REVIEW_REQUIRED,
                "frame undeclared / undecidable and no semantic projector - cannot decide")
    if not m.frames_match:
        return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
                f"different frames ({m.frame_a} vs {m.frame_b}) despite shared words")
    if lexical_trigger >= DUP_LEXICAL:
        return (SemanticDecision.DUPLICATE, SemanticState.SYNTHESIS_REJECTED,
                "same frame and near-identical wording - a duplicate")
    if "logically_supported" in (m.logical_audit_a, m.logical_audit_b):
        return (SemanticDecision.SUPPORTS, SemanticState.SEMANTIC_MEASURED,
                "same frame, one logically supports the other")
    return (SemanticDecision.COMPLEMENTARY, SemanticState.SYNTHESIS_ELIGIBLE,
            "same frame, compatible and non-duplicate - a synthesis candidate")


def _from_distance(m: SemanticMeasurement, d: float
                   ) -> tuple[SemanticDecision, SemanticState, str]:
    """Decide from the meaning-level distance, combined with the other channels."""
    metric = m.distance_metric or ("sqrt_jsd" if m.cosine_distance is None else "cosine")
    src = f"{metric} distance {d:.3f}"
    frames_conflict = m.frames_declared and not m.frames_match

    # combine channels: two claims that are *close* in meaning but carry a negation/antonym
    # opposition are contradictory, not duplicates - the embedding cannot see negation.
    if d <= DIST_SUPPORTS and m.polarity_clash:
        return (SemanticDecision.CONTRADICTORY, SemanticState.SYNTHESIS_REJECTED,
                f"{src}: close in meaning but opposed in polarity - contradictory")

    if m.duplicate is True or d <= DIST_DUPLICATE:
        if frames_conflict:
            return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
                    f"{src}: near-identical but different frames - not merged")
        return (SemanticDecision.DUPLICATE, SemanticState.SYNTHESIS_REJECTED,
                f"{src}: a semantic duplicate, not a synthesis")
    if d <= DIST_COMPLEMENTARY:
        if frames_conflict:
            return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
                    f"{src}: related words but different frames")
        return (SemanticDecision.COMPLEMENTARY, SemanticState.SYNTHESIS_ELIGIBLE,
                f"{src}: clearly related and non-duplicate - a synthesis candidate")
    if d <= DIST_SUPPORTS:
        return (SemanticDecision.SUPPORTS, SemanticState.SEMANTIC_MEASURED,
                f"{src}: related - worth linking, not synthesising")
    if d <= DIST_BORDERLINE:
        return (SemanticDecision.INSUFFICIENT, SemanticState.HUMAN_REVIEW_REQUIRED,
                f"{src}: borderline - a human should look")
    return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
            f"{src}: far apart - unrelated")
