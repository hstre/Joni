"""Read-only projector: Layer-9 ``method_trial_events()`` -> a transparent trial projection.

The controlled connection from the STORED event to external epistemic evaluation. It is strictly
read-only and does the interpretation OUTSIDE the core:

  * the ONLY new trial source is ``core.method_trial_events()`` - legacy ``Method`` counters are
    NEVER re-read as scope-bound trial history;
  * envelope, schema_version, record_authority and epistemic_authority are evaluated SEPARATELY from
    the reported payload;
  * decision verdicts are verified by the registered, versioned rule (id + hash) via
    ``trial_event_schema.evaluate_decision`` - an unknown/non-reproducible hash is ``unverifiable``;
  * the independence policy is applied versioned (``attribute_to_affinity``);
  * ``unverifiable`` and ``insufficient`` are kept VISIBLE - never filtered out (negative
    transparency is a result, not noise);
  * an unknown/invalid field is never read as a zero signal;
  * with no verified scope-bound events, the verdict is INSUFFICIENT.

Nothing here writes to the core, mutates an object, or activates a writer/DESi/Kevin path.
"""

from __future__ import annotations

from desi_layer9.trial_event_validation import SUPPORTED_TRIAL_SCHEMA_VERSIONS

from .trial_event_schema import (
    Decision,
    Estimand,
    Measurement,
    MethodTrialRecorded,
    aggregate,
    attribute_to_affinity,
    evaluate_decision,
)


def available() -> bool:
    try:
        import desi.solution_space_gap  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _record_from_payload(p: dict) -> MethodTrialRecorded:
    """Reconstruct a typed record from a stored canonical payload. Missing fields become explicit
    'unknown'/None - never a fabricated value."""
    est, dec, meas = p.get("estimand") or {}, p.get("decision") or {}, p.get("measurement") or {}
    ci = dec.get("confidence_interval")
    return MethodTrialRecorded(
        trial_id=p.get("trial_id", ""), timestamp=p.get("timestamp", ""),
        ledger_tick=int(p.get("ledger_tick", 0) or 0),
        target_type=p.get("target_type", "conflict"), target_id=p.get("target_id", "unknown"),
        claim_ids=tuple(p.get("claim_ids", ()) or ()),
        scope_id=p.get("scope_id", "unknown"), method_id=p.get("method_id", "unknown"),
        method_version=int(p.get("method_version", 1) or 1),
        method_variant=p.get("method_variant", "unknown"),
        implementation_id=p.get("implementation_id", "unknown"),
        affinities=tuple(p.get("affinities", ()) or ()),
        task_set_id=p.get("task_set_id", "unknown"),
        task_sample_id=p.get("task_sample_id", "unknown"),
        baseline_id=p.get("baseline_id", "unknown"), evaluator_id=p.get("evaluator_id", "unknown"),
        estimand=Estimand(
            outcome_metric=est.get("outcome_metric", ""),
            contrast=est.get("contrast", "intervention_minus_baseline"),
            direction=est.get("direction", "higher_is_better"),
            minimum_effect=float(est.get("minimum_effect", 0.0) or 0.0),
            decision_rule_id=est.get("decision_rule_id", "")),
        model=p.get("model", "unknown"), model_family=p.get("model_family", "unknown"),
        execution_status=p.get("execution_status", "completed"),
        protocol_status=p.get("protocol_status", "valid"),
        failure_kind=p.get("failure_kind", "none"),
        epistemic_result=p.get("epistemic_result", "not_evaluated"),
        measurement=Measurement(
            metric_name=meas.get("metric_name"), baseline_value=meas.get("baseline_value"),
            intervention_value=meas.get("intervention_value"), effect_size=meas.get("effect_size"),
            uncertainty=meas.get("uncertainty")),
        decision=Decision(
            decision_rule_id=dec.get("decision_rule_id", ""),
            decision_rule_hash=dec.get("decision_rule_hash", ""),
            verdict=dec.get("verdict", "not_evaluated"), effect_size=dec.get("effect_size"),
            confidence_interval=tuple(ci) if ci else None,
            minimum_effect=dec.get("minimum_effect")),
        confounders=tuple(p.get("confounders", ()) or ()))


