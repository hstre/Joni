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
    evaluate_payload,
    migrate_method,
    validate,
    verify_events,
)
from joni.autonomy.trial_event_schema import _cross_block_errors as _cross_block

_EST = Estimand(outcome_metric="misclass_rate", direction="higher_is_better", minimum_effect=0.10,
                decision_rule_id="rule_v2")


def _meas(effect, unc=0.02, base=0.40, ci=None):
    # baseline/intervention are kept consistent with the effect (higher_is_better,
    # intervention_minus_baseline); the confidence interval (owned by the measurement) defaults to a
    # tight, resolving interval around the effect.
    inter = round(base + effect, 6)
    if ci is None:
        ci = (round(effect - unc, 6), round(effect + unc, 6))
    return Measurement("misclass_rate", base, inter, effect_size=effect, uncertainty=unc,
                       confidence_interval=ci)


def _dec(verdict, *_ignored, **_kw):
    # the decision is now minimal: rule id + hash + verdict. It carries NO numbers / interval - the
    # statistical evidence lives in the measurement. (Legacy positional args are accepted+ignored.)
    return Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_HASH, verdict=verdict)


def _ev(**kw) -> MethodTrialRecorded:
    base = dict(
        trial_id="t1", timestamp="2026-06-16T00:00:00Z", ledger_tick=1,
        target_type="conflict", target_id="X17", claim_ids=("C-7",), scope_id="qtt",
        method_id="m_causal", method_variant="v2", affinities=("causal",), estimand=_EST,
        execution_status="completed", protocol_status="valid",
        epistemic_result="not_evaluated", note="n/a")
    base.update(kw)
    return MethodTrialRecorded(**base)


# a self-contained, permissive executable contract (the contract is now a CALLABLE, not data).
_PERMISSIVE_CONTRACT_SRC = b"def check_contract(measurement, decision, estimand):\n    return []\n"


def _permissive_contract(measurement, decision, estimand):
    return []


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
                               verdict="success"))
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
def test_outcomes_are_separated_by_variant_scope():
    # a no_benefit in scope 'qtt' and a success in scope 'other' stay SEPARATE cells - a result in
    # one scope never bleeds into another.
    evs = [
        _ev(trial_id="a", scope_id="qtt", method_variant="v2", epistemic_result="no_benefit",
            measurement=_meas(0.04), decision=_dec("no_benefit")),
        _ev(trial_id="b", scope_id="other", method_variant="v2", epistemic_result="success",
            measurement=_meas(0.20, ci=(0.12, 0.28)), decision=_dec("success")),
    ]
    cells = {(o.scope_id, o.method_variant): o.outcome for o in aggregate(verify_events(evs))}
    assert cells[("qtt", "v2")] == "no_benefit" and cells[("other", "v2")] == "success"


