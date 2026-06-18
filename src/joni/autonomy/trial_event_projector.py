"""Read-only projector: Layer-9 ``method_trial_events()`` -> a transparent trial projection.

The controlled connection from the STORED event to external epistemic evaluation. Strictly
read-only; interpretation happens OUTSIDE the core. It separates three orthogonal questions that an
earlier draft conflated:

  1. ``event_usability``     - is a SINGLE event structurally usable?
  2. ``decision_status``     - is its verdict reproducible via the registered, versioned rule?
  3. ``dataset_sufficiency`` - is the WHOLE conflict-/scope-bound history enough for a DESi
                               solution-space gap analysis?

A single rule-verified event is usable and reproducible, but does NOT by itself make the dataset
sufficient. "Verified" is also not "authoritative": a reproducible verdict is a
``measured_candidate`` (``record_authority=authoritative``, ``epistemic_authority=none``) - DESi may
use it, but expert review and later governance remain required.

Rules: only ``method_trial_events()`` is read (legacy counters are never trial history); envelope,
schema_version and both authority levels are evaluated separately; ``unverifiable`` /
``inconsistent`` / ``unsupported_schema`` / ``insufficient`` stay VISIBLE, never filtered; a missing
field is explicit ``unknown``/``None``, never a zero signal. Nothing here writes/activates anything.
"""

from __future__ import annotations

from .trial_event_schema import (
    INDEPENDENCE_POLICY_V1,
    SCHEMA_VERSION,
    Decision,
    Estimand,
    Measurement,
    MethodTrialRecorded,
    _profile,
    aggregate,
    attribute_to_affinity,
    evaluate_payload,
    validate,
)

# The projector's OWN supported set - it may lag the core, so a future schema is surfaced as
# ``unsupported_schema`` (a projector limitation) rather than silently dropped.
PROJECTOR_SUPPORTED_SCHEMA_VERSIONS = ("method_trial_recorded_v3", "method_trial_recorded_v4")
SUFFICIENCY_POLICY_ID = "gap_analysis_sufficiency_v1"
_MIN_INDEPENDENT_VARIANTS = 2          # a conflict needs comparative depth, not a single point


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
    m_ci = meas.get("confidence_interval")
    d_ci = dec.get("confidence_interval")
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
            uncertainty=meas.get("uncertainty"),
            confidence_interval=tuple(m_ci) if m_ci else None),
        decision=Decision(
            decision_rule_id=dec.get("decision_rule_id", ""),
            decision_rule_hash=dec.get("decision_rule_hash", ""),
            verdict=dec.get("verdict", "not_evaluated"), effect_size=dec.get("effect_size"),
            confidence_interval=tuple(d_ci) if d_ci else None,
            minimum_effect=dec.get("minimum_effect")),
        confounders=tuple(p.get("confounders", ()) or ()),
        schema_version=p.get("schema_version", SCHEMA_VERSION))


def _project_event(env: dict) -> tuple[dict, MethodTrialRecorded | None]:
    """One transparent per-event projection + the record IFF it is verified scope-bound evidence."""
    p = env.get("payload") or {}
    base = {
        "object_id": env.get("object_id"), "trial_id": p.get("trial_id", "unknown"),
        "schema_version": env.get("schema_version"),
        "record_status": "registered",                  # Layer 9 confirms the event exists
        "record_authority": env.get("record_authority"),
        "epistemic_authority": env.get("epistemic_authority"),
        "target": f"{p.get('target_type', 'unknown')}:{p.get('target_id', 'unknown')}",
        "scope_id": p.get("scope_id", "unknown"),
        "reported_result": p.get("epistemic_result", "unknown"),
    }
    # (a) the projector cannot interpret this schema -> visible as a PROJECTOR limitation, not a
    #     scientific judgement; never silently dropped.
    if p.get("schema_version") not in PROJECTOR_SUPPORTED_SCHEMA_VERSIONS:
        base.update(projection_status="unsupported_schema", event_usability="unusable",
                    decision_status="not_evaluated", epistemic_weight="none",
                    note="schema version not understood by this projector")
        return base, None

    # (b) a malformed payload (e.g. method_version='abc', a non-numeric effect, a bad CI) must NEVER
    #     crash the projector. It stays VISIBLE as invalid_payload - one bad event cannot stop the
    #     projection of the others (project_trial_events iterates per event).
    try:
        rec = _record_from_payload(p)
        usable = validate(rec) == []                    # structurally well-formed?
        if not usable:
            base.update(projection_status="projected", event_usability="unusable",
                        decision_status="not_applicable", epistemic_weight="none",
                        note="event is structurally invalid; not evaluable")
            return base, None
        # the VERDICT is computed on the RAW canonical payload via the version-pinned capsule,
        # not the reconstructed live record - so no current default/cast touches the verdict.
        dv = evaluate_payload(p)
    except Exception as exc:  # noqa: BLE001 - defensive: any cast/parse error -> invalid, not crash
        base.update(projection_status="invalid_payload", event_usability="unusable",
                    decision_status="not_evaluated", epistemic_weight="none",
                    note=f"payload could not be projected ({type(exc).__name__})")
        return base, None

    verified = (dv["status"] == "verified" and rec.execution_status == "completed"
                and rec.protocol_status == "valid")
    base.update(
        projection_status="projected", event_usability="usable",
        decision_status=dv["status"],
        # verified != authoritative: a reproducible verdict is a measured CANDIDATE, no more.
        epistemic_weight="measured_candidate" if verified else "none",
        note=dv.get("reason", ""))
    return base, (rec if verified else None)


