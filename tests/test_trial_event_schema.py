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


def _prod_r6_capsule():
    # the registry is keyed by capsule_hash; find the production r6 capsule by its rule hash.
    from joni.autonomy.trial_event_schema import DEFAULT_RULE_REGISTRY, RULE_V2_R6_HASH
    return next(a for a in DEFAULT_RULE_REGISTRY.values()
               if a.rule_id == "rule_v2" and a.implementation_hash == RULE_V2_R6_HASH)


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
    rule_hashes = {a.implementation_hash for a in DEFAULT_RULE_REGISTRY.values()
                   if a.rule_id == "rule_v2"}
    assert RULE_V2_HASH in rule_hashes and RULE_V2_R6_HASH in rule_hashes
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
    assert any(a.implementation_hash == RULE_V2_HASH for a in DEFAULT_RULE_REGISTRY.values())


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
    rule_hashes = {a.implementation_hash for a in DEFAULT_RULE_REGISTRY.values()
                   if a.rule_id == "rule_v2"}
    assert RULE_V2_R6_HASH in rule_hashes and RULE_V2_HASH in rule_hashes
    assert evaluate_decision(old_ev)["status"] == "verified"   # old event still verifiable, as r6


def test_historical_artifact_binds_its_own_validator_and_input_contract():
    # an event the CURRENT (tightened) validator would reject stays verifiable under the archived
    # artifact's OWN (lenient, byte-pinned) validator, while the SAME event under the current
    # version is inconsistent - the validator is version-pinned alongside the rule, never swapped.
    from joni.autonomy.trial_event_schema import (
        JOURNAL_SCHEMA_VERSION,
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
    archived = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, const_success_src,
                                      lenient_validator_src, _PERMISSIVE_CONTRACT_SRC)
    current = make_live_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _const_success, _always_reject,
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
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
        _bytes_hash,
        build_rule_registry,
        make_archived_artifact,
    )
    art = _prod_r6_capsule()
    assert art.rule_source == _R6_RULE_SRC                          # byte-identical rule
    assert art.validator_source == _CROSS_BLOCK_V1_SRC             # byte-identical validator
    assert art.implementation_hash == _bytes_hash(_R6_RULE_SRC)
    assert art.validator_hash == _bytes_hash(_CROSS_BLOCK_V1_SRC)
    dup = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                     _CROSS_BLOCK_V1_SRC,
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
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
        make_archived_artifact,
    )
    return make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                     _CROSS_BLOCK_V1_SRC,
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
        build_rule_registry,
        make_rule_entry,
    )
    real = make_rule_entry("rule_v2", "spec", _rule_v2)
    forged = dataclasses.replace(real, validator_fn=lambda *a, **k: [])    # hash kept
    reg = build_rule_registry([forged])
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
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
        build_rule_registry,
        make_archived_artifact,
    )
    art = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                _CROSS_BLOCK_V1_SRC,
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
        RULE_V2_R6_HASH,
        _bytes_hash,
    )
    art = _prod_r6_capsule()
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
        JOURNAL_SCHEMA_VERSION,
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
    old = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, old_rule_src,
                                 b"def cross_block_consistency(*a, **k):\n    return []\n",
                                 _PERMISSIVE_CONTRACT_SRC)
    new = make_live_artifact("rule_v2", JOURNAL_SCHEMA_VERSION,
                             _const_inconclusive, _live_validator,
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
    # an envelope claiming a schema the selected capsule does not decode is unverifiable.
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    assert evaluate_envelope(dict(env, schema_version="method_trial_recorded_v5"), body,
                             reg)["status"] == "unverifiable"


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
        _bytes_hash,
    )
    art = _prod_r6_capsule()
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
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
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
    overridden = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
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


def test_evaluate_payload_runs_on_the_sealed_stored_object():
    from joni.autonomy.trial_event_schema import RULE_V2_R6_HASH, evaluate_payload
    ev = _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
             decision=Decision(decision_rule_id="rule_v2", decision_rule_hash=RULE_V2_R6_HASH,
                               verdict="inconclusive"))
    sealed = ev.to_journal()                             # the canonical SEALED stored object (v4)
    assert evaluate_payload(sealed)["status"] == "verified"
    # an UNSEALED (legacy v3) payload is legacy_unsealed - it is never reconstructed into a verdict.
    assert evaluate_payload(ev.to_dict())["status"] == "legacy_unsealed"


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


def _sealed_split(reg):
    """A sealed (envelope, body) pair for the r13 event under ``reg``."""
    obj = _r13_event().to_journal(reg)
    env = obj["evaluation_envelope"]
    body = {k: v for k, v in obj.items() if k != "evaluation_envelope"}
    return env, body


def test_routing_uses_the_envelope_not_payload_field_paths():
    # routing comes from the stable envelope's capsule_hash; even if the body RELOCATES its decision
    # block, the capsule is still selected via the envelope.
    from joni.autonomy.trial_event_schema import (
        build_rule_registry,
        evaluate_envelope,
        evaluation_body_hash,
    )
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    relocated = dict(body)
    relocated["decision_v3"] = relocated.pop("decision")        # current field path is gone
    env2 = dict(env, evaluation_body_hash=evaluation_body_hash(relocated))
    assert evaluate_envelope(env2, relocated, reg)["status"] == "verified"


def test_unknown_envelope_version_is_unverifiable():
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    assert evaluate_envelope(dict(env, envelope_version="evaluation_envelope_v999"), body,
                             reg)["status"] == "unverifiable"


