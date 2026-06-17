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
from joni.autonomy.trial_event_schema import RULE_V2_HASH


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
        "measurement": {"metric_name": "misclass", "baseline_value": 0.40,
                        "intervention_value": 0.44, "effect_size": 0.04, "uncertainty": 0.02,
                        "confidence_interval": [0.02, 0.06], "nested": {"runs": [1, 2, 3]}},
        "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": RULE_V2_HASH,
                     "verdict": "no_benefit"},
    }
    p.update(kw)
    if "decision" not in kw:                         # keep the recorded verdict consistent
        p["decision"] = dict(p["decision"], verdict=p["epistemic_result"])
    return p


def _payload(**kw):
    return _full_v3(**kw)


def _record(core, payload, *, proposer="kevin"):
    # the only writable trial event is SEALED v4 - seal a v3 body before submit so these
    # recording-mechanics + structural-validation tests run on the real write path. Non-v3 schema
    # values are left untouched so the version-rejection test still exercises the gate.
    if payload.get("schema_version") == "method_trial_recorded_v3":
        from joni.autonomy.trial_event_schema import seal_payload
        payload = seal_payload(payload)
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
    oid = core.all(ObjectType.METHOD_TRIAL_EVENT)[0].id
    before = hashing.snapshot_hash(core)
    core._objects[oid].epistemic_authority = "authoritative"   # white-box: tamper the STORED object
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


# -- 4. an unsupported / non-writable schema version --------------------------------------------- #
def test_unknown_schema_version_is_rejected_and_not_stored():
    core = _core()
    d = _record(core, _payload(schema_version="method_trial_recorded_v5"))
    assert not d.accepted and "not a writable trial-event format" in d.reason
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
    oid = core.all(ObjectType.METHOD_TRIAL_EVENT)[0].id
    stored = core._objects[oid]                            # white-box: corrupt the STORED object
    stored.canonical_payload = stored.canonical_payload.replace("no_benefit", "success")  # tamper
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


# -- decision must not contradict measurement / override the estimand / be ill-formed ------------ #
def test_decision_effect_contradicting_measurement_is_rejected():
    core = _core()
    p = _payload(epistemic_result="success")
    p["measurement"] = dict(p["measurement"], effect_size=-0.20)
    p["decision"] = dict(p["decision"], effect_size=0.20)       # contradicts the measurement
    d = _record(core, p)
    assert not d.accepted and "contradict the measurement" in d.reason


def test_decision_minimum_effect_overriding_estimand_is_rejected():
    core = _core()
    p = _payload(epistemic_result="success")
    p["estimand"] = dict(p["estimand"], minimum_effect=0.50)    # pre-registered threshold
    p["measurement"] = dict(p["measurement"], effect_size=0.20)
    p["decision"] = dict(p["decision"], effect_size=0.20, minimum_effect=0.10)   # lowered post-hoc
    d = _record(core, p)
    assert not d.accepted and "minimum_effect must equal" in d.reason


def test_reversed_confidence_interval_is_rejected():
    core = _core()
    p = _payload()
    p["decision"] = dict(p["decision"], confidence_interval=[0.30, 0.10])
    d = _record(core, p)
    assert not d.accepted and "lower bound must be <= upper" in d.reason


def test_nan_measurement_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], effect_size=float("nan"))
    d = _record(core, p)
    assert not d.accepted and "finite" in d.reason


def test_infinity_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], uncertainty=float("inf"))
    d = _record(core, p)
    assert not d.accepted and "finite" in d.reason


def test_negative_uncertainty_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], uncertainty=-0.1)
    d = _record(core, p)
    assert not d.accepted and "uncertainty must be >= 0" in d.reason


def test_metric_name_not_matching_estimand_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], metric_name="other_metric")
    d = _record(core, p)
    assert not d.accepted and "metric_name must equal" in d.reason


# -- round 5: measurement owns the interval; raw values must imply the effect -------------------- #
def test_decision_supplied_confidence_interval_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"])
    p["measurement"].pop("confidence_interval", None)
    p["decision"] = dict(p["decision"], confidence_interval=[0.02, 0.06])   # interval in DECISION
    d = _record(core, p)
    assert not d.accepted and "confidence_interval must live in the measurement" in d.reason


def test_decision_interval_diverging_from_measurement_is_rejected():
    core = _core()
    p = _payload()
    p["decision"] = dict(p["decision"], confidence_interval=[0.10, 0.30])   # != measurement CI
    d = _record(core, p)
    assert not d.accepted and "must equal measurement.confidence_interval" in d.reason


def test_effect_not_implied_by_baseline_intervention_is_rejected():
    core = _core()
    p = _payload()
    # baseline 0.40, intervention 0.20 imply -0.20 (higher_is_better) but +0.04 is stored.
    p["measurement"] = dict(p["measurement"], baseline_value=0.40, intervention_value=0.20)
    d = _record(core, p)
    assert not d.accepted and "inconsistent with baseline/intervention" in d.reason


def test_effect_outside_its_confidence_interval_is_rejected():
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], confidence_interval=[0.20, 0.40])  # 0.04 not inside
    d = _record(core, p)
    assert not d.accepted and "must lie within" in d.reason


# -- uncertainty is UNINTERPRETED for rule_v2: not cross-checked against the CI ------------------ #
def test_uncertainty_is_uninterpreted_and_not_cross_checked_with_the_ci():
    # without a declared uncertainty_kind there is no scientifically-defined relation to the CI, so
    # the gate does NOT invent one: a large uncertainty alongside a valid CI is accepted, and the
    # rule decides solely from the CI.
    core = _core()
    p = _payload()
    p["measurement"] = dict(p["measurement"], baseline_value=0.40, intervention_value=0.60,
                            effect_size=0.20, uncertainty=100.0, confidence_interval=[0.12, 0.28])
    p["epistemic_result"] = "success"
    p["decision"] = dict(p["decision"], verdict="success")
    assert _record(core, p).accepted


# -- round 7: a real verdict needs the measurement its declared rule requires -------------------- #
def test_success_without_effect_size_is_rejected():
    core = _core()
    p = _payload(epistemic_result="success")
    p["measurement"] = dict(p["measurement"], effect_size=None, confidence_interval=[0.12, 0.28])
    d = _record(core, p)
    assert not d.accepted and "requires measurement.effect_size" in d.reason


def test_real_result_without_confidence_interval_is_rejected_for_rule_v2():
    core = _core()
    p = _payload()      # no_benefit under rule_v2
    p["measurement"] = dict(p["measurement"])
    p["measurement"]["confidence_interval"] = None
    d = _record(core, p)
    assert not d.accepted and "requires measurement.confidence_interval" in d.reason


def test_full_rule_v2_measurement_is_accepted():
    core = _core()
    assert _record(core, _payload()).accepted     # effect_size + CI present


def test_not_evaluated_still_allows_empty_measurement():
    core = _core()
    p = _payload(trial_id="ne", epistemic_result="not_evaluated", execution_status="failed",
                 failure_kind="timeout", protocol_status="unknown",
                 measurement={"metric_name": None, "baseline_value": None,
                              "intervention_value": None, "effect_size": None,
                              "uncertainty": None, "confidence_interval": None})
    assert _record(core, p).accepted
