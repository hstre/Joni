"""The discovery report: confirmed vs candidate edges, and the 'new' count."""
from __future__ import annotations

from joni.solution_space import DeepMethodTrial, discovery_report
from joni.solution_space.discovery import _in_holdout


def _split(n):
    tr, ho, i = [], [], 0
    while len(tr) < n or len(ho) < n:
        t = f"g{i}"
        (ho if _in_holdout(t, 30) else tr).append(t)
        i += 1
    return tr[:n], ho[:n]


def test_empty_history_confirms_nothing():
    rep = discovery_report([])
    assert rep["n_trials"] == 0 and rep["n_confirmed"] == 0 and rep["confirmed"] == []


def test_report_separates_confirmed_from_candidates():
    train, hold = _split(8)
    trials = (
        [DeepMethodTrial("reduction", g, "success", gap_kind="gk_x") for g in train + hold]
        + [DeepMethodTrial("inclusion_exclusion", g, "no_benefit", gap_kind="gk_x")
           for g in train + hold]
    )
    rep = discovery_report(trials, min_support=4, min_rate=0.6)
    confirmed = {(r["method_kind"], r["gap_kind"]) for r in rep["confirmed"]}
    assert ("reduction", "gk_x") in confirmed             # held up on holdout
    assert rep["n_confirmed_new"] >= 1                    # gk_x is not in the a-priori taxonomy
    assert ("counting", "gk_x") not in confirmed          # the failing edge is not confirmed


def test_train_only_edge_is_a_candidate_not_confirmed():
    train, _ = _split(10)
    rep = discovery_report(
        [DeepMethodTrial("reduction", g, "success", gap_kind="gk_y") for g in train], min_support=4)
    assert rep["n_confirmed"] == 0                         # no holdout support
    cand = {(r["method_kind"], r["gap_kind"]) for r in rep["candidates_unconfirmed"]}
    assert ("reduction", "gk_y") in cand