def test_payload_tamper_under_same_envelope_is_unverifiable():
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    tampered = dict(body, measurement=dict(body["measurement"], effect_size=0.99))
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
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    real = _real_archived_artifact()
    assert real.capsule_hash and real.input_adapter_hash and real.exec_env_hash
    reg = build_rule_registry([real])
    env, body = _sealed_split(reg)
    assert env["capsule_hash"] == real.capsule_hash               # mandatory whole-capsule address
    assert evaluate_envelope(env, body, reg)["status"] == "verified"
    # a well-formed seal for a capsule that is not in THIS catalog is marked, never verified.
    assert evaluate_envelope(dict(env, capsule_hash="sha256:" + "0" * 64), body,
                             reg)["status"] == "sealed_unknown_capsule"
    # a missing capsule_hash (mandatory routing key) fails closed as unverifiable.
    miss = dict(env)
    miss.pop("capsule_hash")
    assert evaluate_envelope(miss, body, reg)["status"] == "unverifiable"


def test_production_r6_capsule_binds_adapter_loader_and_capsule_hash():
    from joni.autonomy.trial_event_schema import (
        _VIEW_ADAPTER_SRC,
        _bytes_hash,
    )
    art = _prod_r6_capsule()
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
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
        build_rule_registry,
        make_archived_artifact,
    )
    art = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                _CROSS_BLOCK_V1_SRC,
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
        LOADER_HASH,
    )
    art = _prod_r6_capsule()
    env = art.execution_environment
    assert env["loader_hash"] == LOADER_HASH
    assert env["python_semantics"] == ".".join(platform.python_version_tuple()[:2])
    assert env["future_flag_bits"] == 16777216


# -- round 15: sealed v4 journal at the kernel, capsule routing, legacy_unsealed -------------- #
def _v4_kernel_core():
    import desi_layer9 as l9
    return l9.Layer9()


def _submit(core, payload):
    import desi_layer9 as l9
    from desi_layer9 import Operator as OP
    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance
    return core.submit(l9.make_proposal(PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED,
                       payload=payload, proposer="k",
                       provenance=Provenance.from_model(external=False, model_id="k")), actor="k")


def test_kernel_stores_the_sealed_envelope_and_replay_ignores_the_live_bridge():
    import joni.autonomy.trial_event_schema as S
    core = _v4_kernel_core()
    assert _submit(core, _r13_event().to_journal()).accepted
    stored = core.method_trial_events()[0]["payload"]
    assert "evaluation_envelope" in stored                       # the envelope is journaled
    orig = S.envelope_for_payload
    try:
        S.envelope_for_payload = lambda p, c, r=None: {"envelope_version": "v999"}
        assert evaluate_payload(stored)["status"] == "verified"  # replay uses the STORED envelope
    finally:
        S.envelope_for_payload = orig


def test_gate_rejects_a_v4_event_without_an_envelope():
    from joni.autonomy.trial_event_schema import SCHEMA_VERSION_V4
    core = _v4_kernel_core()
    body = _r13_event().to_dict()
    body["schema_version"] = SCHEMA_VERSION_V4            # claims sealed, but carries no envelope
    d = _submit(core, body)
    assert not d.accepted and "evaluation_envelope" in d.reason
    assert core.method_trial_events() == []              # not stored


def test_gate_rejects_a_v4_event_whose_envelope_body_hash_does_not_bind():
    core = _v4_kernel_core()
    obj = _r13_event().to_journal()
    obj["measurement"] = dict(obj["measurement"], effect_size=0.99)   # tamper after sealing
    d = _submit(core, obj)
    assert not d.accepted and "evaluation_body_hash" in d.reason


def test_two_capsules_with_the_same_rule_hash_coexist():
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _DECODE_V3_SRC,
        _R6_CONTRACT_SRC,
        _R6_RULE_SRC,
        JOURNAL_SCHEMA_VERSION,
        RULE_V2_R6_HASH,
        build_rule_registry,
        make_archived_artifact,
    )
    a1 = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                _CROSS_BLOCK_V1_SRC,
                                _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                                expected_rule_hash=RULE_V2_R6_HASH)
    a2 = make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC,
                                _CROSS_BLOCK_V1_SRC + b"\n# variant B\n", _R6_CONTRACT_SRC,
                                _DECODE_V3_SRC, expected_rule_hash=RULE_V2_R6_HASH)
    assert a1.implementation_hash == a2.implementation_hash      # SAME rule hash
    assert a1.capsule_hash != a2.capsule_hash                    # DIFFERENT capsule
    reg = build_rule_registry([a1, a2])                          # both coexist (capsule-keyed)
    assert len(reg) == 2


def test_capsule_hash_is_the_mandatory_routing_key():
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    no_capsule = dict(env)
    no_capsule.pop("capsule_hash")
    assert evaluate_envelope(no_capsule, body, reg)["status"] == "unverifiable"   # fail-closed


def test_legacy_unsealed_events_never_become_evidence():
    from joni.autonomy.trial_event_schema import aggregate, verify_payloads
    legacy = _r13_event().to_dict()                      # v3, no envelope
    assert evaluate_payload(legacy)["status"] == "legacy_unsealed"
    assert verify_payloads([legacy]) == []               # no epistemic weight
    assert aggregate(verify_payloads([legacy])) == []


