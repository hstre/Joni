"""Read-only trial-event projector: three separated axes + dataset sufficiency.

Frozen tests. The projector separates (1) event_usability, (2) decision_status, (3)
dataset_sufficiency. A single rule-verified event is usable and reproducible but does NOT make the
dataset sufficient; "verified" is a measured_candidate, never authoritative; an unsupported schema
is surfaced distinctly (projector limitation, not scientific judgement). No writer, no production
events, no Kevin consumer; legacy counters are never read as trial history.
"""

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9.provenance import Provenance
from joni.autonomy.trial_event_projector import project_trial_events
from joni.autonomy.trial_event_schema import RULE_V2_HASH


def _core():
    return l9.Layer9()


def _op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


def _open_conflict(core):
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x reduces y", "topic": "t"},
                    ptype=PT.CLAIM_PROPOSAL))
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x not", "topic": "t"}, ptype=PT.CLAIM_PROPOSAL))
    a, b = (c.id for c in core.all(l9.ObjectType.CLAIM))
    core.submit(_op(OP.CONFLICT_OPEN, {"claim_ids": [a, b], "severity": "hard"},
                    target_objects=(a, b)))
    return core.open_conflicts()[0].id


def _est(min_effect=0.10):
    return {"outcome_metric": "misclass", "contrast": "intervention_minus_baseline",
            "direction": "higher_is_better", "minimum_effect": min_effect,
            "decision_rule_id": "rule_v2"}


def _payload(trial_id, result, *, target="X17", scope="qtt", variant="v1", family="deepseek",
             impl="impl-A", task="ts1", evaluator="ev1", rule_hash=RULE_V2_HASH, effect=0.18,
             ci=(0.12, 0.24), min_effect=0.10, claim_ids=("C-7",)):
    return {
        "trial_id": trial_id, "schema_version": "method_trial_recorded_v3",
        "target_type": "conflict", "target_id": target, "claim_ids": list(claim_ids),
        "scope_id": scope, "method_id": "m_causal", "method_variant": variant, "method_version": 1,
        "implementation_id": impl, "model": "m-" + family, "model_family": family,
        "task_set_id": "tset", "task_sample_id": task, "baseline_id": "bl",
        "evaluator_id": evaluator, "affinities": ["causal"],
        "attribution_level": "variant", "attribution_strength": "none",
        "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
        "epistemic_result": result, "estimand": _est(min_effect),
        "measurement": {"metric_name": "misclass", "baseline_value": 0.40,
                        "intervention_value": 0.22, "effect_size": effect, "uncertainty": 0.03},
        "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": rule_hash,
                     "verdict": result, "effect_size": effect, "confidence_interval": list(ci),
                     "minimum_effect": min_effect},
    }


def _no_benefit(trial_id, **kw):
    return _payload(trial_id, "no_benefit", effect=0.04, ci=(0.01, 0.07), **kw)


def _harmful(trial_id, **kw):
    return _payload(trial_id, "harmful", effect=-0.18, ci=(-0.24, -0.12), **kw)


def _record(core, payload):
    return core.submit(l9.make_proposal(
        PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED, payload=payload, proposer="kevin",
        provenance=Provenance.from_model(external=False, model_id="kevin")), actor="kevin")


def _event(proj, trial_id):
    return [e for e in proj["events"] if e["trial_id"] == trial_id][0]


class _StubCore:
    """A core that returns hand-crafted envelopes (to exercise schema versions a real core would
    refuse to store) and no open conflicts."""

    def __init__(self, envelopes):
        self._e = envelopes

    def method_trial_events(self):
        return self._e

    def open_conflicts(self):
        return []


# -- MANDATORY: unknown rule hash -> registered, unverifiable, no weight, still visible --------- #
def test_success_with_unknown_rule_hash_is_registered_but_unverifiable():
    core = _core()
    _record(core, _payload("t:succ", "success", rule_hash="sha256:bogus"))
    e = _event(project_trial_events(core), "t:succ")
    assert e["record_status"] == "registered" and e["event_usability"] == "usable"
    assert e["decision_status"] == "unverifiable" and e["epistemic_weight"] == "none"
    assert e["reported_result"] == "success"            # not counted as success, not removed


# -- 1. a single verified success does NOT make the dataset sufficient --------------------------- #
def test_single_verified_success_stays_insufficient():
    core = _core()
    cid = _open_conflict(core)
    _record(core, _payload("t:ok", "success", target=cid))
    proj = project_trial_events(core)
    e = _event(proj, "t:ok")
    assert e["decision_status"] == "verified"
    ds = proj["dataset_sufficiency"]
    assert ds["rule_verified_events"] == 1
    assert ds["covered_open_conflicts"] == [cid]        # the conflict IS covered...
    assert ds["verdict"] == "insufficient"              # ...but one variant is not enough
    assert any("independent" in r for r in ds["reasons"])


