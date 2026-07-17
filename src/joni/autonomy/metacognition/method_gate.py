"""Adapter: the emergent-method gate -> a metacognition episode + a Layer-9-status outcome.

A pure, side-effect-free view over one method (no desi_layer9 import here, so it is fully
unit-testable): the structured signals available when the method was minted, a deterministic
predicted-success blend, and - later - a belastbares outcome read off the method's Layer-9
status. It never changes the gate; it only observes.

Outcome mapping (source = later Layer-9 status, a belastbare source):
  rejected / retired            -> failure
  active / confirmed            -> success
  provisional with net passes   -> success
  candidate / maturing          -> None  (still unknown - never coerced)
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Episode, KnowledgeBoundary, Outcome, SelectedControl


@dataclass(frozen=True)
class MethodView:
    id: str
    name: str
    status: str                 # lower-case Layer-9 status value
    trial_count: int
    success_count: int
    failure_count: int
    n_topics: int               # breadth of applicable_to
    origin: str


def build_episode(view: MethodView, *, cycle: int, tick: int, config_hash: str,
                  boundary_dark: bool = False) -> Episode:
    n_topics = max(0, int(view.n_topics))
    breadth = min(n_topics / 5.0, 1.0)
    clean_provenance = 1.0 if str(view.origin).startswith("joni:emergent") else 0.5
    trials = view.success_count + view.failure_count
    trial_support = (view.success_count / trials) if trials else 0.5
    signals = {"evidence_breadth": round(breadth, 6),
               "clean_provenance": clean_provenance,
               "trial_support": round(trial_support, 6)}
    predicted = round((breadth + clean_provenance + trial_support) / 3.0, 6)

    if boundary_dark:
        boundary = KnowledgeBoundary.MONITOR_DARK
    elif n_topics < 2:
        boundary = KnowledgeBoundary.INSUFFICIENT_EVIDENCE
    else:
        boundary = KnowledgeBoundary.INSIDE

    return Episode(
        cycle=cycle, created_tick=tick, task_family="method_gate",
        decision_seam="emerge.method_lens", subject_refs=(f"method:{view.id}",),
        signal_sources=("layer9", "emerge"), signals=signals, predicted_success=predicted,
        confidence_source="deterministic:signal_blend", knowledge_boundary=boundary,
        selected_control=SelectedControl.PROCEED, expected_cost=0.0, route="deterministic",
        model_or_tool="emerge", configuration_hash=config_hash)


def resolve(view: MethodView) -> Outcome | None:
    """A belastbares outcome from the later Layer-9 status, or None while still pending."""
    s = str(view.status).lower()
    if s in ("rejected", "retired"):
        return Outcome.FAILURE
    if s in ("active", "confirmed"):
        return Outcome.SUCCESS
    if s == "provisional" and view.success_count > view.failure_count:
        return Outcome.SUCCESS
    return None                     # candidate / maturing provisional -> stays unknown


__all__ = ["MethodView", "build_episode", "resolve"]
