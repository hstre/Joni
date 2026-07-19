"""P1 acceptance: a generalised real trial runs an arbitrary method through the P0 sandbox and the
verdict rests on the metric alone, with a mandatory negative control. The concrete second trial
(unit-canonicalised equality) is a real procedure that beats a naive string baseline."""
from __future__ import annotations

import sys

import pytest

from joni.method_trial import sandbox_trial as st

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                                reason="runs solvers in the POSIX sandbox")

_BRIDGE_FIELDS = ("method_id", "task_set", "task_set_sha", "metric", "lower_is_better",
                  "baseline", "intervention", "delta", "effect_se", "confidence_interval",
                  "min_effect", "affinities", "processor_model", "evaluation_mode")


def test_unit_method_beats_the_baseline_and_passes():
    r = st.run(st.unit_equality_spec())
    assert r["intervention"] == 0.0            # the method solves every frozen case
    assert r["baseline"] > 0.3                 # the string baseline misses the unit-equal pairs
    assert r["delta"] >= 0.15 and r["passed"] is True
    assert r["evaluation_mode"] == "sandbox_trial_v1"


def test_negative_control_shows_no_real_effect():
    r = st.run(st.unit_equality_spec())
    assert r["negative_control_delta"] < r["min_effect"]   # the sham is not a comparable win


def test_result_carries_every_bridge_field():
    r = st.run(st.unit_equality_spec())
    for k in _BRIDGE_FIELDS:
        assert k in r, k


def test_a_method_with_no_advantage_does_not_pass():
    spec = st.unit_equality_spec()
    null = st.TrialSpec(method_id="null", task_set="x", cases=spec.cases,
                        baseline_src=spec.baseline_src, intervention_src=spec.baseline_src,
                        negative_control_src=spec.negative_control_src)
    r = st.run(null)
    assert r["delta"] == 0.0 and r["passed"] is False       # same solver -> no measurable gain


def test_a_crashing_intervention_counts_every_case_wrong():
    spec = st.unit_equality_spec()
    crash = st.TrialSpec(method_id="crash", task_set="x", cases=spec.cases[:4],
                         baseline_src=spec.baseline_src,
                         intervention_src="def solve(p):\n    raise RuntimeError('boom')\n",
                         negative_control_src=spec.negative_control_src)
    r = st.run(crash)
    assert r["intervention"] == 1.0 and r["passed"] is False


def test_task_set_sha_is_deterministic_and_short():
    a, b = st.unit_equality_spec().sha(), st.unit_equality_spec().sha()
    assert a == b and len(a) == 16


def test_record_runs_end_to_end_through_the_bridge():
    # the P1 acceptance: a second real trial runs and is sealed via the existing bridge path
    # (the same writer the conflict trial uses). Fail-open, so it always reports it ran.
    from joni.autonomy.core_state import CoreState, seed_core
    out = st.record(CoreState(seed_core()), st.unit_equality_spec(), run_id="test")
    assert out["ran"] is True
    assert out["result"]["method_id"] == "unit-canonicalised-equality"
    assert out["result"]["passed"] is True
