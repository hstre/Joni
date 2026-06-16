"""Acceptance proof for the METHOD_TRIAL_RECORDED schema PROPOSAL.

These tests pin the contract BEFORE any core change: the forbidden combinations, the conservative
legacy migration, scope separation, multi-affinity roll-up, and the central rule that a technical
failure carries no methodological signal. They touch no core object - the schema module duck-types
a legacy Method via a tiny fake.
"""

from joni.autonomy.trial_event_schema import (
    Measurement,
    MethodTrialRecorded,
    aggregate,
    attribute_to_affinity,
    migrate_method,
    validate,
)


def _ev(**kw) -> MethodTrialRecorded:
    base = dict(
        trial_id="t1", timestamp="2026-06-16T00:00:00Z", ledger_tick=1,
        target_type="conflict", target_id="X17", claim_ids=("C-7",), scope_id="qtt",
        method_id="m_causal", method_variant="v2", affinities=("causal",),
        execution_status="completed", epistemic_result="not_evaluated", note="n/a")
    base.update(kw)
    return MethodTrialRecorded(**base)


# -- validation: forbidden combinations ---------------------------------------------------------- #
def test_technical_failure_cannot_carry_a_result():
    bad = _ev(execution_status="technical_failure", epistemic_result="no_benefit")
    assert any("technical failure is not a scientific result" in e for e in validate(bad))
    ok = _ev(execution_status="technical_failure", epistemic_result="not_evaluated", note="oom")
    assert validate(ok) == []


def test_real_result_requires_completion_and_measurement():
    no_metric = _ev(epistemic_result="no_benefit")
    assert any("requires a measurement" in e for e in validate(no_metric))
    good = _ev(epistemic_result="no_benefit",
               measurement=Measurement("misclass_rate", 0.40, 0.39, effect_size=0.01,
                                       uncertainty=0.05, higher_is_better=False))
    assert validate(good) == []


def test_success_sign_and_harmful_sign():
    # success with non-positive effect is forbidden (that is not an improvement)...
    bad_succ = _ev(epistemic_result="success",
                   measurement=Measurement("acc", 0.5, 0.5, effect_size=0.0, uncertainty=0.01))
    assert any("non-positive effect_size" in e for e in validate(bad_succ))
    # ...and harmful must actually worsen.
    bad_harm = _ev(epistemic_result="harmful",
                   measurement=Measurement("acc", 0.5, 0.6, effect_size=0.1, uncertainty=0.01))
    assert any("non-negative effect_size" in e for e in validate(bad_harm))
    good_harm = _ev(epistemic_result="harmful",
                    measurement=Measurement("acc", 0.5, 0.4, effect_size=-0.1, uncertainty=0.01))
    assert validate(good_harm) == []


def test_inconclusive_within_uncertainty_is_not_success():
    inconclusive = _ev(
        epistemic_result="success",
        measurement=Measurement("acc", 0.5, 0.52, effect_size=0.02, uncertainty=0.05))
    assert any("within uncertainty" in e for e in validate(inconclusive))


def test_affinity_attribution_forbidden_on_raw_event():
    bad = _ev(attribution_level="affinity")
    assert any("affinity-level is earned by aggregation only" in e for e in validate(bad))


def test_structural_minimums():
    assert any("claim_ids" in e for e in validate(_ev(claim_ids=())))
    assert any("completed + not_evaluated requires a note" in e for e in validate(_ev(note="")))


# -- legacy migration: conservative ---------------------------------------------------------------#
class _FakeMethod:
    id = "m_old"
    version = 1
    applicable_to = ("causal", "boundary")
    supporting_runs = ("r1",)
    failed_runs = ("r2",)
    success_count = 1
    failure_count = 1


def test_legacy_success_becomes_weak_success_failure_becomes_not_evaluated():
    evs = migrate_method(_FakeMethod())
    assert all(validate(e) == [] for e in evs)
    succ = [e for e in evs if e.epistemic_result == "success"]
    # the OLD failure must NEVER become no_benefit - it is not_evaluated (no demoting signal).
    assert all(e.epistemic_result != "no_benefit" for e in evs)
    assert any(e.epistemic_result == "not_evaluated" for e in evs)
    assert succ and succ[0].scope_id == "unknown" and succ[0].method_variant == "unknown"
    assert succ[0].field_sources["epistemic_result"]["confidence"] == "derived"


# -- aggregation + scope separation + multi-affinity --------------------------------------------- #
def test_no_benefit_demotes_only_its_own_variant_scope():
    measured = Measurement("misclass_rate", 0.40, 0.40, effect_size=0.0, uncertainty=0.02,
                           higher_is_better=False)
    evs = [
        _ev(trial_id="a", scope_id="qtt", method_variant="v2", epistemic_result="no_benefit",
            measurement=measured),
        _ev(trial_id="b", scope_id="other", method_variant="v2", epistemic_result="not_evaluated",
            note="not run here"),
    ]
    cells = {(o.scope_id, o.method_variant): o.outcome for o in aggregate(evs)}
    assert cells[("qtt", "v2")] == "no_benefit"          # demoted here...
    assert cells[("other", "v2")] != "no_benefit"        # ...never leaks to another scope


def test_technical_only_cell_is_not_a_negative_result():
    evs = [_ev(trial_id="a", execution_status="technical_failure",
               epistemic_result="not_evaluated", note="timeout")]
    o = aggregate(evs)[0]
    assert o.outcome == "technical_only"                 # no methodological signal


def test_harmful_dominates_within_a_cell():
    good = Measurement("acc", 0.5, 0.6, effect_size=0.1, uncertainty=0.01)
    bad = Measurement("acc", 0.5, 0.4, effect_size=-0.1, uncertainty=0.01)
    evs = [
        _ev(trial_id="a", epistemic_result="success", measurement=good),
        _ev(trial_id="b", epistemic_result="harmful", measurement=bad),
    ]
    assert aggregate(evs)[0].outcome == "harmful"        # safety dominates


def test_multi_affinity_method_rolls_up_to_each_affinity():
    bad = Measurement("misclass_rate", 0.4, 0.4, effect_size=0.0, uncertainty=0.02,
                      higher_is_better=False)
    # two DISTINCT variants both show no_benefit on the same (target, scope) for affinity 'causal'.
    evs = [
        _ev(trial_id="a", method_variant="v1", affinities=("causal", "boundary"),
            epistemic_result="no_benefit", measurement=bad),
        _ev(trial_id="b", method_variant="v2", affinities=("causal",),
            epistemic_result="no_benefit", measurement=bad),
    ]
    attrs = {a.affinity: a for a in attribute_to_affinity(aggregate(evs))}
    # >= 2 distinct variants no_benefit -> a LIMITED affinity attribution (never from one variant).
    assert attrs["causal"].strength == "limited" and attrs["causal"].n_variants_no_benefit == 2
    # ...boundary, seen failing in only ONE variant, is NOT condemned.
    assert attrs["boundary"].strength == "none" and attrs["boundary"].n_variants_no_benefit == 1


def test_single_variant_no_benefit_never_condemns_the_affinity():
    bad = Measurement("misclass_rate", 0.4, 0.4, effect_size=0.0, uncertainty=0.02,
                      higher_is_better=False)
    evs = [_ev(trial_id="a", method_variant="v1", epistemic_result="no_benefit", measurement=bad)]
    attrs = attribute_to_affinity(aggregate(evs))
    assert attrs[0].strength == "none"                   # one variant is scope+variant bound only
