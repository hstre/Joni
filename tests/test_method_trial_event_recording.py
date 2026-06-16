"""Layer-9 append-only METHOD_TRIAL_RECORDED recording (the minimal first core step).

Proves the new event path is lossless, immutable, idempotent, inert (never touches the legacy
counters or promotion), provenance-rich, and replay-identical - and that it carries record vs
epistemic authority separately so a generic reader can never mistake a recorded trial for a
confirmed scientific result. No writer/projector/DESi/Kevin wiring; no legacy-counter change.
"""

import copy

import desi_layer9 as l9
from desi_layer9 import ObjectType
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9.provenance import Provenance


def _core():
    return l9.Layer9()


def _full_v3(**kw):
    """A complete, structurally-valid v3 payload (with a nested measurement field for the
    deep-copy tests). ``decision.verdict`` is kept consistent with ``epistemic_result``."""
    p = {
        "trial_id": "trial:001", "schema_version": "method_trial_recorded_v3",
        "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
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
                        "intervention_value": 0.39, "effect_size": 0.04, "uncertainty": 0.02,
                        "nested": {"runs": [1, 2, 3]}},
        "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": "sha256:test",
                     "verdict": "no_benefit", "effect_size": 0.04,
                     "confidence_interval": [0.01, 0.07], "minimum_effect": 0.10},
    }
    p.update(kw)
    if "decision" not in kw:                         # keep the recorded verdict consistent
        p["decision"] = dict(p["decision"], verdict=p["epistemic_result"])
    return p


def _payload(**kw):
    return _full_v3(**kw)


def _record(core, payload, *, proposer="kevin"):
    return core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED, payload=payload, proposer=proposer,
        provenance=Provenance.from_model(external=False, model_id="kevin")), actor=proposer)


def _make_method(core):
    core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_PROPOSE,
        payload={"name": "m", "summary": "s", "applicable_to": ["causal"]}, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")))
    return core.all(ObjectType.METHOD)[0]


# -- 1. append -------------------------------------------------------------------------------- #
def test_append_records_one_immutable_event():
    core = _core()
    d = _record(core, _payload())
    assert d.accepted
    evs = core.method_trial_events()
    assert len(evs) == 1
    e = evs[0]
    assert e["payload"]["trial_id"] == "trial:001" and e["object_id"].startswith("MTE-")
    assert e["record_authority"] == "authoritative" and e["epistemic_authority"] == "none"


# -- 2. read: deep-copy isolation (nested payload cannot be mutated through the API) ---------- #
def test_read_returns_independent_deep_copies():
    core = _core()
    _record(core, _payload())
    first = core.method_trial_events()[0]["payload"]
    first["measurement"]["nested"]["runs"].append(999)        # mutate the returned copy
    first["epistemic_result"] = "success"
    again = core.method_trial_events()[0]["payload"]
    assert again["measurement"]["nested"]["runs"] == [1, 2, 3]   # stored state untouched
    assert again["epistemic_result"] == "no_benefit"


def test_original_payload_reference_cannot_mutate_stored_event():
    core = _core()
    src = _payload()
    _record(core, src)
    src["measurement"]["nested"]["runs"].append(42)           # mutate the ORIGINAL after submit
    src["scope_id"] = "tampered"
    stored = core.method_trial_events()[0]["payload"]
    assert stored["measurement"]["nested"]["runs"] == [1, 2, 3] and stored["scope_id"] == "qtt"


# -- 3. idempotency on trial_id -------------------------------------------------------------- #
def test_identical_retry_creates_no_duplicate():
    core = _core()
    _record(core, _payload())
    d2 = _record(core, copy.deepcopy(_payload()))             # exact retry
    assert d2.accepted and "idempotent" in d2.reason
    assert len(core.method_trial_events()) == 1               # still one record


def test_same_trial_id_different_payload_is_rejected():
    core = _core()
    _record(core, _payload())
    d = _record(core, _payload(epistemic_result="not_evaluated", protocol_status="invalid"))
    assert not d.accepted and "conflict" in d.reason.lower()
    assert len(core.method_trial_events()) == 1


