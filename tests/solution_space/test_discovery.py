"""Baustein C — the discoverer, and its measurement against a known ground truth.

Verifies: a planted (method_kind, gap_kind) edge is recovered and confirmed; noise is rejected; the
HOLDOUT gate actually bites (a train-only edge is not confirmed); discovered edges feed back into
Baustein B; and the synthetic-ground-truth measurement recovers the truth with a low false-positive
rate (the falsification of the mechanism itself).
"""
from __future__ import annotations

from dataclasses import dataclass

from joni.solution_space import (
    DeepMethodTrial,
    discover_affinities,
    propose_operators,
    to_extra_affinities,
)
from joni.solution_space.discovery import _in_holdout
from joni.solution_space.discovery_measure import measure


def _trials_for(edge_kind_id, gap_kind, targets, result):
    return [DeepMethodTrial(method_id=edge_kind_id, target=t, result=result, gap_kind=gap_kind)
            for t in targets]


def _split_targets(n):
    """n gap ids split into (train, holdout) by the discoverer's own hash rule."""
    train, hold = [], []
    i = 0
    while len(train) < n or len(hold) < n:
        t = f"g{i}"
        (hold if _in_holdout(t, 30) else train).append(t)
        i += 1
    return train[:n], hold[:n]


def test_recovers_a_real_edge_and_rejects_noise():
    train, hold = _split_targets(8)
    # 'reduction' (kind=reduction) succeeds on gap-kind 'gk_x' on BOTH splits
    good = (_trials_for("reduction", "gk_x", train, "success")
            + _trials_for("reduction", "gk_x", hold, "success"))
    # 'inclusion_exclusion' (kind=counting) mostly FAILS on 'gk_x'
    noise = (_trials_for("inclusion_exclusion", "gk_x", train, "no_benefit")
             + _trials_for("inclusion_exclusion", "gk_x", hold, "no_benefit"))
    disc = discover_affinities(good + noise, min_support=4, min_rate=0.6)
    confirmed = {(d.method_kind, d.gap_kind) for d in disc if d.confirmed}
    assert ("reduction", "gk_x") in confirmed
    assert ("counting", "gk_x") not in confirmed
    # 'gk_x' is not in the a-priori taxonomy -> the edge is genuinely NEW
    assert next(d for d in disc if d.confirmed).is_new is True


def test_holdout_gate_rejects_a_train_only_edge():
    train, _ = _split_targets(10)
    # all successes, but ALL on train gaps -> no holdout support -> must NOT confirm
    disc = discover_affinities(_trials_for("reduction", "gk_y", train, "success"),
                               min_support=4, min_rate=0.6)
    cand = [d for d in disc if d.method_kind == "reduction" and d.gap_kind == "gk_y"]
    assert cand and cand[0].train_rate == 1.0 and cand[0].support_holdout == 0
    assert cand[0].confirmed is False


def test_discovered_edges_feed_back_into_baustein_b():
    @dataclass(frozen=True)
    class _C:
        id: str
        kind: str
        severity: str = "hard"
        unresolved_since: int = 0

    @dataclass(frozen=True)
    class _S:
        conflicts: tuple = ()
        provenance: object = None

    snap = _S(conflicts=(_C("G1", "gk_new"),))
    # without discovery: gk_new is unknown -> base table (no 'counting' emphasis)
    base = propose_operators(snap, top_k_per_gap=50)
    assert all(p.provenance is not None for p in base)
    extra = {"gk_new": (("counting", 0.95),)}          # a (pretend-)discovered strong edge
    with_disc = propose_operators(snap, top_k_per_gap=50, extra_kind_affinities=extra)
    got_counting = [p for p in with_disc if p.method_kind == "counting"]
    assert got_counting and max(p.priority for p in got_counting) > 0.9   # discovery raised it


def test_to_extra_affinities_uses_holdout_weight_and_only_confirmed():
    train, hold = _split_targets(8)
    disc = discover_affinities(
        _trials_for("reduction", "gk_z", train, "success")
        + _trials_for("reduction", "gk_z", hold, "success"), min_support=4)
    extra = to_extra_affinities(disc)
    assert "gk_z" in extra and extra["gk_z"][0][0] == "reduction"
    assert extra["gk_z"][0][1] >= 0.6                  # weight is the holdout rate


def test_measurement_recovers_truth_with_low_false_positive_rate():
    r = measure()                                       # clean regime p=.85/.12
    assert r["recall"] == 1.0                           # every planted edge recovered
    assert r["false_positive_rate"] == 0.0             # and no noise confirmed
    assert set(map(tuple, r["confirmed_edges"])) == set(map(tuple, r["true_edges"]))


def test_measurement_is_not_trivially_perfect_but_stays_fp_safe():
    # a no-signal world (noise everywhere) must confirm NOTHING (specificity of the gate)
    r = measure(true_edges=frozenset(), p_true=0.5, p_noise=0.12)
    assert r["tp"] == 0 and r["fp"] == 0
