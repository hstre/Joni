"""Replay / legacy-coexistence / trial_id-uniqueness for METHOD_TRIAL_RECORDED (Package A).

Proves, against frozen journals, that the new append-only event path replays identically, coexists
with the legacy METHOD_TRIAL_RECORD path without either touching the other, stays idempotent across
save/load, fails CLOSED on an unknown operator, and that trial_id uniqueness holds under the actual
(synchronous, serial, non-reentrant) submit model - plus an explicit BOUNDARY test showing the
guarantee depends on that non-reentrancy. No interpretation, no counter migration.
"""

import copy

import pytest

import desi_layer9 as l9
from desi_layer9 import ObjectType, hashing, persistence
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9 import core as core_mod
from desi_layer9.core import JournalEntry
from desi_layer9.provenance import Provenance


def _core():
    return l9.Layer9()


def _payload(**kw):
    p = {
        "trial_id": "trial:001", "schema_version": "method_trial_recorded_v3",
        "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7"],
        "scope_id": "qtt", "method_id": "m_causal", "method_variant": "v2", "method_version": 1,
        "implementation_id": "impl-A", "model": "deepseek-chat", "model_family": "deepseek",
        "sampling": {"temperature": 0}, "task_set_id": "ts", "task_sample_id": "s1",
        "baseline_id": "bl", "evaluator_id": "ev", "affinities": ["causal"],
        "attribution_level": "variant", "attribution_strength": "none",
        "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
        "epistemic_result": "no_benefit",
        "estimand": {"outcome_metric": "misclass", "contrast": "intervention_minus_baseline",
                     "direction": "higher_is_better", "minimum_effect": 0.10,
                     "decision_rule_id": "rule_v2"},
        "measurement": {"metric_name": "misclass", "baseline_value": 0.4,
                        "intervention_value": 0.39, "effect_size": 0.04, "uncertainty": 0.02},
        "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": "sha256:test",
                     "verdict": "no_benefit", "effect_size": 0.04,
                     "confidence_interval": [0.01, 0.07], "minimum_effect": 0.10},
    }
    p.update(kw)
    if "decision" not in kw:
        p["decision"] = dict(p["decision"], verdict=p["epistemic_result"])
    return p


def _record(core, payload):
    return core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED, payload=payload, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")), actor="kevin")


def _make_method(core):
    core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_PROPOSE,
        payload={"name": "m", "summary": "s", "applicable_to": ["causal"]}, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")))
    return core.all(ObjectType.METHOD)[0]


def _legacy_trial(core, mid, success, run_id):
    return core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORD, payload={"success": success, "run_id": run_id},
        proposer="kevin", provenance=Provenance.from_model(external=False, model_id="kevin"),
        target_objects=(mid,)), actor="kevin")


def _roundtrip_journal(core):
    """Freeze and thaw the journal exactly as persistence does, then replay."""
    frozen = [JournalEntry.from_dict(e.to_dict()) for e in core.journal]
    return persistence.replay(frozen)


# -- 1-3. coexistence: each world replays identically and never touches the other ---------------- #
def test_only_legacy_journal_replays_and_has_no_new_events():
    core = _core()
    m = _make_method(core)
    _legacy_trial(core, m.id, True, "r1")
    _legacy_trial(core, m.id, False, "r2")
    r = _roundtrip_journal(core)
    assert hashing.snapshot_hash(r) == hashing.snapshot_hash(core)
    assert r.get(m.id).success_count == 1 and r.get(m.id).failure_count == 1
    assert r.method_trial_events() == []


def test_only_new_journal_replays_and_has_no_counter_effect():
    core = _core()
    m = _make_method(core)
    _record(core, _payload(trial_id="t:a"))
    _record(core, _payload(trial_id="t:b", epistemic_result="success"))
    r = _roundtrip_journal(core)
    assert r.method_trial_events() == core.method_trial_events()
    assert hashing.snapshot_hash(r) == hashing.snapshot_hash(core)
    mm = r.get(m.id)
    assert mm.success_count == 0 and mm.failure_count == 0 and mm.trial_count == 0


def test_mixed_journal_keeps_the_two_worlds_separate_through_replay():
    core = _core()
    m = _make_method(core)
    _legacy_trial(core, m.id, True, "r1")
    _record(core, _payload(trial_id="t:new"))
    _legacy_trial(core, m.id, True, "r2")
    r = _roundtrip_journal(core)
    assert hashing.snapshot_hash(r) == hashing.snapshot_hash(core)
    assert r.get(m.id).success_count == 2                       # only legacy counts
    evs = r.method_trial_events()
    assert len(evs) == 1 and evs[0]["payload"]["trial_id"] == "t:new"   # only new events


