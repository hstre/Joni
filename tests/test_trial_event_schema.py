"""Acceptance proof for the METHOD_TRIAL_RECORDED schema PROPOSAL (v2, review round).

Pins the contract BEFORE any core change: the three-axis status model and its forbidden
combinations, the decision-rule-anchored ``no_benefit``, the conservative legacy migration
(verified against the old writers), scope separation, multi-affinity roll-up, and - the point of
this round - that affinity attribution needs INDEPENDENT variants, not just two of them. Touches no
core object; the schema module duck-types a legacy Method via a tiny fake.
"""

from joni.autonomy.trial_event_schema import (
    Estimand,
    Measurement,
    MethodTrialRecorded,
    aggregate,
    attribute_to_affinity,
    migrate_method,
    validate,
)

_EST = Estimand(outcome_metric="misclass_rate", direction="higher_is_better", minimum_effect=0.10,
                decision_rule_id="rule_v2")


def _meas(effect, unc=0.02, base=0.40, inter=0.30):
    return Measurement("misclass_rate", base, inter, effect_size=effect, uncertainty=unc)


def _ev(**kw) -> MethodTrialRecorded:
    base = dict(
        trial_id="t1", timestamp="2026-06-16T00:00:00Z", ledger_tick=1,
        target_type="conflict", target_id="X17", claim_ids=("C-7",), scope_id="qtt",
        method_id="m_causal", method_variant="v2", affinities=("causal",), estimand=_EST,
        execution_status="completed", protocol_status="valid",
        epistemic_result="not_evaluated", note="n/a")
    base.update(kw)
    return MethodTrialRecorded(**base)


# -- three-axis status model: forbidden combinations --------------------------------------------- #
def test_failed_execution_cannot_carry_a_result():
    bad = _ev(execution_status="failed", failure_kind="technical", epistemic_result="no_benefit")
    assert any("non-completed run has no scientific result" in e for e in validate(bad))
    ok = _ev(execution_status="failed", failure_kind="timeout", epistemic_result="not_evaluated")
    assert validate(ok) == []


def test_failed_requires_a_failure_kind_and_vice_versa():
    assert any("failed' requires a failure_kind" in e
               for e in validate(_ev(execution_status="failed", epistemic_result="not_evaluated")))
    assert any("requires execution_status 'failed'" in e
               for e in validate(_ev(failure_kind="model")))


def test_invalid_protocol_carries_no_result():
    bad = _ev(protocol_status="invalid", epistemic_result="success", measurement=_meas(0.18))
    assert any("protocol_status 'invalid' requires" in e for e in validate(bad))
    ok = _ev(protocol_status="invalid", epistemic_result="not_evaluated")
    assert validate(ok) == []


def test_unknown_protocol_cannot_carry_a_real_result():
    bad = _ev(protocol_status="unknown", epistemic_result="no_benefit", measurement=_meas(0.05))
    assert any("requires protocol_status 'valid'" in e for e in validate(bad))


# -- estimand / decision rule: no_benefit must be the rule's verdict ----------------------------- #
def test_real_result_requires_measurement_and_estimand():
    no_metric = _ev(epistemic_result="no_benefit", measurement=Measurement("m", None, None))
    assert any("requires a measurement" in e for e in validate(no_metric))
    no_rule = _ev(epistemic_result="no_benefit", estimand=Estimand(minimum_effect=0.0),
                  measurement=_meas(0.05))
    assert any("decision_rule_id and minimum_effect > 0" in e for e in validate(no_rule))


def test_no_benefit_means_minimum_effect_not_met():
    # effect resolved (0.05 > uncertainty 0.02) but BELOW minimum_effect 0.10 -> a valid no_benefit.
    good = _ev(epistemic_result="no_benefit", measurement=_meas(0.05, unc=0.02))
    assert validate(good) == []
    # an effect that MEETS the threshold may NOT be labelled no_benefit (that is success).
    bad = _ev(epistemic_result="no_benefit", measurement=_meas(0.18, unc=0.02))
    assert any("must be the decision rule's verdict" in e for e in validate(bad))


def test_success_needs_to_clear_the_threshold_and_beat_noise():
    below = _ev(epistemic_result="success", measurement=_meas(0.05))     # under min_effect
    assert any("requires effect_size >= minimum_effect" in e for e in validate(below))
    within_noise = _ev(epistemic_result="success", measurement=_meas(0.12, unc=0.20))
    assert any("beyond" in e for e in validate(within_noise))
    good = _ev(epistemic_result="success", measurement=_meas(0.18, unc=0.03))
    assert validate(good) == []


def test_harmful_needs_a_worsening_beyond_threshold():
    bad = _ev(epistemic_result="harmful", measurement=_meas(0.05))
    assert any("requires effect_size <= -minimum_effect" in e for e in validate(bad))
    good = _ev(epistemic_result="harmful", measurement=_meas(-0.15, unc=0.03))
    assert validate(good) == []


def test_affinity_attribution_forbidden_on_raw_event():
    assert any("affinity-level is earned by aggregation only" in e
               for e in validate(_ev(attribution_level="affinity")))
    assert any("never carries attribution_strength" in e
               for e in validate(_ev(attribution_strength="limited")))


def test_structural_minimums():
    assert any("claim_ids" in e for e in validate(_ev(claim_ids=())))
    assert any("requires a note" in e for e in validate(_ev(note="")))