def test_evaluation_body_hash_is_a_distinct_scope_from_kernel_payload_hash():
    # the kernel's payload_hash covers the WHOLE stored object (incl. envelope); the envelope's
    # evaluation_body_hash covers only the body - distinct names, distinct byte ranges.
    import hashlib

    from desi_layer9.trial_event_validation import canonical_payload
    from joni.autonomy.trial_event_schema import evaluation_body_hash
    obj = _r13_event().to_journal()
    kernel_payload_hash = "sha256:" + hashlib.sha256(
        canonical_payload(obj).encode("utf-8")).hexdigest()
    body_hash = evaluation_body_hash(obj)
    assert kernel_payload_hash != body_hash              # different scopes, different names
    assert obj["evaluation_envelope"]["evaluation_body_hash"] == body_hash


# -- round 16: frozen live capsule, v4-only write boundary, operational mode, manifest ------- #
def _kernel():
    import desi_layer9 as l9
    return l9.Layer9()


def _submit16(core, payload):
    import desi_layer9 as l9
    from desi_layer9 import Operator as OP
    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance
    return core.submit(l9.make_proposal(PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED,
                       payload=payload, proposer="k",
                       provenance=Provenance.from_model(external=False, model_id="k")),
                       actor="k")


def test_live_production_capsule_is_frozen_against_a_validator_monkeypatch():
    # the CURRENT production capsule is byte-pinned (no live wrapper); patching the gate validator
    # after sealing must NOT change a sealed event's evaluation.
    import dataclasses

    import desi_layer9.trial_event_validation as V
    from joni.autonomy.trial_event_schema import RULE_V2_HASH
    contra = _ev(epistemic_result="success", measurement=_meas(0.20, ci=(0.12, 0.28)),
                 decision=Decision("rule_v2", RULE_V2_HASH, "success"))
    contra = dataclasses.replace(contra, estimand=dataclasses.replace(contra.estimand,
                                                                      outcome_metric="OTHER"))
    assert evaluate_decision(contra)["status"] == "inconsistent"
    orig = V.cross_block_consistency
    try:
        V.cross_block_consistency = lambda *a, **k: []        # sabotage the LIVE gate validator
        assert evaluate_decision(contra)["status"] == "inconsistent"   # frozen capsule, unchanged
    finally:
        V.cross_block_consistency = orig


def test_production_current_capsule_is_archived_and_byte_pinned():
    from joni.autonomy.trial_event_schema import (
        _CROSS_BLOCK_V1_SRC,
        _RULE_V2_V2_SRC,
        DEFAULT_RULE_REGISTRY,
        RULE_V2_HASH,
        _bytes_hash,
    )
    cur = next(a for a in DEFAULT_RULE_REGISTRY.values()
               if a.rule_id == "rule_v2" and a.implementation_hash == RULE_V2_HASH)
    assert cur.rule_source == _RULE_V2_V2_SRC                  # byte-pinned, not a live function
    assert cur.validator_source == _CROSS_BLOCK_V1_SRC         # byte-pinned validator
    assert _bytes_hash(_RULE_V2_V2_SRC) == RULE_V2_HASH


def test_v3_trial_event_is_never_writable_under_any_public_api():
    # the write boundary is DETERMINISTIC (no replay privilege); a v3 trial event is never stored
    # there is no public parameter combination that stores one.
    core = _kernel()
    v3 = _r13_event().to_dict()                                # unsealed v3
    d = _submit16(core, v3)
    assert not d.accepted and "not a writable trial-event format" in d.reason
    assert core.method_trial_events() == []
    # submit() exposes no replay/bypass parameter at all.
    import inspect
    assert "replaying" not in inspect.signature(core.submit).parameters


def test_a_rejected_v3_attempt_replays_to_an_identical_state():
    # a rejected v3 submission is journaled but reproduces its rejection on replay deterministically
    # no privileged path turns it into a stored trial event; state = f(seed, journal) holds.
    import desi_layer9 as l9
    from desi_layer9 import hashing, persistence
    core = _kernel()
    _submit16(core, _r13_event().to_dict())                   # rejected
    assert core.method_trial_events() == []
    replayed = persistence.replay([l9.JournalEntry.from_dict(e.to_dict()) for e in core.journal])
    assert replayed.method_trial_events() == []               # no trial event from the rejected try
    assert hashing.snapshot_hash(replayed) == hashing.snapshot_hash(core)   # identical state


def test_pre_v4_v3_data_migrates_by_resealing_to_v4():
    # the migration contract: pre-existing v3 trial data becomes writable by RE-SEALING to v4.
    from joni.autonomy.trial_event_schema import seal_payload
    core = _kernel()
    v3 = _r13_event().to_dict()
    assert not _submit16(core, v3).accepted                   # raw v3 is not writable
    assert _submit16(_kernel(), seal_payload(v3)).accepted     # re-sealed to v4 -> writable


def test_new_v4_epistemic_submission_is_accepted():
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    stored = core.method_trial_events()[0]["payload"]
    assert "evaluation_envelope" in stored