def test_idempotent_retry_is_audited_distinctly():
    core = _core()
    _record(core, _payload(trial_id="T-42"))
    d2 = _record(core, copy.deepcopy(_payload(trial_id="T-42")))
    # accepted, but explicitly tagged and naming the existing record - not a silent no-op.
    assert d2.accepted and "idempotent_existing" in d2.reason and "MTE-1" in d2.reason
    assert len(core.all(ObjectType.METHOD_TRIAL_EVENT)) == 1     # no second object
    # the LEDGER distinguishes the new recording from the retry...
    recorded = [e for e in core.ledger if e.operator == OP.METHOD_TRIAL_RECORDED]
    decisions = [e.decision for e in recorded]
    assert decisions.count("accepted") == 1 and decisions.count("idempotent_existing") == 1
    # ...so counting real recordings (accepted + an output object) yields 1, never 2.
    new_records = [e for e in recorded if e.decision == "accepted" and e.output_refs]
    assert len(new_records) == 1


# -- hash semantics: precisely named, never a bare "integrity hash" -------------------------- #
def test_payload_hash_and_record_object_hash_are_distinct_and_correct():
    import hashlib

    from desi_layer9 import hashing
    from desi_layer9.core import trial_event_hashes
    core = _core()
    _record(core, _payload())
    o = core.all(ObjectType.METHOD_TRIAL_EVENT)[0]
    h = trial_event_hashes(o)
    assert h["payload_hash"] == "sha256:" + hashlib.sha256(
        o.canonical_payload.encode("utf-8")).hexdigest()
    assert h["record_object_hash"] == "sha256:" + hashlib.sha256(
        hashing.object_canonical(o).encode("utf-8")).hexdigest()
    env = core.method_trial_events()[0]["hashes"]
    assert set(env) == {"payload_hash", "record_object_hash"} and env == h


def test_record_object_hash_covers_provenance_and_authorities_payload_hash_does_not():
    from desi_layer9.core import trial_event_hashes
    core = _core()
    _record(core, _payload())
    o = core.all(ObjectType.METHOD_TRIAL_EVENT)[0]
    base = trial_event_hashes(o)
    o.created_by = "someone_else"               # actor
    o.epistemic_authority = "authoritative"     # both authority levels are covered...
    o.schema_version = "tampered"               # ...and schema_version
    after = trial_event_hashes(o)
    assert after["payload_hash"] == base["payload_hash"]              # payload content unchanged
    assert after["record_object_hash"] != base["record_object_hash"]  # full record changed


def test_record_object_hash_is_the_same_material_snapshot_uses():
    from desi_layer9 import hashing
    core = _core()
    _record(core, _payload())
    o = core.all(ObjectType.METHOD_TRIAL_EVENT)[0]
    before = hashing.snapshot_hash(core)
    o.epistemic_authority = "authoritative"     # a field the record_object_hash covers
    assert hashing.snapshot_hash(core) != before  # snapshot folds in the same object material


def test_record_object_hash_shares_one_serializer_with_snapshot():
    # PROOF that there are no two parallel field lists: the record_object_hash preimage is EXACTLY
    # the per-object material snapshot_hash composes from (the same object_canonical function), so a
    # change to the snapshot serializer cannot leave the two claiming to hash the same record.
    import hashlib

    from desi_layer9 import hashing
    from desi_layer9.core import trial_event_hashes
    core = _core()
    _record(core, _payload())
    o = core.all(ObjectType.METHOD_TRIAL_EVENT)[0]
    preimage = hashing.object_canonical(o)
    assert trial_event_hashes(o)["record_object_hash"] == \
        "sha256:" + hashlib.sha256(preimage.encode("utf-8")).hexdigest()
    snapshot_parts = [hashing.object_canonical(x)
                      for x in sorted(core.objects.values(), key=lambda y: y.id)]
    assert preimage in snapshot_parts          # the very same serialization feeds snapshot_hash


