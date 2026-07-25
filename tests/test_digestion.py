"""Priority 2: intake is coupled to digestion. New intake is permitted only when a test, a
Streitfrage, or a Hindsight review happened within the grace window; deterministic backpressure
that engages only when digestion stalls and never deadlocks (a fresh start always permits)."""
from __future__ import annotations

import json

from joni.autonomy import digestion


def test_digested_this_cycle_recognises_real_work():
    assert digestion.digested_this_cycle({"sandbox_trials": [{"verdict": "benefit"}]}) is True
    assert digestion.digested_this_cycle({"skill_retrials": [{"verdict": "benefit"}]}) is True
    assert digestion.digested_this_cycle({"hindsight": {"reviews_triggered": 3}}) is True
    # mere condensation / an empty cycle is not digestion
    assert digestion.digested_this_cycle({"disputes": [{"size": 5}]}) is False
    assert digestion.digested_this_cycle({"hindsight": {"reviews_triggered": 0}}) is False
    assert digestion.digested_this_cycle({}) is False


def test_intake_permitted_engages_only_after_digestion_stalls(tmp_path):
    p = tmp_path / "digestion.json"
    # no history yet -> a fresh window always permits (never freezes a cold start)
    assert digestion.intake_permitted(5, path=p) is True
    # digestion happened at cycle 10 -> permitted at 10 and 11 (within grace 1), blocked at 12
    p.write_text(json.dumps({"last_digested_cycle": 10}))
    assert digestion.intake_permitted(10, path=p) is True
    assert digestion.intake_permitted(11, path=p) is True
    assert digestion.intake_permitted(12, path=p) is False        # stalled beyond grace -> blocked


def test_note_records_the_marker_and_advances_only_on_digestion(tmp_path):
    p = tmp_path / "digestion.json"
    ext = {"hindsight": {"reviews_triggered": 2}}
    st = digestion.note(7, ext, path=p)
    assert st["last_digested_cycle"] == 7 and st["digested_this_cycle"] is True
    assert ext["digestion"]["total_digested"] == 1
    # a dry next cycle does NOT advance the marker (so intake will start to close if it persists)
    st2 = digestion.note(8, {}, path=p)
    assert st2["last_digested_cycle"] == 7 and st2["digested_this_cycle"] is False
    assert st2["total_cycles"] == 2 and st2["total_digested"] == 1
    assert json.loads(p.read_text())["last_digested_cycle"] == 7


def test_coupling_never_deadlocks_a_fresh_start(tmp_path):
    # first cycle: no marker -> intake permitted; digestion happens -> marker set -> still permitted
    p = tmp_path / "digestion.json"
    assert digestion.intake_permitted(1, path=p) is True
    digestion.note(1, {"sandbox_trials": [{"verdict": "no_benefit"}]}, path=p)
    assert digestion.intake_permitted(2, path=p) is True


def test_note_and_permit_are_fail_open_without_a_path():
    assert digestion.note(1, {}, path=None) is not None            # no crash without a store
    assert digestion.intake_permitted(1, path=None) is True