def test_a_technical_failure_is_not_evidence():
    # a failed/not_evaluated event has no verdict -> verify_events excludes it -> it can never feed
    # aggregation or affinity attribution (no technical event masquerades as a negative).
    evs = [_ev(trial_id="a", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated")]
    assert verify_events(evs) == []
    assert aggregate(verify_events(evs)) == []


def test_success_plus_harmful_in_a_cell_is_conflicting_not_negative():
    # success AND harmful in one cell -> CONFLICTING (not 'harmful'); the success evidence and the
    # harmful safety signal are both preserved, so the success is not erased.
    evs = [
        _ev(trial_id="a", epistemic_result="success", measurement=_meas(0.18),
            decision=_dec("success", 0.18, (0.12, 0.24))),
        _ev(trial_id="b", epistemic_result="harmful", measurement=_meas(-0.15),
            decision=_dec("harmful", -0.15, (-0.20, -0.10))),
    ]
    o = aggregate(verify_events(evs))[0]
    assert o.outcome == "conflicting" and o.has_success and o.has_harmful


def test_harmful_only_cell_dominates_as_a_safety_signal():
    evs = [_ev(trial_id="b", epistemic_result="harmful", measurement=_meas(-0.15),
               decision=_dec("harmful", -0.15, (-0.20, -0.10)))]
    o = aggregate(verify_events(evs))[0]
    assert o.outcome == "harmful" and o.has_harmful and not o.has_success


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
    a = attribute_to_affinity(aggregate(verify_events(evs)))[0]
    assert a.strength == "none" and not a.independent


def test_independent_variants_give_a_limited_attribution_under_the_policy():
    a = attribute_to_affinity(aggregate(verify_events(_independent_pair())))[0]
    assert a.strength == "limited" and a.independent and a.policy_id == "independence_policy_v1"


def test_independence_policy_is_configurable_and_versioned():
    # a stricter policy that still demands model-family independence rejects same-family variants;
    # a relaxed policy that drops every requirement could accept them - the bar is explicit, not
    # baked into the aggregation.
    same_family = [_neg("v1", model_family="deepseek", impl="impl-A", task="ts1", evaluator="ev1",
                        conf=("a",)),
                   _neg("v2", model_family="deepseek", impl="impl-B", task="ts2", evaluator="ev2",
                        conf=("b",))]
    strict = attribute_to_affinity(aggregate(verify_events(same_family)))[0]
    assert strict.strength == "none" and "model_families" in strict.reason
    relaxed = IndependencePolicy(policy_id="independence_policy_relaxed",
                                 require_model_families_distinct=False)
    out = attribute_to_affinity(aggregate(verify_events(same_family)), policy=relaxed)[0]
    assert out.strength == "limited" and out.policy_id == "independence_policy_relaxed"


def test_a_success_makes_the_affinity_picture_inconsistent():
    evs = _independent_pair() + [
        _ev(trial_id="ok", method_variant="v3", epistemic_result="success", measurement=_meas(0.18),
            decision=_dec("success", 0.18, (0.12, 0.24)))]
    a = attribute_to_affinity(aggregate(verify_events(evs)))[0]
    assert a.strength == "none" and "inconsistent" in a.reason


def test_multi_affinity_method_rolls_up_to_each_affinity():
    evs = [_neg("v1", model_family="deepseek", impl="impl-A", task="ts1", evaluator="ev1",
                conf=("noise_a",), aff=("causal", "boundary")),
           _neg("v2", model_family="openai", impl="impl-B", task="ts2", evaluator="ev2",
                conf=("noise_b",), aff=("causal",))]
    attrs = {a.affinity: a for a in attribute_to_affinity(aggregate(verify_events(evs)))}
    assert attrs["causal"].strength == "limited"
    assert attrs["boundary"].strength == "none"   # one variant never condemns the move


def test_single_variant_no_benefit_never_condemns_the_affinity():
    evidence = verify_events([_neg("v1", model_family="deepseek", impl="impl-A")])
    a = attribute_to_affinity(aggregate(evidence))[0]
    assert a.strength == "none"


# -- independence: real OVERLAP detection, not a len(union) count ------------------------------- #
def _cell(variant, *, impls, families, tasks, evals, conf=(), outcome="no_benefit",
          aff=("causal",)):
    from joni.autonomy.trial_event_schema import VariantScopeOutcome
    return VariantScopeOutcome(
        target_id="X1", scope_id="s", method_id="m", method_variant=variant, affinities=aff,
        outcome=outcome, n_completed_valid=1, n_unusable=0, protocol_valid=True, models=(),
        model_families=families, implementations=impls, task_samples=tasks, evaluators=evals,
        confounders=conf, evidence=(variant,))


def test_partially_overlapping_implementations_are_not_independent():
    # each variant has a distinct impl AND a SHARED one -> len(union)=3 >= 2 would (wrongly) pass;
    # real overlap detection flags the shared dependency.
    cells = [_cell("v1", impls=("shared", "iA"), families=("deepseek",), tasks=("t1",),
                   evals=("e1",), conf=("a",)),
             _cell("v2", impls=("shared", "iB"), families=("openai",), tasks=("t2",),
                   evals=("e2",), conf=("b",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "none" and not a.independent


def test_fully_shared_model_impl_sample_evaluator_is_not_independent():
    cells = [_cell("v1", impls=("impl",), families=("fam",), tasks=("ts",), evals=("ev",),
                   conf=("c",)),
             _cell("v2", impls=("impl",), families=("fam",), tasks=("ts",), evals=("ev",),
                   conf=("c",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "none" and not a.independent


def test_genuinely_disjoint_dependencies_are_independent():
    cells = [_cell("v1", impls=("iA",), families=("deepseek",), tasks=("t1",), evals=("e1",),
                   conf=("a",)),
             _cell("v2", impls=("iB",), families=("openai",), tasks=("t2",), evals=("e2",),
                   conf=("b",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "limited" and a.independent


# -- fail-closed independence: unknown / missing != independent ---------------------------------- #
def test_unknown_dimension_value_is_not_independent():
    cells = [_cell("v1", impls=("unknown",), families=("unknown",), tasks=("unknown",),
                   evals=("e1",), conf=("a",)),
             _cell("v2", impls=("iB",), families=("openai",), tasks=("t2",), evals=("e2",),
                   conf=("b",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "none" and not a.independent and "incomplete" in a.reason


def test_missing_dimension_value_is_not_independent():
    cells = [_cell("v1", impls=(), families=("deepseek",), tasks=("t1",), evals=("e1",),
                   conf=("a",)),                              # implementation MISSING
             _cell("v2", impls=("iB",), families=("openai",), tasks=("t2",), evals=("e2",),
                   conf=("b",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "none" and "incomplete" in a.reason


def test_all_dimensions_known_and_disjoint_are_independent():
    cells = [_cell("v1", impls=("iA",), families=("deepseek",), tasks=("t1",), evals=("e1",),
                   conf=("a",)),
             _cell("v2", impls=("iB",), families=("openai",), tasks=("t2",), evals=("e2",),
                   conf=("b",))]
    a = attribute_to_affinity(cells)[0]
    assert a.strength == "limited" and a.independent


# -- mixed success + harmful must NOT produce a negative affinity demotion ----------------------- #
def _mixed_variant(variant, family, impl, task, ev):
    return [_ev(trial_id=f"{variant}-s", method_variant=variant, model_family=family,
                implementation_id=impl, task_sample_id=task, evaluator_id=ev,
                epistemic_result="success", measurement=_meas(0.18),
                decision=_dec("success", 0.18, (0.12, 0.24))),
            _ev(trial_id=f"{variant}-h", method_variant=variant, model_family=family,
                implementation_id=impl, task_sample_id=task, evaluator_id=ev,
                epistemic_result="harmful", measurement=_meas(-0.15),
                decision=_dec("harmful", -0.15, (-0.20, -0.10)))]


def test_two_independent_mixed_cells_do_not_demote_the_affinity():
    evs = _mixed_variant("v1", "deepseek", "iA", "t1", "e1") + \
        _mixed_variant("v2", "openai", "iB", "t2", "e2")
    outs = aggregate(verify_events(evs))
    assert all(o.outcome == "conflicting" for o in outs)
    assert any(o.has_harmful for o in outs)                  # safety signal stays visible
    a = attribute_to_affinity(outs)[0]
    assert a.strength == "none" and "inconsistent" in a.reason   # success evidence blocks demotion


def test_two_independent_pure_harmful_variants_remain_demotable():
    evs = [_ev(trial_id="a", method_variant="v1", model_family="deepseek", implementation_id="iA",
               task_sample_id="t1", evaluator_id="e1", epistemic_result="harmful",
               measurement=_meas(-0.15), decision=_dec("harmful", -0.15, (-0.20, -0.10))),
           _ev(trial_id="b", method_variant="v2", model_family="openai", implementation_id="iB",
               task_sample_id="t2", evaluator_id="e2", epistemic_result="harmful",
               measurement=_meas(-0.15), decision=_dec("harmful", -0.15, (-0.20, -0.10)))]
    a = attribute_to_affinity(aggregate(verify_events(evs)))[0]
    assert a.strength == "limited" and a.independent          # no success -> demotion allowed


# -- verified must reflect the MEASUREMENT, not the decision's own duplicated numbers ------------ #
def test_decision_contradicting_measurement_is_inconsistent():
    # the measurement says -0.20 (worse); a decision that mirrors +0.20 must be inconsistent.
    ev = _ev(epistemic_result="success", measurement=_meas(-0.20),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_HASH,
                               verdict="success", effect_size=0.20))
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_decision_overriding_preregistered_threshold_is_inconsistent():
    ev = _ev(epistemic_result="success",
             estimand=Estimand(outcome_metric="misclass_rate", direction="higher_is_better",
                               minimum_effect=0.50, decision_rule_id="rule_v2"),
             measurement=_meas(0.20),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_HASH,
                               verdict="success", minimum_effect=0.10))
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_metric_name_mismatch_is_inconsistent():
    ev = _ev(epistemic_result="success",
             measurement=Measurement("other_metric", 0.40, 0.60, effect_size=0.20,
                                      uncertainty=0.02, confidence_interval=(0.18, 0.22)),
             decision=_dec("success"))
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_consistent_measurement_and_decision_verifies():
    ev = _ev(epistemic_result="success", measurement=_meas(0.20),
             decision=_dec("success", 0.20, (0.12, 0.28)))
    assert evaluate_decision(ev)["status"] == "verified"


def test_verdict_is_computed_from_measurement_not_decision_number():
    # the measurement clears the threshold; the decision's own (ignored) number is wrong but equal,
    # so the verdict comes from the measurement.
    ev = _ev(epistemic_result="success", measurement=_meas(0.20),
             decision=_dec("success", 0.20, (0.12, 0.28)))
    assert evaluate_decision(ev)["computed"] == "success"


# -- round 5: verified must be bound to the actual observation ----------------------------------- #
def test_success_needs_interval_resolution_not_a_bare_point_estimate():
    # effect over the threshold, but HUGE uncertainty and NO confidence interval -> inconclusive,
    # so a claimed success is inconsistent, never verified.
    ev = _ev(epistemic_result="success",
             measurement=Measurement("misclass_rate", 0.40, 0.60, effect_size=0.20,
                                      uncertainty=100.0, confidence_interval=None),
             decision=_dec("success"))
    from joni.autonomy.trial_event_schema import _rule_v2
    assert _rule_v2(ev) == "inconclusive"
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_harmful_unresolved_point_estimate_is_not_verified():
    ev = _ev(epistemic_result="harmful",
             measurement=Measurement("misclass_rate", 0.60, 0.40, effect_size=-0.20,
                                      uncertainty=100.0, confidence_interval=None),
             decision=_dec("harmful"))
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_interval_fully_beyond_zero_verifies():
    ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=_dec("success"))
    assert evaluate_decision(ev)["status"] == "verified"


def test_decision_supplied_interval_is_rejected_as_inconsistent():
    # the favourable interval lives in the DECISION while the measurement has huge uncertainty and
    # no interval -> the decision may not supply its own statistical justification.
    ev = _ev(epistemic_result="success",
             measurement=Measurement("misclass_rate", 0.40, 0.60, effect_size=0.20,
                                      uncertainty=100.0, confidence_interval=None),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_HASH,
                               verdict="success", confidence_interval=(0.10, 0.30)))
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_baseline_intervention_must_imply_the_stored_effect():
    # baseline 0.40, intervention 0.20 under higher_is_better imply -0.20, but +0.20 is stored.
    ev = _ev(epistemic_result="success",
             measurement=Measurement("misclass_rate", 0.40, 0.20, effect_size=0.20,
                                      uncertainty=0.02, confidence_interval=(0.18, 0.22)),
             decision=_dec("success"))
    assert any("inconsistent with baseline/intervention" in e for e in _cross_block(ev))


def test_lower_is_better_orientation_is_consistent():
    # lower_is_better: a DROP from 0.40 to 0.20 is an improvement of +0.20 (oriented positive).
    ev = _ev(epistemic_result="success",
             estimand=Estimand(outcome_metric="m", contrast="intervention_minus_baseline",
                               direction="lower_is_better", minimum_effect=0.10,
                               decision_rule_id="rule_v2"),
             measurement=Measurement("m", 0.40, 0.20, effect_size=0.20, uncertainty=0.02,
                                      confidence_interval=(0.18, 0.22)),
             decision=_dec("success"))
    assert _cross_block(ev) == [] and evaluate_decision(ev)["status"] == "verified"


def test_rule_hash_binds_to_the_actual_implementation():
    import hashlib
    import inspect

    from joni.autonomy import trial_event_schema as s
    expected = "sha256:" + hashlib.sha256(inspect.getsource(s._rule_v2).encode("utf-8")).hexdigest()
    assert expected == s.RULE_V2_HASH and expected == s.RULE_V2_IMPL_HASH
    # the descriptor (spec) hash is a SEPARATE attestation, not the binding one.
    assert s.RULE_V2_SPEC_HASH != s.RULE_V2_IMPL_HASH


def test_registry_rejects_an_implementation_hash_mismatch():
    # an event citing rule_v2 but a stale/forged implementation hash is unverifiable, not verified.
    ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=Decision(decision_rule_id="rule_v2",
                               decision_rule_hash="sha256:" + "0" * 64, verdict="success"))
    assert evaluate_decision(ev)["status"] == "unverifiable"


# -- round 6: the rule hash must bind to the ACTUAL executed function ---------------------------- #
def test_forged_registry_function_with_copied_hash_is_unverifiable():
    # an artifact whose rule_fn is NOT _rule_v2 but CLAIMS the correct implementation_hash must not
    # verify a measurement that is clearly harmful as a success: the hash is re-derived from the
    # actual function at use, so the forged claim is exposed.
    from joni.autonomy.trial_event_schema import EvaluationArtifact
    ev = _ev(epistemic_result="success", measurement=_meas(-0.20, ci=(-0.28, -0.12)),
             decision=_dec("success"))
    forged_art = EvaluationArtifact(
        rule_id="rule_v2", schema_version="x", implementation_hash=RULE_V2_HASH,
        validator_hash="sha256:0", input_contract_hash="sha256:0", input_contract={},
        rule_fn=lambda e: "success")
    forged = {("rule_v2", RULE_V2_HASH): forged_art}
    assert evaluate_decision(ev, forged)["status"] == "unverifiable"


def test_genuine_registered_implementation_verifies():
    ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=_dec("success"))
    assert evaluate_decision(ev)["status"] == "verified"


def test_default_registry_is_immutable():
    import pytest

    from joni.autonomy.trial_event_schema import DEFAULT_RULE_REGISTRY
    with pytest.raises(TypeError):
        DEFAULT_RULE_REGISTRY[("x", "y")] = None        # MappingProxyType rejects mutation


def test_make_rule_entry_computes_the_hash_from_the_function():
    from joni.autonomy.trial_event_schema import (
        RULE_V2_IMPL_HASH,
        RULE_V2_SPEC_HASH,
        _rule_v2,
        make_rule_entry,
    )
    entry = make_rule_entry("rule_v2", RULE_V2_SPEC_HASH, _rule_v2)
    assert entry.implementation_hash == RULE_V2_IMPL_HASH      # computed, not claimed


# -- round 6: success must mean the minimum effect is statistically SUPPORTED -------------------- #
def test_ci_positive_but_reaching_below_min_is_inconclusive_not_success():
    from joni.autonomy.trial_event_schema import _rule_v2
    # CI lower bound 0.001 < minimum_effect 0.10 -> the minimum effect is NOT supported.
    ev = _ev(epistemic_result="success", measurement=_meas(0.11, ci=(0.001, 0.219)),
             decision=_dec("success"))
    assert _rule_v2(ev) == "inconclusive"
    assert evaluate_decision(ev)["status"] == "inconsistent"


def test_ci_fully_above_min_is_a_verified_success():
    ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=_dec("success"))
    assert evaluate_decision(ev)["status"] == "verified"


def test_harmful_needs_ci_fully_beyond_negative_min():
    from joni.autonomy.trial_event_schema import _rule_v2
    # negative direction resolved, but the interval reaches above -min -> inconclusive, not harmful.
    near = _ev(epistemic_result="harmful", measurement=_meas(-0.11, ci=(-0.219, -0.001)),
               decision=_dec("harmful"))
    assert _rule_v2(near) == "inconclusive"
    far = _ev(epistemic_result="harmful", measurement=_meas(-0.20, ci=(-0.28, -0.12)),
              decision=_dec("harmful"))
    assert evaluate_decision(far)["status"] == "verified"


def test_partial_success_is_not_producible_by_rule_v2():
    from joni.autonomy.trial_event_schema import _rule_v2
    ev = _ev(epistemic_result="partial_success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=_dec("partial_success"))
    assert _rule_v2(ev) != "partial_success"
    assert evaluate_decision(ev)["status"] == "inconsistent"   # unreachable under rule_v2


# -- round 7: the aggregation API cannot bypass verification ------------------------------------- #
def _harmful_raw(variant, family, impl, task, evaluator, *, rule_hash=RULE_V2_HASH):
    return MethodTrialRecorded(
        trial_id=f"h-{variant}", timestamp="t", ledger_tick=1, target_type="conflict",
        target_id="X17", claim_ids=("C-7",), scope_id="qtt", method_id="m", method_variant=variant,
        implementation_id=impl, model_family=family, task_sample_id=task, evaluator_id=evaluator,
        affinities=("causal",), estimand=_EST,
        measurement=Measurement("misclass_rate", 0.40, 0.20, effect_size=-0.20, uncertainty=0.02,
                                confidence_interval=(-0.28, -0.12)),
        decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=rule_hash,
                          verdict="harmful"),
        epistemic_result="harmful")


def test_unverified_harmful_events_cannot_drive_affinity_attribution():
    # two structurally-valid harmful events with a BOGUS rule hash -> evaluate_decision says
    # unverifiable; they must NOT produce any affinity attribution via the aggregation API.
    bogus = [_harmful_raw("v1", "deepseek", "iA", "t1", "e1", rule_hash="sha256:bogus"),
             _harmful_raw("v2", "openai", "iB", "t2", "e2", rule_hash="sha256:bogus")]
    assert all(evaluate_decision(e)["status"] == "unverifiable" for e in bogus)
    assert verify_events(bogus) == []                          # no evidence
    assert aggregate(verify_events(bogus)) == []               # no outcomes
    assert attribute_to_affinity(aggregate(verify_events(bogus))) == []   # no attribution


def test_aggregate_rejects_raw_events_directly():
    import pytest
    raw = [_harmful_raw("v1", "deepseek", "iA", "t1", "e1")]
    with pytest.raises(TypeError):
        aggregate(raw)                                         # raw events are not evidence


def test_verified_evidence_cannot_be_forged():
    import pytest

    from joni.autonomy.trial_event_schema import VerifiedTrialEvidence
    with pytest.raises(TypeError):
        VerifiedTrialEvidence(_harmful_raw("v1", "d", "i", "t", "e"), "harmful")   # no token


def test_only_verified_evidence_yields_a_limited_attribution():
    # the SAME two harmful variants, now with the correct rule hash, verify and demote (limited).
    good = [_harmful_raw("v1", "deepseek", "iA", "t1", "e1"),
            _harmful_raw("v2", "openai", "iB", "t2", "e2")]
    a = attribute_to_affinity(aggregate(verify_events(good)))[0]
    assert a.strength == "limited" and a.independent


# -- round 7: no_benefit is an EQUIVALENCE verdict (a precise null is no_benefit) ---------------- #
def test_precise_null_within_band_is_no_benefit():
    from joni.autonomy.trial_event_schema import _rule_v2
    ev = _ev(epistemic_result="no_benefit", measurement=_meas(0.0, ci=(-0.01, 0.01)),
             decision=_dec("no_benefit"))
    assert _rule_v2(ev) == "no_benefit"
    assert evaluate_decision(ev)["status"] == "verified"


def test_small_positive_within_band_is_also_no_benefit():
    from joni.autonomy.trial_event_schema import _rule_v2
    ev = _ev(epistemic_result="no_benefit", measurement=_meas(0.04, ci=(0.02, 0.06)),
             decision=_dec("no_benefit"))
    assert _rule_v2(ev) == "no_benefit"


def test_interval_overlapping_threshold_is_inconclusive():
    from joni.autonomy.trial_event_schema import _rule_v2
    ev = _ev(epistemic_result="success", measurement=_meas(0.11, ci=(0.001, 0.219)),
             decision=_dec("success"))
    assert _rule_v2(ev) == "inconclusive"


def test_negative_band_mirror_is_no_benefit_and_overlap_is_inconclusive():
    from joni.autonomy.trial_event_schema import _rule_v2
    within = _ev(epistemic_result="no_benefit", measurement=_meas(-0.04, ci=(-0.06, -0.02)),
                 decision=_dec("no_benefit"))
    overlap = _ev(epistemic_result="harmful", measurement=_meas(-0.11, ci=(-0.219, -0.001)),
                  decision=_dec("harmful"))
    assert _rule_v2(within) == "no_benefit" and _rule_v2(overlap) == "inconclusive"


# -- round 8: substitution, inconclusive, historical rules, operational channel ----------------- #
def test_substituted_evidence_via_dataclasses_replace_is_rejected():
    import dataclasses
    genuine = verify_events([_neg("v1", model_family="deepseek", impl="iA", task="t1",
                                  evaluator="e1")])[0]
    # swap the PAYLOAD under the surviving token: the bogus payload no longer re-verifies
    forged_payload = _harmful_raw("v1", "deepseek", "iA", "t1", "e1",
                                  rule_hash="sha256:bogus").to_dict()
    forged = dataclasses.replace(genuine, payload=forged_payload, verdict="harmful")
    import pytest
    with pytest.raises(ValueError):                       # aggregate RE-ATTESTS and rejects it
        aggregate([forged])


def test_inconclusive_is_rule_verifiable_and_aggregable():
    # CI straddles the threshold -> rule_v2 computes inconclusive; it must VERIFY (not n/a)
    # and be aggregated, but produce NO affinity attribution.
    from joni.autonomy.trial_event_schema import _rule_v2
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.05, ci=(-0.02, 0.12)),
             decision=_dec("inconclusive"))
    assert _rule_v2(ev) == "inconclusive"
    assert evaluate_decision(ev)["status"] == "verified"
    outs = aggregate(verify_events([ev]))
    assert len(outs) == 1 and outs[0].outcome == "inconclusive"
    assert attribute_to_affinity(outs) == [] or all(
        a.strength == "none" for a in attribute_to_affinity(outs))


def test_inconclusive_maps_to_desi_inconclusive():
    import pytest
    pytest.importorskip("desi.solution_space_gap")   # optional integration only
    from joni.autonomy.trial_event_schema import to_desi_method_trials
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.05, ci=(-0.02, 0.12)),
             decision=_dec("inconclusive"))
    trials = to_desi_method_trials(aggregate(verify_events([ev])))
    assert trials and trials[0].result == "inconclusive"


# a DISTINCT historical implementation (different source -> hash); decides from the decoder VIEW,
# never the event's own epistemic_result.
def _const_rule_v2_archived(view):
    return "success"


def test_historical_rule_versions_coexist_append_only():
    import pytest

    from joni.autonomy.trial_event_schema import (
        RULE_V2_SPEC_HASH,
        build_rule_registry,
        make_rule_entry,
    )
    archived = make_rule_entry("rule_v2", RULE_V2_SPEC_HASH, _const_rule_v2_archived)
    current = make_rule_entry("rule_v2", RULE_V2_SPEC_HASH, __import__(
        "joni.autonomy.trial_event_schema", fromlist=["_rule_v2"])._rule_v2)
    registry = build_rule_registry([archived, current])
    assert archived.implementation_hash != current.implementation_hash    # distinct versions
    # an event citing the ARCHIVED hash verifies under the archived implementation...
    old_ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=archived.implementation_hash,
                                   verdict="success"))
    assert evaluate_decision(old_ev, registry)["status"] == "verified"
    # ...and is NEVER re-interpreted under the current implementation hash.
    new_ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=current.implementation_hash,
                                   verdict="success"))
    assert evaluate_decision(new_ev, registry)["status"] == "verified"
    # the registry is append-only: a duplicate key is refused.
    with pytest.raises(ValueError):
        build_rule_registry([archived, archived])


def test_technical_failures_travel_the_operational_channel_not_attribution():
    from joni.autonomy.trial_event_schema import operational_observations
    tech = _ev(trial_id="t-fail", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated", method_variant="v9")
    assert verify_events([tech]) == []                    # NOT epistemic evidence
    assert aggregate(verify_events([tech])) == []         # no attribution path
    ops = operational_observations([tech])
    assert len(ops) == 1 and ops[0].method_variant == "v9"
    assert ops[0].execution_status == "failed" and ops[0].desi_result == "technical_failure"


# -- round 9: operational classification is not blanket 'technical_failure' ---------------------- #
def _op_one(ev):
    from joni.autonomy.trial_event_schema import operational_observations
    obs = operational_observations([ev])
    assert len(obs) == 1
    return obs[0]


def test_completed_valid_not_evaluated_is_unevaluated_not_technical_failure():
    ev = _ev(trial_id="u", execution_status="completed", protocol_status="valid",
             failure_kind="none", epistemic_result="not_evaluated", note="pilot stopped early")
    assert _op_one(ev).desi_result == "unevaluated"


def test_failed_run_is_technical_failure():
    ev = _ev(trial_id="f", execution_status="failed", failure_kind="timeout",
             epistemic_result="not_evaluated")
    assert _op_one(ev).desi_result == "technical_failure"


def test_cancelled_run_is_cancelled():
    ev = _ev(trial_id="c", execution_status="cancelled", failure_kind="none",
             epistemic_result="not_evaluated")
    assert _op_one(ev).desi_result == "cancelled"


def test_invalid_protocol_run_is_protocol_invalid():
    ev = _ev(trial_id="p", execution_status="completed", protocol_status="invalid",
             failure_kind="none", epistemic_result="not_evaluated")
    assert _op_one(ev).desi_result == "protocol_invalid"


def test_no_operational_state_produces_attribution():
    evs = [_ev(trial_id="u", execution_status="completed", protocol_status="valid",
               failure_kind="none", epistemic_result="not_evaluated", note="unevaluated"),
           _ev(trial_id="f", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated")]
    assert verify_events(evs) == [] and aggregate(verify_events(evs)) == []


# -- round 9: the PRODUCTION rule catalog keeps the archived version ----------------------------- #
def test_production_catalog_holds_current_and_archived_versions():
    from joni.autonomy.trial_event_schema import (
        DEFAULT_RULE_REGISTRY,
        RULE_V2_HASH,
        RULE_V2_R6_HASH,
    )
    assert ("rule_v2", RULE_V2_HASH) in DEFAULT_RULE_REGISTRY
    assert ("rule_v2", RULE_V2_R6_HASH) in DEFAULT_RULE_REGISTRY
    assert RULE_V2_HASH != RULE_V2_R6_HASH


def test_old_event_verifies_under_its_archived_version_in_production_catalog():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH
    # effect 0.03, CI [-0.05, 0.08] (mn=0.10): a zero-straddling interval inside the equivalence
    # band. The ARCHIVED r6 rule (which requires excluding zero for no_benefit) calls this
    # 'inconclusive'; the CURRENT rule calls it 'no_benefit'. An event recorded under the r6 hash
    # must keep verifying as 'inconclusive' via the production DEFAULT registry - it is evaluated by
    # the archived r6 implementation, never re-interpreted under the current rule.
    old_ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
                 decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                                   verdict="inconclusive"))
    assert evaluate_decision(old_ev)["status"] == "verified"        # uses the archived r6 impl


def test_same_measurement_under_current_rule_is_not_the_old_verdict():
    # the same measurement under the CURRENT hash is 'no_benefit', so an 'inconclusive' claim there
    # is inconsistent - the old r6 verdict is never re-applied under the new rule.
    new_ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
                 decision=_dec("inconclusive"))
    assert evaluate_decision(new_ev)["status"] == "inconsistent"


def test_production_catalog_is_immutable_and_append_only():
    import pytest

    from joni.autonomy.trial_event_schema import (
        DEFAULT_RULE_REGISTRY,
        RULE_V2_HASH,
        RULE_V2_SPEC_HASH,
        _rule_v2,
        build_rule_registry,
        make_rule_entry,
    )
    with pytest.raises(TypeError):
        DEFAULT_RULE_REGISTRY[("x", "y")] = None       # immutable
    with pytest.raises(ValueError):                    # append-only: no overwrite
        build_rule_registry([make_rule_entry("rule_v2", RULE_V2_SPEC_HASH, _rule_v2),
                             make_rule_entry("rule_v2", RULE_V2_SPEC_HASH, _rule_v2)])
    assert ("rule_v2", RULE_V2_HASH) in DEFAULT_RULE_REGISTRY


# -- round 10: the archived r6 hash is the REAL prior-release hash, not recomputed from a copy --- #
_R6_RELEASE_HASH = "sha256:2438455fd5dde3db1bb401efaccd7f13bf5fa4dd6cf6cb052b2dce2e390e05a4"


def test_archived_r6_hash_is_the_literal_prior_release_hash():
    # the archived rule's implementation_hash is the EXACT hash published with release 7810e25,
    # derived from the stored verbatim BYTES - never re-derived from a later-typed copy of the fn.
    from joni.autonomy.trial_event_schema import (
        _R6_RULE_SRC,
        RULE_V2_R6_HASH,
        _bytes_hash,
    )
    assert RULE_V2_R6_HASH == _R6_RELEASE_HASH                 # the published historical hash
    assert _bytes_hash(_R6_RULE_SRC) == _R6_RELEASE_HASH       # derived from the archived bytes
    # the live rule's hash is COMPUTED from current source and is a different version entirely.
    from joni.autonomy.trial_event_schema import RULE_V2_HASH
    assert RULE_V2_HASH != _R6_RELEASE_HASH


def test_archived_artifact_rejects_a_copy_with_a_mismatched_expected_hash():
    # make_archived_artifact ENFORCES the pinned historical hash: a re-typed/altered rule body that
    # no longer hashes to the published value is refused - a copy can never masquerade as the
    # original.
    import pytest

    from joni.autonomy.trial_event_schema import make_archived_artifact
    altered = b"def _rule_v2(ev):\n    return 'success'  # a later, altered copy\n"
    with pytest.raises(ValueError):
        make_archived_artifact("rule_v2", "v@r6", altered, b"validator", {},
                               expected_rule_hash=_R6_RELEASE_HASH)


def test_event_under_real_r6_hash_verifies_then_a_new_version_is_appended():
    # the full mandated flow: (1) fix the real prior-release hash; (2) record an event under that
    # exact hash; (3) verify it under the new software; (4) append a new rule version; (5) the old
    # event stays verifiable under its original hash; (6) the hash is the byte-pinned historic one.
    from joni.autonomy.trial_event_schema import (
        DEFAULT_RULE_REGISTRY,
        RULE_V2_HASH,
        RULE_V2_R6_HASH,
    )
    assert RULE_V2_R6_HASH == _R6_RELEASE_HASH
    old_ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
                 decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                                   verdict="inconclusive"))
    # the production registry already carries BOTH the archived r6 and the appended current version.
    assert ("rule_v2", RULE_V2_R6_HASH) in DEFAULT_RULE_REGISTRY
    assert ("rule_v2", RULE_V2_HASH) in DEFAULT_RULE_REGISTRY
    assert evaluate_decision(old_ev)["status"] == "verified"   # old event still verifiable, as r6