# -- legacy migration: conservative, verified against the old writers ---------------------------- #
class _FakeMethod:
    id = "m_old"
    version = 1
    applicable_to = ("causal", "boundary")
    supporting_runs = ("kevin-c12", "kevin-real-7")   # one simulation run, one measured-trial run
    failed_runs = ("kevin-c13",)
    success_count = 2
    failure_count = 1


def test_legacy_success_is_not_trusted_by_default():
    evs = migrate_method(_FakeMethod())
    assert all(validate(e) == [] for e in evs)
    # NOTHING migrates to a real success without proof; no event is no_benefit either.
    assert all(e.epistemic_result != "success" for e in evs)
    assert all(e.epistemic_result != "no_benefit" for e in evs)
    assert all(e.epistemic_result == "not_evaluated" for e in evs)
    # the old boolean is preserved as provenance only.
    assert any(e.legacy_reported_success for e in evs)


def test_legacy_success_upgraded_only_for_a_proven_run_class():
    evs = migrate_method(_FakeMethod(), proven_success_runs=("kevin-real",))
    assert all(validate(e) == [] for e in evs)
    succ = [e for e in evs if e.epistemic_result == "success"]
    # only the proven 'kevin-real' run becomes a weak success; the simulation run does not...
    assert len(succ) == 1 and succ[0].run_id.startswith("kevin-real")
    assert succ[0].legacy and succ[0].scope_id == "unknown" and succ[0].method_variant == "unknown"
    # ...and the old failure is STILL never no_benefit.
    assert all(e.epistemic_result != "no_benefit" for e in evs)


# -- aggregation: scope separation, technical, harmful, multi-affinity --------------------------- #
def test_no_benefit_demotes_only_its_own_variant_scope():
    evs = [
        _ev(trial_id="a", scope_id="qtt", method_variant="v2", epistemic_result="no_benefit",
            measurement=_meas(0.05)),
        _ev(trial_id="b", scope_id="other", method_variant="v2", epistemic_result="not_evaluated",
            note="not run here"),
    ]
    cells = {(o.scope_id, o.method_variant): o.outcome for o in aggregate(evs)}
    assert cells[("qtt", "v2")] == "no_benefit"
    assert cells[("other", "v2")] != "no_benefit"


def test_unusable_cell_is_not_a_negative_result():
    evs = [_ev(trial_id="a", execution_status="failed", failure_kind="timeout",
               epistemic_result="not_evaluated")]
    assert aggregate(evs)[0].outcome == "technical_only"


def test_harmful_dominates_within_a_cell():
    evs = [
        _ev(trial_id="a", epistemic_result="success", measurement=_meas(0.18, unc=0.03)),
        _ev(trial_id="b", epistemic_result="harmful", measurement=_meas(-0.15, unc=0.03)),
    ]
    assert aggregate(evs)[0].outcome == "harmful"


# -- affinity attribution: INDEPENDENCE, not a flat count ---------------------------------------- #
def _neg(variant, model, impl, conf=(), aff=("causal",)):
    return _ev(trial_id=f"t-{variant}", method_variant=variant, model=model, implementation_id=impl,
               affinities=aff, confounders=conf, epistemic_result="no_benefit",
               measurement=_meas(0.05))


def test_two_highly_correlated_variants_do_not_demote_the_affinity():
    # two variants, but SAME model + SAME shared confounder -> not independent -> strength none.
    evs = [_neg("v1", "deepseek-chat", "impl-A", conf=("shared_prompt_bug",)),
           _neg("v2", "deepseek-chat", "impl-A", conf=("shared_prompt_bug",))]
    a = attribute_to_affinity(aggregate(evs))[0]
    assert a.strength == "none" and not a.independent
    assert "share one model" in a.reason or "shared by all" in a.reason


def test_two_independent_variants_give_a_limited_attribution():
    evs = [_neg("v1", "deepseek-chat", "impl-A", conf=("noise_a",)),
           _neg("v2", "gpt-4o", "impl-B", conf=("noise_b",))]
    a = attribute_to_affinity(aggregate(evs))[0]
    assert a.strength == "limited" and a.independent and a.n_variants_negative == 2


def test_a_success_makes_the_affinity_picture_inconsistent():
    evs = [_neg("v1", "deepseek-chat", "impl-A", conf=("noise_a",)),
           _neg("v2", "gpt-4o", "impl-B", conf=("noise_b",)),
           _ev(trial_id="ok", method_variant="v3", model="claude", implementation_id="impl-C",
               epistemic_result="success", measurement=_meas(0.18, unc=0.03))]
    a = attribute_to_affinity(aggregate(evs))[0]
    assert a.strength == "none" and "inconsistent" in a.reason


def test_multi_affinity_method_rolls_up_to_each_affinity():
    # two INDEPENDENT variants fail on 'causal'; 'boundary' is touched by only one of them.
    evs = [_neg("v1", "deepseek-chat", "impl-A", conf=("noise_a",), aff=("causal", "boundary")),
           _neg("v2", "gpt-4o", "impl-B", conf=("noise_b",), aff=("causal",))]
    attrs = {a.affinity: a for a in attribute_to_affinity(aggregate(evs))}
    assert attrs["causal"].strength == "limited"
    assert attrs["boundary"].strength == "none"     # one variant never condemns the move


def test_single_variant_no_benefit_never_condemns_the_affinity():
    a = attribute_to_affinity(aggregate([_neg("v1", "deepseek-chat", "impl-A")]))[0]
    assert a.strength == "none"
