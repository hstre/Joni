"""Adapter B/2: the conflict-resolution seam -> a metacognition episode + a Layer-9 outcome.

A pure view over one Layer-9 conflict (no desi_layer9 import): the structured signals present
when the conflict was opened (severity, breadth, kind), a deterministic predicted-resolvability
blend, and - later - a belastbares outcome from the conflict's own status:

  resolved                         -> success   (a real Layer-9 adjudication / supersede)
  open and older than STALE cycles -> failure   (it festered; the seam never resolved it)
  open and recent                  -> None       (still pending - unknown, never coerced)

A distinct decision seam from the method gate, so the metrics can be grouped and compared.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Episode, KnowledgeBoundary, Outcome, SelectedControl


@dataclass(frozen=True)
class ConflictView:
    id: str
    conflict_status: str            # lower-case: "open" / "resolved"
    severity: str                   # "soft" / "hard"
    conflict_kind: str
    n_claims: int


def build_episode(view: ConflictView, *, cycle: int, tick: int, config_hash: str) -> Episode:
    is_hard = 1.0 if str(view.severity).lower() == "hard" else 0.0
    breadth = min(max(0, int(view.n_claims)) / 4.0, 1.0)
    # a hard (flatly contradictory) conflict is more likely to be adjudicated than a soft one
    predicted = round(0.35 + 0.35 * is_hard + 0.15 * breadth, 6)
    signals = {"is_hard": is_hard, "claim_breadth": round(breadth, 6)}
    return Episode(
        cycle=cycle, created_tick=tick, task_family="conflict_gate",
        decision_seam="conflict.resolution", subject_refs=(f"conflict:{view.id}",),
        signal_sources=("layer9", "conflict"), signals=signals, predicted_success=predicted,
        confidence_source="deterministic:conflict_blend",
        knowledge_boundary=KnowledgeBoundary.CONFLICTING, selected_control=SelectedControl.VERIFY,
        expected_cost=0.0, route="deterministic", model_or_tool="conflict_engine",
        configuration_hash=config_hash)


def resolve(view: ConflictView, *, age: int, stale_cycles: int) -> Outcome | None:
    """Belastbares outcome from the conflict's later status (or None while still pending)."""
    if str(view.conflict_status).lower() == "resolved":
        return Outcome.SUCCESS
    if age >= stale_cycles:
        return Outcome.FAILURE                       # open far too long -> the seam did not resolve
    return None                                      # recently open -> stays unknown


__all__ = ["ConflictView", "build_episode", "resolve"]
