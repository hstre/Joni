"""Foundation of the metacognition supervisor: strict schema, append-only audit, honest metrics."""

import pytest

from joni.autonomy.metacognition import audit, metrics
from joni.autonomy.metacognition.models import (
    Episode,
    KnowledgeBoundary,
    Outcome,
    OutcomeEvent,
    SelectedControl,
)


def _ep(**over):
    base = dict(
        cycle=1, created_tick=10, task_family="method_gate", decision_seam="emerge.method",
        subject_refs=("m:1",), signal_sources=("layer9", "quality"),
        signals={"evidence_coverage": 0.5, "n_conflicts": 0.0}, predicted_success=0.7,
        confidence_source="deterministic:signal_blend", knowledge_boundary=KnowledgeBoundary.INSIDE,
        selected_control=SelectedControl.PROCEED, expected_cost=0.0, route="deterministic",
        model_or_tool="none", configuration_hash="cfg123",
    )
    base.update(over)
    return Episode(**base)


# ---- schema / validation ---------------------------------------------------------

def test_deterministic_episode_id_is_stable():
    assert _ep().episode_id() == _ep().episode_id()
    assert _ep().episode_id() != _ep(cycle=2).episode_id()


def test_values_outside_unit_interval_are_rejected():
    with pytest.raises(ValueError):
        _ep(predicted_success=1.5)
    with pytest.raises(ValueError):
        _ep(signals={"x": 2.0})


def test_wrong_types_are_rejected():
    with pytest.raises(ValueError):
        _ep(cycle="1")
    with pytest.raises(ValueError):
        _ep(predicted_success="high")
    with pytest.raises(ValueError):
        _ep(expected_cost=-1.0)


def test_closed_enumerations_are_enforced():
    with pytest.raises(ValueError):
        Outcome("great")
    with pytest.raises(ValueError):
        KnowledgeBoundary("dunno")
    with pytest.raises(ValueError):
        SelectedControl("wing_it")


def test_unknown_schema_fields_are_rejected_on_load():
    rec = _ep().to_record()
    rec["smuggled"] = 1
    with pytest.raises(ValueError):
        Episode.from_record(rec)


def test_roundtrip_record_is_faithful():
    ep = _ep()
    back = Episode.from_record(ep.to_record())
    assert back.to_record() == ep.to_record()
    assert back.outcome is Outcome.UNKNOWN                    # default, not coerced


# ---- outcome events: append-only, never coerced ----------------------------------

def test_outcome_event_rejects_unknown_and_non_robust_source():
    with pytest.raises(ValueError):
        OutcomeEvent(episode_id="e", outcome=Outcome.UNKNOWN, outcome_source="ci_result",
                     outcome_cycle=2, resolved_tick=20)
    with pytest.raises(ValueError):
        OutcomeEvent(episode_id="e", outcome=Outcome.SUCCESS, outcome_source="vibes",
                     outcome_cycle=2, resolved_tick=20)


def test_late_outcome_is_a_new_event_and_never_rewrites_the_episode(tmp_path):
    log = audit.AuditLog(tmp_path / "metacognition.jsonl")
    ep = _ep()
    eid = log.append_episode(ep)
    assert log.pending_episode_ids() == {eid}                 # unknown stays pending
    raw_before = (tmp_path / "metacognition.jsonl").read_text()

    log.append_outcome(OutcomeEvent(episode_id=eid, outcome=Outcome.FAILURE,
                                    outcome_source="later_layer9_status", outcome_cycle=9,
                                    resolved_tick=90, outcome_refs=("m:1",)))
    # the ORIGINAL episode line is unchanged - the outcome is a separate appended event
    assert raw_before in (tmp_path / "metacognition.jsonl").read_text()
    assert log.pending_episode_ids() == set()
    joined = log.joined()
    assert joined[0]["effective_outcome"] == "failure" and joined[0]["resolved"] is True
    # the stored episode record itself still says unknown (append-only, not mutated)
    assert log.episodes()[0]["outcome"] == "unknown"


# ---- metrics: honest refusal, no coercion ----------------------------------------

def test_missing_outcome_is_not_a_failure():
    rows = [{"predicted_success": 0.9, "effective_outcome": "unknown",
             "selected_control": "proceed"}]
    assert metrics.binary_pairs(rows) == []                   # unknown excluded, not counted as 0


def test_calibration_refuses_below_minimum(monkeypatch):
    monkeypatch.setenv("JONI_METACOG_MIN_OUTCOMES", "30")
    rows = [{"predicted_success": 0.8, "effective_outcome": "success"}] * 5
    out = metrics.calibration(rows)
    assert out["verdict"] == "insufficient_evidence" and out["n_binary_outcomes"] == 5


def test_calibration_computes_with_enough_data(monkeypatch):
    monkeypatch.setenv("JONI_METACOG_MIN_OUTCOMES", "4")
    rows = ([{"predicted_success": 0.9, "effective_outcome": "success"}] * 3 +
            [{"predicted_success": 0.2, "effective_outcome": "failure"}] * 3)
    out = metrics.calibration(rows)
    assert out["verdict"] == "computed" and out["n_binary_outcomes"] == 6
    assert 0.0 <= out["brier"] <= 1.0 and 0.0 <= out["ece"] <= 1.0
    assert out["auroc"] is not None                           # both classes present
    assert metrics.ECE_BINS == 10                             # fixed, documented bins


def test_auroc_is_none_without_both_classes():
    assert metrics.auroc([(0.9, 1), (0.8, 1)]) is None


def test_coverage_surfaces_unknown_and_monitor_dark():
    rows = [
        {"resolved": True, "effective_outcome": "success", "knowledge_boundary": "inside"},
        {"resolved": False, "effective_outcome": "unknown", "knowledge_boundary": "monitor_dark"},
    ]
    cov = metrics.coverage(rows)
    assert cov["outcome_coverage"] == 0.5 and cov["unknown_rate"] == 0.5
    assert cov["monitor_dark_rate"] == 0.5