def test_one_canonical_serializer_feeds_both_record_and_snapshot(monkeypatch):
    # Architecture contract: canonical_object_representation(object) feeds BOTH record_object_hash
    # and snapshot_hash - one function, not two that happen to agree today. Proven structurally:
    from desi_layer9 import core as core_mod
    from desi_layer9 import hashing
    # (1) the record-hash path references the SAME function object as the hashing module.
    assert core_mod.object_canonical is hashing.object_canonical
    # (2) the snapshot path resolves that one serializer dynamically: patch it -> snapshot changes.
    core = _core()
    _record(core, _payload())
    orig = hashing.object_canonical
    before = hashing.snapshot_hash(core)
    monkeypatch.setattr(hashing, "object_canonical", lambda o: "MARK|" + orig(o))
    assert hashing.snapshot_hash(core) != before


# -- 4. unknown schema version --------------------------------------------------------------- #
def test_unknown_schema_version_is_rejected_and_not_stored():
    core = _core()
    d = _record(core, _payload(schema_version="method_trial_recorded_v4"))
    assert not d.accepted and "unsupported schema_version" in d.reason
    assert core.method_trial_events() == []


def test_structural_forbidden_combination_is_rejected():
    core = _core()
    d = _record(core, _payload(execution_status="failed", failure_kind="timeout"))
    # failed + no_benefit is a forbidden structural combination
    assert not d.accepted and "non-completed execution" in d.reason


# -- 5. epistemic authority stays 'none' even for a success ---------------------------------- #
def test_success_event_is_recorded_but_not_epistemically_authoritative():
    core = _core()
    d = _record(core, _payload(trial_id="t:succ", epistemic_result="success"))
    assert d.accepted
    e = [x for x in core.method_trial_events() if x["payload"]["trial_id"] == "t:succ"][0]
    assert e["payload"]["epistemic_result"] == "success"
    assert e["record_authority"] == "authoritative" and e["epistemic_authority"] == "none"


# -- 6. inertness: legacy counters and promotion untouched ----------------------------------- #
def test_recording_events_never_touches_legacy_counters_or_promotion():
    core = _core()
    m = _make_method(core)
    before = (m.success_count, m.failure_count, m.trial_count, m.supporting_runs, m.failed_runs)
    for i in range(3):
        _record(core, _payload(trial_id=f"t{i}", epistemic_result="success"))
    m2 = core.get(m.id)
    after = (m2.success_count, m2.failure_count, m2.trial_count, m2.supporting_runs, m2.failed_runs)
    assert before == after                                    # counters completely inert
    assert len(core.method_trial_events()) == 3


def test_coexists_with_legacy_trial_record():
    core = _core()
    m = _make_method(core)
    core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORD, payload={"success": True, "run_id": "r1"},
        proposer="kevin", provenance=Provenance.from_model(external=False, model_id="kevin"),
        target_objects=(m.id,)))
    _record(core, _payload(trial_id="t:new"))
    m2 = core.get(m.id)
    assert m2.success_count == 1 and m2.trial_count == 1      # legacy reflects ONLY the legacy op
    trials = core.method_trial_events()
    assert len(trials) == 1                                   # new path reflects ONLY the new event
    assert trials[0]["payload"]["trial_id"] == "t:new"


# -- 7. replay / integrity ------------------------------------------------------------------- #
def test_replay_reconstructs_identical_events_and_hash():
    from desi_layer9 import hashing, persistence
    core = _core()
    _record(core, _payload(trial_id="t:a"))
    _record(core, _payload(trial_id="t:b", epistemic_result="success"))
    _record(core, copy.deepcopy(_payload(trial_id="t:a")))    # idempotent retry in the journal too
    before_hash = hashing.snapshot_hash(core)
    before_events = core.method_trial_events()

    replayed = persistence.replay(core.journal)
    assert hashing.snapshot_hash(replayed) == before_hash
    assert replayed.method_trial_events() == before_events
    ok, problems = hashing.verify_chain(replayed)
    assert ok, problems