# -- 4. new software replays an old (legacy-only) journal ---------------------------------------- #
def test_new_software_replays_an_old_journal_unchanged():
    core = _core()
    m = _make_method(core)
    _legacy_trial(core, m.id, True, "r1")
    old_doc = persistence.to_doc(core)                          # an "old" persisted state
    restored = persistence.from_doc(old_doc)                    # new software loads it
    assert restored.get(m.id).success_count == 1
    assert restored.method_trial_events() == []


# -- 5. older software meeting an unknown new operator fails CLOSED ------------------------------ #
def test_old_software_fails_closed_on_unknown_operator():
    # an older runtime's Operator enum cannot represent the new value -> from_dict raises at LOAD,
    # never silently drops or misinterprets the entry.
    raw = {"operator": "method_trial_recorded_FUTURE", "proposal_type": "method_proposal",
           "payload": {}, "proposer": "kevin", "provenance": {}, "target_objects": [],
           "actor": "kevin", "governance_approved": False}
    with pytest.raises(ValueError):
        JournalEntry.from_dict(raw)


def test_known_operator_without_handler_is_rejected_in_the_gate(monkeypatch):
    # if a build knows the operator but lacks the handler, the gate rejects it (audited), mints
    # nothing, and replay can continue - no silent acceptance.
    core = _core()
    monkeypatch.delitem(core_mod._HANDLERS, OP.METHOD_TRIAL_RECORDED, raising=False)
    d = _record(core, _payload())
    assert not d.accepted and "not implemented" in d.reason
    assert core.method_trial_events() == []


# -- 6-7. idempotency / uniqueness survive save/load --------------------------------------------- #
def test_identical_retry_after_save_load_creates_no_duplicate(tmp_path):
    core = _core()
    _record(core, _payload(trial_id="T-9"))
    persistence.save(core, tmp_path / "s.json")
    reloaded = persistence.load(tmp_path / "s.json")
    d = _record(reloaded, copy.deepcopy(_payload(trial_id="T-9")))   # retry after restart
    assert d.accepted and "idempotent_existing" in d.reason
    assert len(reloaded.all(ObjectType.METHOD_TRIAL_EVENT)) == 1


def test_divergent_payload_same_id_after_save_load_is_rejected(tmp_path):
    core = _core()
    _record(core, _payload(trial_id="T-9"))
    persistence.save(core, tmp_path / "s.json")
    reloaded = persistence.load(tmp_path / "s.json")
    d = _record(reloaded, _payload(trial_id="T-9", epistemic_result="not_evaluated",
                                   protocol_status="invalid"))
    assert not d.accepted and "conflict" in d.reason.lower()
    assert len(reloaded.all(ObjectType.METHOD_TRIAL_EVENT)) == 1


# -- 8. trial_id uniqueness and the concurrency BOUNDARY ----------------------------------------- #
def test_sequential_submits_are_unique_under_the_real_serial_model():
    # submit is synchronous, serial and non-reentrant (no async/threads/locks in core/persistence),
    # so the lookup-then-mint runs atomically within ONE submit: a second identical submit finds the
    # first and records nothing.
    core = _core()
    _record(core, _payload(trial_id="T-1"))
    _record(core, copy.deepcopy(_payload(trial_id="T-1")))
    assert len(core.all(ObjectType.METHOD_TRIAL_EVENT)) == 1


def test_BOUNDARY_forced_reentrancy_would_break_uniqueness():
    # This documents the LIMIT of the guarantee: the uniqueness check is not a store-level atomic
    # constraint - it relies on submit being non-reentrant/serial. If we artificially interleave a
    # second submit AFTER the lookup but BEFORE the first mint commits, two objects appear for one
    # trial_id. In-process this interleave cannot occur; a future multi-writer store MUST add an
    # atomic unique constraint on trial_id (see docs/PROTECTION_ZONES.md / replay notes).
    core = _core()
    orig_mint = core._mint
    fired = {"x": False}

    def racing_mint(cls, otype, p, actor, **fields):
        if otype is ObjectType.METHOD_TRIAL_EVENT and not fired["x"]:
            fired["x"] = True
            core._mint = orig_mint                              # the reentrant call mints normally
            _record(core, copy.deepcopy(_payload(trial_id="T-race")))
        return orig_mint(cls, otype, p, actor, **fields)

    core._mint = racing_mint
    _record(core, _payload(trial_id="T-race"))
    # boundary: only the serial, non-reentrant submit model prevents this double-mint.
    assert len(core.all(ObjectType.METHOD_TRIAL_EVENT)) == 2
