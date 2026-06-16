"""Acceptance proof for the METHOD_TRIAL_RECORDED schema PROPOSAL (v3, final review round).

Pins the contract BEFORE any core change. v3 closes the last places where metadata could become
evidence: a legacy success needs a VERIFIED artifact (not a run-id); affinity attribution needs a
VERSIONED independence policy (not a count/OR); and the epistemic VERDICT comes from a registered,
hashed rule evaluator, not a universal formula in the schema validator. Touches no core object.
"""

from joni.autonomy.trial_event_schema import (
    RULE_V2_HASH,
    Decision,
    Estimand,
    IndependencePolicy,
    LegacyValidation,
    Measurement,
    MethodTrialRecorded,
    aggregate,
    attribute_to_affinity,
    evaluate_decision,
    migrate_method,
    validate,
)

_EST = Estimand(outcome_metric="misclass_rate", direction="higher_is_better", minimum_effect=0.10,
                decision_rule_id="rule_v2")


def _meas(effect, unc=0.02, base=0.40, inter=0.30):
    return Measurement("misclass_rate", base, inter, effect_size=effect, uncertainty=unc)


def _dec(verdict, effect, ci, mn=0.10):
    return Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_HASH, verdict=verdict,
                    effect_size=effect, confidence_interval=ci, minimum_effect=mn)


def _ev(**kw) -> MethodTrialRecorded:
    base = dict(
        trial_id="t1", timestamp="2026-06-16T00:00:00Z", ledger_tick=1,
        target_type="conflict", target_id="X17", claim_ids=("C-7",), scope_id="qtt",
        method_id="m_causal", method_variant="v2", affinities=("causal",), estimand=_EST,
        execution_status="completed", protocol_status="valid",
        epistemic_result="not_evaluated", note="n/a")
    base.update(kw)
    return MethodTrialRecorded(**base)


# -- three-axis status model (carried from v2) --------------------------------------------------- #
def test_failed_execution_cannot_carry_a_result():
    bad = _ev(execution_status="failed", failure_kind="technical", epistemic_result="no_benefit")
    assert any("non-completed run has no result" in e for e in validate(bad))
    assert validate(_ev(execution_status="failed", failure_kind="timeout",
                        epistemic_result="not_evaluated")) == []


def test_failed_requires_a_failure_kind_and_vice_versa():
    assert any("failed' requires a failure_kind" in e
               for e in validate(_ev(execution_status="failed", epistemic_result="not_evaluated")))
    assert any("requires execution_status 'failed'" in e
               for e in validate(_ev(failure_kind="model")))


def test_invalid_protocol_carries_no_result():
    bad = _ev(protocol_status="invalid", epistemic_result="success",
              measurement=_meas(0.18), decision=_dec("success", 0.18, (0.1, 0.26)))
    assert any("protocol_status 'invalid' requires" in e for e in validate(bad))
    assert validate(_ev(protocol_status="invalid", epistemic_result="not_evaluated")) == []


# -- decision block: STRUCTURE in the validator, VERDICT in the rule evaluator ------------------- #
def test_validator_checks_structure_not_the_statistics():
    # a real result needs a registered rule id+hash and verdict == epistemic_result...
    no_rule = _ev(epistemic_result="no_benefit", measurement=_meas(0.04),
                  decision=Decision(verdict="no_benefit"))
    assert any("decision_rule_id AND decision_rule_hash" in e for e in validate(no_rule))
    mism = _ev(epistemic_result="no_benefit", measurement=_meas(0.04),
               decision=_dec("success", 0.04, (0.02, 0.06)))
    assert any("must equal epistemic_result" in e for e in validate(mism))
    # ...but the validator does NOT itself recompute the verdict from effect/uncertainty.
    ok = _ev(epistemic_result="no_benefit", measurement=_meas(0.04),
             decision=_dec("no_benefit", 0.04, (0.02, 0.06)))
    assert validate(ok) == []


