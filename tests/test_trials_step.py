"""Kevin trials Joni's shelf in-process each cycle - recorded, never promoted."""

import desi_layer9 as l9
from joni.autonomy import trials
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_no_op_without_kevin(monkeypatch):
    # Simulate Kevin not being installed: the step is a clean no-op.
    import builtins
    real_import = builtins.__import__

    def fake(name, *a, **k):
        if name == "kevin" or name.startswith("kevin."):
            raise ImportError("no kevin")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    cs = CoreState(l9.Layer9())
    out = trials.run_trials(cs, _Proto(), 0)
    assert out == {"trialed": 0, "succeeded": 0, "failed": 0, "activation_ready": 0}


def test_kevin_trials_the_methods_on_jonis_shelf():
    import pytest
    pytest.importorskip("kevin")
    cs = CoreState(l9.Layer9())
    mid = cs.propose_method(name="react-router",
                            summary="a declarative routing framework for the web",
                            applicable_to=("routing",), origin="https://github.com/x")
    proto = _Proto()
    out = trials.run_trials(cs, proto, 1)
    assert out["trialed"] == 1
    m = cs.core.get(mid)
    assert m.trial_count == 1
    assert m.status is l9.Status.CANDIDATE          # trialed, never promoted
    assert any(k == "trialed" for k, _ in proto.events)


def test_trials_dedup_within_the_same_run_id():
    import pytest
    pytest.importorskip("kevin")
    cs = CoreState(l9.Layer9())
    mid = cs.propose_method(name="five_whys", summary="a technique to chase a cause",
                            applicable_to=("routing",))
    trials.run_trials(cs, _Proto(), 3, run_id="same")
    trials.run_trials(cs, _Proto(), 3, run_id="same")     # same id -> no second trial
    assert cs.core.get(mid).trial_count == 1


def test_unproductive_methods_are_retired_after_enough_trials(monkeypatch):
    """Joni's Auftrag: the trial has a clear pass/FAIL criterion. An untried method gets its fair
    chance; once it has had enough trials with no measurable gain it is DISCARDED via the gate, so
    the shelf does not grow without ever maturing."""
    from joni.autonomy.core_state import seed_core
    cs = CoreState(seed_core())
    m1 = cs.propose_method(name="m1", summary="s", applicable_to=("routing",))
    cs.propose_method(name="m2", summary="s", applicable_to=("memory",))
    # a high bar: an untried method is NOT retired (it has not had its chance yet)
    monkeypatch.setenv("JONI_METHOD_MAX_TRIALS", "8")
    assert trials.retire_unproductive(cs, _Proto(), 1) == 0
    # trial budget exhausted with no net gain -> discarded, gate-recorded as REJECTED
    monkeypatch.setenv("JONI_METHOD_MAX_TRIALS", "0")
    assert trials.retire_unproductive(cs, _Proto(), 2, max_retire=5) == 2
    assert cs.core.get(m1).status.value == "rejected"
    # bounded per cycle
    monkeypatch.setenv("JONI_METHOD_MAX_TRIALS", "0")
    for _ in range(7):
        cs.propose_method(name="x", summary="s", applicable_to=("routing",))
    assert trials.retire_unproductive(cs, _Proto(), 3, max_retire=3) == 3


def test_real_method_trial_is_measured_and_distinct_from_the_mock():
    """The real protocol (kevin.real_trial) runs, stores a provenance-bearing result, and is kept
    separate from the synthetic simulator. Decision rests on the metric (provisional weight)."""
    ext: dict = {}
    cs = CoreState(l9.Layer9())
    out = trials.run_real_method_trial(cs, ext, _Proto(), 1)
    if not out.get("ran"):
        return                                      # kevin not installed -> clean no-op
    rt = ext["real_trial"]
    assert rt["evaluation_mode"] == "real_trial_protocol_v1"
    assert rt["epistemic_weight"] == "provisional"          # NOT 'none' (that's the mock)
    assert rt["baseline"] > rt["intervention"] and rt["passed"] is True
    assert rt["task_set_sha"] and rt["repetitions"] >= 1     # provenance present


def test_real_method_trial_is_recorded_as_a_sealed_event_and_projected():
    """The measured trial is written to the one authoritative core as a sealed v4 event (verdict by
    rule_v2) and projected into the DESi solution-space-gap view. Idempotent per content."""
    from joni.autonomy import kevin_trial_bridge as bridge
    ext: dict = {}
    cs = CoreState(l9.Layer9())
    out = trials.run_real_method_trial(cs, ext, _Proto(), 1)
    if not out.get("ran"):
        return                                      # kevin not installed -> clean no-op
    assert out["recorded"] is True
    assert ext["trial_events"]["count"] == 1
    assert ext["trial_events"]["last"]["verdict"] in ("success", "no_benefit", "harmful",
                                                      "inconclusive", "not_evaluated")
    # the stored event: authoritative record, but the verdict is NOT core-confirmed
    env = cs.core.method_trial_events()[0]
    assert env["record_authority"] == "authoritative"
    assert env["epistemic_authority"] == "none"
    # idempotent: a second identical run does not mint a second event
    trials.run_real_method_trial(cs, ext, _Proto(), 2)
    assert bridge.trial_event_count(cs) == 1


def test_the_writer_is_switchable(monkeypatch):
    """The trial-event writer crosses the irreversible journal boundary, so it is switchable
    (JONI_TRIAL_WRITER=0) without a code change - then nothing is recorded."""
    from joni.autonomy import kevin_trial_bridge as bridge
    monkeypatch.setenv("JONI_TRIAL_WRITER", "0")
    ext: dict = {}
    cs = CoreState(l9.Layer9())
    out = trials.run_real_method_trial(cs, ext, _Proto(), 1)
    if not out.get("ran"):
        return
    assert out["recorded"] is False
    assert bridge.trial_event_count(cs) == 0
