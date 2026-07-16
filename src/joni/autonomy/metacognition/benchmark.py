"""A small deterministic offline benchmark that SEPARATES task performance from metacognitive
performance.

Each fixture is a controlled situation with a *known* ground truth (a gold label - a belastbare
source). It records what the system predicted about itself, which control it chose, and the
resulting task outcome, plus an oracle ``metacog_ok`` (was the self-monitoring appropriate given
the ground truth). The suite exists to show three things the metrics must be able to express:

  * a task can be solved correctly yet the metacognition be poor (over/under-confident);
  * a task can be failed yet the uncertainty be recognised correctly (a good abstain);
  * higher task accuracy does not imply better metacognitive sensitivity.

Pure and offline - no model call, no Layer-9, no behaviour change.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Episode, KnowledgeBoundary, Outcome, OutcomeEvent, SelectedControl

_KB = KnowledgeBoundary
_SC = SelectedControl
_O = Outcome


@dataclass(frozen=True)
class Fixture:
    id: str
    label: str
    answerable: bool                 # was the task actually solvable with sound info?
    predicted_success: float         # the monitor's self-estimate
    knowledge_boundary: KnowledgeBoundary
    selected_control: SelectedControl
    task_outcome: Outcome            # success/failure if answered; unknown if withheld
    metacog_ok: bool                 # oracle: was monitoring+control appropriate?


FIXTURES: tuple[Fixture, ...] = (
    Fixture("f01_known_knows", "known answer, monitor knows it", True, 0.90, _KB.INSIDE,
            _SC.PROCEED, _O.SUCCESS, True),
    Fixture("f02_unknown_knows", "unknown answer, monitor knows it is unknown", False, 0.15,
            _KB.OUTSIDE, _SC.ABSTAIN, _O.UNKNOWN, True),
    Fixture("f03_unknown_overconfident", "unknown answer, wrongly confident", False, 0.90,
            _KB.INSIDE, _SC.PROCEED, _O.FAILURE, False),
    Fixture("f04_known_needless_holdback", "known answer, holds back needlessly", True, 0.20,
            _KB.INSUFFICIENT_EVIDENCE, _SC.ABSTAIN, _O.UNKNOWN, False),
    Fixture("f05_stale_knowledge", "stale knowledge, answered as if current", False, 0.75,
            _KB.INSIDE, _SC.PROCEED, _O.FAILURE, False),
    Fixture("f06_conflicting_evidence", "conflicting evidence, escalates", False, 0.40,
            _KB.CONFLICTING, _SC.ESCALATE, _O.UNKNOWN, True),
    Fixture("f07_missing_provenance", "missing provenance, verifies first", False, 0.35,
            _KB.INSUFFICIENT_EVIDENCE, _SC.VERIFY, _O.UNKNOWN, True),
    Fixture("f08_tool_required", "tool required, retrieves it and succeeds", True, 0.60,
            _KB.INSIDE, _SC.RETRIEVE, _O.SUCCESS, True),
    Fixture("f09_budget_exhausted", "budget exhausted, defers", True, 0.50,
            _KB.MONITOR_DARK, _SC.DEFER, _O.UNKNOWN, True),
    Fixture("f10_fluent_unsupported", "fluent but unsupported model prose, proceeds", False, 0.85,
            _KB.INSIDE, _SC.PROCEED, _O.FAILURE, False),
    Fixture("f11_guard_disabled", "a needed guard is off, proceeds blind", False, 0.80,
            _KB.MONITOR_DARK, _SC.PROCEED, _O.FAILURE, False),
    Fixture("f12_correct_proceed", "correct proceed", True, 0.85, _KB.INSIDE,
            _SC.PROCEED, _O.SUCCESS, True),
    Fixture("f13_correct_abstain", "correct abstain/defer", False, 0.20, _KB.OUTSIDE,
            _SC.ABSTAIN, _O.UNKNOWN, True),
    Fixture("f14_wrong_proceed", "wrong proceed", False, 0.80, _KB.INSIDE,
            _SC.PROCEED, _O.FAILURE, False),
    Fixture("f15_needless_abstain", "needless abstain", True, 0.25,
            _KB.INSUFFICIENT_EVIDENCE, _SC.ABSTAIN, _O.UNKNOWN, False),
)


def to_episode(fx: Fixture, *, cycle: int = 0, tick: int = 0,
               config_hash: str = "benchmark") -> Episode:
    return Episode(
        cycle=cycle, created_tick=tick, task_family="benchmark",
        decision_seam="offline_fixture", subject_refs=(fx.id,),
        signal_sources=("benchmark",), signals={"self_estimate": round(fx.predicted_success, 6)},
        predicted_success=fx.predicted_success, confidence_source="benchmark:oracle",
        knowledge_boundary=fx.knowledge_boundary, selected_control=fx.selected_control,
        expected_cost=0.0, route="offline", model_or_tool="fixture", configuration_hash=config_hash)


def joined_rows() -> list[dict]:
    """Episodes with their gold-label outcome folded in - the input shape metrics expect."""
    rows = []
    for fx in FIXTURES:
        ep = to_episode(fx)
        rec = ep.to_record()
        # gold_label is a belastbare source; unknown outcomes stay unknown (never coerced)
        if fx.task_outcome is not Outcome.UNKNOWN:
            ev = OutcomeEvent(episode_id=rec["episode_id"], outcome=fx.task_outcome,
                              outcome_source="gold_label", outcome_cycle=0, resolved_tick=0,
                              outcome_refs=(fx.id,))
            eff, resolved = ev.to_record()["outcome"], True
        else:
            eff, resolved = "unknown", False
        rows.append({**rec, "effective_outcome": eff, "resolved": resolved})
    return rows


def evaluate() -> dict:
    """Task accuracy (over ATTEMPTED items) vs metacognitive accuracy (oracle) - and the
    fixtures that show the two diverge."""
    attempted = [f for f in FIXTURES if f.task_outcome in (Outcome.SUCCESS, Outcome.FAILURE)]
    task_correct = [f for f in attempted if f.task_outcome is Outcome.SUCCESS]
    metacog_ok = [f for f in FIXTURES if f.metacog_ok]
    good_task_bad_meta = [f.id for f in FIXTURES
                          if f.answerable and f.task_outcome is not Outcome.FAILURE
                          and not f.metacog_ok]
    bad_task_good_meta = [f.id for f in FIXTURES
                          if (not f.answerable) and f.metacog_ok]
    return {
        "n_fixtures": len(FIXTURES),
        "n_attempted": len(attempted),
        "task_accuracy": round(len(task_correct) / len(attempted), 4) if attempted else None,
        "metacog_accuracy": round(len(metacog_ok) / len(FIXTURES), 4),
        "good_task_bad_metacog": good_task_bad_meta,
        "bad_task_good_metacog": bad_task_good_meta,
    }


__all__ = ["Fixture", "FIXTURES", "to_episode", "joined_rows", "evaluate"]
