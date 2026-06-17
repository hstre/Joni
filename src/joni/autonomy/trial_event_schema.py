"""METHOD_TRIAL_RECORDED - reference schema, validation, migration, aggregation (PROPOSAL v3).

Design artifact, deliberately OUTSIDE the protected ``desi_layer9`` core. Defines the immutable,
scope-bound trial event the real Layer-9 history is missing, plus validation, legacy migration and
aggregation/attribution. Writes nothing to the core; ``migrate_method`` duck-types a legacy
``Method`` via ``getattr`` so this file imports no core class and stays a pure, testable contract.

v3 (final review round) closes the last places where METADATA could accidentally become EVIDENCE:

  1. A legacy success is upgraded ONLY against a verifiable trial artifact (protocol id + artifact
     hash + evaluator + confirmed provenance), never a run-id string or allowlist. A run-id is an
     identifier, not evidence. Without the artifact, even ``kevin-real`` stays ``not_evaluated``.

  2. Affinity attribution requires a VERSIONED independence policy to be satisfied - not a flat
     "distinct models OR implementations". Two thin wrappers over the same model/data are not
     independent however many runs they produce.

  3. The epistemic VERDICT is not decided by a universal statistics formula in the generic schema
     validator. The validator checks STRUCTURE and allowed combinations only; a registered,
     versioned ``decision_rule_id`` + ``decision_rule_hash`` (a Rule-Evaluator) decides whether the
     measurement justifies the verdict. An unknown/non-reproducible hash blocks a trustworthy
     verdict.

Carried over from v1/v2: three orthogonal status axes (execution x protocol x epistemic) + a
failure cause; a technical failure carries no methodological signal; trials bound to
method_variant x target x scope, never to an affinity.
"""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass, field
from types import MappingProxyType

SCHEMA_VERSION = "method_trial_recorded_v3"
EVENT_TYPE = "METHOD_TRIAL_RECORDED"

# -- orthogonal axes ----------------------------------------------------------------------------- #
EXECUTION_STATUSES = ("completed", "failed", "cancelled")
PROTOCOL_STATUSES = ("valid", "invalid", "unknown")
FAILURE_KINDS = ("none", "technical", "timeout", "parser", "model", "dependency", "infrastructure")
EPISTEMIC_RESULTS = ("success", "partial_success", "no_benefit", "harmful", "inconclusive",
                     "not_evaluated")
_REAL_RESULTS = ("success", "partial_success", "no_benefit", "harmful")
# Results a rule can REPRODUCIBLY evaluate (incl. inconclusive). ``not_evaluated`` is excluded - it
# carries no verdict. inconclusive is rule-verifiable and aggregable, but yields NO affinity
# demotion
# or promotion (it is neither a negative nor a success outcome).
RULE_EVALUABLE_RESULTS = _REAL_RESULTS + ("inconclusive",)

TARGET_TYPES = ("conflict", "open_question", "evidence_gap")
DIRECTIONS = ("higher_is_better", "lower_is_better")
EVENT_ATTRIBUTION_LEVELS = ("variant", "method")
ATTRIBUTION_STRENGTHS = ("none", "limited", "supported")
VERIFICATION_STATUSES = ("verified", "unverified")

UNKNOWN = "unknown"


@dataclass(frozen=True)
class Estimand:
    """What the trial set out to measure, fixed BEFORE the run."""

    outcome_metric: str = ""
    contrast: str = "intervention_minus_baseline"
    direction: str = "higher_is_better"
    minimum_effect: float = 0.0
    decision_rule_id: str = ""


@dataclass(frozen=True)
class Measurement:
    """The measured outcome. ``effect_size`` is ORIENTED so positive == better. ``None`` when
    nothing was evaluated."""

    metric_name: str | None = None
    baseline_value: float | None = None
    intervention_value: float | None = None
    effect_size: float | None = None
    # A DESCRIPTIVE, UNINTERPRETED scalar (its kind - SE/SD/MAD/... - is not declared), so it is
    # NOT used by rule_v2 and NOT cross-checked against the CI. The CI is the sole authority.
    uncertainty: float | None = None
    # The statistical interval belongs to the MEASUREMENT (the observation), never the decision; it
    # is what rule_v2 uses to decide whether the minimum effect is statistically supported.
    confidence_interval: tuple[float, float] | None = None


@dataclass(frozen=True)
class Decision:
    """The applied, reproducible decision. The VERDICT is produced by the registered rule
    (``decision_rule_id`` @ ``decision_rule_hash``) - NOT by the generic schema validator."""

    decision_rule_id: str = ""
    decision_rule_hash: str = ""
    verdict: str = "not_evaluated"            # must equal epistemic_result
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None
    minimum_effect: float | None = None


@dataclass(frozen=True)
class LegacyValidation:
    """The verifiable artifact that alone may justify upgrading a legacy success. Absent or
    unverified -> the legacy success stays ``not_evaluated``."""

    run_id: str = ""
    artifact_id: str = ""
    artifact_hash: str = ""
    protocol_id: str = ""
    evaluator_id: str = ""
    verification_status: str = "unverified"   # one of VERIFICATION_STATUSES

    def is_verified(self) -> bool:
        return (self.verification_status == "verified" and bool(self.artifact_hash)
                and bool(self.protocol_id) and bool(self.evaluator_id))


