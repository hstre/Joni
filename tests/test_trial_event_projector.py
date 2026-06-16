"""Read-only trial-event projector (the controlled stored-event -> external-evaluation connection).

Frozen tests. The projector reads ONLY method_trial_events(), verifies decision verdicts by the
registered rule (id + hash), applies the versioned independence policy, and - crucially - keeps
registered-but-unverifiable evidence VISIBLE rather than silently dropping it. No writer, no
production events, no Kevin consumer. Legacy counters are never read as trial history.
"""

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9.provenance import Provenance
from joni.autonomy.trial_event_projector import project_trial_events
from joni.autonomy.trial_event_schema import RULE_V2_HASH


def _core():
    return l9.Layer9()


def _est(min_effect=0.10):
    return {"outcome_metric": "misclass", "contrast": "intervention_minus_baseline",
            "direction": "higher_is_better", "minimum_effect": min_effect,
            "decision_rule_id": "rule_v2"}


def _payload(trial_id, result, *, rule_hash=RULE_V2_HASH, effect=0.18, ci=(0.12, 0.24),
             min_effect=0.10, **kw):
    p = {
        "trial_id": trial_id, "schema_version": "method_trial_recorded_v3",
        "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7"],
        "scope_id": "qtt", "method_id": "m_causal", "method_variant": "v2",
        "implementation_id": "impl-A", "model_family": "deepseek", "task_sample_id": "ts1",
        "evaluator_id": "ev1", "affinities": ["causal"],
        "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
        "epistemic_result": result, "estimand": _est(min_effect),
        "measurement": {"metric_name": "misclass", "baseline_value": 0.40,
                        "intervention_value": 0.22, "effect_size": effect, "uncertainty": 0.03},
        "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": rule_hash,
                     "verdict": result, "effect_size": effect, "confidence_interval": list(ci),
                     "minimum_effect": min_effect},
    }
    p.update(kw)
    return p


def _record(core, payload):
    return core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED, payload=payload, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")), actor="kevin")


def _event(proj, trial_id):
    return [e for e in proj["events"] if e["trial_id"] == trial_id][0]


# -- MANDATORY: registered but unknown decision-rule hash stays visible & unverifiable ----------- #
def test_success_with_unknown_rule_hash_is_registered_but_unverifiable():
    core = _core()
    _record(core, _payload("t:succ", "success", rule_hash="sha256:bogus"))
    proj = project_trial_events(core)
    e = _event(proj, "t:succ")
    assert e["record_status"] == "registered"
    assert e["decision_status"] == "unverifiable"
    assert e["epistemic_weight"] == "none"
    # NOT counted as success, NOT removed - it stays visible (negative transparency preserved).
    assert e["reported_result"] == "success"
    assert proj["verified_scope_bound_outcomes"] == []
    assert proj["data_sufficiency"]["verdict"].startswith("insufficient")
    assert proj["data_sufficiency"]["unverifiable_events"] == 1


# -- a verified success contributes; sufficiency flips ------------------------------------------ #
def test_verified_success_is_scope_bound_and_sufficient():
    core = _core()
    _record(core, _payload("t:ok", "success"))      # correct rule hash, consistent numbers
    proj = project_trial_events(core)
    e = _event(proj, "t:ok")
    assert e["decision_status"] == "verified" and e["epistemic_weight"] == "verified_scope_bound"
    assert proj["data_sufficiency"]["verdict"] == "sufficient"
    outs = proj["verified_scope_bound_outcomes"]
    assert len(outs) == 1 and outs[0]["outcome"] == "success" and outs[0]["scope_id"] == "qtt"


# -- a verdict the rule contradicts is flagged inconsistent, weight none, still visible ---------- #
def test_inconsistent_verdict_is_visible_with_no_weight():
    core = _core()
    # claims no_benefit, but a clearly-resolved negative effect under higher_is_better is harmful.
    _record(core, _payload("t:bad", "no_benefit", effect=-0.18, ci=(-0.24, -0.12)))
    proj = project_trial_events(core)
    e = _event(proj, "t:bad")
    assert e["decision_status"] == "inconsistent" and e["epistemic_weight"] == "none"
    assert e["record_status"] == "registered"        # still visible
    assert proj["data_sufficiency"]["inconsistent_events"] == 1


# -- a non-completed / not_evaluated event is registered, not_applicable, weight none ------------ #
def test_not_evaluated_event_is_registered_but_not_applicable():
    core = _core()
    payload = {"trial_id": "t:fail", "schema_version": "method_trial_recorded_v3",
               "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7"],
               "scope_id": "qtt", "method_id": "m", "method_variant": "v2",
               "execution_status": "failed", "failure_kind": "timeout",
               "protocol_status": "unknown", "epistemic_result": "not_evaluated"}
    _record(core, payload)
    proj = project_trial_events(core)
    e = _event(proj, "t:fail")
    assert e["record_status"] == "registered" and e["decision_status"] == "not_applicable"
    assert e["epistemic_weight"] == "none"


# -- empty: INSUFFICIENT, and legacy counters are NOT read as trial history ---------------------- #
def test_insufficient_when_no_events_and_legacy_counters_ignored():
    core = _core()
    # create a method and record a LEGACY trial (mutates counters) - the projector must ignore it.
    core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_PROPOSE,
        payload={"name": "m", "summary": "s", "applicable_to": ["causal"]}, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")))
    m = core.all(l9.ObjectType.METHOD)[0]
    core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORD, payload={"success": True, "run_id": "r1"},
        proposer="kevin", provenance=Provenance.from_model(external=False, model_id="kevin"),
        target_objects=(m.id,)), actor="kevin")
    assert core.get(m.id).success_count == 1          # legacy counter moved...
    proj = project_trial_events(core)
    assert proj["events"] == [] and proj["verified_scope_bound_outcomes"] == []
    # ...but the legacy trial is NOT counted as trial history.
    assert proj["data_sufficiency"]["verdict"].startswith("insufficient")


# -- determinism -------------------------------------------------------------------------------- #
def test_projection_is_deterministic():
    core = _core()
    _record(core, _payload("t:ok", "success"))
    _record(core, _payload("t:succ", "success", rule_hash="sha256:bogus"))
    assert project_trial_events(core) == project_trial_events(core)