def test_historical_artifact_binds_its_own_validator_and_input_contract():
    # an event the CURRENT (tightened) validator would reject stays verifiable under the archived
    # artifact's OWN (lenient, byte-pinned) validator, while the SAME event under the current
    # version is inconsistent - the validator is version-pinned alongside the rule, never swapped.
    from joni.autonomy.trial_event_schema import (
        SCHEMA_VERSION,
        build_rule_registry,
        make_archived_artifact,
        make_live_artifact,
    )
    const_success_src = b"def _rule_v2(view):\n    return 'success'\n"
    lenient_validator_src = (b"def cross_block_consistency(measurement, decision, estimand, *,"
                             b" is_real, has_effect_derivation=False):\n    return []\n")

    def _const_success(view):
        return "success"

    def _always_reject(measurement, decision, estimand, *, is_real, has_effect_derivation=False):
        return ["tightened validator rejects this measurement"]

    # both decode the same (current) event schema; they differ only in the rule + validator version.
    archived = make_archived_artifact("rule_v2", SCHEMA_VERSION, const_success_src,
                                      lenient_validator_src, _PERMISSIVE_CONTRACT_SRC)
    current = make_live_artifact("rule_v2", SCHEMA_VERSION, _const_success, _always_reject,
                                 _permissive_contract)
    assert archived.implementation_hash != current.implementation_hash
    assert archived.validator_hash != current.validator_hash       # distinct validator versions
    registry = build_rule_registry([archived, current])

    meas = _meas(0.20, ci=(0.12, 0.28))
    old_ev = _ev(epistemic_result="success", measurement=meas,
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=archived.implementation_hash,
                                   verdict="success"))
    new_ev = _ev(epistemic_result="success", measurement=meas,
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=current.implementation_hash,
                                   verdict="success"))
    # old event: the archived (lenient) validator accepts -> verified.
    assert evaluate_decision(old_ev, registry)["status"] == "verified"
    # new event: the current (tightened) validator rejects -> inconsistent.
    assert evaluate_decision(new_ev, registry)["status"] == "inconsistent"