# -- 2. events in another scope/conflict don't make the TARGET conflict sufficient --------------- #
def test_other_scope_events_do_not_satisfy_the_target_conflict():
    core = _core()
    cid = _open_conflict(core)                           # the target, left WITHOUT trials
    _record(core, _no_benefit("a", target="OTHER", variant="v1", family="deepseek", impl="iA"))
    _record(core, _no_benefit("b", target="OTHER", variant="v2", family="openai", impl="iB",
                              task="ts2", evaluator="ev2"))
    ds = project_trial_events(core)["dataset_sufficiency"]
    assert cid in ds["open_conflicts_without_trial_history"]
    assert ds["verdict"] == "insufficient"


# -- 3. a rule-verified event remains non-authoritative ------------------------------------------ #
def test_verified_event_is_a_measured_candidate_not_authoritative():
    core = _core()
    _record(core, _payload("t:ok", "success"))
    e = _event(project_trial_events(core), "t:ok")
    assert e["record_authority"] == "authoritative"
    assert e["decision_status"] == "verified"
    assert e["epistemic_authority"] == "none"
    assert e["epistemic_weight"] == "measured_candidate"


# -- 4. enough conflict-scoped, independent history reaches SUFFICIENT_FOR_GAP_ANALYSIS --------- #
def test_sufficient_for_gap_analysis_with_independent_history():
    core = _core()
    cid = _open_conflict(core)
    # two INDEPENDENT verified variants (distinct family/impl/task/evaluator) on the SAME conflict.
    _record(core, _no_benefit("a", target=cid, variant="v1", family="deepseek", impl="iA",
                              task="ts1", evaluator="ev1"))
    _record(core, _no_benefit("b", target=cid, variant="v2", family="openai", impl="iB",
                              task="ts2", evaluator="ev2"))
    ds = project_trial_events(core)["dataset_sufficiency"]
    assert ds["covered_open_conflicts"] == [cid] and ds["analysis_ready_conflicts"] == [cid]
    assert ds["independent_method_variants"] >= 2 and ds["comparison_possible"] is True
    assert {"target_id": cid, "scope_id": "qtt"} in ds["analysis_ready_conflict_scopes"]
    assert ds["verdict"] == "SUFFICIENT_FOR_GAP_ANALYSIS"


def test_two_scopes_of_one_conflict_do_not_jointly_satisfy():
    # the SAME conflict, but one independent variant in EACH of two different scopes -> NOT enough;
    # sufficiency is per (conflict, scope), so neither scope reaches the threshold alone.
    core = _core()
    cid = _open_conflict(core)
    _record(core, _no_benefit("a", target=cid, scope="scope1", variant="v1", family="deepseek",
                              impl="iA", task="ts1", evaluator="ev1"))
    _record(core, _no_benefit("b", target=cid, scope="scope2", variant="v2", family="openai",
                              impl="iB", task="ts2", evaluator="ev2"))
    ds = project_trial_events(core)["dataset_sufficiency"]
    assert ds["covered_open_conflicts"] == [cid]            # the conflict has trials...
    assert ds["analysis_ready_conflict_scopes"] == []       # ...but no single scope is ready
    assert ds["verdict"] == "insufficient"


# -- 5. an unsupported schema stays visible as a projector limitation ---------------------------- #
def test_unsupported_schema_is_visible_not_silently_dropped():
    env = {"object_id": "MTE-9", "schema_version": "method_trial_recorded_v4",
           "record_authority": "authoritative", "epistemic_authority": "none",
           "payload": {"trial_id": "t:future", "schema_version": "method_trial_recorded_v4",
                       "target_type": "conflict", "target_id": "X1", "epistemic_result": "success"}}
    e = project_trial_events(_StubCore([env]))["events"][0]
    assert e["record_status"] == "registered"
    assert e["projection_status"] == "unsupported_schema"
    assert e["decision_status"] == "not_evaluated" and e["epistemic_weight"] == "none"


# -- 6. adding a relevant trial changes sufficiency in a traceable way -------------------------- #
def test_adding_a_relevant_trial_changes_sufficiency_causally():
    core = _core()
    cid = _open_conflict(core)
    _record(core, _no_benefit("a", target=cid, variant="v1", family="deepseek", impl="iA",
                              task="ts1", evaluator="ev1"))
    before = project_trial_events(core)["dataset_sufficiency"]
    assert before["verdict"] == "insufficient" and before["independent_method_variants"] == 1
    # add a SECOND independent variant on the same conflict -> sufficiency flips, traceably.
    _record(core, _no_benefit("b", target=cid, variant="v2", family="openai", impl="iB",
                              task="ts2", evaluator="ev2"))
    after = project_trial_events(core)["dataset_sufficiency"]
    assert after["independent_method_variants"] == 2
    assert after["verdict"] == "SUFFICIENT_FOR_GAP_ANALYSIS"