@dataclass(frozen=True)
class MethodTrialRecorded:
    """ONE immutable, scope-bound trial of a method VARIANT against a concrete epistemic target."""

    trial_id: str
    timestamp: str
    ledger_tick: int

    target_type: str
    target_id: str
    claim_ids: tuple[str, ...] = ()

    scope_id: str = UNKNOWN
    scope_description: str = ""

    method_id: str = UNKNOWN
    method_version: int = 1
    method_variant: str = UNKNOWN
    implementation_id: str = UNKNOWN
    affinities: tuple[str, ...] = ()

    task_set_id: str = UNKNOWN
    task_sample_id: str = UNKNOWN              # which sample/split (for independence checks)
    baseline_id: str = UNKNOWN
    evaluator_id: str = UNKNOWN
    estimand: Estimand = field(default_factory=Estimand)

    model: str = UNKNOWN
    model_family: str = UNKNOWN                # coarser than model (for independence checks)
    sampling: dict = field(default_factory=dict)

    execution_status: str = "completed"
    protocol_status: str = "valid"
    failure_kind: str = "none"
    epistemic_result: str = "not_evaluated"

    measurement: Measurement = field(default_factory=Measurement)
    decision: Decision = field(default_factory=Decision)

    run_id: str = UNKNOWN
    artifact_ids: tuple[str, ...] = ()

    attribution_level: str = "variant"
    attribution_strength: str = "none"
    confounders: tuple[str, ...] = ()

    legacy: bool = False
    legacy_reported_success: bool = False
    legacy_validation: LegacyValidation | None = None
    note: str = ""
    field_sources: dict = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION        # the schema this event was RECORDED under

    def to_dict(self) -> dict:
        m, e, d = self.measurement, self.estimand, self.decision
        lv = self.legacy_validation
        return {
            "schema_version": self.schema_version, "event_type": EVENT_TYPE,
            "trial_id": self.trial_id, "timestamp": self.timestamp, "ledger_tick": self.ledger_tick,
            "target_type": self.target_type, "target_id": self.target_id,
            "claim_ids": list(self.claim_ids),
            "scope_id": self.scope_id, "scope_description": self.scope_description,
            "method_id": self.method_id, "method_version": self.method_version,
            "method_variant": self.method_variant, "implementation_id": self.implementation_id,
            "affinities": list(self.affinities),
            "task_set_id": self.task_set_id, "task_sample_id": self.task_sample_id,
            "baseline_id": self.baseline_id, "evaluator_id": self.evaluator_id,
            "estimand": {"outcome_metric": e.outcome_metric, "contrast": e.contrast,
                         "direction": e.direction, "minimum_effect": e.minimum_effect,
                         "decision_rule_id": e.decision_rule_id},
            "model": self.model, "model_family": self.model_family, "sampling": dict(self.sampling),
            "execution_status": self.execution_status, "protocol_status": self.protocol_status,
            "failure_kind": self.failure_kind, "epistemic_result": self.epistemic_result,
            "measurement": {"metric_name": m.metric_name, "baseline_value": m.baseline_value,
                            "intervention_value": m.intervention_value,
                            "effect_size": m.effect_size, "uncertainty": m.uncertainty,
                            "confidence_interval": m.confidence_interval},
            "decision": {"decision_rule_id": d.decision_rule_id,
                         "decision_rule_hash": d.decision_rule_hash, "verdict": d.verdict,
                         "effect_size": d.effect_size, "confidence_interval": d.confidence_interval,
                         "minimum_effect": d.minimum_effect},
            "run_id": self.run_id, "artifact_ids": list(self.artifact_ids),
            "attribution_level": self.attribution_level,
            "attribution_strength": self.attribution_strength,
            "confounders": list(self.confounders), "legacy": self.legacy,
            "legacy_reported_success": self.legacy_reported_success,
            "legacy_validation": (None if lv is None else {
                "run_id": lv.run_id, "artifact_id": lv.artifact_id,
                "artifact_hash": lv.artifact_hash,
                "protocol_id": lv.protocol_id, "evaluator_id": lv.evaluator_id,
                "verification_status": lv.verification_status}),
            "note": self.note, "field_sources": dict(self.field_sources),
        }


# ================================================================================================ #
# VALIDATION - STRUCTURE and allowed combinations ONLY. The epistemic verdict is NOT decided here
# (no universal statistics formula); see the Rule-Evaluator below.
# ================================================================================================ #
def validate(ev: MethodTrialRecorded) -> list[str]:
    errs: list[str] = []
    e, d, m = ev.estimand, ev.decision, ev.measurement

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
    if e.direction not in DIRECTIONS:
        errs.append(f"estimand.direction '{e.direction}' not in {DIRECTIONS}")

    # 'rule_evaluable' = success/partial/no_benefit/harmful/inconclusive (all need a clean run +
    # measurement + a decision block so the registered rule can reproduce the verdict).
    real = ev.epistemic_result in RULE_EVALUABLE_RESULTS

    # -- axis coherence (forbidden combinations) ------------------------------------------------- #
    if ev.execution_status != "completed" and ev.epistemic_result != "not_evaluated":
        errs.append(f"forbidden: execution_status '{ev.execution_status}' requires "
                    "epistemic_result 'not_evaluated' (a non-completed run has no result)")
    if ev.execution_status == "failed" and ev.failure_kind == "none":
        errs.append("forbidden: execution_status 'failed' requires a failure_kind != 'none'")
    if ev.execution_status != "failed" and ev.failure_kind != "none":
        errs.append(f"forbidden: failure_kind '{ev.failure_kind}' requires execution_status "
                    "'failed'")
    if ev.protocol_status == "invalid" and ev.epistemic_result != "not_evaluated":
        errs.append("forbidden: protocol_status 'invalid' requires epistemic_result "
                    "'not_evaluated'")
    if not ev.legacy and ev.protocol_status == "unknown" and real:
        errs.append(f"forbidden: a real result '{ev.epistemic_result}' requires protocol_status "
                    "'valid' (got 'unknown')")
    if not ev.legacy and real and (ev.execution_status != "completed"
                                   or ev.protocol_status != "valid"):
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires execution 'completed' + "
                    "protocol 'valid'")

    # -- measurement (structural; legacy exempt) ------------------------------------------------- #
    has_metric = m.metric_name is not None and m.baseline_value is not None \
        and m.intervention_value is not None
    if not ev.legacy and real and not has_metric:
        errs.append(f"epistemic_result '{ev.epistemic_result}' requires a measurement "
                    "(metric_name + baseline_value + intervention_value)")

    # -- decision block (STRUCTURE only - the verdict is the rule evaluator's job) --------------- #
    if not ev.legacy and real:
        if not d.decision_rule_id or not d.decision_rule_hash:
            errs.append(f"epistemic_result '{ev.epistemic_result}' requires a decision with a "
                        "decision_rule_id AND decision_rule_hash (a registered, versioned rule)")
        if d.verdict != ev.epistemic_result:
            errs.append(f"decision.verdict '{d.verdict}' must equal epistemic_result "
                        f"'{ev.epistemic_result}'")
        if e.decision_rule_id and d.decision_rule_id and e.decision_rule_id != d.decision_rule_id:
            errs.append("decision.decision_rule_id must match the pre-registered "
                        "estimand.decision_rule_id")

    # -- legacy: a success needs a VERIFIED artifact, never a run-id ----------------------------- #
    if ev.legacy and ev.epistemic_result in _REAL_RESULTS:
        if ev.epistemic_result != "success":
            errs.append("a legacy event may only carry 'success' (with proof) or 'not_evaluated'")
        elif ev.legacy_validation is None or not ev.legacy_validation.is_verified():
            errs.append("forbidden: a legacy 'success' requires a VERIFIED legacy_validation "
                        "(protocol_id + artifact_hash + evaluator_id + verification_status="
                        "'verified') - a run-id is an identifier, not evidence")

    # -- attribution ----------------------------------------------------------------------------- #
    if ev.attribution_level not in EVENT_ATTRIBUTION_LEVELS:
        errs.append(f"attribution_level '{ev.attribution_level}' not allowed on a raw event "
                    f"{EVENT_ATTRIBUTION_LEVELS} (affinity-level is earned by aggregation only)")
    if ev.attribution_strength != "none":
        errs.append("forbidden: a single raw event never carries attribution_strength != 'none'")

    # -- structural minimums --------------------------------------------------------------------- #
    if not ev.trial_id:
        errs.append("trial_id is required")
    if ev.target_type == "conflict" and not ev.claim_ids:
        errs.append("a conflict trial must carry claim_ids (the scope it spans)")
    if not ev.scope_id:
        errs.append("scope_id is required (use 'unknown' explicitly, never empty)")
    if not ev.method_variant:
        errs.append("method_variant is required (use 'unknown' explicitly, never empty)")
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
# RULE-EVALUATOR - the epistemic verdict lives here, keyed by (decision_rule_id, rule_hash), OUT of
# the generic validator. The verdict is computed ENTIRELY from the MEASUREMENT's effect and its own
# confidence interval against the PRE-REGISTERED estimand - never from the decision block, never
# from a decision-supplied interval, and (for rule_v2) NOT from ``measurement.uncertainty`` (that is
# a descriptive field; only the CI drives the verdict - see the Measurement docstring). The rule
# hash binds to the actual executable artefact: the evaluator RE-DERIVES the hash of the registered
# function on every use, so neither a forged registry entry nor a post-hoc swap of ``fn`` can pass.
# ================================================================================================ #
def _rule_v2(ev: MethodTrialRecorded) -> str:
    """Reference decision rule (rule_v2). Computes the verdict from the MEASUREMENT's confidence
    interval against the pre-registered ``estimand.minimum_effect``. ``success``/``harmful`` require
    the whole interval BEYOND the threshold (``ci_low >= min`` / ``ci_high <= -min``).
    ``no_benefit``
    is an EQUIVALENCE verdict: the whole interval lies INSIDE the band ``(-min, +min)`` (zero may be
    included) - a precise null is therefore no_benefit, not weaker than a small positive effect. An
    interval that straddles a threshold boundary is ``inconclusive``. ``measurement.uncertainty`` is
    NOT used by this rule (an uninterpreted descriptive scalar). ``partial_success`` is NOT
    producible by rule_v2 (reserved for other registered rules)."""
    m, est = ev.measurement, ev.estimand
    eff, mn, ci = m.effect_size, est.minimum_effect, m.confidence_interval
    if eff is None or mn is None or mn <= 0:
        return "not_evaluated"
    if ci is None:                                   # no interval -> cannot resolve anything
        return "inconclusive"
    lo, hi = ci
    if hi <= -mn:                                    # interval entirely at/below -minimum_effect
        return "harmful"
    if lo >= mn:                                     # interval entirely at/above +minimum_effect
        return "success"
    if -mn < lo and hi < mn:                         # interval entirely inside the equivalence band
        return "no_benefit"                          # (zero may be inside - a precise null counts)
    return "inconclusive"                            # straddles a threshold boundary