def test_in_place_tampering_is_detectable_and_not_in_the_replayable_truth():
    from desi_layer9 import hashing, persistence
    core = _core()
    _record(core, _payload())
    clean = hashing.snapshot_hash(persistence.replay(core.journal))   # the replayable truth
    assert hashing.snapshot_hash(core) == clean
    obj = core.all(ObjectType.METHOD_TRIAL_EVENT)[0]
    obj.canonical_payload = obj.canonical_payload.replace("no_benefit", "success")  # tamper
    # the live state no longer matches what the journal deterministically reproduces -> detectable.
    assert hashing.snapshot_hash(core) != clean
    # ...and the tamper never entered the replayable truth: replay from the journal is original.
    replayed = persistence.replay(core.journal)
    assert replayed.method_trial_events()[0]["payload"]["epistemic_result"] == "no_benefit"


# -- transitionless object is registered --------------------------------------------------------- #
def test_method_trial_event_is_registered_transitionless():
    from desi_layer9 import transitions
    from desi_layer9.enums import Status
    assert ObjectType.METHOD_TRIAL_EVENT in transitions.TRANSITIONS
    assert transitions.allowed(ObjectType.METHOD_TRIAL_EVENT, Status.ACTIVE) == frozenset()


# -- core gate validates the FULL v3 structural schema, not just a torso ------------------------- #
def test_minimal_apparent_v3_payload_is_rejected():
    core = _core()
    d = _record(core, {"trial_id": "minimal", "schema_version": "method_trial_recorded_v3",
                       "target_type": "conflict", "target_id": "X",
                       "execution_status": "completed", "protocol_status": "valid",
                       "epistemic_result": "success"})
    assert not d.accepted and "missing required field" in d.reason
    assert core.method_trial_events() == []          # never stored


def test_full_v3_payload_is_accepted():
    core = _core()
    assert _record(core, _payload()).accepted
    assert len(core.method_trial_events()) == 1


def test_unknown_extra_field_is_consciously_allowed_and_preserved():
    # extra fields are NOT interpreted but ARE preserved verbatim in the immutable record.
    core = _core()
    assert _record(core, _payload(trial_id="x", extra_field={"k": [1, 2]})).accepted
    assert core.method_trial_events()[0]["payload"]["extra_field"] == {"k": [1, 2]}


def test_real_verdict_without_decision_rule_hash_is_rejected():
    core = _core()
    p = _payload()
    p["decision"] = dict(p["decision"], decision_rule_hash="")    # real result, empty hash
    d = _record(core, p)
    assert not d.accepted and "decision_rule_hash" in d.reason


def test_not_evaluated_may_be_stored_without_measurement_values():
    core = _core()
    p = _payload(trial_id="ne", epistemic_result="not_evaluated", execution_status="failed",
                 failure_kind="timeout", protocol_status="unknown",
                 measurement={"metric_name": None, "baseline_value": None,
                              "intervention_value": None, "effect_size": None, "uncertainty": None})
    assert _record(core, p).accepted
    assert core.method_trial_events()[0]["payload"]["epistemic_result"] == "not_evaluated"


# -- core gate type-checks every field the projector later casts --------------------------------- #
def test_non_integer_method_version_is_rejected():
    core = _core()
    d = _record(core, _payload(method_version="abc"))
    assert not d.accepted and "method_version" in d.reason
    assert core.method_trial_events() == []


def test_non_integer_ledger_tick_is_rejected():
    core = _core()
    d = _record(core, _payload(ledger_tick="oops"))
    assert not d.accepted and "ledger_tick" in d.reason


def test_malformed_confidence_interval_is_rejected():
    core = _core()
    p = _payload()
    p["decision"] = dict(p["decision"], confidence_interval=[0.1])     # not a [low, high] pair
    d = _record(core, p)
    assert not d.accepted and "confidence_interval" in d.reason


def test_non_numeric_measurement_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], effect_size="big")
    d = _record(core, p)
    assert not d.accepted and "effect_size" in d.reason


def test_real_result_requires_independence_provenance():
    core = _core()
    d = _record(core, _payload(implementation_id=""))      # empty independence field
    assert not d.accepted and "implementation_id" in d.reason