def _independent_variant_count(outcomes) -> int:
    """How many sufficiently-INDEPENDENT method variants these outcomes represent (per the versioned
    policy). 0/1 means no comparative depth."""
    if len(outcomes) < _MIN_INDEPENDENT_VARIANTS:
        return len({o.method_variant for o in outcomes})
    ok, _ = INDEPENDENCE_POLICY_V1.satisfied(_profile(list(outcomes)))
    return len({o.method_variant for o in outcomes}) if ok else 1


def _dataset_sufficiency(core, evidence, events) -> dict:
    """Is the WHOLE history enough for a gap analysis? Coverage and comparative depth are judged per
    ``(conflict, scope)`` - NEVER across scopes of the same conflict, and NEVER by event count. A
    conflict is analysis-ready only if at least ONE concrete stable scope has >= MIN independent,
    rule-verified variants."""
    open_ids = {c.id for c in core.open_conflicts()} if hasattr(core, "open_conflicts") else set()
    outcomes = aggregate(evidence)
    by_pair: dict[tuple, list] = {}                 # (target_id, scope_id) -> [outcome...]
    by_conflict: set = set()
    for o in outcomes:
        by_pair.setdefault((o.target_id, o.scope_id), []).append(o)
        by_conflict.add(o.target_id)

    covered = sorted(by_conflict & open_ids)
    uncovered = sorted(open_ids - by_conflict)
    # analysis-ready PAIRS: an open conflict + a single stable scope with enough independent depth.
    ready_pairs = sorted(
        (cid, sid) for (cid, sid), outs in by_pair.items()
        if cid in open_ids and _independent_variant_count(outs) >= _MIN_INDEPENDENT_VARIANTS)
    ready_conflicts = sorted({cid for cid, _ in ready_pairs})
    max_independent = max((_independent_variant_count(v) for v in by_pair.values()), default=0)

    affinity = attribute_to_affinity(outcomes)
    affinity_known = any(a.strength != "none" for a in affinity)
    comparison_possible = bool(ready_pairs)
    ratio = (len(covered) / len(open_ids)) if open_ids else 0.0
    coverage = ("none" if not open_ids else
                "high" if ratio >= 0.67 else "medium" if ratio >= 0.34 else "low")

    reasons: list[str] = []
    if not open_ids:
        reasons.append("no open conflicts to analyse")
    if not covered:
        reasons.append("no open conflict has any verified scope-bound trial history")
    if not ready_pairs:
        reasons.append(f"no (conflict, scope) has >= {_MIN_INDEPENDENT_VARIANTS} independent "
                       "verified variants within a single stable scope (no comparative depth)")
    if uncovered:
        reasons.append(f"{len(uncovered)} open conflict(s) have no trial history")
    if not affinity_known:
        reasons.append("affinity-level attribution not yet admissible (independence "
                       "not established)")

    sufficient = bool(ready_pairs)
    interpretation = {
        "means": ("operational minimum only: for >= 1 open conflict there is enough comparable, "
                  "rule-verified, scope-bound trial history to ATTEMPT a state-dependent gap "
                  "analysis") if sufficient else "the dataset does not yet meet the minimum "
                 "threshold",
        "does_not_mean": [
            "conflict resolved",
            "affinity validated",
            "comprehensive solution-space coverage",
            "DESi added value demonstrated",
            "epistemic authority",
        ],
    }
    return {
        "policy_id": SUFFICIENCY_POLICY_ID,
        "registered_events": len(events),
        "structurally_usable_events": sum(1 for e in events if e["event_usability"] == "usable"),
        "rule_verified_events": len(evidence),
        "covered_open_conflicts": covered,
        "open_conflicts_without_trial_history": uncovered,
        "analysis_ready_conflicts": ready_conflicts,
        "analysis_ready_conflict_scopes": [{"target_id": c, "scope_id": s} for c, s in ready_pairs],
        "scope_coverage": coverage,
        "independent_method_variants": max_independent,
        "comparison_possible": comparison_possible,
        "affinity_attribution_known": affinity_known,
        "unverifiable_events": sum(1 for e in events if e["decision_status"] == "unverifiable"),
        "inconsistent_events": sum(1 for e in events if e["decision_status"] == "inconsistent"),
        "unsupported_schema_events":
            sum(1 for e in events if e["projection_status"] == "unsupported_schema"),
        "verdict": "SUFFICIENT_FOR_GAP_ANALYSIS" if sufficient else "insufficient",
        "interpretation": interpretation,
        "reasons": reasons,
    }