def _impl_hash(fn) -> str | None:
    """The sha256 of a rule function's own source - its executable identity. ``None`` if the source
    cannot be obtained (then it cannot be attested, hence not trustworthy)."""
    try:
        src = inspect.getsource(fn)
    except (OSError, TypeError):
        return None
    return "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()


# The descriptor is a human spec hash; the IMPLEMENTATION hash is derived from the rule's own source
# and is the one an event's ``decision_rule_hash`` must match. Editing _rule_v2 rotates it.
_RULE_V2_DESCRIPTOR = ("rule_v2|source=measurement.ci|threshold=estimand.minimum_effect|"
                       "uncertainty_not_used|harmful:ci_hi<=-min|success:ci_lo>=min|"
                       "no_benefit:ci_within(-min,+min)|else:inconclusive")
RULE_V2_SPEC_HASH = "sha256:" + hashlib.sha256(_RULE_V2_DESCRIPTOR.encode()).hexdigest()
RULE_V2_IMPL_HASH = _impl_hash(_rule_v2)
RULE_V2_HASH = RULE_V2_IMPL_HASH                     # the event's decision_rule_hash binds to code


@dataclass(frozen=True)
class EvaluationArtifact:
    """A VERSION-PINNED evaluation bundle keyed by ``(rule_id, implementation_hash)``. It binds the
    WHOLE evaluation of an event - schema_version + input decoder + input-contract + validator +
    rule - so a future change to *any* live component can never re-interpret an old event. The
    event's ``decision_rule_hash`` selects the artifact; the artifact's OWN (byte-pinned for
    archived, live for current) decoder, contract, validator and rule are used. EVERY hash
    (``implementation_hash``, ``validator_hash``, ``input_contract_hash``, ``decoder_hash``,
    ``canonical_input_projection_hash``) is RE-DERIVED from the actual artifact at use and checked
    against the claim, so a forged artifact (claimed hash, different code/contract) is rejected
    before its code is trusted. ``schema_version`` must equal the event's recorded schema."""

    rule_id: str
    schema_version: str
    implementation_hash: str
    validator_hash: str
    input_contract_hash: str
    input_contract: dict
    decoder_hash: str = ""
    canonical_input_projection_hash: str = ""
    rule_fn: object = None
    rule_source: bytes | None = None        # byte-pinned source for ARCHIVED versions
    validator_fn: object = None
    validator_source: bytes | None = None   # byte-pinned validator snapshot for ARCHIVED versions
    contract_source: bytes | None = None    # byte-pinned canonical-JSON contract for ARCHIVED
    decoder_fn: object = None
    decoder_source: bytes | None = None     # byte-pinned input-decoder snapshot for ARCHIVED


RuleEntry = EvaluationArtifact                # backwards-compatible alias

_RULE_V2_DESCRIPTOR = ("rule_v2|source=measurement.ci|threshold=estimand.minimum_effect|"
                       "uncertainty_not_used|harmful:ci_hi<=-min|success:ci_lo>=min|"
                       "no_benefit:ci_within(-min,+min)|else:inconclusive")
RULE_V2_SPEC_HASH = "sha256:" + hashlib.sha256(_RULE_V2_DESCRIPTOR.encode()).hexdigest()
RULE_V2_IMPL_HASH = _impl_hash(_rule_v2)
RULE_V2_HASH = RULE_V2_IMPL_HASH