def test_historical_artifacts_are_byte_identical_and_append_only():
    # the archived artifact's rule + validator are byte-pinned (identical to the stored files), and
    # the production registry refuses to overwrite the historical version (append-only journal).
    import pytest

    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _R6_CONTRACT_SRC,
        _R6_RULE_SRC,
        DEFAULT_RULE_REGISTRY,
        RULE_V2_R6_HASH,
        SCHEMA_VERSION,
        _bytes_hash,
        build_rule_registry,
        make_archived_artifact,
    )
    art = DEFAULT_RULE_REGISTRY[("rule_v2", RULE_V2_R6_HASH)]
    assert art.rule_source == _R6_RULE_SRC                          # byte-identical rule
    assert art.validator_source == _CROSS_BLOCK_V1_SRC             # byte-identical validator
    assert art.implementation_hash == _bytes_hash(_R6_RULE_SRC)
    assert art.validator_hash == _bytes_hash(_CROSS_BLOCK_V1_SRC)
    dup = make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                                 _R6_CONTRACT_SRC, expected_rule_hash=RULE_V2_R6_HASH)
    with pytest.raises(ValueError):                                # append-only: no overwrite
        build_rule_registry([art, dup])


# -- round 11: validator, input-contract, schema/decoder are CAUSALLY bound, not metadata -- #
def _real_archived_artifact():
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _DECODE_V3_SRC,
        _R6_CONTRACT_SRC,
        _R6_RULE_SRC,
        RULE_V2_R6_HASH,
        SCHEMA_VERSION,
        make_archived_artifact,
    )
    return make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                                  _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                                  expected_rule_hash=RULE_V2_R6_HASH)