def test_rule_evaluator_decides_the_verdict_and_flags_inconsistency():
    # a clearly-resolved NEGATIVE effect under higher_is_better is harmful, not no_benefit -
    # caught by the registered rule, not by the schema validator.
    ev = _ev(epistemic_result="no_benefit", measurement=_meas(-0.15),
             decision=_dec("no_benefit", -0.15, (-0.20, -0.10)))
    assert validate(ev) == []                      # structurally fine
    verdict = evaluate_decision(ev)
    assert verdict["status"] == "inconsistent" and verdict["computed"] == "harmful"


def test_unknown_rule_hash_blocks_a_trustworthy_verdict():
    ev = _ev(epistemic_result="success", measurement=_meas(0.18),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash="sha256:bogus",
                               verdict="success", effect_size=0.18,
                               confidence_interval=(0.12, 0.24), minimum_effect=0.10))
    assert validate(ev) == []                      # structure is fine...
    assert evaluate_decision(ev)["status"] == "unverifiable"   # ...but verdict is not trustworthy


def test_rule_verifies_a_consistent_success():
    ev = _ev(epistemic_result="success", measurement=_meas(0.18),
             decision=_dec("success", 0.18, (0.12, 0.24)))
    assert validate(ev) == [] and evaluate_decision(ev)["status"] == "verified"


def test_attribution_forbidden_on_raw_event():
    assert any("affinity-level is earned by aggregation only" in e
               for e in validate(_ev(attribution_level="affinity")))
    assert any("attribution_strength" in e for e in validate(_ev(attribution_strength="limited")))


# -- legacy migration: a VERIFIED artifact, never a run-id --------------------------------------- #
class _FakeMethod:
    id = "m_old"
    version = 1
    applicable_to = ("causal", "boundary")
    supporting_runs = ("kevin-c12", "kevin-real-7")
    failed_runs = ("kevin-c13",)
    success_count = 2
    failure_count = 1


def test_kevin_real_without_artifact_stays_not_evaluated():
    # even a 'kevin-real' run is NOT trusted on its name alone.
    evs = migrate_method(_FakeMethod())
    assert all(validate(e) == [] for e in evs)
    assert all(e.epistemic_result == "not_evaluated" for e in evs)
    assert any(e.legacy_reported_success for e in evs)


def test_verified_artifact_allows_only_weak_success():
    def resolver(run_id):
        if run_id.startswith("kevin-real"):
            return LegacyValidation(run_id=run_id, artifact_id="a1", artifact_hash="h1",
                                    protocol_id="real_trial_protocol_v1", evaluator_id="ev1",
                                    verification_status="verified")
        return None
    evs = migrate_method(_FakeMethod(), resolve_legacy_validation=resolver)
    assert all(validate(e) == [] for e in evs)
    succ = [e for e in evs if e.epistemic_result == "success"]
    assert len(succ) == 1 and succ[0].run_id.startswith("kevin-real")
    assert succ[0].legacy and succ[0].legacy_validation.is_verified()
    assert succ[0].scope_id == "unknown" and succ[0].method_variant == "unknown"
    assert all(e.epistemic_result != "no_benefit" for e in evs)   # old failure never demotes


def test_unverified_artifact_is_rejected_for_legacy_success():
    # a hand-built legacy 'success' without a verified artifact must fail validation.
    bad = _ev(legacy=True, legacy_reported_success=True, protocol_status="unknown",
              epistemic_result="success", legacy_validation=LegacyValidation(run_id="x"))
    assert any("requires a VERIFIED legacy_validation" in e for e in validate(bad))


# -- aggregation: scope separation, technical, harmful ------------------------------------------- #
def test_no_benefit_demotes_only_its_own_variant_scope():
    evs = [
        _ev(trial_id="a", scope_id="qtt", method_variant="v2", epistemic_result="no_benefit",
            measurement=_meas(0.04), decision=_dec("no_benefit", 0.04, (0.02, 0.06))),
        _ev(trial_id="b", scope_id="other", method_variant="v2", epistemic_result="not_evaluated",
            note="not run here"),
    ]
    cells = {(o.scope_id, o.method_variant): o.outcome for o in aggregate(evs)}
    assert cells[("qtt", "v2")] == "no_benefit" and cells[("other", "v2")] != "no_benefit"