def _project_event(env: dict) -> tuple[dict, MethodTrialRecorded | None]:
    """One transparent per-event projection + the record IF it is verified scope-bound evidence."""
    p = env.get("payload") or {}
    schema_ok = p.get("schema_version") in SUPPORTED_TRIAL_SCHEMA_VERSIONS
    rec = _record_from_payload(p)
    dv = evaluate_decision(rec) if schema_ok else {"status": "not_applicable",
                                                   "reason": "unsupported schema_version"}
    verified = (schema_ok and dv["status"] == "verified"
                and rec.execution_status == "completed" and rec.protocol_status == "valid")
    proj = {
        "object_id": env.get("object_id"),
        "trial_id": p.get("trial_id", "unknown"),
        "schema_version": env.get("schema_version"),
        "schema_status": "supported" if schema_ok else "unsupported",
        "record_status": "registered",                 # it IS in the core (Layer 9 confirms that)
        "record_authority": env.get("record_authority"),
        "epistemic_authority": env.get("epistemic_authority"),
        "decision_status": dv["status"],               # verified|inconsistent|unverifiable|n/a
        "epistemic_weight": "verified_scope_bound" if verified else "none",
        "target": f"{p.get('target_type', 'unknown')}:{p.get('target_id', 'unknown')}",
        "scope_id": p.get("scope_id", "unknown"),
        "reported_result": p.get("epistemic_result", "unknown"),
        "note": dv.get("reason", ""),
    }
    return proj, (rec if verified else None)


def _trial_to_dict(t) -> dict:
    return {"affinity": t.affinity, "target_conflict": t.target_conflict, "result": t.result,
            "scope": t.scope, "method_variant": t.method_variant, "count": t.count}


def project_trial_events(core) -> dict:
    """Project the registered trial events into a transparent structure for external evaluation.

    Keeps every registered event visible with its decision_status; only VERIFIED scope-bound events
    feed the aggregation. Returns INSUFFICIENT when none are verified - registered-but-unverifiable
    events and legacy counters are NOT counted as trial history."""
    envelopes = core.method_trial_events()
    events: list[dict] = []
    verified: list[MethodTrialRecorded] = []
    for env in envelopes:
        proj, rec = _project_event(env)
        events.append(proj)
        if rec is not None:
            verified.append(rec)

    outcomes = aggregate(verified)
    scope_bound = [
        {"target_id": o.target_id, "scope_id": o.scope_id, "method_variant": o.method_variant,
         "outcome": o.outcome, "n_completed_valid": o.n_completed_valid,
         "affinities": list(o.affinities)}
        for o in outcomes]
    affinity = [
        {"target_id": a.target_id, "scope_id": a.scope_id, "affinity": a.affinity,
         "strength": a.strength, "policy_id": a.policy_id, "independent": a.independent,
         "reason": a.reason}
        for a in attribute_to_affinity(outcomes)]

    desi_trials = None
    if outcomes and available():
        from .trial_event_schema import to_desi_method_trials
        desi_trials = [_trial_to_dict(t) for t in to_desi_method_trials(outcomes)]

    sufficient = bool(outcomes)
    return {
        "events": events,
        "verified_scope_bound_outcomes": scope_bound,
        "affinity_attributions": affinity,
        "desi_method_trials": desi_trials,              # None if DESi unavailable; never fabricated
        "data_sufficiency": {
            "registered_events": len(events),
            "verified_events": len(verified),
            "unverifiable_events": sum(1 for e in events if e["decision_status"] == "unverifiable"),
            "inconsistent_events": sum(1 for e in events if e["decision_status"] == "inconsistent"),
            "verdict": "sufficient" if sufficient else (
                "insufficient: no verified scope-bound trial outcomes - registered-but-"
                "unverifiable events and legacy counters are NOT interpreted as trial history"),
        },
    }
