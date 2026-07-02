"""(b) The operator cycle: propose -> apply (injected) -> grade by resolution -> record."""
from __future__ import annotations

from joni.solution_space import DeepMethodProposal
from joni.solution_space.operator_cycle import (
    grade_by_resolution,
    open_conflict_ids,
    run_operator_cycle,
)
from joni.solution_space.trial_store import load_trials


def test_grade_by_resolution_reads_observed_state():
    assert grade_by_resolution("X1", {"X1"}, set()) == "success"          # resolved
    assert grade_by_resolution("X1", {"X1"}, {"X1"}) == "no_benefit"      # still open
    assert grade_by_resolution("X1", {"X1"}, set(), errored=True) == "technical_failure"
    assert grade_by_resolution("X1", set(), set()) == "unknown"       # wasn't open to begin with


class _FakeConflict:
    def __init__(self, cid):
        self.id = cid


class _FakeCore:
    def __init__(self, conflict_ids):
        self._ids = set(conflict_ids)

    def open_conflicts(self):
        return [_FakeConflict(i) for i in sorted(self._ids)]


def _canned_propose(core):
    return [DeepMethodProposal(
        target="conflict:X1", method_id="reduction", method_name="Reduction",
        core_question="q", method_kind="reduction", reason=(), expected_information_gain="high",
        priority=1.0, gap_kind="contradiction")]


def test_open_conflict_ids_reads_the_core():
    assert open_conflict_ids(_FakeCore({"A", "B"})) == {"A", "B"}


def test_cycle_records_success_when_apply_resolves_the_gap(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    core = _FakeCore({"X1"})

    def apply_resolve(c, proposal):
        c._ids.discard("X1")                     # the injected creative step resolves the conflict

    trial = run_operator_cycle(core, p, apply_resolve, propose=_canned_propose)
    assert trial.result == "success" and trial.method_id == "reduction"
    assert trial.target == "X1" and trial.gap_kind == "contradiction"
    assert load_trials(p) == [trial]             # persisted for Baustein C


def test_cycle_records_no_benefit_when_apply_is_a_noop(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    trial = run_operator_cycle(_FakeCore({"X1"}), p, lambda c, pr: None, propose=_canned_propose)
    assert trial.result == "no_benefit"


def test_cycle_records_technical_failure_when_apply_raises(tmp_path):
    p = str(tmp_path / "trials.jsonl")

    def boom(c, pr):
        raise RuntimeError("apply blew up")

    trial = run_operator_cycle(_FakeCore({"X1"}), p, boom, propose=_canned_propose)
    assert trial.result == "technical_failure"


def test_cycle_no_proposals_records_nothing(tmp_path):
    p = str(tmp_path / "trials.jsonl")
    assert run_operator_cycle(_FakeCore(set()), p, lambda c, pr: None, propose=lambda c: []) is None
    assert load_trials(p) == []