def test_operational_event_seals_as_v4_and_the_kernel_accepts_it():
    from joni.autonomy.trial_event_schema import evaluate_payload, operational_observations
    tech = _ev(trial_id="op-t", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated", method_variant="v9")
    obj = tech.to_journal()
    assert "operational_envelope" in obj and "evaluation_envelope" not in obj
    assert obj["operational_envelope"]["operational_class"] == "technical_failure"
    core = _kernel()
    assert _submit16(core, obj).accepted                       # gate accepts operational
    stored = core.method_trial_events()[0]["payload"]
    assert evaluate_payload(stored)["status"] == "operational"
    assert verify_events([tech]) == []                         # never epistemic evidence
    assert operational_observations([stored])[0].desi_result == "technical_failure"


def test_completed_valid_not_evaluated_seals_as_unevaluated():
    ev = _ev(trial_id="u", execution_status="completed", protocol_status="valid",
             failure_kind="none", epistemic_result="not_evaluated")
    obj = ev.to_journal()
    assert obj["operational_envelope"]["operational_class"] == "unevaluated"
    assert _submit16(_kernel(), obj).accepted


def test_to_journal_never_emits_a_v4_object_the_gate_rejects():
    from desi_layer9.trial_event_validation import validate_v4_seal
    cases = [
        _ev(epistemic_result="inconclusive", measurement=_meas(0.03, ci=(-0.05, 0.08)),
            decision=_dec("inconclusive")),                          # epistemic
        _ev(execution_status="failed", failure_kind="timeout", epistemic_result="not_evaluated"),
        _ev(execution_status="cancelled", failure_kind="none", epistemic_result="not_evaluated"),
        _ev(execution_status="completed", protocol_status="invalid", failure_kind="none",
            epistemic_result="not_evaluated"),
    ]
    for ev in cases:
        assert validate_v4_seal(ev.to_journal()) == []        # gate accepts every to_journal output


def test_gate_rejects_a_v4_object_with_both_seals():
    from desi_layer9.trial_event_validation import validate_v4_seal
    obj = _r13_event().to_journal()
    both = dict(obj, operational_envelope={'x': 1})            # both seals -> refused
    assert any("EXACTLY ONE" in e for e in validate_v4_seal(both))


def test_unknown_capsule_is_sealed_unknown_not_a_verdict():
    from joni.autonomy.trial_event_schema import build_rule_registry, evaluate_envelope
    reg = build_rule_registry([_real_archived_artifact()])
    env, body = _sealed_split(reg)
    res = evaluate_envelope(dict(env, capsule_hash="sha256:" + "f" * 64), body, reg)
    assert res["status"] == "sealed_unknown_capsule"          # marked, never verified
    # and it never becomes evidence.
    sealed = dict(body, evaluation_envelope=dict(env, capsule_hash="sha256:" + "f" * 64))
    from joni.autonomy.trial_event_schema import verify_payloads
    assert verify_payloads([sealed], reg) == []


# -- round 17: deterministic write boundary + body-bound operational class --------------------- #
def test_operational_class_must_be_derived_from_the_body():
    # a writer cannot mislabel a technical failure as merely unevaluated (or vice versa): the gate
    # derives the class from the body's execution/protocol status and requires equality.
    tech = _ev(trial_id="op", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated")
    obj = tech.to_journal()
    assert obj["operational_envelope"]["operational_class"] == "technical_failure"
    mis = dict(obj, operational_envelope=dict(obj["operational_envelope"],
                                              operational_class="unevaluated"))
    d = _submit16(_kernel(), mis)
    assert not d.accepted and "operational_class" in d.reason
    assert _submit16(_kernel(), tech.to_journal()).accepted    # the correctly-derived class is fine


def test_each_operational_class_is_pinned_to_its_execution_state():
    from desi_layer9.trial_event_validation import derive_operational_class, validate_v4_seal
    cases = {
        ("failed", "valid"): "technical_failure",
        ("cancelled", "valid"): "cancelled",
        ("completed", "invalid"): "protocol_invalid",
        ("completed", "valid"): "unevaluated",
    }
    for (exec_s, proto), klass in cases.items():
        kw = dict(execution_status=exec_s, protocol_status=proto, epistemic_result="not_evaluated")
        if exec_s == "failed":
            kw["failure_kind"] = "timeout"
        obj = _ev(trial_id=f"op-{exec_s}-{proto}", **kw).to_journal()
        assert derive_operational_class(obj) == klass
        assert obj["operational_envelope"]["operational_class"] == klass
        assert validate_v4_seal(obj) == []                     # the derived class is accepted
        # any OTHER class for the same body is refused.
        wrong = "unevaluated" if klass != "unevaluated" else "technical_failure"
        bad = dict(obj, operational_envelope=dict(obj["operational_envelope"],
                                                  operational_class=wrong))
        assert any("operational_class" in e for e in validate_v4_seal(bad))


def test_submit_carries_no_mutable_replay_state():
    # the replay context is not a mutable Core attribute (no self._replaying); the boundary depends
    # only on the proposal.
    core = _kernel()
    assert not hasattr(core, "_replaying")
    _submit16(core, _r13_event().to_journal())
    assert not hasattr(core, "_replaying")


# -- round 18: journal immutability + versioned v3->v4 migration contract --------------------- #
def test_mutating_the_caller_payload_after_submit_cannot_rewrite_the_journal():
    from desi_layer9 import hashing
    core = _kernel()
    obj = _r13_event().to_journal()
    assert _submit16(core, obj).accepted
    snap = hashing.snapshot_hash(core)
    obj["measurement"]["effect_size"] = 999                   # mutate the caller's nested dict
    obj["evaluation_envelope"]["capsule_hash"] = "sha256:0"   # and the envelope
    assert core.journal[-1].payload["measurement"]["effect_size"] != 999   # journal is frozen
    assert hashing.snapshot_hash(core) == snap                # state unchanged


def test_mutating_an_exported_journal_dict_cannot_rewrite_the_journal():
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    exported = core.journal[-1].to_dict()
    exported["payload"]["measurement"]["effect_size"] = -7    # mutate the EXPORT
    assert core.journal[-1].payload["measurement"]["effect_size"] != -7


def test_from_dict_does_not_alias_its_input():
    import desi_layer9 as l9
    src = {"operator": "method_trial_recorded", "proposal_type": "method_proposal",
           "payload": {"measurement": {"effect_size": 0.03}}, "proposer": "k", "provenance": {},
            "target_objects": [], "actor": "k", "governance_approved": False, "reason": "",
            "tick": 0}
    entry = l9.JournalEntry.from_dict(src)
    src["payload"]["measurement"]["effect_size"] = 42         # mutate the input dict
    assert entry.payload["measurement"]["effect_size"] == 0.03


def test_journal_replay_is_immune_to_external_mutation():
    import desi_layer9 as l9
    from desi_layer9 import hashing, persistence
    core = _kernel()
    obj = _r13_event().to_journal()
    _submit16(core, obj)
    snap = hashing.snapshot_hash(core)
    obj["measurement"]["effect_size"] = 999                   # try to poison after the fact
    replayed = persistence.replay([l9.JournalEntry.from_dict(e.to_dict()) for e in core.journal])
    assert hashing.snapshot_hash(replayed) == snap            # replay reproduces the same state
    assert len(replayed.method_trial_events()) == 1


def _raw_v3_entry(body: dict):
    """Wrap a v3 trial BODY into a persisted journal-entry dict (no attestation). Deep-copies the
    body so a shared constant is never mutated by a test."""
    import copy

    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance
    return {"operator": "method_trial_recorded", "proposal_type": PT.METHOD_PROPOSAL.value,
            "payload": copy.deepcopy(body), "proposer": "kevin",
            "provenance": Provenance.from_model(external=False, model_id="kevin").to_dict(),
            "target_objects": [], "actor": "kevin", "governance_approved": False,
            "reason": "", "tick": 0}


def _v3_body(trial_id="hist", rule_hash=None):
    from joni.autonomy.trial_event_schema import RULE_V2_HASH
    return _ev(trial_id=trial_id, epistemic_result="inconclusive",
               measurement=_meas(0.03, ci=(-0.05, 0.08)),
               decision=Decision("rule_v2", rule_hash or RULE_V2_HASH, "inconclusive")).to_dict()


def _demo_doc_and_catalog():
    """A CLEAN historical document (one demo v3 trial) plus the PINNED dev allowlist attesting its
    FULL entry. The demo anchor lives HERE (the test), never in the production catalog. The
    attestation binds the whole delivered document: full-entry hashes + journal hash + document hash
    + snapshot_hash. Tests then tamper the returned doc to prove each binding."""
    from types import MappingProxyType

    from joni.autonomy.trial_event_schema import (
        _document_hash,
        _full_entry_hash,
        _journal_hash,
        build_historical_attestation,
    )
    entry = _raw_v3_entry(_v3_body("__demo_historical_v3__"))
    journal = [entry]
    snap = "sha256:" + "a" * 64                                 # the historical snapshot selector
    doc = {"journal": journal, "tick": 0, "snapshot_hash": snap}
    att = build_historical_attestation(
        verifier_id="historical_kernel_demo_v1", kernel_release="7810e25",
        gate_policy_version="trial_gate_policy_v1",
        historical_kernel_artifact_hash="sha256:" + "k" * 64,
        gate_policy_artifact_hash="sha256:" + "p" * 64,
        source_document_hash=_document_hash(doc), source_journal_hash=_journal_hash(journal),
        source_snapshot_hash=snap, accepted_full_entry_hashes=[_full_entry_hash(entry)])
    doc["historical_attestation"] = att
    catalog = MappingProxyType({att["verifier_id"]: att})
    return doc, catalog


def test_historical_v3_journal_migrates_to_v4_and_the_trial_reappears():
    from joni.autonomy.trial_event_schema import load_migrated
    doc, cat = _demo_doc_and_catalog()
    core, log = load_migrated(doc, trusted_attestations=cat)
    evs = core.method_trial_events()
    assert len(evs) == 1 and evs[0]["schema_version"] == "method_trial_recorded_v4"
    assert evs[0]["payload"]["measurement"]["effect_size"] == 0.03   # body preserved verbatim
    assert log[0]["attestation"]["verifier_id"] == "historical_kernel_demo_v1"


def test_migration_is_fail_closed_on_an_unknown_capsule():
    # even an attested full entry whose cited rule has no known capsule is fail-closed.
    import pytest

    from joni.autonomy.trial_event_schema import (
        JournalMigrationError,
        _full_entry_hash,
        migrate_journal_entries,
    )
    bad = _raw_v3_entry(_v3_body("bad", rule_hash="sha256:unknown"))
    accepted = {_full_entry_hash(bad)}
    with pytest.raises(JournalMigrationError):
        migrate_journal_entries([bad], accepted_full_entry_hashes=accepted)


def test_migration_introduces_no_submit_privilege_v3_still_unwritable():
    # the migrator transforms the journal; it does NOT relax the write boundary. A raw v3 submission
    # remains rejected.
    core = _kernel()
    assert not _submit16(core, _r13_event().to_dict()).accepted


def test_a_raw_v3_journal_is_not_directly_replayable_without_migration():
    # honest backward-compat: a historical v3 trial entry is NOT raw-replayable
    # (only migration loads it). Replay rejects it; no trial event is reconstructed.
    import desi_layer9 as l9
    from desi_layer9 import persistence
    replayed = persistence.replay([l9.JournalEntry.from_dict(_raw_v3_entry(_v3_body("h")))])
    assert replayed.method_trial_events() == []


# -- round 19: TRUE state immutability + migration trust-source -------------------------------- #
def _make_v4_proposal(payload):
    import desi_layer9 as l9
    from desi_layer9 import Operator as OP
    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance
    return l9.make_proposal(PT.METHOD_PROPOSAL, OP.METHOD_TRIAL_RECORDED, payload=payload,
                            proposer="k", provenance=Provenance.from_model(external=False,
                                                                           model_id="k"))


def test_mutating_the_original_proposal_after_submit_does_not_change_state():
    # MANDATORY-1: submit() stores its OWN deep copy, never the caller's instance. Mutating the
    # proposal (or its nested payload) AFTER submit changes nothing - submit is the only writer.
    from desi_layer9 import hashing
    core = _kernel()
    prop = _make_v4_proposal(_r13_event().to_journal())
    assert core.submit(prop, actor="k").accepted
    snap = hashing.snapshot_hash(core)
    prop.payload["measurement"]["effect_size"] = 999          # mutate the caller's instance
    prop.payload["evaluation_envelope"]["capsule_hash"] = "sha256:0"
    stored = core.method_trial_events()[0]["payload"]
    assert stored["measurement"]["effect_size"] != 999        # authoritative state untouched
    assert hashing.snapshot_hash(core) == snap


def test_mutating_a_get_result_does_not_change_state():
    # MANDATORY-2: get() hands back a deep copy; mutating it cannot reach into the kernel. The trial
    # record stores its payload as an immutable canonical string - no shared nested state.
    from desi_layer9 import hashing
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    oid = core.method_trial_events()[0]["object_id"]
    snap = hashing.snapshot_hash(core)
    got = core.get(oid)
    got.canonical_payload = "{}"                              # mutate the returned object
    got.record_authority = "forged"
    assert core.get(oid).canonical_payload != "{}"
    assert core.get(oid).record_authority == "authoritative"
    assert hashing.snapshot_hash(core) == snap


def test_mutating_an_all_result_does_not_change_state():
    # MANDATORY-3: all() hands back deep copies; mutating the list or its members changes nothing.
    from desi_layer9 import ObjectType, hashing
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    snap = hashing.snapshot_hash(core)
    listing = core.all(ObjectType.METHOD_TRIAL_EVENT)
    listing[0].canonical_payload = "{}"                       # mutate a member
    listing.append("garbage")                                 # mutate the returned list
    assert all(o.canonical_payload != "{}"
               for o in core.all(ObjectType.METHOD_TRIAL_EVENT))
    assert hashing.snapshot_hash(core) == snap


def test_a_journal_entry_payload_cannot_be_mutated_in_place():
    # MANDATORY-4: the journal entry is FROZEN and stores canonical bytes; payload is reconstructed
    # on read, so a direct mutation either raises or is simply ineffective.
    from desi_layer9 import hashing
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    snap = hashing.snapshot_hash(core)
    entry = core.journal[0]
    entry.payload["measurement"]["effect_size"] = 777         # mutate the parsed view
    import pytest
    with pytest.raises((AttributeError, Exception)):          # frozen dataclass: no field rebind
        entry.payload_canonical = "{}"
    assert core.journal[0].payload["measurement"]["effect_size"] != 777
    assert hashing.snapshot_hash(core) == snap


def test_the_journal_list_cannot_be_appended_popped_or_cleared_externally():
    # MANDATORY-5: the public journal is a read-only tuple; append/pop/clear are not available.
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    j = core.journal
    assert isinstance(j, tuple)
    for op in ("append", "pop", "clear"):
        assert not hasattr(j, op)
    assert len(core.journal) == 1                              # unchanged


def test_snapshot_ledger_and_replay_are_identical_after_all_mutation_attempts():
    # MANDATORY-6: after exhausting every external mutation vector, snapshot, ledger chain and a
    # fresh replay all reproduce the SAME authoritative state.
    import desi_layer9 as l9
    from desi_layer9 import ObjectType, hashing, persistence
    core = _kernel()
    prop = _make_v4_proposal(_r13_event().to_journal())
    assert core.submit(prop, actor="k").accepted
    snap = hashing.snapshot_hash(core)
    ok, breaks = hashing.verify_chain(core)
    assert ok and breaks == []
    # exhaust the vectors
    oid = core.method_trial_events()[0]["object_id"]
    prop.payload["measurement"]["effect_size"] = 1            # original proposal
    core.get(oid).canonical_payload = "{}"                    # get() result
    for o in core.all(ObjectType.METHOD_TRIAL_EVENT):         # all() result
        o.canonical_payload = "{}"
    core.journal[0].payload["measurement"]["effect_size"] = 4  # parsed journal view
    assert hashing.snapshot_hash(core) == snap                # snapshot unchanged
    ok2, breaks2 = hashing.verify_chain(core)
    assert ok2 and breaks2 == []                              # ledger chain intact
    replayed = persistence.replay([l9.JournalEntry.from_dict(e.to_dict()) for e in core.journal])
    assert hashing.snapshot_hash(replayed) == snap            # replay reproduces the same state


# -- round 20: the WHOLE public state surface is immutable ------------------------------------- #
def test_mutating_an_objects_value_does_not_change_state():
    # BLOCKER-1 (r20): core.objects[id] hands back a DEEP COPY, not the real internal instance, so
    # neither core.objects[id] = x nor core.objects[id].field = x can reach authoritative state.
    from desi_layer9 import Status, hashing
    core = _kernel()
    assert _submit16(core, _r13_event().to_journal()).accepted
    oid = core.method_trial_events()[0]["object_id"]
    snap = hashing.snapshot_hash(core)
    external = core.objects[oid]
    external.status = Status.REJECTED                          # the reviewer's exact reproduction
    external.canonical_payload = "{}"
    assert hashing.snapshot_hash(core) == snap                # internal state untouched
    assert core.objects[oid].status is not Status.REJECTED
    import pytest
    with pytest.raises(TypeError):                            # keys cannot be injected either
        core.objects["INJECT"] = 1


def test_the_ledger_cannot_be_cleared_or_mutated_externally():
    # BLOCKER-2 (r20): the public ledger is an immutable tuple of deep copies - clear/append/pop are
    # unavailable, and editing a returned event cannot reach the hash chain.
    from desi_layer9 import hashing
    core = _kernel()
    _submit16(core, _r13_event().to_journal())
    led = core.ledger
    assert isinstance(led, tuple)
    for op in ("clear", "append", "pop"):
        assert not hasattr(led, op)
    n = len(core.ledger)
    led[0].reason = "tampered"                                # mutate a returned (copied) event
    ok, problems = hashing.verify_chain(core)
    assert ok and not problems and len(core.ledger) == n     # chain intact, nothing removed


def test_the_logical_clock_is_read_only_and_monotonic():
    # BLOCKER (r20, secondary): there is no bare core.tick setter; the only clock input is the
    # monotonic set_clock(), which never moves backward (replay determinism).
    import pytest

    core = _kernel()
    with pytest.raises(AttributeError):
        core.tick = 5                                         # no public setter
    core.set_clock(3)
    assert core.tick == 3
    core.set_clock(3)                                         # equal is allowed
    with pytest.raises(ValueError):
        core.set_clock(2)                                     # backward is refused


def test_there_is_no_public_minter_or_seq_write_surface():
    # BLOCKER (r20, secondary): the id minter is private; a caller cannot mint ids / shift sequence
    # outside submit().
    core = _kernel()
    assert not hasattr(core, "minter")                        # renamed to _minter (internal)
    assert hasattr(core, "_minter")


# -- round 21: the attestation binds the FULL entry + document, and the demo anchor is NOT in prod #
def test_changing_journal_metadata_of_an_attested_body_is_refused():
    # the reviewer's exact reproduction: keep the attested trial BODY + attestation + snapshot, but
    # swap the JournalEntry's actor/proposer/provenance/governance/reason. Migration must refuse -
    # the attestation binds the WHOLE entry, not just the body.
    import pytest

    from desi_layer9.provenance import Provenance
    from joni.autonomy.trial_event_schema import JournalMigrationError, load_migrated
    tampers = [
        {"actor": "mallory"},
        {"proposer": "mallory"},
        {"governance_approved": True},
        {"reason": "forged metadata"},
        {"provenance": Provenance.from_model(external=False, model_id="mallory").to_dict()},
        {"tick": 99},
        {"operator": "claim_create"},
        {"proposal_type": "claim_proposal"},
        {"target_objects": ["X-1"]},
    ]
    for tamper in tampers:
        doc, cat = _demo_doc_and_catalog()
        doc["journal"][0].update(tamper)                      # body + attestation untouched
        with pytest.raises(JournalMigrationError):
            load_migrated(doc, trusted_attestations=cat)


def test_reusing_the_pinned_snapshot_string_with_a_different_journal_is_refused():
    # BLOCKER-2: source_snapshot_hash is only a selector; the real binding is source_journal_hash /
    # source_document_hash over the DELIVERED content. Copying the known snapshot string onto a
    # different journal does not migrate.
    import pytest

    from joni.autonomy.trial_event_schema import JournalMigrationError, load_migrated
    doc, cat = _demo_doc_and_catalog()
    doc["journal"].append(_raw_v3_entry(_v3_body("smuggled")))   # add an entry, keep the snapshot
    with pytest.raises(JournalMigrationError):
        load_migrated(doc, trusted_attestations=cat)


def test_the_production_catalog_is_empty_so_no_demo_document_migrates():
    # BLOCKER-4: the demo anchor is NOT registered in production. With the default (empty) catalog,
    # even the perfectly-formed demo document is fail-closed; only an explicitly-injected dev/test
    # catalog migrates it.
    import pytest

    from joni.autonomy.trial_event_schema import (
        _TRUSTED_HISTORICAL_ATTESTATIONS,
        JournalMigrationError,
        load_migrated,
    )
    assert dict(_TRUSTED_HISTORICAL_ATTESTATIONS) == {}        # production default: empty allowlist
    doc, cat = _demo_doc_and_catalog()
    with pytest.raises(JournalMigrationError):
        load_migrated(doc)                                    # production catalog -> fail-closed
    core, _ = load_migrated(doc, trusted_attestations=cat)    # explicit dev catalog -> migrates
    assert len(core.method_trial_events()) == 1


def test_a_forged_attestation_for_a_deadbeef_document_is_refused():
    # a self-consistent forged attestation whose digest is not the allowlisted anchor is refused.
    import pytest

    from joni.autonomy.trial_event_schema import (
        JournalMigrationError,
        _document_hash,
        _full_entry_hash,
        _journal_hash,
        build_historical_attestation,
        load_migrated,
    )
    entry = _raw_v3_entry(_v3_body("evil"))
    doc = {"journal": [entry], "tick": 0, "snapshot_hash": "sha256:DEADBEEF"}
    forged = build_historical_attestation(
        verifier_id="historical_kernel_demo_v1", kernel_release="7810e25",
        gate_policy_version="trial_gate_policy_v1",
        historical_kernel_artifact_hash="sha256:" + "k" * 64,
        gate_policy_artifact_hash="sha256:" + "p" * 64,
        source_document_hash=_document_hash(doc), source_journal_hash=_journal_hash([entry]),
        source_snapshot_hash="sha256:DEADBEEF",
        accepted_full_entry_hashes=[_full_entry_hash(entry)])
    doc["historical_attestation"] = forged
    _, cat = _demo_doc_and_catalog()                          # only the demo digest is allowlisted
    with pytest.raises(JournalMigrationError):
        load_migrated(doc, trusted_attestations=cat)


def test_a_tampered_attestation_field_is_rejected():
    # the attestation_digest is recomputed from the body; a tampered field keeping the old digest
    # fails, and even rebuilding the digest fails (it is no longer the allowlisted anchor).
    import pytest

    from joni.autonomy.trial_event_schema import JournalMigrationError, load_migrated
    doc, cat = _demo_doc_and_catalog()
    doc["historical_attestation"]["kernel_release"] = "ATTACKER"   # field changed, old digest kept
    with pytest.raises(JournalMigrationError):
        load_migrated(doc, trusted_attestations=cat)


def test_a_caller_cannot_self_declare_acceptance_with_its_own_verifier():
    # a caller's OWN attestation (new verifier_id) is not in the pinned allowlist -> fail-closed.
    import pytest

    from joni.autonomy.trial_event_schema import (
        JournalMigrationError,
        _document_hash,
        _full_entry_hash,
        _journal_hash,
        build_historical_attestation,
        load_migrated,
    )
    entry = _raw_v3_entry(_v3_body("mine"))
    doc = {"journal": [entry], "tick": 0, "snapshot_hash": "sha256:" + "a" * 64}
    own = build_historical_attestation(
        verifier_id="my_own_verifier", kernel_release="7810e25",
        gate_policy_version="trial_gate_policy_v1",
        historical_kernel_artifact_hash="sha256:" + "k" * 64,
        gate_policy_artifact_hash="sha256:" + "p" * 64,
        source_document_hash=_document_hash(doc), source_journal_hash=_journal_hash([entry]),
        source_snapshot_hash="sha256:" + "a" * 64,
        accepted_full_entry_hashes=[_full_entry_hash(entry)])
    doc["historical_attestation"] = own
    _, cat = _demo_doc_and_catalog()                          # only the demo verifier allowlisted
    with pytest.raises(JournalMigrationError):
        load_migrated(doc, trusted_attestations=cat)


def test_load_migrated_takes_no_caller_supplied_verifier_function():
    # the historical_verifier=lambda: True escape hatch stays GONE; trust is an injected list of
    # pinned digests, never an executable.
    import inspect

    from joni.autonomy.trial_event_schema import load_migrated
    params = inspect.signature(load_migrated).parameters
    assert "historical_verifier" not in params
    assert "trusted_attestations" in params                   # an allowlist, not a function


def test_an_unattested_v3_command_fails_closed():
    # a v3 command with NO attested accepted set cannot be migrated to accepted v4 - fail-closed.
    import pytest

    from joni.autonomy.trial_event_schema import JournalMigrationError, migrate_journal_entries
    with pytest.raises(JournalMigrationError):
        migrate_journal_entries([_raw_v3_entry(_v3_body("x"))])


def test_the_migration_log_documents_the_full_attestation_chain():
    # the migration is auditable: the log records the pinned digest + kernel/policy artifacts +
    # document/journal/snapshot hashes, and per entry the attested FULL-entry hash + capsule.
    from joni.autonomy.trial_event_schema import load_migrated
    doc, cat = _demo_doc_and_catalog()
    _, log = load_migrated(doc, trusted_attestations=cat)
    att = log[0]["attestation"]
    for k in ("verifier_id", "kernel_release", "gate_policy_version",
              "historical_kernel_artifact_hash", "gate_policy_artifact_hash",
              "source_document_hash",
              "source_journal_hash", "source_snapshot_hash", "attestation_digest",
              "accepted_full_entry_hashes"):
        assert k in att
    rec = log[1]
    assert rec["from"] == "method_trial_recorded_v3" and rec["to"] == "method_trial_recorded_v4"
    assert rec["attested_full_entry_hash"].startswith("sha256:")
    assert rec["capsule_hash"] and rec["capsule_hash"].startswith("sha256:")


def test_migration_output_does_not_alias_its_input():
    # the migrated entries are FULLY deep-copied; mutating the input after migration cannot reach
    # into the migrated output (and vice versa).
    from joni.autonomy.trial_event_schema import _full_entry_hash, migrate_journal_entries
    demo = _raw_v3_entry(_v3_body("alias"))
    passthrough = {"operator": "noop", "payload": {"a": {"b": 1}},
                   "proposal_type": "method_proposal", "proposer": "k", "provenance": {},
                   "target_objects": [], "actor": "k", "governance_approved": False,
                   "reason": "", "tick": 0}
    src = [demo, passthrough]
    accepted = {_full_entry_hash(demo)}
    migrated, _ = migrate_journal_entries(src, accepted_full_entry_hashes=accepted)
    src[0]["payload"]["measurement"]["effect_size"] = 12345   # mutate the v3 input post-migration
    src[1]["payload"]["a"]["b"] = 999                         # mutate the pass-through input
    assert migrated[0]["payload"]["measurement"]["effect_size"] == 0.03   # sealed body unchanged
    assert migrated[1]["payload"]["a"]["b"] == 1              # pass-through copy independent
