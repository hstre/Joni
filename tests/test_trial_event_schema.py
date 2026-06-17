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
    # a registry whose fn is NOT _rule_v2 but claims the correct implementation_hash must not verify
    # a measurement that is clearly harmful as a success.
    from joni.autonomy.trial_event_schema import RULE_V2_SPEC_HASH, RuleEntry
    ev = _ev(epistemic_result="success", measurement=_meas(-0.20, ci=(-0.28, -0.12)),
             decision=_dec("success"))
    forged = {("rule_v2", RULE_V2_HASH):
              RuleEntry("rule_v2", RULE_V2_SPEC_HASH, RULE_V2_HASH, lambda e: "success")}
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