def test_unusable_cell_is_not_a_negative_result():
    evs = [_ev(trial_id="a", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated")]
    assert aggregate(evs)[0].outcome == "technical_only"


def test_harmful_dominates_within_a_cell():
    evs = [
        _ev(trial_id="a", epistemic_result="success", measurement=_meas(0.18),
            decision=_dec("success", 0.18, (0.12, 0.24))),
        _ev(trial_id="b", epistemic_result="harmful", measurement=_meas(-0.15),
            decision=_dec("harmful", -0.15, (-0.20, -0.10))),
    ]
    assert aggregate(evs)[0].outcome == "harmful"


# -- affinity attribution: a VERSIONED independence policy, not a count -------------------------- #
def _neg(variant, *, model_family, impl, task="ts_shared", evaluator="ev_shared", conf=(),
         aff=("causal",)):
    return _ev(trial_id=f"t-{variant}", method_variant=variant, model_family=model_family,
               implementation_id=impl, task_sample_id=task, evaluator_id=evaluator,
               affinities=aff, confounders=conf, epistemic_result="no_benefit",
               measurement=_meas(0.04), decision=_dec("no_benefit", 0.04, (0.02, 0.06)))


def _independent_pair(aff=("causal",)):
    return [_neg("v1", model_family="deepseek", impl="impl-A", task="ts1", evaluator="ev1",
                 conf=("noise_a",), aff=aff),
            _neg("v2", model_family="openai", impl="impl-B", task="ts2", evaluator="ev2",
                 conf=("noise_b",), aff=aff)]


def test_two_insufficiently_independent_variants_give_no_attribution():
    # two variants, but same model family + same impl + same task split + shared confounder.
    evs = [_neg("v1", model_family="deepseek", impl="impl-A", conf=("shared_bug",)),
           _neg("v2", model_family="deepseek", impl="impl-A", conf=("shared_bug",))]
    a = attribute_to_affinity(aggregate(evs))[0]
    assert a.strength == "none" and not a.independent


def test_independent_variants_give_a_limited_attribution_under_the_policy():
    a = attribute_to_affinity(aggregate(_independent_pair()))[0]
    assert a.strength == "limited" and a.independent and a.policy_id == "independence_policy_v1"


def test_independence_policy_is_configurable_and_versioned():
    # a stricter policy that still demands model-family independence rejects same-family variants;
    # a relaxed policy that drops every requirement could accept them - the bar is explicit, not
    # baked into the aggregation.
    same_family = [_neg("v1", model_family="deepseek", impl="impl-A", task="ts1", evaluator="ev1",
                        conf=("a",)),
                   _neg("v2", model_family="deepseek", impl="impl-B", task="ts2", evaluator="ev2",
                        conf=("b",))]
    strict = attribute_to_affinity(aggregate(same_family))[0]
    assert strict.strength == "none" and "model families" in strict.reason
    relaxed = IndependencePolicy(policy_id="independence_policy_relaxed",
                                 require_model_families_distinct=False)
    out = attribute_to_affinity(aggregate(same_family), policy=relaxed)[0]
    assert out.strength == "limited" and out.policy_id == "independence_policy_relaxed"


def test_a_success_makes_the_affinity_picture_inconsistent():
    evs = _independent_pair() + [
        _ev(trial_id="ok", method_variant="v3", epistemic_result="success", measurement=_meas(0.18),
            decision=_dec("success", 0.18, (0.12, 0.24)))]
    a = attribute_to_affinity(aggregate(evs))[0]
    assert a.strength == "none" and "inconsistent" in a.reason


def test_multi_affinity_method_rolls_up_to_each_affinity():
    evs = [_neg("v1", model_family="deepseek", impl="impl-A", task="ts1", evaluator="ev1",
                conf=("noise_a",), aff=("causal", "boundary")),
           _neg("v2", model_family="openai", impl="impl-B", task="ts2", evaluator="ev2",
                conf=("noise_b",), aff=("causal",))]
    attrs = {a.affinity: a for a in attribute_to_affinity(aggregate(evs))}
    assert attrs["causal"].strength == "limited"
    assert attrs["boundary"].strength == "none"   # one variant never condemns the move


def test_single_variant_no_benefit_never_condemns_the_affinity():
    a = attribute_to_affinity(aggregate([_neg("v1", model_family="deepseek", impl="impl-A")]))[0]
    assert a.strength == "none"