def desi_method_trials(core) -> tuple:
    """The rule-verified, scope-bound trial outcomes as DESi ``MethodTrial`` OBJECTS (what the
    EpistemicGapSnapshot.method_trials field needs - the dict form in ``project_trial_events`` is
    JSON-only). Empty tuple if DESi is unavailable or no verified trial event exists."""
    if not available():
        return ()
    from .trial_event_schema import to_desi_method_trials, verify_payloads
    stored = [p for p in ((env.get("payload") or {}) for env in core.method_trial_events())
              if p.get("schema_version") in PROJECTOR_SUPPORTED_SCHEMA_VERSIONS]
    return to_desi_method_trials(aggregate(verify_payloads(stored)))


def project_trial_events(core) -> dict:
    """Project the registered trial events into a transparent structure. Every registered event is
    visible with its three-axis status; only VERIFIED scope-bound events feed aggregation; dataset
    sufficiency is judged against real open-conflict/scope coverage, not event count."""
    envelopes = core.method_trial_events()
    events: list[dict] = []
    stored: list[dict] = []
    for env in envelopes:
        proj, _ = _project_event(env)
        events.append(proj)
        p = env.get("payload") or {}
        if p.get("schema_version") in PROJECTOR_SUPPORTED_SCHEMA_VERSIONS:
            stored.append(p)                      # the RAW stored journal object (env + payload)

    # the ONLY evidence path: verify_payloads verifies the STORED (envelope, payload) pair via the
    # version-pinned capsule and admits only verified ones - NO dataclass reconstruction is a
    # precondition for aggregation, and no aggregate(raw) bypass exists. Operational (non-epistemic)
    # observations travel a SEPARATE channel that never feeds attribution.
    from .trial_event_schema import operational_observations, verify_payloads
    evidence = verify_payloads(stored)
    outcomes = aggregate(evidence)
    ops = [
        {"trial_id": o.trial_id, "target_id": o.target_id, "scope_id": o.scope_id,
         "method_variant": o.method_variant, "execution_status": o.execution_status,
         "protocol_status": o.protocol_status, "failure_kind": o.failure_kind,
         "desi_result": o.desi_result}
        for o in operational_observations(stored)]
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
        desi_trials = [
            {"affinity": t.affinity, "target_conflict": t.target_conflict, "result": t.result,
             "scope": t.scope, "method_variant": t.method_variant, "count": t.count}
            for t in to_desi_method_trials(outcomes)]

    return {
        "events": events,
        "verified_scope_bound_outcomes": scope_bound,
        "affinity_attributions": affinity,
        "operational_observations": ops,                # technical/not_evaluated; NEVER attribution
        "desi_method_trials": desi_trials,              # None if DESi unavailable; never fabricated
        "dataset_sufficiency": _dataset_sufficiency(core, evidence, events),
    }
