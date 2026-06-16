"""METHOD_TRIAL_RECORDED - reference schema, validation, migration, aggregation (PROPOSAL v2).

This module is a *design artifact*, deliberately kept OUTSIDE the protected ``desi_layer9`` core.
It defines - without yet touching the core or regenerating the lock - the immutable, scope-bound
trial event the real Layer-9 history is missing today, plus the validation, legacy migration and
aggregation/attribution rules that go with it. Nothing here writes to the core; ``migrate_method``
duck-types a legacy ``Method`` via ``getattr`` so this file imports no core class and stays a pure,
testable contract.

v2 (review round) tightens four things so the new clean schema cannot import old false precision:

  1. Legacy ``success=true`` is NOT trusted as epistemic success. Verified against the writers:
     the DOMINANT historical writer (kevin ``trial_runner.trial_methods``) sets ``success`` from a
     SYNTHETIC structural-overlap heuristic on a foreign task and tags its own report
     "a simulation, not an effectiveness measurement"; only ``real_trial.run_real_trial``
     (predefined metric + threshold + clean negative control, run_id ``kevin-real``) has measured
     success semantics, and even there the measured result lives in a separate artifact, not in the
     ``Method`` counters. So by default legacy success migrates to ``not_evaluated`` +
     ``legacy_reported_success=true`` + ``attribution_strength="none"``. Only a run class PROVEN to
     carry measured-success semantics (passed via ``proven_success_runs``) may become a weak
     ``success``.

  2. Status is modelled on THREE orthogonal axes instead of one overloaded list:
     ``execution_status`` (did it run?) x ``protocol_status`` (was the protocol valid?) x
     ``epistemic_result`` (what did a valid, completed run show?), plus a ``failure_kind`` cause.
     A technical failure is now ``execution_status="failed"`` + ``failure_kind="technical"`` - it
     never collides with a result.

  3. Affinity attribution is NOT a flat "two variants = limited" rule. A limited affinity statement
     needs SUFFICIENTLY INDEPENDENT variants (distinct models/implementations, no shared dominant
     confounder, valid protocols, consistent results). Two highly-correlated variants do not count.

  4. Every event carries an ``estimand`` (outcome metric, contrast, direction, minimum effect,
     decision-rule id). ``no_benefit`` must follow from that pre-registered decision rule (minimum
     effect not met) - never be inferred post-hoc from a small or negative number.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = "method_trial_recorded_v2"
EVENT_TYPE = "METHOD_TRIAL_RECORDED"

# -- the orthogonal axes ------------------------------------------------------------------------- #
EXECUTION_STATUSES = ("completed", "failed", "cancelled")
PROTOCOL_STATUSES = ("valid", "invalid", "unknown")
FAILURE_KINDS = ("none", "technical", "timeout", "parser", "model", "dependency", "infrastructure")
EPISTEMIC_RESULTS = ("success", "partial_success", "no_benefit", "harmful", "inconclusive",
                     "not_evaluated")

# A methodological result is meaningful only for these (the rest carry no signal).
_REAL_RESULTS = ("success", "partial_success", "no_benefit", "harmful")
_RESULTS_NEEDING_COMPLETION = _REAL_RESULTS + ("inconclusive",)

TARGET_TYPES = ("conflict", "open_question", "evidence_gap")
DIRECTIONS = ("higher_is_better", "lower_is_better")
# Attribution a SINGLE raw event may claim. "affinity" is forbidden on a raw event - it is earned
# only by aggregation across sufficiently independent variants (see ATTRIBUTION rules below).
EVENT_ATTRIBUTION_LEVELS = ("variant", "method")
ATTRIBUTION_STRENGTHS = ("none", "limited", "supported")

UNKNOWN = "unknown"


@dataclass(frozen=True)
class Estimand:
    """What the trial set out to measure, fixed BEFORE the run. ``no_benefit`` must come from
    applying ``decision_rule_id`` (``minimum_effect`` not met), not from a post-hoc small number."""

    outcome_metric: str = ""
    contrast: str = "intervention_minus_baseline"
    direction: str = "higher_is_better"        # one of DIRECTIONS
    minimum_effect: float = 0.0                 # the pre-registered threshold of relevance
    decision_rule_id: str = ""


@dataclass(frozen=True)
class Measurement:
    """The measured outcome of a completed trial. ``effect_size`` is ORIENTED so positive == better
    (per the estimand direction). ``None`` everywhere when nothing was evaluated."""

    metric_name: str | None = None
    baseline_value: float | None = None
    intervention_value: float | None = None
    effect_size: float | None = None          # oriented: > 0 better, < 0 worse
    uncertainty: float | None = None          # e.g. half-width of a CI on effect_size


@dataclass(frozen=True)
class MethodTrialRecorded:
    """ONE immutable, scope-bound trial of a method VARIANT against a concrete epistemic target.

    Bound PRIMARILY to ``(method_id, method_version, method_variant)`` x ``(target_id, scope_id)`` -
    never to an affinity. ``affinities`` only records which content-free thinking-moves the variant
    exercised, so attribution can later roll *up* to an affinity, slowly and with limits.
    """

    trial_id: str
    timestamp: str                            # ISO-8601 UTC
    ledger_tick: int

    # -- target ---------------------------------------------------------------------------------- #
    target_type: str
    target_id: str
    claim_ids: tuple[str, ...] = ()

    # -- scope (the bounded task context; demotion can never escape it) -------------------------- #
    scope_id: str = UNKNOWN
    scope_description: str = ""

    # -- intervention (the variant under test) --------------------------------------------------- #
    method_id: str = UNKNOWN
    method_version: int = 1
    method_variant: str = UNKNOWN
    implementation_id: str = UNKNOWN          # implementation lineage (for independence checks)
    affinities: tuple[str, ...] = ()

    # -- trial design ---------------------------------------------------------------------------- #
    task_set_id: str = UNKNOWN
    baseline_id: str = UNKNOWN
    evaluator_id: str = UNKNOWN
    estimand: Estimand = field(default_factory=Estimand)

    # -- model + sampling provenance ------------------------------------------------------------- #
    model: str = UNKNOWN
    sampling: dict = field(default_factory=dict)

    # -- the orthogonal axes --------------------------------------------------------------------- #
    execution_status: str = "completed"
    protocol_status: str = "valid"
    failure_kind: str = "none"
    epistemic_result: str = "not_evaluated"

    # -- measured outcome ------------------------------------------------------------------------ #
    measurement: Measurement = field(default_factory=Measurement)

    # -- artifacts / run identity ---------------------------------------------------------------- #
    run_id: str = UNKNOWN
    artifact_ids: tuple[str, ...] = ()

    # -- attribution + provenance ---------------------------------------------------------------- #
    attribution_level: str = "variant"
    attribution_strength: str = "none"        # a single event never establishes affinity strength
    confounders: tuple[str, ...] = ()
    # legacy: predates the measurement regime -> metric/sign/estimand rules relaxed, but flagged
    # so a weak legacy prior can NEVER be mistaken for a measured result.
    legacy: bool = False
    legacy_reported_success: bool = False     # what the OLD boolean said (provenance only)
    note: str = ""
    field_sources: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        m, e = self.measurement, self.estimand
        return {
            "schema_version": SCHEMA_VERSION, "event_type": EVENT_TYPE,
            "trial_id": self.trial_id, "timestamp": self.timestamp, "ledger_tick": self.ledger_tick,
            "target_type": self.target_type, "target_id": self.target_id,
            "claim_ids": list(self.claim_ids),
            "scope_id": self.scope_id, "scope_description": self.scope_description,
            "method_id": self.method_id, "method_version": self.method_version,
            "method_variant": self.method_variant, "implementation_id": self.implementation_id,
            "affinities": list(self.affinities),
            "task_set_id": self.task_set_id, "baseline_id": self.baseline_id,
            "evaluator_id": self.evaluator_id,
            "estimand": {"outcome_metric": e.outcome_metric, "contrast": e.contrast,
                         "direction": e.direction, "minimum_effect": e.minimum_effect,
                         "decision_rule_id": e.decision_rule_id},
            "model": self.model, "sampling": dict(self.sampling),
            "execution_status": self.execution_status, "protocol_status": self.protocol_status,
            "failure_kind": self.failure_kind, "epistemic_result": self.epistemic_result,
            "measurement": {"metric_name": m.metric_name, "baseline_value": m.baseline_value,
                            "intervention_value": m.intervention_value,
                            "effect_size": m.effect_size, "uncertainty": m.uncertainty},
            "run_id": self.run_id, "artifact_ids": list(self.artifact_ids),
            "attribution_level": self.attribution_level,
            "attribution_strength": self.attribution_strength,
            "confounders": list(self.confounders), "legacy": self.legacy,
            "legacy_reported_success": self.legacy_reported_success, "note": self.note,
            "field_sources": dict(self.field_sources),
        }


# ================================================================================================ #
# VALIDATION - forbidden combinations are enforced here, not by convention.
# ================================================================================================ #
def validate(ev: MethodTrialRecorded) -> list[str]:
    """Return a list of rule violations (empty == valid)."""
    errs: list[str] = []
    m, e = ev.measurement, ev.estimand

    # -- enum membership ------------------------------------------------------------------------- #
    if ev.execution_status not in EXECUTION_STATUSES:
        errs.append(f"execution_status '{ev.execution_status}' not in {EXECUTION_STATUSES}")
    if ev.protocol_status not in PROTOCOL_STATUSES:
        errs.append(f"protocol_status '{ev.protocol_status}' not in {PROTOCOL_STATUSES}")
    if ev.failure_kind not in FAILURE_KINDS:
        errs.append(f"failure_kind '{ev.failure_kind}' not in {FAILURE_KINDS}")
    if ev.epistemic_result not in EPISTEMIC_RESULTS:
        errs.append(f"epistemic_result '{ev.epistemic_result}' not in {EPISTEMIC_RESULTS}")
    if ev.target_type not in TARGET_TYPES:
        errs.append(f"target_type '{ev.target_type}' not in {TARGET_TYPES}")
    if ev.estimand.direction not in DIRECTIONS:
        errs.append(f"estimand.direction '{ev.estimand.direction}' not in {DIRECTIONS}")

    real = ev.epistemic_result in _REAL_RESULTS

    # -- axis coherence (forbidden combinations) ------------------------------------------------- #
    # (R1) a run that did not COMPLETE carries no result.
    if ev.execution_status != "completed" and ev.epistemic_result != "not_evaluated":
        errs.append(f"forbidden: execution_status '{ev.execution_status}' requires "
                    "epistemic_result 'not_evaluated' (a non-completed run has no scientific "
                    "result)")
    # (R1b) failed <=> a failure_kind; a completed/cancelled run has none.
    if ev.execution_status == "failed" and ev.failure_kind == "none":
        errs.append("forbidden: execution_status 'failed' requires a failure_kind != 'none'")
    if ev.execution_status != "failed" and ev.failure_kind != "none":
        errs.append(f"forbidden: failure_kind '{ev.failure_kind}' requires execution_status "
                    "'failed'")
    # (R2) an invalid protocol can carry no reliable result; unknown protocol can carry no REAL one.
    if ev.protocol_status == "invalid" and ev.epistemic_result != "not_evaluated":
        errs.append("forbidden: protocol_status 'invalid' requires epistemic_result "
                    "'not_evaluated'")
    # (legacy is exempt: it predates the protocol regime, carries protocol 'unknown' honestly, and
    #  stays clearly weak via legacy=True / no measurement - so it cannot be mistaken for a measured
    #  result; but it is NEVER exempt from R1 above or the truly-invalid rule.)
    if not ev.legacy and ev.protocol_status == "unknown" and real:
        errs.append(f"forbidden: a real result '{ev.epistemic_result}' requires protocol_status "
                    "'valid' (got 'unknown')")
    # (R3) a real result needs a clean, valid, completed run.
    if not ev.legacy and real and (ev.execution_status != "completed"
                                   or ev.protocol_status != "valid"):
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires execution 'completed' + "
                    "protocol 'valid'")

    # -- measurement + estimand (legacy exempt) -------------------------------------------------- #
    has_metric = m.metric_name is not None and m.baseline_value is not None \
        and m.intervention_value is not None
    if not ev.legacy and real and not has_metric:
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires a measurement "
                    "(metric_name + baseline_value + intervention_value)")
    if not ev.legacy and real and (not e.decision_rule_id or e.minimum_effect <= 0):
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires an estimand with a "
                    "decision_rule_id and minimum_effect > 0 (threshold must be pre-registered)")

    # (R4) the result must be the OUTPUT of the decision rule, not a post-hoc label.
    if not ev.legacy and m.effect_size is not None and e.minimum_effect > 0:
        eff, mn, unc = m.effect_size, e.minimum_effect, (m.uncertainty or 0.0)
        if ev.epistemic_result == "success" and not (eff >= mn and eff > unc):
            errs.append("forbidden: 'success' requires effect_size >= minimum_effect AND beyond "
                        "uncertainty (else inconclusive/no_benefit)")
        if ev.epistemic_result == "harmful" and not (eff <= -mn):
            errs.append("forbidden: 'harmful' requires effect_size <= -minimum_effect")
        if ev.epistemic_result == "no_benefit" and not (abs(eff) < mn and abs(eff) > unc):
            errs.append("forbidden: 'no_benefit' must be the decision rule's verdict - effect "
                        "RESOLVED (|effect| > uncertainty) but BELOW minimum_effect; a clear "
                        "improvement is 'success', pure noise is 'inconclusive'")
        if ev.epistemic_result == "inconclusive" and abs(eff) > unc and unc > 0:
            errs.append("forbidden: 'inconclusive' requires |effect_size| <= uncertainty")

    # -- attribution --------------------------------------------------------------------------- #
    if ev.attribution_level not in EVENT_ATTRIBUTION_LEVELS:
        errs.append(f"attribution_level '{ev.attribution_level}' not allowed on a raw event "
                    f"{EVENT_ATTRIBUTION_LEVELS} (affinity-level is earned by aggregation only)")
    if ev.attribution_strength != "none":
        errs.append("forbidden: a single raw event never carries attribution_strength != 'none' "
                    "(affinity strength is earned only by independent aggregation)")

    # -- structural minimums --------------------------------------------------------------------- #
    if not ev.trial_id:
        errs.append("trial_id is required")
    if ev.target_type == "conflict" and not ev.claim_ids:
        errs.append("a conflict trial must carry claim_ids (the scope it spans)")
    if not ev.scope_id:
        errs.append("scope_id is required (use 'unknown' explicitly, never empty)")
    if not ev.method_variant:
        errs.append("method_variant is required (use 'unknown' explicitly, never empty)")
    # (R5) a completed, valid run that evaluated nothing must say why.
    if ev.execution_status == "completed" and ev.protocol_status == "valid" \
            and ev.epistemic_result == "not_evaluated" and not ev.note:
        errs.append("completed + valid + not_evaluated requires a note explaining why nothing was "
                    "evaluated")
    return errs


def validate_or_raise(ev: MethodTrialRecorded) -> MethodTrialRecorded:
    errs = validate(ev)
    if errs:
        raise ValueError("invalid METHOD_TRIAL_RECORDED: " + "; ".join(errs))
    return ev


# ================================================================================================ #
# LEGACY MIGRATION - conservative by construction, justified against the OLD writers/handler.
#
#   Verified semantics of the legacy boolean (core ``_h_method_trial_record`` stores only
#   ``success`` + ``run_id`` into GLOBAL counters):
#     * DOMINANT writer kevin ``trial_runner.trial_methods``: ``success = improvement >= MIN`` with
#       ``improvement = fit * HELP`` on a deterministically picked FOREIGN task - a synthetic
#       structural-overlap heuristic the writer itself tags "a simulation, not an effectiveness
#       measurement". => NOT measured epistemic benefit.
#     * ``real_trial.run_real_trial`` (run_id ``kevin-real``): predefined metric + threshold + clean
#       negative control. => measured success semantics, but the full result lives in a SEPARATE
#       artifact, not in the Method counters.
#
#   Therefore: old success=true -> ``not_evaluated`` + ``legacy_reported_success=true`` by DEFAULT.
#   Only run classes PROVEN to carry measured success (via ``proven_success_runs``) become a weak
#   ``success``. Old success=false -> ``not_evaluated`` (NEVER no_benefit): technical vs
#   methodological is unknown, so it carries no demoting signal.
# ================================================================================================ #
def migrate_method(method, *, base_tick: int = 0, proven_success_runs=None) \
        -> list[MethodTrialRecorded]:
    """Duck-type a legacy ``Method`` into immutable events without inventing signal.

    ``proven_success_runs`` is an optional predicate ``run_id -> bool`` (or a set/tuple of run_id
    prefixes) selecting run classes WHOSE SUCCESS SEMANTICS ARE PROVEN to be measured. By default
    NOTHING is proven, so every legacy success becomes ``not_evaluated`` - old false precision is
    not imported."""
    if proven_success_runs is None:
        def _proven(_run_id: str) -> bool:
            return False
    elif callable(proven_success_runs):
        _proven = proven_success_runs
    else:
        prefixes = tuple(proven_success_runs)
        def _proven(run_id: str) -> bool:
            return any(run_id.startswith(p) for p in prefixes)

    mid = getattr(method, "id", UNKNOWN)
    version = int(getattr(method, "version", 1) or 1)
    affinities = tuple(getattr(method, "applicable_to", ()) or ())
    supporting = tuple(getattr(method, "supporting_runs", ()) or ())
    failed = tuple(getattr(method, "failed_runs", ()) or ())
    success_count = int(getattr(method, "success_count", 0) or 0)
    failure_count = int(getattr(method, "failure_count", 0) or 0)

    events: list[MethodTrialRecorded] = []
    tick = base_tick

    def _emit(run_id: str, result: str, reported_success: bool, note: str, conf: str) -> None:
        nonlocal tick
        tick += 1
        events.append(MethodTrialRecorded(
            trial_id=f"legacy:{mid}:{result}:{run_id}:{tick}", timestamp="legacy",
            ledger_tick=tick, target_type="conflict", target_id=UNKNOWN, claim_ids=(UNKNOWN,),
            scope_id=UNKNOWN, method_id=mid, method_version=version, method_variant=UNKNOWN,
            affinities=affinities, execution_status="completed", protocol_status="unknown",
            epistemic_result=result, run_id=run_id, attribution_level="method",
            attribution_strength="none", legacy=True, legacy_reported_success=reported_success,
            note=note,
            field_sources={"scope_id": {"source": "n/a", "confidence": "unknown"},
                           "method_variant": {"source": "n/a", "confidence": "unknown"},
                           "epistemic_result": {"source": "legacy Method counters",
                                                "confidence": conf}}))

    def _success_or_not(run_id: str) -> None:
        if _proven(run_id):
            _emit(run_id, "success", True,
                  "legacy success from a PROVEN measured run class - weak prior only "
                  "(no scope/variant/effect recorded)", "derived")
        else:
            _emit(run_id, "not_evaluated", True,
                  "legacy success from an UNPROVEN run class (dominant writer was a simulation, "
                  "not an effectiveness measurement) - reported-only, no demoting/promoting signal",
                  "unknown")

    named_succ = [r for r in supporting if r and r != "unknown"]
    for r in named_succ:
        _success_or_not(r)
    for i in range(max(0, success_count - len(named_succ))):
        _success_or_not(f"legacy-agg-{i}")

    named_fail = [r for r in failed if r and r != "unknown"]
    for r in named_fail:
        _emit(r, "not_evaluated", False,
              "legacy failure: technical vs methodological unknown - carries no demoting signal",
              "unknown")
    for i in range(max(0, failure_count - len(named_fail))):
        _emit(f"legacy-agg-fail-{i}", "not_evaluated", False,
              "legacy aggregate failure without a run-id - no demoting signal", "unknown")

    return events


# ================================================================================================ #
# AGGREGATION + ATTRIBUTION
# ================================================================================================ #
MIN_VARIANTS_FOR_AFFINITY = 2


@dataclass(frozen=True)
class VariantScopeOutcome:
    """The aggregated outcome of one method VARIANT in one scope on one target."""

    target_id: str
    scope_id: str
    method_id: str
    method_variant: str
    affinities: tuple[str, ...]
    outcome: str                 # success|no_benefit|harmful|inconclusive|technical_only|
    #                              not_evaluated
    n_completed_valid: int
    n_unusable: int              # failed / cancelled / invalid-protocol runs (no signal)
    protocol_valid: bool
    models: tuple[str, ...]
    implementations: tuple[str, ...]
    confounders: tuple[str, ...]
    evidence: tuple[str, ...]


def _cell_outcome(evs: list[MethodTrialRecorded]) -> tuple[str, int, int]:
    usable = [e for e in evs if e.execution_status == "completed" and e.protocol_status == "valid"]
    unusable = [e for e in evs if e not in usable]
    results = {e.epistemic_result for e in usable if e.epistemic_result != "not_evaluated"}
    if "harmful" in results:                       # safety dominates
        outcome = "harmful"
    elif results & {"success", "partial_success"}:
        outcome = "success"
    elif "no_benefit" in results:
        outcome = "no_benefit"
    elif "inconclusive" in results:
        outcome = "inconclusive"
    elif unusable and not usable:                  # only unusable runs -> no methodological signal
        outcome = "technical_only"
    else:
        outcome = "not_evaluated"
    return outcome, len(usable), len(unusable)


def aggregate(events: list[MethodTrialRecorded]) -> list[VariantScopeOutcome]:
    """Roll valid events up to one outcome per (target, scope, variant). Invalid events are dropped
    (a caller should ``validate`` first); never invents an outcome it did not see."""
    cells: dict[tuple, list[MethodTrialRecorded]] = {}
    for e in events:
        if validate(e):
            continue
        cells.setdefault((e.target_id, e.scope_id, e.method_id, e.method_variant), []).append(e)
    out: list[VariantScopeOutcome] = []
    for (target, scope, mid, variant), evs in sorted(cells.items()):
        outcome, n_v, n_u = _cell_outcome(evs)
        usable = [e for e in evs if e.execution_status == "completed"
                  and e.protocol_status == "valid"]
        affs = tuple(sorted({a for e in evs for a in e.affinities}))
        out.append(VariantScopeOutcome(
            target_id=target, scope_id=scope, method_id=mid, method_variant=variant,
            affinities=affs, outcome=outcome, n_completed_valid=n_v, n_unusable=n_u,
            protocol_valid=bool(usable) and n_u == 0,
            models=tuple(sorted({e.model for e in usable})),
            implementations=tuple(sorted({e.implementation_id for e in usable})),
            confounders=tuple(sorted({c for e in usable for c in e.confounders})),
            evidence=tuple(e.trial_id for e in evs)))
    return out


# Outcome -> DESi MethodTrial.result. A purely unusable cell maps to "technical_failure" (no
# methodological signal -> DESi keeps the move open); not_evaluated -> "unknown".
_OUTCOME_TO_DESI = {
    "success": "success", "no_benefit": "no_benefit", "harmful": "harmful",
    "inconclusive": "inconclusive", "technical_only": "technical_failure",
    "not_evaluated": "unknown",
}


def to_desi_method_trials(outcomes: list[VariantScopeOutcome]):
    """Map aggregated, scope-bound outcomes to DESi ``MethodTrial`` DTOs (one per affinity x cell).
    The consumable end of the updated projector; imports DESi lazily, like the live projector."""
    from desi.solution_space_gap import MethodTrial
    trials = []
    for o in outcomes:
        result = _OUTCOME_TO_DESI.get(o.outcome, "unknown")
        count = max(1, o.n_unusable if o.outcome == "technical_only" else o.n_completed_valid)
        for aff in o.affinities:
            trials.append(MethodTrial(
                affinity=aff, target_conflict=o.target_id, result=result, scope=o.scope_id,
                method_variant=o.method_variant, count=count))
    return tuple(trials)


@dataclass(frozen=True)
class AffinityScopeAttribution:
    """A LIMITED, multi-variant attribution to an affinity in a scope - earned only when the failing
    variants are SUFFICIENTLY INDEPENDENT (not just numerous)."""

    target_id: str
    scope_id: str
    affinity: str
    n_variants_negative: int
    independent: bool
    strength: str                # "none" | "limited" | "supported"
    reason: str
    evidence: tuple[str, ...]


def _independent(neg: list[VariantScopeOutcome]) -> tuple[bool, str]:
    """Are these failing variant-cells independent enough to say something about the AFFINITY?
    Requires: >= MIN distinct variants, all protocol-valid, distinct models OR implementations (not
    all sharing one), and NO confounder common to all (no dominant shared störquelle)."""
    if len({c.method_variant for c in neg}) < MIN_VARIANTS_FOR_AFFINITY:
        return False, "fewer than 2 distinct variants"
    if not all(c.protocol_valid for c in neg):
        return False, "a contributing variant lacked a valid protocol"
    distinct_models = len({m for c in neg for m in c.models})
    distinct_impls = len({i for c in neg for i in c.implementations})
    if distinct_models < 2 and distinct_impls < 2:
        return False, "variants share one model and one implementation (highly correlated)"
    conf_sets = [set(c.confounders) for c in neg]
    common = set.intersection(*conf_sets) if conf_sets else set()
    if common:
        return False, f"a dominant confounder is shared by all variants ({sorted(common)})"
    return True, "distinct variants, independent models/implementations, no shared confounder"


def attribute_to_affinity(outcomes: list[VariantScopeOutcome]) -> list[AffinityScopeAttribution]:
    """Roll variant-scope outcomes up to affinity-scope attributions. Demotion of an AFFINITY is
    earned only by SUFFICIENTLY INDEPENDENT failing variants - never by a flat variant count, and
    never if a success for the same affinity-scope makes the picture inconsistent."""
    by_key: dict[tuple[str, str, str], list[VariantScopeOutcome]] = {}
    for o in outcomes:
        for aff in o.affinities:
            by_key.setdefault((o.target_id, o.scope_id, aff), []).append(o)
    res: list[AffinityScopeAttribution] = []
    for (target, scope, aff), cells in sorted(by_key.items()):
        neg = [c for c in cells if c.outcome in ("no_benefit", "harmful")]
        has_success = any(c.outcome == "success" for c in cells)
        if has_success:
            indep, why, strength = False, "inconsistent: a variant succeeded for this affinity", \
                "none"
        else:
            indep, why = _independent(neg)
            if not indep:
                strength = "none"
            elif len({c.method_variant for c in neg}) >= max(MIN_VARIANTS_FOR_AFFINITY + 1, 3):
                strength = "supported"
            else:
                strength = "limited"
        res.append(AffinityScopeAttribution(
            target_id=target, scope_id=scope, affinity=aff,
            n_variants_negative=len({c.method_variant for c in neg}), independent=indep,
            strength=strength, reason=why,
            evidence=tuple(t for c in cells for t in c.evidence)))
    return res
