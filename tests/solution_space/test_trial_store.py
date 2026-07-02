"""The deep-method trial ledger: append -> load round-trip, and discovery straight off the store."""
from __future__ import annotations

from joni.solution_space import DeepMethodTrial
from joni.solution_space.discovery import _in_holdout
from joni.solution_space.trial_store import discover_from_store, load_trials, record_trial


def test_empty_store_is_safe(tmp_path):
    p = str(tmp_path / "none.jsonl")
    assert load_trials(p) == []
    assert discover_from_store(p) == []


def test_round_trip_preserves_all_fields(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    t = DeepMethodTrial(method_id="reduction", target="g1", result="success", scope="s",
                        count=2, gap_kind="gk_a")
    record_trial(p, t)
    back = load_trials(p)
    assert len(back) == 1 and back[0] == t


def test_discovery_reads_straight_off_the_store(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    # split target ids so 'reduction' on gk_x has both train and holdout support, all successes
    train = [f"g{i}" for i in range(60) if not _in_holdout(f"g{i}", 30)][:8]
    hold = [f"g{i}" for i in range(60) if _in_holdout(f"g{i}", 30)][:8]
    for gid in train + hold:
        record_trial(p, DeepMethodTrial("reduction", gid, "success", gap_kind="gk_x"))
    disc = discover_from_store(p, min_support=4, min_rate=0.6)
    confirmed = [(d.method_kind, d.gap_kind) for d in disc if d.confirmed]
    assert ("reduction", "gk_x") in confirmed