def _bytes_hash(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _canonical_contract_bytes(d: dict) -> bytes:
    import json
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _contract_hash(d: dict) -> str:
    return _bytes_hash(_canonical_contract_bytes(d))


def _read_artifact(name: str) -> bytes:
    import pathlib
    return (pathlib.Path(__file__).parent / "rule_artifacts" / name).read_bytes()


def _validator_globals() -> dict:
    from desi_layer9 import trial_event_validation as v
    return {"_finite": v._finite, "_ci_errors": v._ci_errors, "_EPS": v._EPS}


def _exec_callable(src: bytes, name: str, extra: dict | None = None):
    ns = {"MethodTrialRecorded": MethodTrialRecorded}
    if extra:
        ns.update(extra)
    exec(compile(src.decode("utf-8"), f"<artifact:{name}>", "exec"), ns)   # noqa: S102
    return ns[name]


def _decode_v3(ev: MethodTrialRecorded):
    """The v3 canonical INPUT projection: event -> (measurement, decision, estimand) block dicts.
    This is the ONLY place that maps event fields to the validator/rule input. It is versioned and
    HASHED (``decoder_hash``) so a historical event is never silently re-projected by a changed
    decoder; a historical artifact carries its own byte-pinned decoder snapshot."""
    m, d, e = ev.measurement, ev.decision, ev.estimand
    meas = {"metric_name": m.metric_name, "baseline_value": m.baseline_value,
            "intervention_value": m.intervention_value, "effect_size": m.effect_size,
            "uncertainty": m.uncertainty, "confidence_interval": m.confidence_interval}
    dec = {"effect_size": d.effect_size, "minimum_effect": d.minimum_effect,
           "confidence_interval": d.confidence_interval}
    est = {"outcome_metric": e.outcome_metric, "contrast": e.contrast, "direction": e.direction,
           "minimum_effect": e.minimum_effect}
    return meas, dec, est


def _projection_schema_hash(meas: dict, dec: dict, est: dict) -> str:
    """Hash of the KEY-SCHEMA a decoder emits (not the values). Re-derived from the actual decode at
    use, so a decoder that emits a different input shape than the artifact declares is rejected."""
    schema = {"measurement": sorted(meas), "decision": sorted(dec), "estimand": sorted(est)}
    return _bytes_hash(_canonical_contract_bytes(schema))


# a value-free probe used ONLY to derive the key-schema a decoder produces at artifact-build time.
_PROJECTION_PROBE = None


def _projection_hash_of(decoder_fn) -> str:
    global _PROJECTION_PROBE
    if _PROJECTION_PROBE is None:
        _PROJECTION_PROBE = MethodTrialRecorded(trial_id="_probe", timestamp="_", ledger_tick=0,
                                                target_type="_", target_id="_")
    return _projection_schema_hash(*decoder_fn(_PROJECTION_PROBE))


def _apply_input_contract(contract: dict, meas: dict, dec: dict, est: dict) -> list[str]:
    """Enforce the historical input contract BEFORE the validator/rule run. Unmet required inputs
    make the event non-evaluable under THIS contract (reported as a structural inconsistency)."""
    errors: list[str] = []
    if contract.get("require_effect") and meas.get("effect_size") is None:
        errors.append("input contract requires measurement.effect_size")
    if contract.get("require_confidence_interval") and meas.get("confidence_interval") is None:
        errors.append("input contract requires measurement.confidence_interval")
    blocks = {"measurement": meas, "decision": dec, "estimand": est}
    for spec in contract.get("required_fields", ()):
        block, _, fld = spec.partition(".")
        if meas.get(spec) is not None or (block in blocks and blocks[block].get(fld) is not None):
            continue
        errors.append(f"input contract requires non-null '{spec}'")
    for fld in contract.get("required_measurement_fields", ()):
        if meas.get(fld) is None:
            errors.append(f"input contract requires non-null measurement.{fld}")
    return errors


def _as_contract(contract) -> tuple[dict, bytes]:
    """Accept a dict (canonicalised to bytes) or already-canonical bytes; return (dict, bytes)."""
    import json
    if isinstance(contract, (bytes, bytearray)):
        return json.loads(bytes(contract).decode("utf-8")), bytes(contract)
    return dict(contract), _canonical_contract_bytes(contract)


def make_live_artifact(rule_id, schema_version, rule_fn, validator_fn, input_contract,
                       decoder_fn=_decode_v3):
    """An artifact bound to LIVE functions; every hash tracks the current source."""
    cdict, cbytes = _as_contract(input_contract)
    return EvaluationArtifact(
        rule_id, schema_version, implementation_hash=_impl_hash(rule_fn),
        validator_hash=_impl_hash(validator_fn), input_contract_hash=_bytes_hash(cbytes),
        input_contract=cdict, decoder_hash=_impl_hash(decoder_fn),
        canonical_input_projection_hash=_projection_hash_of(decoder_fn),
        rule_fn=rule_fn, validator_fn=validator_fn, decoder_fn=decoder_fn)


def make_archived_artifact(rule_id, schema_version, rule_src, validator_src, contract,
                           decoder_src=None, *, expected_rule_hash=None):
    """An artifact whose decoder + contract + validator + rule are ALL BYTE-PINNED verbatim. The
    implementation hash is the sha256 of the stored rule bytes - the REAL historical hash, not one
    recomputed from a later copy. A pinned ``expected_rule_hash`` (from the prior release) is
    enforced. ``contract`` may be canonical-JSON bytes (byte-pinned) or a dict; ``decoder_src``
    defaults to the v3 decoder snapshot."""
    rh = _bytes_hash(rule_src)
    if expected_rule_hash is not None and rh != expected_rule_hash:
        raise ValueError(f"archived rule artifact hash {rh} != expected {expected_rule_hash}")
    cdict, cbytes = _as_contract(contract)
    dsrc = _DECODE_V3_SRC if decoder_src is None else decoder_src
    decoder_fn = _exec_callable(dsrc, "_decode_v3")
    return EvaluationArtifact(
        rule_id, schema_version, implementation_hash=rh, validator_hash=_bytes_hash(validator_src),
        input_contract_hash=_bytes_hash(cbytes), input_contract=cdict,
        decoder_hash=_bytes_hash(dsrc),
        canonical_input_projection_hash=_projection_hash_of(decoder_fn),
        rule_source=rule_src, validator_source=validator_src, contract_source=cbytes,
        decoder_source=dsrc)


def make_rule_entry(rule_id: str, spec_hash: str, fn) -> EvaluationArtifact:
    """Compatibility shim: a LIVE artifact whose implementation_hash is COMPUTED from ``fn`` and
    which binds the current validator + input contract + decoder."""
    from desi_layer9.trial_event_validation import (
        RULE_INPUT_CONTRACTS,
        cross_block_consistency,
    )
    return make_live_artifact(rule_id, SCHEMA_VERSION, fn, cross_block_consistency,
                              RULE_INPUT_CONTRACTS.get(rule_id, {}))


def build_rule_registry(artifacts):
    """An APPEND-ONLY, immutable catalog keyed by ``(rule_id, implementation_hash)``. A key may
    never be overwritten - to keep an irreversible journal reproducible, a changed rule is ADDED as
    a new artifact (with the old one archived byte-for-byte), never replacing an existing one."""
    reg: dict = {}
    for a in artifacts:
        key = (a.rule_id, a.implementation_hash)
        if key in reg:
            raise ValueError(f"rule registry is append-only; {key} is already registered")
        reg[key] = a
    return MappingProxyType(reg)


# THE PRODUCTION CATALOG - append-only, immutable, byte-pinned. The archived r6 rule is loaded from
# its VERBATIM historical source (its hash is the REAL prior-release hash), together with byte-
# pinned snapshots of the decoder, contract and validator it ran under; the current rule is live.
_R6_RULE_SRC = _read_artifact("rule_v2_r6.pysrc")
_CROSS_BLOCK_V1_SRC = _read_artifact("cross_block_v1.pysrc")
_DECODE_V3_SRC = _read_artifact("decode_v3.pysrc")
_R6_CONTRACT_SRC = _read_artifact("rule_v2_r6.contract.json")
RULE_V2_R6_HASH = _bytes_hash(_R6_RULE_SRC)             # the real historical hash (2438455f...)


def _default_registry():
    from desi_layer9.trial_event_validation import (
        RULE_INPUT_CONTRACTS,
        cross_block_consistency,
    )
    return build_rule_registry([
        make_archived_artifact("rule_v2", SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                               _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                               expected_rule_hash=RULE_V2_R6_HASH),
        make_live_artifact("rule_v2", SCHEMA_VERSION, _rule_v2, cross_block_consistency,
                           RULE_INPUT_CONTRACTS.get("rule_v2", {})),
    ])


DEFAULT_RULE_REGISTRY = _default_registry()


def _blocks(ev: MethodTrialRecorded):
    """The CURRENT (live) input projection. Historical eval uses the artifact's own decoder."""
    return _decode_v3(ev)


def _cross_block_errors(ev: MethodTrialRecorded) -> list[str]:
    """The CURRENT canonical consistency check (used for live evaluation and by tests)."""
    from desi_layer9.trial_event_validation import cross_block_consistency
    return cross_block_consistency(*_blocks(ev), is_real=True)


@dataclass(frozen=True)
class _Resolved:
    rule_fn: object
    rule_hash: str
    validator_fn: object
    validator_hash: str
    decoder_fn: object
    decoder_hash: str
    contract: dict
    contract_hash: str


def _resolve_artifact(art: EvaluationArtifact) -> _Resolved:
    """Materialise an artifact and RE-DERIVE every hash from the actual (byte-pinned for archived,
    live for current) component, so claimed metadata can never attest different executed code."""
    if art.rule_source is not None:
        rule_hash = _bytes_hash(art.rule_source)
        rule_fn = _exec_callable(art.rule_source, "_rule_v2")
    else:
        rule_hash, rule_fn = _impl_hash(art.rule_fn), art.rule_fn
    if art.validator_source is not None:
        validator_hash = _bytes_hash(art.validator_source)
        validator_fn = _exec_callable(art.validator_source, "cross_block_consistency",
                                      _validator_globals())
    else:
        validator_hash, validator_fn = _impl_hash(art.validator_fn), art.validator_fn
    if art.decoder_source is not None:
        decoder_hash = _bytes_hash(art.decoder_source)
        decoder_fn = _exec_callable(art.decoder_source, "_decode_v3")
    else:
        decoder_hash, decoder_fn = _impl_hash(art.decoder_fn), art.decoder_fn
    if art.contract_source is not None:
        contract = _as_contract(art.contract_source)[0]
        contract_hash = _bytes_hash(art.contract_source)
    else:
        contract, contract_hash = dict(art.input_contract), _contract_hash(art.input_contract)
    return _Resolved(rule_fn, rule_hash, validator_fn, validator_hash, decoder_fn, decoder_hash,
                     contract, contract_hash)


def evaluate_decision(ev: MethodTrialRecorded, registry=None) -> dict:
    """Evaluate the event under the EXACT version-pinned artifact its ``decision_rule_hash`` selects
    - its OWN schema, decoder, input-contract, validator AND rule. ``status`` in {"verified",
    "inconsistent", "unverifiable", "not_applicable"}. EVERY component hash is re-derived from the
    actual artifact and checked against the claim before that component is trusted, so claimed
    metadata can never attest a different executed decoder/contract/validator/rule. A schema
    mismatch, any hash mismatch, an unknown hash, an unmet input contract, a measurement the rule's
    own validator rejects, or a verdict the rule does not compute is never ``verified``; an old
    event is never re-interpreted under a newer component."""
    reg = DEFAULT_RULE_REGISTRY if registry is None else registry
    d = ev.decision
    if ev.epistemic_result not in RULE_EVALUABLE_RESULTS:
        return {"status": "not_applicable", "reason": "no rule-evaluable verdict (not_evaluated)"}
    art = reg.get((d.decision_rule_id, d.decision_rule_hash))
    if art is None:
        return {"status": "unverifiable",
                "reason": f"decision rule '{d.decision_rule_id}'@'{d.decision_rule_hash}' is not "
                          "in the registered append-only catalog - no trustworthy verdict"}
    # the artifact may only evaluate the schema version it was registered for.
    ev_schema = getattr(ev, "schema_version", SCHEMA_VERSION)
    if ev_schema != art.schema_version:
        return {"status": "unverifiable",
                "reason": f"event schema '{ev_schema}' != artifact schema '{art.schema_version}' - "
                          "the historical evaluation capsule does not decode this schema"}
    try:
        r = _resolve_artifact(art)
    except Exception as exc:  # noqa: BLE001
        return {"status": "unverifiable", "reason": f"artifact could not be resolved ({exc!r})"}
    # every component hash must match the claim BEFORE its code/contract is trusted.
    for name, derived, claimed in (
        ("implementation_hash", r.rule_hash, art.implementation_hash),
        ("rule selector", r.rule_hash, d.decision_rule_hash),
        ("validator_hash", r.validator_hash, art.validator_hash),
        ("decoder_hash", r.decoder_hash, art.decoder_hash),
        ("input_contract_hash", r.contract_hash, art.input_contract_hash),
    ):
        if derived is None or derived != claimed:
            return {"status": "unverifiable",
                    "reason": f"artifact {name} does not match the re-derived component "
                              f"({derived} != {claimed}) - no trustworthy verdict"}
    # the artifact's OWN (version-pinned) decoder projects the input; its key-schema is re-checked.
    meas, dec, est = r.decoder_fn(ev)
    proj = _projection_schema_hash(meas, dec, est)
    if proj != art.canonical_input_projection_hash:
        return {"status": "unverifiable",
                "reason": f"decoder produced an unexpected input projection ({proj} != "
                          f"{art.canonical_input_projection_hash}) - no trustworthy verdict"}
    # the artifact's OWN input contract is APPLIED before validator/rule run.
    cerr = _apply_input_contract(r.contract, meas, dec, est)
    if cerr:
        return {"status": "inconsistent", "reason": "; ".join(cerr)}
    # the artifact's OWN (version-pinned) validator runs - not necessarily the current one.
    xb = r.validator_fn(meas, dec, est, is_real=True)
    if xb:
        return {"status": "inconsistent", "reason": "; ".join(xb)}
    computed = r.rule_fn(ev)
    if computed != d.verdict or computed != ev.epistemic_result:
        return {"status": "inconsistent", "computed": computed, "claimed": d.verdict,
                "reason": f"rule computes '{computed}' from the measurement, event claims "
                          f"'{d.verdict}'"}
    return {"status": "verified", "computed": computed}


# ================================================================================================ #
# LEGACY MIGRATION - a success is upgraded ONLY against a VERIFIED artifact, never a run-id.
#   old success=true  -> not_evaluated by DEFAULT; -> weak 'success' iff a resolver returns a
#                        VERIFIED LegacyValidation for that run.
#   old success=false -> not_evaluated (NEVER no_benefit).
# ================================================================================================ #
def migrate_method(method, *, base_tick: int = 0, resolve_legacy_validation=None) \
        -> list[MethodTrialRecorded]:
    """Duck-type a legacy ``Method`` into immutable events without inventing signal.

    ``resolve_legacy_validation`` is an optional ``run_id -> LegacyValidation | None`` that supplies
    a VERIFIABLE artifact. By default nothing is verifiable, so every legacy success becomes
    ``not_evaluated`` - a run-id alone never upgrades anything."""
    mid = getattr(method, "id", UNKNOWN)
    version = int(getattr(method, "version", 1) or 1)
    affinities = tuple(getattr(method, "applicable_to", ()) or ())
    supporting = tuple(getattr(method, "supporting_runs", ()) or ())
    failed = tuple(getattr(method, "failed_runs", ()) or ())
    success_count = int(getattr(method, "success_count", 0) or 0)
    failure_count = int(getattr(method, "failure_count", 0) or 0)

    events: list[MethodTrialRecorded] = []
    tick = base_tick

    def _emit(run_id, result, reported, note, conf, lv=None):
        nonlocal tick
        tick += 1
        events.append(MethodTrialRecorded(
            trial_id=f"legacy:{mid}:{result}:{run_id}:{tick}", timestamp="legacy",
            ledger_tick=tick, target_type="conflict", target_id=UNKNOWN, claim_ids=(UNKNOWN,),
            scope_id=UNKNOWN, method_id=mid, method_version=version, method_variant=UNKNOWN,
            affinities=affinities, execution_status="completed", protocol_status="unknown",
            epistemic_result=result, run_id=run_id, attribution_level="method",
            attribution_strength="none", legacy=True, legacy_reported_success=reported,
            legacy_validation=lv, note=note,
            field_sources={"scope_id": {"source": "n/a", "confidence": "unknown"},
                           "method_variant": {"source": "n/a", "confidence": "unknown"},
                           "epistemic_result": {"source": "legacy Method counters",
                                                "confidence": conf}}))

    def _success_or_not(run_id):
        lv = resolve_legacy_validation(run_id) if resolve_legacy_validation else None
        if lv is not None and lv.is_verified():
            _emit(run_id, "success", True,
                  "legacy success backed by a VERIFIED trial artifact - weak prior only "
                  "(no scope/variant/effect recorded)", "derived", lv)
        else:
            _emit(run_id, "not_evaluated", True,
                  "legacy success with no verified artifact (a run-id is not evidence) - "
                  "reported-only, no demoting/promoting signal", "unknown")

    named_succ = [r for r in supporting if r and r != "unknown"]
    for r in named_succ:
        _success_or_not(r)
    for i in range(max(0, success_count - len(named_succ))):
        _success_or_not(f"legacy-agg-{i}")

    named_fail = [r for r in failed if r and r != "unknown"]
    for r in named_fail:
        _emit(r, "not_evaluated", False,
              "legacy failure: technical vs methodological unknown - no demoting signal", "unknown")
    for i in range(max(0, failure_count - len(named_fail))):
        _emit(f"legacy-agg-fail-{i}", "not_evaluated", False,
              "legacy aggregate failure without a run-id - no demoting signal", "unknown")
    return events


# ================================================================================================ #
# AGGREGATION + ATTRIBUTION
# ================================================================================================ #
@dataclass(frozen=True)
class VariantScopeOutcome:
    target_id: str
    scope_id: str
    method_id: str
    method_variant: str
    affinities: tuple[str, ...]
    outcome: str
    n_completed_valid: int
    n_unusable: int
    protocol_valid: bool
    models: tuple[str, ...]
    model_families: tuple[str, ...]
    implementations: tuple[str, ...]
    task_samples: tuple[str, ...]
    evaluators: tuple[str, ...]
    confounders: tuple[str, ...]
    evidence: tuple[str, ...]
    has_success: bool = False        # any success/partial_success among the usable events
    has_harmful: bool = False        # any harmful among the usable events (safety signal preserved)


def _cell_outcome(evs: list[MethodTrialRecorded]) -> tuple[str, int, int, bool, bool]:
    usable = [e for e in evs if e.execution_status == "completed" and e.protocol_status == "valid"]
    unusable = [e for e in evs if e not in usable]
    results = {e.epistemic_result for e in usable if e.epistemic_result != "not_evaluated"}
    has_success = bool(results & {"success", "partial_success"})
    has_harmful = "harmful" in results
    if has_success and has_harmful:
        # both present: a CONFLICTING cell. harmful is kept as a safety signal (has_harmful) but the
        # success evidence is NOT erased - so affinity attribution can see it and refuse demotion.
        outcome = "conflicting"
    elif has_harmful:
        outcome = "harmful"
    elif has_success:
        outcome = "success"
    elif "no_benefit" in results:
        outcome = "no_benefit"
    elif "inconclusive" in results:
        outcome = "inconclusive"
    elif unusable and not usable:
        outcome = "technical_only"
    else:
        outcome = "not_evaluated"
    return outcome, len(usable), len(unusable), has_success, has_harmful


_EVIDENCE_TOKEN = object()


def canonical_event(event: MethodTrialRecorded) -> str:
    """Canonical string form of an event (its full v3 payload) for binding attestations."""
    from desi_layer9.trial_event_validation import canonical_payload
    return canonical_payload(event.to_dict())


def _evidence_attestation(event: MethodTrialRecorded, verdict: str) -> str:
    """A structural attestation BINDING the verdict to the canonical event. If the event is later
    swapped (e.g. via ``dataclasses.replace``), this no longer matches - so the token alone is never
    the integrity root."""
    return "sha256:" + hashlib.sha256(
        (canonical_event(event) + "|" + verdict).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerifiedTrialEvidence:
    """A trial event whose verdict has been VERIFIED by the registered rule. The private token
    guards
    against accidental direct construction; the ``attestation`` BINDS the verdict to the canonical
    event so a post-hoc substitution is detectable; and ``aggregate`` additionally RE-EVALUATES
    every
    event (it never trusts the token or the stored verdict as the integrity root)."""

    event: MethodTrialRecorded
    verdict: str
    attestation: str = ""
    _token: object = None

    def __post_init__(self):
        if self._token is not _EVIDENCE_TOKEN:
            raise TypeError("VerifiedTrialEvidence is created only by verify_events()")


def verify_events(events: list[MethodTrialRecorded], registry=None) -> list[VerifiedTrialEvidence]:
    """The only way to turn raw events into aggregable evidence: runs ``evaluate_decision`` on each
    and keep ONLY those whose verdict the registered rule verifies (structurally valid AND
    rule-verified). Unverifiable / inconsistent / non-evaluable / invalid events carry no
    weight."""
    out: list[VerifiedTrialEvidence] = []
    for ev in events:
        if validate(ev):
            continue
        if evaluate_decision(ev, registry)["status"] == "verified":
            out.append(VerifiedTrialEvidence(
                ev, ev.epistemic_result, _evidence_attestation(ev, ev.epistemic_result),
                _EVIDENCE_TOKEN))
    return out


def aggregate(evidence: list[VerifiedTrialEvidence], registry=None) -> list[VariantScopeOutcome]:
    """Roll VERIFIED evidence up to one outcome per (target, scope, variant). The token is NOT
    trusted
    as the integrity root: every evidence object is RE-ATTESTED here - its attestation must bind to
    its current event, its verdict must equal the event result, and the event must RE-VERIFY
    under
    the registered rule. A substituted event (``dataclasses.replace`` keeping the token) is
    rejected."""
    cells: dict[tuple, list[MethodTrialRecorded]] = {}
    for ve in evidence:
        if not isinstance(ve, VerifiedTrialEvidence):
            raise TypeError("aggregate() accepts only VerifiedTrialEvidence (see verify_events)")
        e = ve.event
        if ve.verdict != e.epistemic_result:
            raise ValueError("evidence verdict does not match its event (substituted?)")
        if ve.attestation != _evidence_attestation(e, ve.verdict):
            raise ValueError("evidence attestation does not bind to its event (substituted?)")
        if evaluate_decision(e, registry)["status"] != "verified":
            raise ValueError("evidence event does not re-verify under the registered rule")
        cells.setdefault((e.target_id, e.scope_id, e.method_id, e.method_variant), []).append(e)
    out: list[VariantScopeOutcome] = []
    for (target, scope, mid, variant), evs in sorted(cells.items()):
        outcome, n_v, n_u, has_s, has_h = _cell_outcome(evs)
        usable = [e for e in evs if e.execution_status == "completed"
                  and e.protocol_status == "valid"]
        out.append(VariantScopeOutcome(
            target_id=target, scope_id=scope, method_id=mid, method_variant=variant,
            affinities=tuple(sorted({a for e in evs for a in e.affinities})), outcome=outcome,
            n_completed_valid=n_v, n_unusable=n_u, protocol_valid=bool(usable) and n_u == 0,
            models=tuple(sorted({e.model for e in usable})),
            model_families=tuple(sorted({e.model_family for e in usable})),
            implementations=tuple(sorted({e.implementation_id for e in usable})),
            task_samples=tuple(sorted({e.task_sample_id for e in usable})),
            evaluators=tuple(sorted({e.evaluator_id for e in usable})),
            confounders=tuple(sorted({c for e in usable for c in e.confounders})),
            evidence=tuple(e.trial_id for e in evs), has_success=has_s, has_harmful=has_h))
    return out


@dataclass(frozen=True)
class OperationalTrialObservation:
    """A NON-epistemic record that a method VARIANT was ATTEMPTED but produced no rule-evaluable
    verdict. A SEPARATE channel from ``VerifiedTrialEvidence``: it may inform DESi that a move was
    tried (classified by ``desi_result``) but NEVER produces affinity attribution. The
    classification distinguishes a real technical failure from a merely-unevaluated/cancelled run -
    DESi must not learn 'no epistemic verdict => the technique failed'."""

    trial_id: str
    target_id: str
    scope_id: str
    method_id: str
    method_variant: str
    affinities: tuple[str, ...]
    execution_status: str
    protocol_status: str
    failure_kind: str
    desi_result: str            # technical_failure|unevaluated|cancelled|protocol_invalid|unknown


def _operational_class(ev: MethodTrialRecorded) -> str:
    """Classify a non-rule-evaluable event WITHOUT collapsing everything to 'technical_failure'."""
    if ev.execution_status == "failed":
        return "technical_failure"
    if ev.execution_status == "cancelled":
        return "cancelled"
    if ev.protocol_status == "invalid":
        return "protocol_invalid"
    if ev.execution_status == "completed" and ev.protocol_status == "valid":
        return "unevaluated"                      # ran cleanly but no outcome was evaluated
    return "unknown_operational"


def operational_observations(
        events: list[MethodTrialRecorded]) -> list[OperationalTrialObservation]:
    """The operational (non-epistemic) channel: structurally-valid events that carry NO
    rule-evaluable verdict. They stay VISIBLE as 'a move was attempted but not evaluable', strictly
    separate from verified evidence - never feeding attribution - and CLASSIFIED so DESi can tell a
    technical failure from a merely-unevaluated or cancelled run."""
    out: list[OperationalTrialObservation] = []
    for ev in events:
        if validate(ev):
            continue
        if ev.epistemic_result not in RULE_EVALUABLE_RESULTS:    # not_evaluated etc.
            out.append(OperationalTrialObservation(
                trial_id=ev.trial_id, target_id=ev.target_id, scope_id=ev.scope_id,
                method_id=ev.method_id, method_variant=ev.method_variant,
                affinities=ev.affinities, execution_status=ev.execution_status,
                protocol_status=ev.protocol_status, failure_kind=ev.failure_kind,
                desi_result=_operational_class(ev)))
    return out


_OUTCOME_TO_DESI = {
    "success": "success", "no_benefit": "no_benefit", "harmful": "harmful",
    "inconclusive": "inconclusive", "technical_only": "technical_failure",
    "not_evaluated": "unknown",
    # a conflicting cell (success AND harmful) must NOT demote a move -> inconclusive for DESi.
    "conflicting": "inconclusive",
}


def to_desi_method_trials(outcomes: list[VariantScopeOutcome]):
    """Map aggregated, scope-bound outcomes to DESi ``MethodTrial`` DTOs (one per affinity x cell).
    Imports DESi lazily, like the live projector."""
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


# -- independence: a VERSIONED policy, not a count or an OR -------------------------------------- #
@dataclass(frozen=True)
class IndependenceProfile:
    n_variants: int
    method_variants_distinct: bool
    implementations_distinct: bool
    model_families_distinct: bool
    task_samples_independent: bool
    evaluator_independent: bool
    shared_confounders: tuple[str, ...]
    # dimensions where at least one variant has an unknown/missing value -> fail-closed: unknown is
    # NOT independence. These make the dimension non-distinct AND give a precise reason.
    incomplete_dimensions: tuple[str, ...] = ()


@dataclass(frozen=True)
class IndependencePolicy:
    """The explicit, versioned bar a set of failing variants must clear before it may say anything
    about an AFFINITY. Every requirement defaults ON; a profile that misses any stays 'none'."""

    policy_id: str = "independence_policy_v1"
    min_variants: int = 2
    require_implementations_distinct: bool = True
    require_model_families_distinct: bool = True
    require_task_samples_independent: bool = True
    require_evaluator_independent: bool = True
    forbid_shared_confounders: bool = True

    def satisfied(self, p: IndependenceProfile) -> tuple[bool, str]:
        if p.n_variants < self.min_variants or not p.method_variants_distinct:
            return False, f"fewer than {self.min_variants} distinct variants"
        checks = (
            (self.require_implementations_distinct, "implementations", p.implementations_distinct),
            (self.require_model_families_distinct, "model_families", p.model_families_distinct),
            (self.require_task_samples_independent, "task_samples", p.task_samples_independent),
            (self.require_evaluator_independent, "evaluators", p.evaluator_independent),
        )
        for required, name, distinct in checks:
            if required and not distinct:
                # unknown/missing is reported distinctly from a genuine shared dependency.
                if name in p.incomplete_dimensions:
                    return False, ("independence metadata incomplete: "
                                   f"{name} unknown for >= 1 variant")
                return False, f"{name} not distinct (shared dependency)"
        if self.forbid_shared_confounders and p.shared_confounders:
            return False, f"a confounder is shared across variants ({list(p.shared_confounders)})"
        return True, f"independence policy '{self.policy_id}' satisfied"


INDEPENDENCE_POLICY_V1 = IndependencePolicy()


def _shared_across_variants(cells: list[VariantScopeOutcome], attr: str) -> set:
    """Values of ``attr`` that appear in >= 2 DISTINCT method variants - a shared dependency that
    breaks independence. (A plain ``len(union) >= n`` count is fooled by overlapping sets like
    {shared, impl-A} / {shared, impl-B}; this is not.)"""
    owners: dict = {}
    for c in cells:
        for v in getattr(c, attr):
            owners.setdefault(v, set()).add(c.method_variant)
    return {v for v, variants in owners.items() if len(variants) >= 2}


_UNKNOWN_VALUES = ("", "unknown")


def _known(v) -> bool:
    return v is not None and v not in _UNKNOWN_VALUES


def _dimension_state(cells: list[VariantScopeOutcome], attr: str) -> tuple[bool, bool]:
    """Return ``(distinct, incomplete)`` for one independence dimension, FAIL-CLOSED: a variant with
    no KNOWN value makes the dimension non-distinct AND incomplete (unknown != independent). A known
    value shared by >= 2 variants also makes it non-distinct."""
    per_variant: dict = {}
    for c in cells:
        per_variant.setdefault(c.method_variant, set())
        per_variant[c.method_variant] |= {v for v in getattr(c, attr) if _known(v)}
    incomplete = any(not vals for vals in per_variant.values())
    owners: dict = {}
    for variant, vals in per_variant.items():
        for v in vals:
            owners.setdefault(v, set()).add(variant)
    shared = any(len(vs) >= 2 for vs in owners.values())
    return (not incomplete and not shared), incomplete


def _profile(neg: list[VariantScopeOutcome]) -> IndependenceProfile:
    variants = {c.method_variant for c in neg}
    impl_d, impl_i = _dimension_state(neg, "implementations")
    fam_d, fam_i = _dimension_state(neg, "model_families")
    task_d, task_i = _dimension_state(neg, "task_samples")
    eval_d, eval_i = _dimension_state(neg, "evaluators")
    incomplete = tuple(name for name, inc in (
        ("implementations", impl_i), ("model_families", fam_i),
        ("task_samples", task_i), ("evaluators", eval_i)) if inc)
    return IndependenceProfile(
        n_variants=len(variants), method_variants_distinct=len(variants) == len(neg),
        implementations_distinct=impl_d, model_families_distinct=fam_d,
        task_samples_independent=task_d, evaluator_independent=eval_d,
        shared_confounders=tuple(sorted(_shared_across_variants(neg, "confounders"))),
        incomplete_dimensions=incomplete)


@dataclass(frozen=True)
class AffinityScopeAttribution:
    target_id: str
    scope_id: str
    affinity: str
    n_variants_negative: int
    policy_id: str
    independent: bool
    strength: str                # "none" | "limited" | "supported"
    reason: str
    evidence: tuple[str, ...]


def attribute_to_affinity(outcomes: list[VariantScopeOutcome], *,
                          policy: IndependencePolicy = INDEPENDENCE_POLICY_V1
                          ) -> list[AffinityScopeAttribution]:
    """Roll variant-scope outcomes up to affinity-scope attributions. A limited/supported affinity
    statement is earned ONLY when ``policy`` is satisfied AND no success makes it inconsistent -
    never by a bare variant count."""
    by_key: dict[tuple[str, str, str], list[VariantScopeOutcome]] = {}
    for o in outcomes:
        for aff in o.affinities:
            by_key.setdefault((o.target_id, o.scope_id, aff), []).append(o)
    res: list[AffinityScopeAttribution] = []
    for (target, scope, aff), cells in sorted(by_key.items()):
        neg = [c for c in cells if c.outcome in ("no_benefit", "harmful") and c.protocol_valid]
        # ANY success/partial_success in the evidence (incl. inside a CONFLICTING cell) blocks a
        # negative affinity demotion - the picture is inconsistent, not negative.
        if any(c.has_success for c in cells):
            indep, strength = False, "none"
            why = "inconsistent: success evidence exists for this affinity"
        else:
            indep, why = policy.satisfied(_profile(neg)) if neg else (False, "no negative variants")
            if not indep:
                strength = "none"
            elif len({c.method_variant for c in neg}) >= max(policy.min_variants + 1, 3):
                strength = "supported"
            else:
                strength = "limited"
        res.append(AffinityScopeAttribution(
            target_id=target, scope_id=scope, affinity=aff,
            n_variants_negative=len({c.method_variant for c in neg}), policy_id=policy.policy_id,
            independent=indep, strength=strength, reason=why,
            evidence=tuple(t for c in cells for t in c.evidence)))
    return res