def _contradiction_event(hash_):
    # metric_name != estimand.outcome_metric: a real cross-block contradiction caught here.
    import dataclasses
    ev = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=hash_,
                               verdict="success"))
    return dataclasses.replace(ev, estimand=dataclasses.replace(ev.estimand,
                                                                outcome_metric="OTHER_METRIC"))


def test_real_validator_artifact_and_hash_verify_normally():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    real = _real_archived_artifact()
    reg = build_rule_registry([real])
    ok = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    assert evaluate_decision(ok, reg)["status"] == "verified"
    # the honest archived validator still CATCHES a real contradiction (it is actually executed).
    assert evaluate_decision(_contradiction_event(RULE_V2_R6_HASH), reg)["status"] == "inconsistent"


def test_validator_bytes_swap_with_copied_hash_is_unverifiable():
    # the reviewer's attack: real rule bytes + copied real validator_hash + manipulated validator
    # bytes that always return [] -> the contradiction would slip through IF the hash were trusted.
    import dataclasses

    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    real = _real_archived_artifact()
    forged_validator = (b"def cross_block_consistency(measurement, decision, estimand, *, is_real,"
                        b" has_effect_derivation=False):\n    return []\n")
    attack = dataclasses.replace(real, validator_source=forged_validator)  # hash kept
    reg = build_rule_registry([attack])
    assert evaluate_decision(_contradiction_event(RULE_V2_R6_HASH), reg)["status"] == "unverifiable"


