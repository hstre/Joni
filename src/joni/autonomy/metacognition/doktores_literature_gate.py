"""Adapter A (literature arm): Doktores' self-improvement review -> a metacognition episode.

For each fetched paper/repo, Doktores judges whether it grounds a concrete non-core improvement
and, if so, files an Auftrag (a commission) that a human-gated session implements via a PR. The
review log (``extensions['doktores_review']``) carries the structured signals: ``applicable``,
``component_key``, the ``served_model`` tier that judged it, and the source. The belastbares
outcome is the eventual PR/CI state of that commission - supplied by ``pr_outcomes`` (documented
implementation, or a GitHub joni-auftrag issue/PR). Linking a commission to its PR is best-effort
(by component key), so many episodes legitimately stay ``unknown``.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Episode, KnowledgeBoundary, Outcome, SelectedControl

_HARD_MODEL_TOKENS = ("deepseek", "hard", "pro")


@dataclass(frozen=True)
class ReviewSignal:
    component_key: str
    applicable: bool
    served_model: str
    source: str
    is_fulltext: bool


def build_episode(sig: ReviewSignal, *, cycle: int, tick: int, config_hash: str) -> Episode:
    applicable = 1.0 if sig.applicable else 0.0
    is_hard = 1.0 if any(t in str(sig.served_model).lower() for t in _HARD_MODEL_TOKENS) else 0.0
    is_full = 1.0 if sig.is_fulltext else 0.0
    predicted = round(0.30 + 0.30 * applicable + 0.20 * is_full + 0.10 * is_hard, 6)
    signals = {"applicable": applicable, "is_fulltext": is_full, "is_hard_model": is_hard}
    boundary = (KnowledgeBoundary.INSIDE if sig.applicable
                else KnowledgeBoundary.INSUFFICIENT_EVIDENCE)
    return Episode(
        cycle=cycle, created_tick=tick, task_family="doktores_literature",
        decision_seam="doktores.literature_review",
        subject_refs=(f"commission:doktores:{sig.component_key}",),
        signal_sources=("doktores", "verifier"), signals=signals, predicted_success=predicted,
        confidence_source="deterministic:review_blend", knowledge_boundary=boundary,
        selected_control=SelectedControl.ASK_HUMAN,      # files an Auftrag for a human-gated PR
        expected_cost=0.0, route="escalation",
        model_or_tool=str(sig.served_model) or "joni-hard", configuration_hash=config_hash)


def outcome_for(index_value: str) -> Outcome | None:
    """Map a PR-outcome index value ('success'/'failure') to an Outcome, else None (pending)."""
    v = str(index_value or "").lower()
    if v == "success":
        return Outcome.SUCCESS
    if v == "failure":
        return Outcome.FAILURE
    return None


__all__ = ["ReviewSignal", "build_episode", "outcome_for"]