# -- sufficiency does NOT depend on successes: negative results count too ------------------------ #
def test_sufficiency_from_independent_negative_results_without_global_demotion():
    core = _core()
    cid = _open_conflict(core)
    # two INDEPENDENT, verified, NON-success variants (no_benefit + harmful) on the same conflict.
    _record(core, _no_benefit("a", target=cid, variant="v1", family="deepseek", impl="iA",
                              task="ts1", evaluator="ev1"))
    _record(core, _harmful("b", target=cid, variant="v2", family="openai", impl="iB",
                           task="ts2", evaluator="ev2"))
    proj = project_trial_events(core)
    ds = proj["dataset_sufficiency"]
    # negative results give enough comparative depth -> sufficient...
    assert ds["verdict"] == "SUFFICIENT_FOR_GAP_ANALYSIS"
    assert ds["independent_method_variants"] >= 2
    assert "DESi added value demonstrated" in ds["interpretation"]["does_not_mean"]
    # ...the attribution is SCOPE-BOUND (tied to this conflict+scope), never a global demotion...
    for a in proj["affinity_attributions"]:
        assert a["target_id"] == cid and a["scope_id"] == "qtt"
    # ...and nothing is epistemically confirmed: both stay measured_candidate, authority none.
    weights = {e["trial_id"]: e for e in proj["events"]}
    for tid in ("a", "b"):
        assert weights[tid]["epistemic_weight"] == "measured_candidate"
        assert weights[tid]["epistemic_authority"] == "none"


def test_projection_is_deterministic():
    core = _core()
    cid = _open_conflict(core)
    _record(core, _payload("t:ok", "success", target=cid))
    _record(core, _payload("t:succ", "success", rule_hash="sha256:bogus"))
    assert project_trial_events(core) == project_trial_events(core)


# -- the projector NEVER crashes on an accepted/registered payload ------------------------------- #
def _env(payload, oid="MTE-x"):
    return {"object_id": oid, "schema_version": payload.get("schema_version"),
            "record_authority": "authoritative", "epistemic_authority": "none", "payload": payload}


def test_malformed_payload_is_invalid_not_a_crash_and_others_still_project():
    bad = {"trial_id": "bad", "schema_version": "method_trial_recorded_v3",
           "target_type": "conflict", "target_id": "X", "scope_id": "s", "method_id": "m",
           "method_variant": "v", "method_version": "abc",          # would crash int()
           "execution_status": "completed", "protocol_status": "valid",
           "epistemic_result": "not_evaluated"}
    good = _payload("good", "success")
    proj = project_trial_events(_StubCore([_env(bad, "MTE-1"), _env(good, "MTE-2")]))
    b = _event(proj, "bad")
    assert b["projection_status"] == "invalid_payload" and b["event_usability"] == "unusable"
    assert b["epistemic_weight"] == "none" and b["record_status"] == "registered"
    assert any(e["trial_id"] == "good" for e in proj["events"])     # the good one still projects


def test_malformed_confidence_interval_stays_visible_not_crashing():
    bad = _payload("ci", "no_benefit")
    bad["decision"] = dict(bad["decision"], confidence_interval="not-a-pair")
    proj = project_trial_events(_StubCore([_env(bad, "MTE-1")]))
    e = _event(proj, "ci")
    assert e["projection_status"] in ("invalid_payload", "projected")
    assert e["epistemic_weight"] == "none"                          # never silently counted


# -- incomplete independence metadata can never reach sufficiency -------------------------------- #
def test_incomplete_independence_metadata_does_not_reach_sufficiency():
    core = _core()
    cid = _open_conflict(core)
    # v1 has unknown implementation/model-family/task-sample; v2 concrete. unknown != independent.
    _record(core, _no_benefit("a", target=cid, scope="qtt", variant="v1", family="unknown",
                              impl="unknown", task="unknown", evaluator="e1"))
    _record(core, _no_benefit("b", target=cid, scope="qtt", variant="v2", family="openai",
                              impl="iB", task="t2", evaluator="e2"))
    ds = project_trial_events(core)["dataset_sufficiency"]
    assert ds["analysis_ready_conflict_scopes"] == [] and ds["verdict"] == "insufficient"


# -- the projector must not grant 'verified' to a decision that contradicts the measurement ------ #
def test_decision_measurement_contradiction_projects_as_inconsistent():
    payload = _payload("c", "success")
    payload["measurement"] = dict(payload["measurement"], effect_size=-0.20)
    payload["decision"] = dict(payload["decision"], effect_size=0.20)   # contradicts measurement
    e = project_trial_events(_StubCore([_env(payload, "MTE-1")]))["events"][0]
    assert e["decision_status"] == "inconsistent" and e["epistemic_weight"] == "none"


def test_threshold_override_projects_as_inconsistent():
    payload = _payload("c", "success")
    payload["estimand"] = dict(payload["estimand"], minimum_effect=0.50)
    payload["decision"] = dict(payload["decision"], minimum_effect=0.10)   # lowered post-hoc
    e = project_trial_events(_StubCore([_env(payload, "MTE-1")]))["events"][0]
    assert e["decision_status"] == "inconsistent" and e["epistemic_weight"] == "none"