def test_live_validator_hash_is_reattested_each_use():
    # a LIVE artifact whose validator_fn is swapped for an always-accept one while keeping the real
    # validator_hash is also rejected - the live validator hash is re-derived at every use.
    import dataclasses

    from joni.autonomy.trial_event_schema import (
        RULE_V2_HASH,
        _rule_v2,
        make_rule_entry,
    )
    real = make_rule_entry("rule_v2", "spec", _rule_v2)
    forged = dataclasses.replace(real, validator_fn=lambda *a, **k: [])    # hash kept
    reg = {("rule_v2", RULE_V2_HASH): forged}
    assert evaluate_decision(_contradiction_event(RULE_V2_HASH), reg)["status"] == "unverifiable"


# a DIFFERENT but valid self-contained contract interpreter (so swapping it changes its hash).
_IMPOSSIBLE_CONTRACT_SRC = (b"def check_contract(measurement, decision, estimand):\n"
                            b"    if measurement.get('impossible') is None:\n"
                            b"        return ['needs impossible field']\n"
                            b"    return []\n")


def test_input_contract_swap_with_stale_hash_is_unverifiable():
    import dataclasses

    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    real = _real_archived_artifact()
    # swap the contract interpreter bytes but KEEP the original input_contract_hash -> stale.
    attack = dataclasses.replace(real, contract_source=_IMPOSSIBLE_CONTRACT_SRC)
    reg = build_rule_registry([attack])                      # input_contract_hash is now stale
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    assert evaluate_decision(ev, reg)["status"] == "unverifiable"


def test_input_contract_is_actually_applied():
    # a CONSISTENT artifact whose contract interpreter demands an impossible field enforces it: the
    # event cannot satisfy it, so it is inconsistent (never verified).
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _DECODE_V3_SRC,
        _R6_RULE_SRC,
        RULE_V2_R6_HASH,
        SCHEMA_VERSION,
        build_rule_registry,
        make_archived_artifact,
    )
    art = make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                                 _IMPOSSIBLE_CONTRACT_SRC, _DECODE_V3_SRC,
                                 expected_rule_hash=RULE_V2_R6_HASH)
    reg = build_rule_registry([art])
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    assert evaluate_decision(ev, reg)["status"] == "inconsistent"


def test_real_r6_contract_requires_effect_and_ci():
    # the production r6 artifact carries the REAL historical contract (require_effect + require_ci)
    # as a byte-pinned interpreter. An event with no CI cannot be evaluated under it.

    from joni.autonomy.trial_event_schema import (
        _R6_CONTRACT_SRC,
        DEFAULT_RULE_REGISTRY,
        RULE_V2_R6_HASH,
        _bytes_hash,
    )
    art = DEFAULT_RULE_REGISTRY[("rule_v2", RULE_V2_R6_HASH)]
    assert art.input_contract_hash == _bytes_hash(_R6_CONTRACT_SRC)   # the contract is byte-pinned
    assert b"confidence_interval" in _R6_CONTRACT_SRC and b"effect_size" in _R6_CONTRACT_SRC
    no_ci = _ev(epistemic_result="inconclusive",
                measurement=Measurement("misclass_rate", 0.40, 0.43, effect_size=0.03,
                                        uncertainty=0.02, confidence_interval=None),
                decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                                  verdict="inconclusive"))
    assert evaluate_decision(no_ci)["status"] == "inconsistent"


def test_new_artifact_may_carry_a_stricter_contract_old_event_stays_under_old():
    # an old artifact (lenient {}) and a new artifact (stricter contract) coexist; the SAME
    # measurement is evaluable under the old hash but not the new - old events keep their own
    # contract, never the new stricter one.
    from joni.autonomy.trial_event_schema import (
        SCHEMA_VERSION,
        build_rule_registry,
        make_archived_artifact,
        make_live_artifact,
    )

    def _const_inconclusive(view):
        return "inconclusive"

    def _live_validator(measurement, decision, estimand, *, is_real, has_effect_derivation=False):
        return []

    def _require_uncertainty(measurement, decision, estimand):
        return [] if measurement.get("uncertainty") is not None else ["needs uncertainty"]
    old_rule_src = b"def _rule_v2(view):\n    return 'inconclusive'\n"
    old = make_archived_artifact("rule_v2", SCHEMA_VERSION, old_rule_src,
                                 b"def cross_block_consistency(*a, **k):\n    return []\n",
                                 _PERMISSIVE_CONTRACT_SRC)
    new = make_live_artifact("rule_v2", SCHEMA_VERSION, _const_inconclusive, _live_validator,
                             _require_uncertainty)
    reg = build_rule_registry([old, new])
    no_unc = Measurement("misclass_rate", 0.40, 0.43, effect_size=0.03, uncertainty=None,
                         confidence_interval=(-0.05, 0.08))
    old_ev = _ev(epistemic_result="inconclusive", measurement=no_unc,
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=old.implementation_hash,
                                   verdict="inconclusive"))
    new_ev = _ev(epistemic_result="inconclusive", measurement=no_unc,
                 decision=Decision(decision_rule_id="rule_v2",
                                   decision_rule_hash=new.implementation_hash,
                                   verdict="inconclusive"))
    assert evaluate_decision(old_ev, reg)["status"] == "verified"        # lenient old contract
    assert evaluate_decision(new_ev, reg)["status"] == "inconsistent"    # stricter new contract


def test_schema_version_mismatch_is_unverifiable():
    import dataclasses

    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH
    future = dataclasses.replace(
        _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
            decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                              verdict="inconclusive")),
        schema_version="method_trial_recorded_v4")
    assert evaluate_decision(future)["status"] == "unverifiable"


def test_decoder_bytes_swap_with_copied_hash_is_unverifiable():
    # a decoder swapped for one that drops the metric_name (so the contradiction can't be seen),
    # while keeping the real decoder_hash, is rejected - the decoder hash is re-derived at use.
    import dataclasses

    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    real = _real_archived_artifact()
    forged_decoder = (b"def _decode_v3(ev):\n"
                      b"    m, d, e = ev.measurement, ev.decision, ev.estimand\n"
                      b"    return ({'effect_size': m.effect_size,"
                      b" 'confidence_interval': m.confidence_interval},"
                      b" {'minimum_effect': d.minimum_effect},"
                      b" {'minimum_effect': e.minimum_effect})\n")
    attack = dataclasses.replace(real, decoder_source=forged_decoder)   # decoder_hash unchanged
    reg = build_rule_registry([attack])
    assert evaluate_decision(_contradiction_event(RULE_V2_R6_HASH), reg)["status"] == "unverifiable"


def test_production_r6_artifact_binds_decoder_contract_validator():
    from joni.autonomy.trial_event_schema import (
        _DECODE_V3_SRC,
        _R6_CONTRACT_SRC,
        DEFAULT_RULE_REGISTRY,
        RULE_V2_R6_HASH,
        _bytes_hash,
    )
    art = DEFAULT_RULE_REGISTRY[("rule_v2", RULE_V2_R6_HASH)]
    assert art.decoder_source == _DECODE_V3_SRC and art.decoder_hash == _bytes_hash(_DECODE_V3_SRC)
    assert art.contract_source == _R6_CONTRACT_SRC
    assert art.input_contract_hash == _bytes_hash(_R6_CONTRACT_SRC)
    assert art.canonical_input_projection_hash and art.validator_hash and art.implementation_hash


