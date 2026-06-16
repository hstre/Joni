"""METHOD_TRIAL_RECORDED - reference schema, validation, migration, aggregation (PROPOSAL).

This module is a *design artifact*, deliberately kept OUTSIDE the protected ``desi_layer9`` core.
It defines - without yet touching the core or regenerating the lock - the immutable, scope-bound
trial event the real Layer-9 history is missing today, plus the validation, legacy migration and
aggregation/attribution rules that go with it. Nothing here writes to the core; ``migrate_method``
duck-types a legacy ``Method`` via ``getattr`` so this file imports no core class and stays a pure,
testable contract.

Why it exists: the read-only projector measured that Joni's current Layer-9 records only GLOBAL
``Method.success_count``/``failure_count`` + ``run_id`` - it logs that a trial happened, not what it
*meant*, on *which* conflict, in *which* scope, with *which* method variant. Without that, DESi's
gap analysis degrades to a static conflict-kind table. This event fixes the data capture at the
source so a local negative result can never become a global demotion, and a technical failure can
never masquerade as a scientific negative.

Two orthogonal axes are kept strictly separate (the central design rule):
  * ``execution_status``  - did the trial *run* cleanly?      (operational)
  * ``epistemic_result``  - what did a clean run *show*?       (methodological)
A non-completed run yields NO scientific result (``epistemic_result == "not_evaluated"``). A
technical failure therefore demotes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = "method_trial_recorded_v1"
EVENT_TYPE = "METHOD_TRIAL_RECORDED"

# -- the two orthogonal axes --------------------------------------------------------------------- #
# Did the trial RUN cleanly? Operational only - says nothing about whether the move fits.
EXECUTION_STATUSES = ("completed", "technical_failure", "cancelled", "invalid_protocol")
# What did a CLEAN run SHOW? Methodological - only meaningful when execution_status == "completed".
EPISTEMIC_RESULTS = ("success", "partial_success", "no_benefit", "harmful", "inconclusive",
                     "not_evaluated")

# A real run produced a scientific result only for these (the rest carry no methodological signal).
_RESULTS_NEEDING_COMPLETION = (
    "success", "partial_success", "no_benefit", "harmful", "inconclusive")
# These require a recorded measurement (metric + baseline + intervention).
_RESULTS_NEEDING_METRIC = ("success", "partial_success", "no_benefit", "harmful")

TARGET_TYPES = ("conflict", "open_question", "evidence_gap")
# Attribution a SINGLE raw event may claim. "affinity" is forbidden on a raw event - it is earned
# only by aggregation across several variants (see ATTRIBUTION rules below).
EVENT_ATTRIBUTION_LEVELS = ("variant", "method")

UNKNOWN = "unknown"


@dataclass(frozen=True)
class Measurement:
    """The measured outcome of a completed trial. ``None`` everywhere when nothing was evaluated."""

    metric_name: str | None = None
    baseline_value: float | None = None
    intervention_value: float | None = None
    effect_size: float | None = None          # signed: > 0 improvement, < 0 worsening (metric-dir)
    uncertainty: float | None = None          # e.g. half-width of a CI on effect_size
    higher_is_better: bool = True             # so "improvement" has an unambiguous sign


@dataclass(frozen=True)
class MethodTrialRecorded:
    """ONE immutable, scope-bound trial of a method VARIANT against a concrete epistemic target.

    The trial is bound PRIMARILY to ``(method_id, method_version, method_variant)`` x
    ``(target_id, scope_id)`` - never to an affinity. ``affinities`` only records which content-free
    thinking-moves the variant exercised, so attribution can later roll *up* to an affinity, slowly
    and with limits - never the other way round.
    """

    trial_id: str
    timestamp: str                            # ISO-8601 UTC
    ledger_tick: int

    # -- target (what epistemic gap was this aimed at) ------------------------------------------- #
    target_type: str                          # one of TARGET_TYPES
    target_id: str
    claim_ids: tuple[str, ...] = ()

    # -- scope (the bounded task context; demotion can never escape it) -------------------------- #
    scope_id: str = UNKNOWN
    scope_description: str = ""

    # -- intervention (the variant under test) --------------------------------------------------- #
    method_id: str = UNKNOWN
    method_version: int = 1
    method_variant: str = UNKNOWN
    affinities: tuple[str, ...] = ()          # thinking-moves the variant exercised

    # -- trial design (frozen task set, baseline, evaluator) ------------------------------------- #
    task_set_id: str = UNKNOWN
    baseline_id: str = UNKNOWN
    evaluator_id: str = UNKNOWN

    # -- model + sampling provenance (reproducibility of the run) -------------------------------- #
    model: str = UNKNOWN
    sampling: dict = field(default_factory=dict)   # e.g. {"temperature":0, "top_p":1, "seed":7}

    # -- the two orthogonal axes ----------------------------------------------------------------- #
    execution_status: str = "completed"
    epistemic_result: str = "not_evaluated"

    # -- measured outcome ------------------------------------------------------------------------ #
    measurement: Measurement = field(default_factory=Measurement)

    # -- artifacts / run identity ---------------------------------------------------------------- #
    run_id: str = UNKNOWN
    artifact_ids: tuple[str, ...] = ()

    # -- attribution + provenance ---------------------------------------------------------------- #
    attribution_level: str = "variant"
    confounders: tuple[str, ...] = ()
    # True only for events produced by legacy migration: they predate the measurement regime, so the
    # metric/sign rules are relaxed - but they stay flagged so a weak legacy prior can NEVER be
    # mistaken for a measured result.
    legacy: bool = False
    note: str = ""
    # field path -> {"source": str, "confidence": "direct"|"derived"|"unknown"}
    field_sources: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        m = self.measurement
        return {
            "schema_version": SCHEMA_VERSION, "event_type": EVENT_TYPE,
            "trial_id": self.trial_id, "timestamp": self.timestamp, "ledger_tick": self.ledger_tick,
            "target_type": self.target_type, "target_id": self.target_id,
            "claim_ids": list(self.claim_ids),
            "scope_id": self.scope_id, "scope_description": self.scope_description,
            "method_id": self.method_id, "method_version": self.method_version,
            "method_variant": self.method_variant, "affinities": list(self.affinities),
            "task_set_id": self.task_set_id, "baseline_id": self.baseline_id,
            "evaluator_id": self.evaluator_id, "model": self.model, "sampling": dict(self.sampling),
            "execution_status": self.execution_status, "epistemic_result": self.epistemic_result,
            "measurement": {
                "metric_name": m.metric_name, "baseline_value": m.baseline_value,
                "intervention_value": m.intervention_value, "effect_size": m.effect_size,
                "uncertainty": m.uncertainty, "higher_is_better": m.higher_is_better},
            "run_id": self.run_id, "artifact_ids": list(self.artifact_ids),
            "attribution_level": self.attribution_level, "confounders": list(self.confounders),
            "legacy": self.legacy, "note": self.note, "field_sources": dict(self.field_sources),
        }


# ================================================================================================ #
# VALIDATION - forbidden combinations are enforced here, not by convention.
# ================================================================================================ #
def validate(ev: MethodTrialRecorded) -> list[str]:
    """Return a list of rule violations (empty == valid). The forbidden combinations encode the
    central rule: a non-completed run can never carry a scientific result."""
    errs: list[str] = []

    if ev.execution_status not in EXECUTION_STATUSES:
        errs.append(f"execution_status '{ev.execution_status}' not in {EXECUTION_STATUSES}")
    if ev.epistemic_result not in EPISTEMIC_RESULTS:
        errs.append(f"epistemic_result '{ev.epistemic_result}' not in {EPISTEMIC_RESULTS}")
    if ev.target_type not in TARGET_TYPES:
        errs.append(f"target_type '{ev.target_type}' not in {TARGET_TYPES}")

    # (R1) FORBIDDEN: a run that did not complete cleanly producing any methodological result.
    #      technical_failure / cancelled / invalid_protocol => epistemic_result MUST be
    #      not_evaluated.
    if ev.execution_status != "completed" and ev.epistemic_result != "not_evaluated":
        errs.append("forbidden: execution_status != 'completed' requires epistemic_result == "
                    f"'not_evaluated' (got '{ev.epistemic_result}') - a technical failure is not a "
                    "scientific result")

    # (R2) A real methodological result requires a clean run...
    if ev.epistemic_result in _RESULTS_NEEDING_COMPLETION and ev.execution_status != "completed":
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires execution_status "
                    "'completed'")

    # (R3) ...and a real *quantified* result requires a recorded measurement. Legacy events are
    #      exempt (no measurement existed) but stay flagged via ``legacy`` so they read as weak.
    m = ev.measurement
    has_metric = m.metric_name is not None and m.baseline_value is not None \
        and m.intervention_value is not None
    if not ev.legacy and ev.epistemic_result in _RESULTS_NEEDING_METRIC and not has_metric:
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires a measurement "
                    "(metric_name + baseline_value + intervention_value)")

    # (R4) Sign coherence: success must improve beyond uncertainty; harmful must worsen.
    if not ev.legacy and ev.epistemic_result == "success" and m.effect_size is not None:
        if m.effect_size <= 0:
            errs.append("forbidden: epistemic_result 'success' with non-positive effect_size")
        elif m.uncertainty is not None and m.effect_size <= m.uncertainty:
            errs.append("forbidden: 'success' effect_size within uncertainty - that is "
                        "'inconclusive', not success")
    if not ev.legacy and ev.epistemic_result == "harmful" and m.effect_size is not None \
            and m.effect_size >= 0:
        errs.append("forbidden: epistemic_result 'harmful' with non-negative effect_size")

    # (R5) Attribution: a SINGLE raw event may never claim affinity-level attribution.
    if ev.attribution_level not in EVENT_ATTRIBUTION_LEVELS:
        errs.append(f"attribution_level '{ev.attribution_level}' not allowed on a raw event "
                    f"{EVENT_ATTRIBUTION_LEVELS} (affinity-level is earned by aggregation only)")

    # (R6) Structural minimums - no global/unscoped trials masquerading as evidence.
    if not ev.trial_id:
        errs.append("trial_id is required")
    if ev.target_type == "conflict" and not ev.claim_ids:
        errs.append("a conflict trial must carry claim_ids (the scope it spans)")
    if not ev.scope_id:
        errs.append("scope_id is required (use 'unknown' explicitly, never empty)")
    if not ev.method_variant:
        errs.append("method_variant is required (use 'unknown' explicitly, never empty)")

    # (R7) not_evaluated on a COMPLETED run must say why (deferred / evaluator absent) - otherwise
    #      it is an empty record pretending to be a trial.
    if ev.execution_status == "completed" and ev.epistemic_result == "not_evaluated" \
            and not ev.note:
        errs.append("completed + not_evaluated requires a note explaining why nothing was "
                    "evaluated")

    return errs


def validate_or_raise(ev: MethodTrialRecorded) -> MethodTrialRecorded:
    errs = validate(ev)
    if errs:
        raise ValueError("invalid METHOD_TRIAL_RECORDED: " + "; ".join(errs))
    return ev


# ================================================================================================ #
# LEGACY MIGRATION - conservative by construction.
#   old success=true  -> success, but with LIMITED provenance (no scope/variant/metric known)
#   old success=false -> not_evaluated (NEVER no_benefit): we cannot tell a technical failure from a
#                        methodological one, so it carries no demoting signal.
# ================================================================================================ #
def migrate_method(method, *, base_tick: int = 0) -> list[MethodTrialRecorded]:
    """Duck-type a legacy ``Method`` (``success_count``/``failure_count``/``supporting_runs``/
    ``failed_runs``/``applicable_to``) into immutable trial events without inventing signal.

    Imports nothing from the core - reads via ``getattr`` so it works on the real object or a fake.
    """
    mid = getattr(method, "id", UNKNOWN)
    version = int(getattr(method, "version", 1) or 1)
    affinities = tuple(getattr(method, "applicable_to", ()) or ())
    supporting = tuple(getattr(method, "supporting_runs", ()) or ())
    failed = tuple(getattr(method, "failed_runs", ()) or ())
    success_count = int(getattr(method, "success_count", 0) or 0)
    failure_count = int(getattr(method, "failure_count", 0) or 0)

    src_success = {"source": "legacy Method.success_count", "confidence": "derived"}
    src_unknown = {"source": "legacy Method.failure_count (kind unknown)", "confidence": "unknown"}
    events: list[MethodTrialRecorded] = []
    tick = base_tick

    def _emit(run_id: str, result: str, sources: dict, note: str) -> None:
        nonlocal tick
        tick += 1
        events.append(MethodTrialRecorded(
            trial_id=f"legacy:{mid}:{result}:{run_id}:{tick}", timestamp="legacy",
            ledger_tick=tick, target_type="conflict", target_id=UNKNOWN, claim_ids=(UNKNOWN,),
            scope_id=UNKNOWN, method_id=mid, method_version=version, method_variant=UNKNOWN,
            affinities=affinities, execution_status="completed", epistemic_result=result,
            run_id=run_id, attribution_level="method", legacy=True, note=note,
            field_sources={"scope_id": {"source": "n/a", "confidence": "unknown"},
                           "method_variant": {"source": "n/a", "confidence": "unknown"},
                           "epistemic_result": sources}))

    # successes: directionally usable, but explicitly limited (no scope/variant/metric).
    named_succ = [r for r in supporting if r and r != "unknown"]
    for r in named_succ:
        _emit(r, "success", src_success,
              "legacy success: no scope/variant/metric recorded - usable only as a weak prior")
    for i in range(max(0, success_count - len(named_succ))):
        _emit(f"legacy-agg-{i}", "success", src_success,
              "legacy aggregate success without a run-id - weak prior only")

    # failures: NEVER no_benefit. We do not know if these were technical or methodological.
    named_fail = [r for r in failed if r and r != "unknown"]
    for r in named_fail:
        _emit(r, "not_evaluated", src_unknown,
              "legacy failure: technical vs methodological unknown - carries no demoting signal")
    for i in range(max(0, failure_count - len(named_fail))):
        _emit(f"legacy-agg-fail-{i}", "not_evaluated", src_unknown,
              "legacy aggregate failure without a run-id - no demoting signal")

    return events


# ================================================================================================ #
# AGGREGATION + ATTRIBUTION
#   1. roll events up to (target_id, scope_id, method_variant) - the variant is what a trial tests;
#   2. within that cell, derive one outcome (harmful dominates for safety; technical-only => no
#      methodological signal);
#   3. attribute to an AFFINITY only across >= MIN_VARIANTS_FOR_AFFINITY distinct variants in the
#      same scope, and even then only "limited" - a single variant's no_benefit never condemns the
#      whole thinking-move, it stays scope+variant bound.
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
    outcome: str                 # success | no_benefit | harmful | inconclusive | technical_only |
    #                              not_evaluated
    n_completed: int
    n_technical: int
    evidence: tuple[str, ...]    # trial_ids that produced this


def _cell_outcome(evs: list[MethodTrialRecorded]) -> tuple[str, int, int]:
    completed = [e for e in evs if e.execution_status == "completed"]
    technical = [e for e in evs if e.execution_status != "completed"]
    results = {e.epistemic_result for e in completed
               if e.epistemic_result != "not_evaluated"}
    if "harmful" in results:                       # safety dominates
        outcome = "harmful"
    elif results & {"success", "partial_success"}:
        outcome = "success"
    elif "no_benefit" in results:
        outcome = "no_benefit"
    elif "inconclusive" in results:
        outcome = "inconclusive"
    elif technical and not completed:              # only technical runs -> no methodological signal
        outcome = "technical_only"
    else:
        outcome = "not_evaluated"
    return outcome, len(completed), len(technical)


def aggregate(events: list[MethodTrialRecorded]) -> list[VariantScopeOutcome]:
    """Roll valid events up to one outcome per (target, scope, variant). Invalid events are dropped
    (a caller should ``validate`` first); this never invents an outcome it did not see."""
    cells: dict[tuple, list[MethodTrialRecorded]] = {}
    for e in events:
        if validate(e):
            continue
        cells.setdefault((e.target_id, e.scope_id, e.method_id, e.method_variant), []).append(e)
    out: list[VariantScopeOutcome] = []
    for (target, scope, mid, variant), evs in sorted(cells.items()):
        outcome, n_c, n_t = _cell_outcome(evs)
        affs = tuple(sorted({a for e in evs for a in e.affinities}))
        out.append(VariantScopeOutcome(
            target_id=target, scope_id=scope, method_id=mid, method_variant=variant,
            affinities=affs, outcome=outcome, n_completed=n_c, n_technical=n_t,
            evidence=tuple(e.trial_id for e in evs)))
    return out


@dataclass(frozen=True)
class AffinityScopeAttribution:
    """A LIMITED, multi-variant attribution to an affinity in a scope - never from one variant."""

    target_id: str
    scope_id: str
    affinity: str
    n_variants_no_benefit: int
    n_variants_total: int
    strength: str                # "none" | "limited" | "supported"
    evidence: tuple[str, ...]


# Outcome -> DESi MethodTrial.result. A purely technical cell maps to "technical_failure" (no
# methodological signal -> DESi keeps the move open); not_evaluated -> "unknown".
_OUTCOME_TO_DESI = {
    "success": "success", "no_benefit": "no_benefit", "harmful": "harmful",
    "inconclusive": "inconclusive", "technical_only": "technical_failure",
    "not_evaluated": "unknown",
}


def to_desi_method_trials(outcomes: list[VariantScopeOutcome]):
    """Map aggregated, scope-bound outcomes to DESi ``MethodTrial`` DTOs (one per affinity x cell).

    This is the consumable end of the *updated* projector: once the core emits METHOD_TRIAL_RECORDED
    events, the projector reads them, ``aggregate``s, and calls this to fill ``method_trials`` as a
    DIRECT signal - replacing today's honest ``unknown``. Imports DESi lazily, exactly like the live
    projector, so this module has no hard dependency on it."""
    from desi.solution_space_gap import MethodTrial
    trials = []
    for o in outcomes:
        result = _OUTCOME_TO_DESI.get(o.outcome, "unknown")
        count = max(1, o.n_technical if o.outcome == "technical_only" else o.n_completed)
        for aff in o.affinities:
            trials.append(MethodTrial(
                affinity=aff, target_conflict=o.target_id, result=result, scope=o.scope_id,
                method_variant=o.method_variant, count=count))
    return tuple(trials)


def attribute_to_affinity(outcomes: list[VariantScopeOutcome]) -> list[AffinityScopeAttribution]:
    """Roll variant-scope outcomes up to affinity-scope attributions. Demotion of an AFFINITY is
    gradual and capped: one variant's no_benefit -> "none" (stays variant-bound); >= MIN distinct
    variants no_benefit/harmful -> "limited"; only repeated across many -> "supported"."""
    by_key: dict[tuple[str, str, str], list[VariantScopeOutcome]] = {}
    for o in outcomes:
        for aff in o.affinities:
            by_key.setdefault((o.target_id, o.scope_id, aff), []).append(o)
    res: list[AffinityScopeAttribution] = []
    for (target, scope, aff), cells in sorted(by_key.items()):
        neg = {c.method_variant for c in cells if c.outcome in ("no_benefit", "harmful")}
        total = {c.method_variant for c in cells}
        if len(neg) >= max(MIN_VARIANTS_FOR_AFFINITY + 1, 3):
            strength = "supported"
        elif len(neg) >= MIN_VARIANTS_FOR_AFFINITY:
            strength = "limited"
        else:
            strength = "none"               # a single variant never condemns the whole move
        res.append(AffinityScopeAttribution(
            target_id=target, scope_id=scope, affinity=aff, n_variants_no_benefit=len(neg),
            n_variants_total=len(total), strength=strength,
            evidence=tuple(t for c in cells for t in c.evidence)))
    return res
