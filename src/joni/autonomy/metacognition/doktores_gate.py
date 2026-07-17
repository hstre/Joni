"""Adapter A: the Doktores coherence verifier -> a metacognition episode + a Layer-9 outcome.

Joni's Doktores is a probabilistic verifier over Joni's OWN ideas: for each hypothesis it emits a
structured coherence verdict (``coherent`` yes/no + a short reason), recorded in
``extensions['doktores_hyp_log']``. That verdict is the monitoring signal; the belastbares outcome
is the hypothesis's LATER Layer-9 status (promoted/survived vs rejected/superseded). No PR/CI
reader is needed for this seam - the outcome is in-state and deterministic.

(The richer multi-dimensional verifier the brief sketches - per-dimension means, dispersion, red
flags, veto - is not present in Joni's Doktores today; it lives in the DESi Semantic Layer. The
literature-review Doktores -> commission -> PR path, whose outcome IS PR/CI state, needs a separate
GitHub-state reader and is left as a documented future adapter.)
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Episode, KnowledgeBoundary, Outcome, SelectedControl


@dataclass(frozen=True)
class DoktoresVerdict:
    hypothesis_id: str
    coherent: bool
    topic: str


@dataclass(frozen=True)
class ClaimView:
    id: str
    status: str                     # lower-case Layer-9 claim status


_SUCCESS_STATUS = frozenset({"active", "confirmed", "achieved"})
_FAILURE_STATUS = frozenset({"rejected", "superseded", "outdated", "abandoned"})


def build_episode(v: DoktoresVerdict, *, cycle: int, tick: int, config_hash: str) -> Episode:
    coherent = 1.0 if v.coherent else 0.0
    predicted = 0.70 if v.coherent else 0.20      # a coherent idea is judged likelier to survive
    boundary = KnowledgeBoundary.INSIDE if v.coherent else KnowledgeBoundary.CONFLICTING
    return Episode(
        cycle=cycle, created_tick=tick, task_family="doktores_coherence",
        decision_seam="doktores.coherence", subject_refs=(f"claim:{v.hypothesis_id}",),
        signal_sources=("doktores", "layer9"), signals={"coherent": coherent},
        predicted_success=predicted, confidence_source="deterministic:coherence_verdict",
        knowledge_boundary=boundary, selected_control=SelectedControl.VERIFY,
        expected_cost=0.0, route="escalation", model_or_tool="joni-hard",
        configuration_hash=config_hash)


def resolve(claim: ClaimView) -> Outcome | None:
    """Belastbares outcome from the hypothesis-claim's later Layer-9 status (else pending)."""
    s = str(claim.status).lower()
    if s in _SUCCESS_STATUS:
        return Outcome.SUCCESS
    if s in _FAILURE_STATUS:
        return Outcome.FAILURE
    return None                     # candidate / tentative / contested -> still unknown


__all__ = ["DoktoresVerdict", "ClaimView", "build_episode", "resolve"]