# -- round 12: the capsule is CLOSED - no live helper, no direct event access, raw entry --- #
def test_historical_validator_is_self_contained_under_live_helper_change(monkeypatch):
    # the byte-pinned validator carries its OWN helpers; sabotaging the LIVE _finite/_EPS must not
    # change a historical evaluation (the capsule imports no epistemically-relevant runtime helper).
    import desi_layer9.trial_event_validation as V
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    reg = build_rule_registry([_real_archived_artifact()])
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    assert evaluate_decision(ev, reg)["status"] == "verified"
    monkeypatch.setattr(V, "_finite", lambda x: False)       # sabotage the LIVE helper
    monkeypatch.setattr(V, "_EPS", 999.0)
    assert evaluate_decision(ev, reg)["status"] == "verified"   # historical result is unchanged


def test_historical_validator_bytes_tamper_is_unverifiable():
    import dataclasses

    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        RULE_V2_R6_HASH,
        build_rule_registry,
    )
    real = _real_archived_artifact()
    tampered = dataclasses.replace(real, validator_source=_CROSS_BLOCK_V1_SRC + b"\n# tampered\n")
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    assert evaluate_decision(ev, build_rule_registry([tampered]))["status"] == "unverifiable"


def test_the_rule_input_comes_from_the_decoder_not_the_event():
    # an event whose RAW measurement the r6 rule calls 'inconclusive', claiming 'success'. With the
    # real decoder it is inconsistent; with a decoder that projects a resolved 'success' input, the
    # SAME event verifies - proving the rule (and validator) decide from the DECODER output only.
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _R6_CONTRACT_SRC,
        _R6_RULE_SRC,
        RULE_V2_R6_HASH,
        SCHEMA_VERSION,
        build_rule_registry,
        make_archived_artifact,
    )
    ev = _ev(epistemic_result="success", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="success"))
    real_reg = build_rule_registry([_real_archived_artifact()])
    assert evaluate_decision(ev, real_reg)["status"] == "inconsistent"   # raw data -> inconclusive

    override_decoder = (
        b"def _decode_v3(payload):\n"
        b"    meas = {'metric_name': 'misclass_rate', 'baseline_value': 0.40,\n"
        b"            'intervention_value': 0.60, 'effect_size': 0.20, 'uncertainty': 0.02,\n"
        b"            'confidence_interval': (0.12, 0.28)}\n"
        b"    dec = {'effect_size': None, 'minimum_effect': None, 'confidence_interval': None}\n"
        b"    est = {'outcome_metric': 'misclass_rate',"
        b" 'contrast': 'intervention_minus_baseline',\n"
        b"           'direction': 'higher_is_better', 'minimum_effect': 0.10}\n"
        b"    return meas, dec, est\n")
    # a CONSISTENT artifact carrying that decoder (all hashes incl. the capsule recomputed).
    overridden = make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC,
                                        _CROSS_BLOCK_V1_SRC, _R6_CONTRACT_SRC, override_decoder,
                                        expected_rule_hash=RULE_V2_R6_HASH)
    over_reg = build_rule_registry([overridden])
    # the rule now sees the decoder's resolved 'success' projection, not the event's raw values.
    assert evaluate_decision(ev, over_reg)["status"] == "verified"


def test_live_contract_interpreter_change_does_not_affect_archived():
    # the archived contract is a byte-pinned interpreter; changing the LIVE check_contract must not
    # change a historical evaluation (the meaning is hashed with the capsule).
    import joni.autonomy.trial_event_schema as S
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, build_rule_registry
    reg = build_rule_registry([_real_archived_artifact()])
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    orig = S.check_contract
    try:
        S.check_contract = lambda m, d, e: ["live interpreter now rejects everything"]
        assert evaluate_decision(ev, reg)["status"] == "verified"   # archived, unchanged
    finally:
        S.check_contract = orig


def test_evaluate_payload_runs_on_the_raw_stored_payload():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, evaluate_payload
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    raw = ev.to_dict()                                   # the canonical stored payload (plain dict)
    assert evaluate_payload(raw)["status"] == "verified"
    # an UNKNOWN extra current-irrelevant field in the raw payload does not disturb the capsule.
    raw_plus = dict(raw, some_future_field={"x": 1})
    assert evaluate_payload(raw_plus)["status"] == "verified"


# -- round 13: routing envelope, byte-pinned adapter, pinned loader, composite capsule hash ------ #
def _r13_event():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH
    return _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
               decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                                 verdict="inconclusive"))


def test_input_adapter_is_byte_pinned_live_change_has_no_effect():
    # the decoder->rule view adapter is byte-pinned into the capsule; sabotaging the LIVE build_view
    # must not change a historical evaluation (no un-attested transform between decoder & rule).
    import joni.autonomy.trial_event_schema as S
    from joni.autonomy.trial_event_schema import build_rule_registry
    reg = build_rule_registry([_real_archived_artifact()])
    orig = S.build_view
    try:
        S.build_view = lambda m, d, e: (_ for _ in ()).throw(AssertionError("sabotaged"))
        assert evaluate_decision(_r13_event(), reg)["status"] == "verified"   # archived adapter
    finally:
        S.build_view = orig


def test_input_adapter_bytes_tamper_is_unverifiable():
    import dataclasses

    from joni.autonomy.trial_event_schema import build_rule_registry
    real = _real_archived_artifact()
    tampered = dataclasses.replace(real, adapter_source=real.adapter_source + b"\n# tamper\n")
    assert evaluate_decision(_r13_event(), build_rule_registry([tampered]))["status"] \
        == "unverifiable"


def test_routing_uses_the_envelope_not_payload_field_paths():
    # routing comes from the stable envelope; even if the payload RELOCATES its decision block, the
    # artifact is still selected via the envelope's rule_hash.
    from joni.autonomy.trial_event_schema import (
        _payload_hash,
        build_rule_registry,
        envelope_for_payload,
        evaluate_envelope,
    )
    reg = build_rule_registry([_real_archived_artifact()])
    payload = _r13_event().to_dict()
    relocated = dict(payload)
    relocated["decision_v3"] = relocated.pop("decision")        # current field path is gone
    env = dict(envelope_for_payload(payload), payload_hash=_payload_hash(relocated))
    assert evaluate_envelope(env, relocated, reg)["status"] == "verified"


def test_unknown_envelope_version_is_unverifiable():
    from joni.autonomy.trial_event_schema import (
        build_rule_registry,
        envelope_for_payload,
        evaluate_envelope,
    )
    reg = build_rule_registry([_real_archived_artifact()])
    payload = _r13_event().to_dict()
    env = dict(envelope_for_payload(payload), envelope_version="evaluation_envelope_v999")
    assert evaluate_envelope(env, payload, reg)["status"] == "unverifiable"


def test_payload_tamper_under_same_envelope_is_unverifiable():
    from joni.autonomy.trial_event_schema import (
        build_rule_registry,
        envelope_for_payload,
        evaluate_envelope,
    )
    reg = build_rule_registry([_real_archived_artifact()])
    payload = _r13_event().to_dict()
    env = envelope_for_payload(payload)                         # binds the ORIGINAL payload_hash
    tampered = dict(payload, measurement=dict(payload["measurement"], effect_size=0.99))
    assert evaluate_envelope(env, tampered, reg)["status"] == "unverifiable"


def test_loader_compiles_historical_bytes_under_explicit_pinned_semantics():
    # the r6 rule has an un-imported annotation; it loads ONLY because the pinned loader applies the
    # 'annotations' future flag with dont_inherit=True. Without that flag it must fail - proving the
    # loader semantics are explicit and bound, not inherited from the calling module.
    import pytest

    from joni.autonomy.trial_event_schema import _R6_RULE_SRC, _exec_callable
    fn = _exec_callable(_R6_RULE_SRC, "_rule_v2", future_flags=("annotations",))
    assert callable(fn)
    with pytest.raises(NameError):
        _exec_callable(_R6_RULE_SRC, "_rule_v2", future_flags=())


