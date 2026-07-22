"""S0: a procedural episode (context, action, observation, robust outcome) is strictly validated,
built READ-ONLY from real measured signals, deterministically identified, and append-only. Nothing
is invented; 'unknown' stays 'unknown' (a resolved outcome needs a belastbare source)."""
from __future__ import annotations

import pytest

from joni.autonomy.metacognition.models import Outcome
from joni.method_trial import episodes


def _ep(**over):
    base = dict(context="benchmark:frozen_unit_equality_v1", action="apply_method:M-1",
                observation="delta=0.4 vs baseline", outcome=Outcome.SUCCESS,
                outcome_source="deterministic_checker", refs=("M-1",), cycle=3)
    base.update(over)
    return episodes.ProceduralEpisode(**base)


def test_a_valid_episode_round_trips_and_ids_deterministically():
    e = _ep()
    assert e.episode_id().startswith("ep-") and len(e.episode_id()) == 19
    assert episodes.ProceduralEpisode.from_record(e.to_record()).episode_id() == e.episode_id()
    assert e.flow_key() == ("benchmark:frozen_unit_equality_v1", "apply_method:M-1")
    assert e.is_resolved() is True


def test_unknown_stays_unknown():
    # a resolved outcome without a robust source is rejected - never silently upgraded
    with pytest.raises(ValueError):
        _ep(outcome=Outcome.SUCCESS, outcome_source="a_model_said_so")
    with pytest.raises(ValueError):
        _ep(outcome=Outcome.FAILURE, outcome_source="")
    # an 'unknown' episode is allowed, but may not claim a source it doesn't have
    pending = _ep(outcome=Outcome.UNKNOWN, outcome_source="")
    assert pending.is_resolved() is False
    with pytest.raises(ValueError):
        _ep(outcome=Outcome.UNKNOWN, outcome_source="deterministic_checker")


def test_strict_validation_rejects_bad_fields():
    with pytest.raises(ValueError):
        _ep(context="  ")                      # blank
    with pytest.raises(ValueError):
        _ep(refs=())                           # un-referenced: not built from real state
    with pytest.raises(ValueError):
        _ep(cycle=-1)                          # cycle >= 0
    with pytest.raises(ValueError):
        episodes.ProceduralEpisode.from_record({**_ep().to_record(), "surprise": 1})


def test_from_trial_maps_measured_verdicts_and_invents_nothing():
    benefit = episodes.from_trial(
        {"method": "M-1", "task_set": "frozen_unit_equality_v1", "verdict": "benefit",
         "delta": 0.4, "name": "unit-lens"}, cycle=2)
    assert benefit.outcome is Outcome.SUCCESS and benefit.outcome_source == "deterministic_checker"
    assert benefit.refs == ("M-1",) and "frozen_unit_equality_v1" in benefit.context
    assert episodes.from_trial({"method": "M-2", "verdict": "harmful", "delta": -0.3},
                               cycle=2).outcome is Outcome.FAILURE
    assert episodes.from_trial({"method": "M-3", "verdict": "no_benefit", "delta": 0.0},
                               cycle=2).outcome is Outcome.MIXED
    # not robustly classifiable -> NO episode (the method was never actually applied)
    assert episodes.from_trial({"method": "M-4", "verdict": "no_solver"}, cycle=2) is None
    assert episodes.from_trial({"verdict": "benefit", "delta": 0.4}, cycle=2) is None   # no method


def test_extract_from_run_reads_trials_and_retrials_readonly():
    ext = {"sandbox_trials": [{"method": "M-1", "task_set": "frozen_unit_equality_v1",
                               "verdict": "benefit", "delta": 0.4, "name": "unit-lens"},
                              {"method": "M-9", "verdict": "no_solver"}],   # skipped, no invention
           "skill_retrials": [{"method": "M-1", "skill_id": "skill-abc",
                               "task_set": "frozen_unit_equality_v1", "verdict": "harmful",
                               "delta": -0.2, "name": "M-1"}]}
    eps = episodes.extract_from_run(None, ext, cycle=5)
    assert len(eps) == 2                                        # the no_solver row produced nothing
    assert {e.outcome for e in eps} == {Outcome.SUCCESS, Outcome.FAILURE}
    retrial = next(e for e in eps if e.outcome is Outcome.FAILURE)
    assert "skill-abc" in retrial.refs                         # references the real skill id


def test_record_and_load_are_append_only_and_dedupe(tmp_path):
    store = tmp_path / "episodes.jsonl"
    e = _ep()
    assert episodes.record([e, e], store_path=store) == 1      # de-duped within the write
    assert episodes.record([_ep(cycle=4)], store_path=store) == 1
    loaded = episodes.load(store)
    assert len(loaded) == 2                                    # two distinct episodes, append-only
    # a malformed line is skipped, never fatal
    store.write_text(store.read_text() + "{ not json\n")
    assert len(episodes.load(store)) == 2


def test_record_missing_store_is_a_clean_noop(tmp_path):
    assert episodes.record([_ep()], store_path=None) == 0
    assert episodes.record([], store_path=tmp_path / "x.jsonl") == 0
    assert episodes.load(tmp_path / "nope.jsonl") == []