def test_wrong_execution_environment_flags_make_it_unverifiable():
    # an artifact whose pinned execution_environment drops the required future flag can no longer
    # compile its own rule -> unverifiable (the loader/exec-env is part of the capsule).
    import dataclasses

    from joni.autonomy.trial_event_schema import build_rule_registry
    real = _real_archived_artifact()
    broken_env = dict(real.execution_environment, future_flags=[])
    broken = dataclasses.replace(real, execution_environment=broken_env)
    assert evaluate_decision(_r13_event(), build_rule_registry([broken]))["status"] \
        == "unverifiable"


def test_capsule_hash_binds_every_component_and_addresses_the_whole_capsule():
    from joni.autonomy.trial_event_schema import (
        build_rule_registry,
        envelope_for_payload,
        evaluate_envelope,
    )
    real = _real_archived_artifact()
    assert real.capsule_hash and real.input_adapter_hash and real.exec_env_hash
    reg = build_rule_registry([real])
    payload = _r13_event().to_dict()
    env = envelope_for_payload(payload)
    # an envelope MAY pin the whole-capsule address; a correct one verifies, a wrong one does not.
    assert evaluate_envelope(dict(env, capsule_hash=real.capsule_hash), payload, reg)["status"] \
        == "verified"
    assert evaluate_envelope(dict(env, capsule_hash="sha256:" + "0" * 64), payload, reg)["status"] \
        == "unverifiable"


def test_production_r6_capsule_binds_adapter_loader_and_capsule_hash():
    from joni.autonomy.trial_event_schema import (
        _VIEW_ADAPTER_SRC,
        DEFAULT_RULE_REGISTRY,
        RULE_V2_R6_HASH,
        _bytes_hash,
    )
    art = DEFAULT_RULE_REGISTRY[("rule_v2", RULE_V2_R6_HASH)]
    assert art.adapter_source == _VIEW_ADAPTER_SRC
    assert art.input_adapter_hash == _bytes_hash(_VIEW_ADAPTER_SRC)
    assert art.execution_environment.get("future_flags") == {"annotations": 16777216}
    assert art.execution_environment.get("loader_version") == "artifact_loader_v1"
    assert art.exec_env_hash and art.capsule_hash
    assert art.envelope_version == "evaluation_envelope_v1"


# -- round 14: loader trust-root, exec-env closure, python pinning, stored envelope, one path - #
def _r14_reg():
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _DECODE_V3_SRC,
        _R6_CONTRACT_SRC,
        _R6_RULE_SRC,
        RULE_V2_R6_HASH,
        SCHEMA_VERSION,
        build_rule_registry,
        make_archived_artifact,
    )
    art = make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                                 _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                                 expected_rule_hash=RULE_V2_R6_HASH)
    return art, build_rule_registry([art])


def _harmful_claims_success():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH
    return _ev(epistemic_result="success", measurement=_meas(-0.20, ci=(-0.25, -0.15)),
               decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                                 verdict="success"))


def test_swapping_the_live_loader_does_not_change_historical_evaluation():
    # THE reviewer attack: replace the module-global _exec_callable after the registry is built. The
    # loader is bootstrapped FROM ITS BYTES in _resolve_artifact, so the swap has no effect.
    import joni.autonomy.trial_event_schema as schema
    _, reg = _r14_reg()
    ev = _harmful_claims_success()
    assert evaluate_decision(ev, reg)["computed"] == "harmful"      # honest: harmful != success
    orig = schema._exec_callable
    try:
        schema._exec_callable = lambda src, name, **k: (lambda view: "success")
        assert evaluate_decision(ev, reg)["status"] == "inconsistent"   # unaffected by the swap
        assert evaluate_decision(ev, reg)["computed"] == "harmful"
    finally:
        schema._exec_callable = orig


def test_tampered_loader_bytes_with_copied_hash_is_unverifiable():
    import joni.autonomy.trial_event_schema as schema
    _, reg = _r14_reg()
    ev = _r13_event()
    orig = schema._LOADER_SRC
    try:
        schema._LOADER_SRC = orig + b"\n# tamper\n"            # bytes change, claimed hash stale
        assert evaluate_decision(ev, reg)["status"] == "unverifiable"
    finally:
        schema._LOADER_SRC = orig


def test_execution_environment_binds_numeric_flag_values():
    import dataclasses
    art, _ = _r14_reg()
    from joni.autonomy.trial_event_schema import build_rule_registry
    # the NUMERIC flag value is part of the bound contract; changing it (not just the name) breaks
    # the exec-env hash -> unverifiable.
    broken = dataclasses.replace(
        art, execution_environment=dict(art.execution_environment, future_flag_bits=0))
    res = evaluate_decision(_r13_event(), build_rule_registry([broken]))
    assert res["status"] == "unverifiable"
    assert art.execution_environment["future_flags"]["annotations"] == 16777216


def test_python_semantics_is_enforced():
    import dataclasses
    art, _ = _r14_reg()
    from joni.autonomy.trial_event_schema import build_rule_registry
    wrong = dataclasses.replace(
        art, execution_environment=dict(art.execution_environment, python_semantics="2.7"))
    assert evaluate_decision(_r13_event(), build_rule_registry([wrong]))["status"] == "unverifiable"


def test_stored_envelope_replay_ignores_a_changed_live_bridge():
    # to_journal embeds the envelope; replay uses the STORED envelope, so monkeypatching the live
    # envelope_for_payload after journaling cannot re-route a stored event.
    import joni.autonomy.trial_event_schema as schema
    _, reg = _r14_reg()
    obj = _r13_event().to_journal()
    assert "evaluation_envelope" in obj
    orig = schema.envelope_for_payload
    try:
        schema.envelope_for_payload = lambda p: {"envelope_version": "evaluation_envelope_v999"}
        assert evaluate_payload(obj, reg)["status"] == "verified"
    finally:
        schema.envelope_for_payload = orig


def test_journal_payload_tamper_is_detected_on_replay():
    _, reg = _r14_reg()
    obj = _r13_event().to_journal()
    obj = dict(obj)
    obj["measurement"] = dict(obj["measurement"], effect_size=0.99)   # tamper, envelope unchanged
    assert evaluate_payload(obj, reg)["status"] == "unverifiable"     # payload_hash mismatch


def test_aggregation_path_runs_from_stored_objects_not_reconstruction():
    from joni.autonomy.trial_event_schema import (
        RULE_V2_R6_HASH,
        aggregate,
        attribute_to_affinity,
        verify_payloads,
    )
    _, reg = _r14_reg()
    stored = [
        _ev(trial_id=f"h{i}", epistemic_result="harmful", method_variant=f"v{i}",
            implementation_id=f"i{i}", model_family=fam, task_sample_id=f"t{i}",
            evaluator_id=f"e{i}",
            measurement=_meas(-0.20, ci=(-0.28, -0.12)),
            decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                              verdict="harmful")).to_journal()
        for i, fam in [(1, "deepseek"), (2, "openai")]]
    evidence = verify_payloads(stored, reg)                 # stored dicts, no reconstruction
    assert len(evidence) == 2 and all(isinstance(e.payload, dict) for e in evidence)
    a = attribute_to_affinity(aggregate(evidence, reg))[0]
    assert a.strength == "limited" and a.independent


def test_production_capsule_binds_loader_and_python_semantics():
    import platform

    from joni.autonomy.trial_event_schema import (
        DEFAULT_RULE_REGISTRY,
        LOADER_HASH,
        RULE_V2_R6_HASH,
    )
    art = DEFAULT_RULE_REGISTRY[("rule_v2", RULE_V2_R6_HASH)]
    env = art.execution_environment
    assert env["loader_hash"] == LOADER_HASH
    assert env["python_semantics"] == ".".join(platform.python_version_tuple()[:2])
    assert env["future_flag_bits"] == 16777216
