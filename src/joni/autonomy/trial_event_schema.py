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
# the SEALED journal format: a v4 stored object MUST embed the stable evaluation envelope (with the
# composite capsule_hash). v3 events are legacy/unsealed and never produce verified evidence.
SCHEMA_VERSION_V4 = "method_trial_recorded_v4"
JOURNAL_SCHEMA_VERSION = SCHEMA_VERSION_V4
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

    def to_journal(self, registry=None) -> dict:
        """The canonical SEALED STORED form (v4): the body PLUS the embedded, stable evaluation
        envelope (with the mandatory whole-capsule ``capsule_hash``). Replay routes from the
        envelope, never from a live bridge."""
        return seal_payload(self.to_dict(), registry)


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
    decoder_hash: str = ""
    canonical_input_projection_hash: str = ""
    input_adapter_hash: str = ""
    exec_env_hash: str = ""
    capsule_hash: str = ""
    envelope_version: str = ""
    execution_environment: dict = field(default_factory=dict)
    input_contract: dict = field(default_factory=dict)   # descriptive only; the fn is the truth
    rule_fn: object = None
    rule_source: bytes | None = None        # byte-pinned rule source for ARCHIVED versions
    validator_fn: object = None
    validator_source: bytes | None = None   # byte-pinned SELF-CONTAINED validator for ARCHIVED
    contract_fn: object = None
    contract_source: bytes | None = None    # byte-pinned SELF-CONTAINED contract fn for ARCHIVED
    decoder_fn: object = None
    decoder_source: bytes | None = None     # byte-pinned input-decoder snapshot for ARCHIVED
    adapter_fn: object = None
    adapter_source: bytes | None = None     # byte-pinned input-adapter (blocks->view) for


RuleEntry = EvaluationArtifact                # backwards-compatible alias
EVALUATION_ENVELOPE_VERSION = "evaluation_envelope_v1"

_RULE_V2_DESCRIPTOR = ("rule_v2|source=measurement.ci|threshold=estimand.minimum_effect|"
                       "uncertainty_not_used|harmful:ci_hi<=-min|success:ci_lo>=min|"
                       "no_benefit:ci_within(-min,+min)|else:inconclusive")
RULE_V2_SPEC_HASH = "sha256:" + hashlib.sha256(_RULE_V2_DESCRIPTOR.encode()).hexdigest()
RULE_V2_IMPL_HASH = _impl_hash(_rule_v2)
RULE_V2_HASH = RULE_V2_IMPL_HASH


def _bytes_hash(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def _read_artifact(name: str) -> bytes:
    import pathlib
    return (pathlib.Path(__file__).parent / "rule_artifacts" / name).read_bytes()


# ================================================================================================ #
# PINNED LOADER + EXECUTION ENVIRONMENT - the byte-pinned sources are only meaningful together with
# the COMPILER SEMANTICS they were validated under. The loader is ITSELF a byte-pinned artifact
# (``loader_v1.pysrc``): it is re-hashed and BOOTSTRAPPED FROM ITS BYTES at every use, so replacing
# the live ``_exec_callable`` global cannot change what is executed. It takes NUMERIC future-flag
# bits + optimise as arguments (no mutable global flag table) and compiles with dont_inherit=True
# so execution never depends on the caller's __future__ flags. The loader + the FULL numeric
# execution environment (incl. python_semantics) are hashed and bound into the capsule.
# ================================================================================================ #
ARTIFACT_LOADER_VERSION = "artifact_loader_v1"
# numeric compiler flag VALUES (not just names) - part of the hashed execution contract.
_FUTURE_FLAG_BITS = {"annotations": __import__("__future__").annotations.compiler_flag}
_LOADER_SRC = _read_artifact("loader_v1.pysrc")
LOADER_HASH = _bytes_hash(_LOADER_SRC)


def _future_flag_bits(future_flags) -> int:
    """Sum the NUMERIC bits for the named flags. ``future_flags`` may be names or a {name: bits}
    mapping; an unknown name fails closed (KeyError) at load."""
    bits = 0
    for name in future_flags:
        bits |= _FUTURE_FLAG_BITS[name]
    return bits


def _bootstrap_loader(loader_src: bytes):
    """Materialise the byte-pinned loader FROM ITS BYTES (not the module global), so a swapped live
    loader cannot be the executed one. This tiny bootstrap is the irreducible trust root."""
    ns: dict = {}
    exec(compile(loader_src.decode("utf-8"), "<artifact:loader>", "exec"), ns)   # noqa: S102
    return ns["load_callable"]


def _python_semantics() -> str:
    import platform
    return ".".join(platform.python_version_tuple()[:2])


def _execution_environment(future_flags=("annotations",), optimize: int = 0) -> dict:
    """The pinned compiler/runtime contract under which a capsule's bytes are executed. Carries the
    NUMERIC flag values + python major.minor + the loader's byte hash."""
    bits = {name: _FUTURE_FLAG_BITS[name] for name in future_flags}
    return {"language": "python", "python_semantics": _python_semantics(),
            "future_flags": bits, "future_flag_bits": _future_flag_bits(future_flags),
            "optimize": optimize, "loader_version": ARTIFACT_LOADER_VERSION,
            "loader_hash": LOADER_HASH}


def _exec_env_hash(env: dict) -> str:
    # the ENTIRE binding contract - numeric flags, optimise, loader id+hash AND python_semantics
    # hashed; python_semantics is part of the capsule's meaning, not merely descriptive.
    binding = {k: env.get(k) for k in ("future_flags", "future_flag_bits", "optimize",
                                       "loader_version", "loader_hash", "python_semantics")}
    return _bytes_hash(_canonical_json_bytes(binding))


def _exec_callable(src: bytes, name: str, *, future_flags=("annotations",), optimize: int = 0):
    """Compatibility/test helper: load one callable via the byte-pinned loader bootstrapped from its
    bytes (so this function being patched does not change what production resolution executes)."""
    load = _bootstrap_loader(_LOADER_SRC)
    return load(src, name, _future_flag_bits(future_flags), optimize)


def _decode_v3(payload: dict):
    """The LIVE v3 input projection: the RAW canonical payload dict -> (measurement, decision,
    estimand) block dicts. Historical events use the artifact's OWN byte-pinned decoder; this is the
    current snapshot, kept byte-identical to ``rule_artifacts/decode_v3.pysrc``."""
    m = payload.get("measurement") or {}
    d = payload.get("decision") or {}
    e = payload.get("estimand") or {}
    m_ci = m.get("confidence_interval")
    d_ci = d.get("confidence_interval")
    meas = {"metric_name": m.get("metric_name"), "baseline_value": m.get("baseline_value"),
            "intervention_value": m.get("intervention_value"), "effect_size": m.get("effect_size"),
            "uncertainty": m.get("uncertainty"),
            "confidence_interval": tuple(m_ci) if m_ci is not None else None}
    dec = {"effect_size": d.get("effect_size"), "minimum_effect": d.get("minimum_effect"),
           "confidence_interval": tuple(d_ci) if d_ci is not None else None}
    est = {"outcome_metric": e.get("outcome_metric"), "contrast": e.get("contrast"),
           "direction": e.get("direction"), "minimum_effect": e.get("minimum_effect")}
    return meas, dec, est


def check_contract(measurement: dict, decision: dict, estimand: dict) -> list[str]:
    """The LIVE rule_v2 input contract (require effect + CI). Both the requirement AND its
    interpretation are in this function - so the contract's MEANING is hashed, not just its data.
    Historical events use the artifact's OWN byte-pinned contract; this is the current snapshot,
    kept byte-identical to ``rule_artifacts/contract_v2_r6.pysrc``."""
    errors: list[str] = []
    if measurement.get("effect_size") is None:
        errors.append("input contract requires measurement.effect_size")
    if measurement.get("confidence_interval") is None:
        errors.append("input contract requires measurement.confidence_interval")
    return errors


def build_view(meas: dict, dec: dict, est: dict):
    """The LIVE input adapter: turn the decoder's block dicts into the read-only view the rule
    consumes. Byte-pinned for archived versions (``view_adapter_v1.pysrc``) and bound by
    ``input_adapter_hash`` so no un-attested transform sits between decoder and rule."""
    from types import SimpleNamespace
    return SimpleNamespace(measurement=SimpleNamespace(**meas), decision=SimpleNamespace(**dec),
                           estimand=SimpleNamespace(**est))


def _canonical_json_bytes(d) -> bytes:
    import json
    return json.dumps(d, sort_keys=True, separators=(",", ":"), default=list).encode("utf-8")


ENVELOPE_KEY = "evaluation_envelope"        # the epistemic (rule-evaluable) seal
OPERATIONAL_ENVELOPE_KEY = "operational_envelope"   # the operational (not-evaluated) seal
_ENVELOPE_KEYS = (ENVELOPE_KEY, OPERATIONAL_ENVELOPE_KEY)
OPERATIONAL_ENVELOPE_VERSION = "operational_envelope_v1"


def evaluation_body_hash(payload: dict) -> str:
    """Hash of the EVALUATION BODY (the payload EXCLUDING any embedded envelope), using the SAME
    canonicalisation as the Layer-9 gate, so the gate and the evaluator agree on the binding. NB:
    this is a DIFFERENT scope from the kernel's ``payload_hash`` (which covers the whole stored
    object including the envelope) - hence the distinct name ``evaluation_body_hash``."""
    from desi_layer9.trial_event_validation import canonical_payload
    body = {k: v for k, v in payload.items() if k not in _ENVELOPE_KEYS}
    return _bytes_hash(canonical_payload(body).encode("utf-8"))


def _split_journal(stored: dict) -> tuple[dict | None, dict]:
    """Split a stored journal object into (epistemic evaluation envelope or None, payload body)."""
    env = stored.get(ENVELOPE_KEY)
    body = {k: v for k, v in stored.items() if k not in _ENVELOPE_KEYS}
    return env, body


def _projection_schema_hash(meas: dict, dec: dict, est: dict) -> str:
    """Hash of the KEY-SCHEMA a decoder emits (not the values). Re-derived from the actual decode at
    use, so a decoder that emits a different input shape than the artifact declares is rejected."""
    schema = {"measurement": sorted(meas), "decision": sorted(dec), "estimand": sorted(est)}
    return _bytes_hash(_canonical_json_bytes(schema))


# a value-free probe PAYLOAD used ONLY to derive the key-schema a decoder produces at build time.
_PROJECTION_PROBE_PAYLOAD = {"measurement": {}, "decision": {}, "estimand": {}}


def _projection_hash_of(decoder_fn) -> str:
    return _projection_schema_hash(*decoder_fn(_PROJECTION_PROBE_PAYLOAD))


def _capsule_hash(*, rule_hash, validator_hash, contract_hash, decoder_hash, projection_hash,
                  adapter_hash, exec_env_hash, schema_version, envelope_version) -> str:
    """A single composite hash over EVERY causally-relevant component + the routing/loader contract.
    Uniquely addresses the WHOLE evaluation capsule, so the same rule_hash under a different
    validator/decoder/adapter/loader is a DIFFERENT capsule."""
    parts = {"rule": rule_hash, "validator": validator_hash, "contract": contract_hash,
             "decoder": decoder_hash, "projection": projection_hash, "input_adapter": adapter_hash,
             "exec_env": exec_env_hash, "schema_version": schema_version,
             "envelope_version": envelope_version}
    return _bytes_hash(_canonical_json_bytes(parts))


def make_live_artifact(rule_id, schema_version, rule_fn, validator_fn, contract_fn,
                       decoder_fn=_decode_v3, adapter_fn=build_view):
    """An artifact bound to LIVE functions; every hash tracks the current source. Decoder, contract,
    validator, rule AND the input-adapter (blocks -> view) are bound, together with the loader /
    execution-environment, into one ``capsule_hash``."""
    env = _execution_environment()
    eh = _exec_env_hash(env)
    proj = _projection_hash_of(decoder_fn)
    rh, vh, ch, dh, ah = (_impl_hash(rule_fn), _impl_hash(validator_fn), _impl_hash(contract_fn),
                          _impl_hash(decoder_fn), _impl_hash(adapter_fn))
    return EvaluationArtifact(
        rule_id, schema_version, implementation_hash=rh, validator_hash=vh, input_contract_hash=ch,
        decoder_hash=dh, canonical_input_projection_hash=proj, input_adapter_hash=ah,
        exec_env_hash=eh, envelope_version=EVALUATION_ENVELOPE_VERSION, execution_environment=env,
        capsule_hash=_capsule_hash(
            rule_hash=rh, validator_hash=vh, contract_hash=ch, decoder_hash=dh,
                                   projection_hash=proj, adapter_hash=ah, exec_env_hash=eh,
                                   schema_version=schema_version,
                                   envelope_version=EVALUATION_ENVELOPE_VERSION),
        rule_fn=rule_fn, validator_fn=validator_fn, contract_fn=contract_fn, decoder_fn=decoder_fn,
        adapter_fn=adapter_fn)


def make_archived_artifact(rule_id, schema_version, rule_src, validator_src, contract_src,
                           decoder_src=None, adapter_src=None, *, expected_rule_hash=None):
    """An artifact whose decoder + contract + validator + rule + input-adapter are ALL BYTE-PINNED,
    SELF-CONTAINED verbatim source, executed under a pinned loader/execution-environment. The
    implementation hash is the sha256 of the stored rule bytes - the REAL historical hash, not one
    recomputed from a later copy. A pinned ``expected_rule_hash`` is enforced. ``decoder_src`` /
    ``adapter_src`` default to the v3 snapshots."""
    rh = _bytes_hash(rule_src)
    if expected_rule_hash is not None and rh != expected_rule_hash:
        raise ValueError(f"archived rule artifact hash {rh} != expected {expected_rule_hash}")
    dsrc = _DECODE_V3_SRC if decoder_src is None else decoder_src
    asrc = _VIEW_ADAPTER_SRC if adapter_src is None else adapter_src
    env = _execution_environment()
    eh = _exec_env_hash(env)
    decoder_fn = _exec_callable(dsrc, "_decode_v3")
    proj = _projection_hash_of(decoder_fn)
    vh, ch, dh, ah = (_bytes_hash(validator_src), _bytes_hash(contract_src), _bytes_hash(dsrc),
                      _bytes_hash(asrc))
    return EvaluationArtifact(
        rule_id, schema_version, implementation_hash=rh, validator_hash=vh, input_contract_hash=ch,
        decoder_hash=dh, canonical_input_projection_hash=proj, input_adapter_hash=ah,
        exec_env_hash=eh, envelope_version=EVALUATION_ENVELOPE_VERSION, execution_environment=env,
        capsule_hash=_capsule_hash(
            rule_hash=rh, validator_hash=vh, contract_hash=ch, decoder_hash=dh,
                                   projection_hash=proj, adapter_hash=ah, exec_env_hash=eh,
                                   schema_version=schema_version,
                                   envelope_version=EVALUATION_ENVELOPE_VERSION),
        rule_source=rule_src, validator_source=validator_src, contract_source=contract_src,
        decoder_source=dsrc, adapter_source=asrc)


def make_rule_entry(rule_id: str, spec_hash: str, fn) -> EvaluationArtifact:
    """Compatibility shim: a LIVE artifact whose implementation_hash is COMPUTED from ``fn`` and
    which binds the current validator + contract + decoder."""
    from desi_layer9.trial_event_validation import cross_block_consistency
    return make_live_artifact(rule_id, JOURNAL_SCHEMA_VERSION, fn, cross_block_consistency,
                              check_contract)


def build_rule_registry(artifacts):
    """An APPEND-ONLY, immutable catalog keyed by the composite ``capsule_hash`` - so two capsules
    with the SAME rule (same rule_hash) but a different validator/contract/decoder/loader/exec-env
    coexist without hash tricks. A capsule_hash may never be overwritten."""
    reg: dict = {}
    for a in artifacts:
        if a.capsule_hash in reg:
            raise ValueError(f"rule registry is append-only; capsule {a.capsule_hash} is already "
                             "registered")
        reg[a.capsule_hash] = a
    return MappingProxyType(reg)


def _resolve_capsule_hash(registry, rule_id: str, rule_hash: str) -> str | None:
    """Find the capsule_hash whose artifact has this (rule_id, rule_hash). Used WRITER-side to
    new event; ambiguity (two capsules share the rule) is an explicit error - the writer must then
    name the capsule_hash directly."""
    hits = [a.capsule_hash for a in registry.values()
            if a.rule_id == rule_id and a.implementation_hash == rule_hash]
    if len(hits) > 1:
        raise ValueError(f"rule '{rule_id}'@'{rule_hash}' maps to multiple capsules; name the "
                         "capsule_hash explicitly")
    return hits[0] if hits else None


# THE PRODUCTION CATALOG - append-only, immutable, byte-pinned. The archived r6 rule is loaded from
# its VERBATIM historical source (its hash is the REAL prior-release hash), together with byte-
# pinned snapshots of the decoder, contract and validator it ran under; the current rule is live.
_R6_RULE_SRC = _read_artifact("rule_v2_r6.pysrc")
_CROSS_BLOCK_V1_SRC = _read_artifact("cross_block_v1.pysrc")
_DECODE_V3_SRC = _read_artifact("decode_v3.pysrc")
_R6_CONTRACT_SRC = _read_artifact("contract_v2_r6.pysrc")
_VIEW_ADAPTER_SRC = _read_artifact("view_adapter_v1.pysrc")
_RULE_V2_V2_SRC = _read_artifact("rule_v2_v2.pysrc")   # current rule, byte-pinned (no wrapper)
RULE_V2_R6_HASH = _bytes_hash(_R6_RULE_SRC)             # the real historical hash (2438455f...)


def _default_registry():
    # BOTH production capsules are ARCHIVED, byte-pinned and SELF-CONTAINED - no live wrapper that
    # could dynamically import (and thus fail to bind) the current validator/contract/decoder.
    return build_rule_registry([
        make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _R6_RULE_SRC, _CROSS_BLOCK_V1_SRC,
                               _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                               expected_rule_hash=RULE_V2_R6_HASH),
        make_archived_artifact("rule_v2", JOURNAL_SCHEMA_VERSION, _RULE_V2_V2_SRC,
                               _CROSS_BLOCK_V1_SRC, _R6_CONTRACT_SRC, _DECODE_V3_SRC,
                               expected_rule_hash=RULE_V2_HASH),
    ])


DEFAULT_RULE_REGISTRY = _default_registry()


def _live_cross_block(measurement, decision, estimand, *, is_real, has_effect_derivation=False):
    """Thin live wrapper over the current gate validator - used ONLY by tests/make_rule_entry, NEVER
    by the production catalog (which is fully byte-pinned and self-contained)."""
    from desi_layer9.trial_event_validation import cross_block_consistency
    return cross_block_consistency(measurement, decision, estimand, is_real=is_real,
                                   has_effect_derivation=has_effect_derivation)


def _blocks(ev: MethodTrialRecorded):
    """The CURRENT (live) input projection from a LIVE event (used by the gate path and tests)."""
    return _decode_v3(ev.to_dict())


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
    contract_fn: object
    contract_hash: str
    adapter_fn: object
    adapter_hash: str
    exec_env_hash: str
    capsule_hash: str


class _LoaderError(Exception):
    """Raised when the pinned loader / execution-environment cannot be trusted (fail-closed)."""


def _trusted_loader(art: EvaluationArtifact):
    """Re-attest the execution environment and return the loader BOOTSTRAPPED FROM ITS BYTES. The
    actually-executed loader's hash is re-derived and checked against the artifact's claim (a
    live loader cannot be the one executed), python major.minor must match, and the whole numeric
    exec-env hash must match - before any artifact byte is executed."""
    env = art.execution_environment or {}
    if _bytes_hash(_LOADER_SRC) != env.get("loader_hash"):
        raise _LoaderError("loader hash does not match the executed loader bytes")
    if env.get("python_semantics") != _python_semantics():
        raise _LoaderError(f"python semantics {env.get('python_semantics')!r} != runtime "
                           f"{_python_semantics()!r}")
    if _exec_env_hash(env) != art.exec_env_hash:
        raise _LoaderError("execution-environment hash does not match the re-derived environment")
    bits = env.get("future_flag_bits")
    if bits is None:
        bits = _future_flag_bits(env.get("future_flags", ("annotations",)))
    opt = int(env.get("optimize", 0))
    load = _bootstrap_loader(_LOADER_SRC)
    return (lambda src, name: load(src, name, bits, opt)), _exec_env_hash(env)


def _resolve_artifact(art: EvaluationArtifact) -> _Resolved:
    """Materialise an artifact and RE-DERIVE every hash from the actual (byte-pinned for archived,
    live for current) component, so claimed metadata can never attest different executed code. The
    byte-pinned components are SELF-CONTAINED and are compiled by the re-attested, byte-bootstrapped
    PINNED loader under the artifact's own (re-checked) execution-environment."""
    _exec, exec_env_hash = _trusted_loader(art)
    if art.rule_source is not None:
        rule_hash, rule_fn = _bytes_hash(art.rule_source), _exec(art.rule_source, "_rule_v2")
    else:
        rule_hash, rule_fn = _impl_hash(art.rule_fn), art.rule_fn
    if art.validator_source is not None:
        validator_hash = _bytes_hash(art.validator_source)
        validator_fn = _exec(art.validator_source, "cross_block_consistency")
    else:
        validator_hash, validator_fn = _impl_hash(art.validator_fn), art.validator_fn
    if art.decoder_source is not None:
        decoder_hash, decoder_fn = _bytes_hash(art.decoder_source), _exec(art.decoder_source,
                                                                          "_decode_v3")
    else:
        decoder_hash, decoder_fn = _impl_hash(art.decoder_fn), art.decoder_fn
    if art.contract_source is not None:
        contract_hash, contract_fn = _bytes_hash(art.contract_source), _exec(art.contract_source,
                                                                             "check_contract")
    else:
        contract_hash, contract_fn = _impl_hash(art.contract_fn), art.contract_fn
    if art.adapter_source is not None:
        adapter_hash, adapter_fn = _bytes_hash(art.adapter_source), _exec(art.adapter_source,
                                                                          "build_view")
    else:
        adapter_hash, adapter_fn = _impl_hash(art.adapter_fn), art.adapter_fn
    proj = _projection_hash_of(decoder_fn)
    capsule = _capsule_hash(
        rule_hash=rule_hash, validator_hash=validator_hash, contract_hash=contract_hash,
        decoder_hash=decoder_hash, projection_hash=proj, adapter_hash=adapter_hash,
        exec_env_hash=exec_env_hash, schema_version=art.schema_version,
        envelope_version=art.envelope_version)
    return _Resolved(rule_fn, rule_hash, validator_fn, validator_hash, decoder_fn, decoder_hash,
                     contract_fn, contract_hash, adapter_fn, adapter_hash, exec_env_hash, capsule)


def evaluate_envelope(envelope: dict, payload: dict, registry=None) -> dict:
    """THE canonical evaluation entry. Routing comes from a STABLE ``evaluation_envelope``: it
    addresses the WHOLE capsule by the MANDATORY ``capsule_hash`` (rule_id/rule_hash are
    cross-checks only); the payload BODY is bound by ``evaluation_body_hash``. Then the artifact's
    OWN re-attested loader compiles its OWN byte-pinned decoder -> contract -> validator ->
    input-adapter -> rule. EVERY component hash (incl. adapter, exec-env and the composite capsule)
    is re-derived and checked. ``status`` in {"verified", "inconsistent", "unverifiable",
    "not_applicable"}."""
    reg = DEFAULT_RULE_REGISTRY if registry is None else registry
    if envelope.get("envelope_version") != EVALUATION_ENVELOPE_VERSION:
        return {"status": "unverifiable",
                "reason": f"unknown evaluation envelope version "
                          f"{envelope.get('envelope_version')!r} - fail-closed routing"}
    rule_id, rule_hash_claim = envelope.get("rule_id"), envelope.get("rule_hash")
    claimed_verdict, schema_claim = envelope.get("claimed_verdict"), envelope.get("schema_version")
    capsule_claim = envelope.get("capsule_hash")
    if claimed_verdict not in RULE_EVALUABLE_RESULTS:
        return {"status": "not_applicable", "reason": "no rule-evaluable verdict (not_evaluated)"}
    # the capsule_hash is the MANDATORY routing key - it addresses the whole evaluator, not just a
    # rule. A missing/unknown capsule_hash fails closed.
    if not capsule_claim:
        return {"status": "unverifiable",
                "reason": "envelope carries no capsule_hash - the whole-capsule address is "
                          "mandatory; fail-closed routing"}
    # the BODY is bound to the envelope - it cannot be swapped under the same routing.
    if envelope.get("evaluation_body_hash") != evaluation_body_hash(payload):
        return {"status": "unverifiable",
                "reason": "evaluation_body_hash does not match the payload body - envelope/payload "
                          "binding broken"}
    art = reg.get(capsule_claim)
    if art is None:
        # the write-gate accepts any syntactically-sealed v4 (the kernel must not depend on this
        # catalog); a well-formed seal whose capsule is unknown HERE is marked distinctly and is
        # NEVER treated as a regular verdict (verify_payloads skips it; only "verified" aggregates).
        return {"status": "sealed_unknown_capsule",
                "reason": f"capsule '{capsule_claim}' is sealed but not in this registered catalog "
                          "- never treated as a verified verdict"}
    if schema_claim != art.schema_version:
        return {"status": "unverifiable",
                "reason": f"envelope schema '{schema_claim}' != artifact schema "
                          f"'{art.schema_version}' - the capsule does not decode this schema"}
    try:
        r = _resolve_artifact(art)
    except Exception as exc:  # noqa: BLE001
        return {"status": "unverifiable", "reason": f"artifact could not be resolved ({exc!r})"}
    # every component hash (and the composite capsule) must match BEFORE its code is trusted. The
    # capsule_hash claimed in the ENVELOPE must equal the re-derived one AND the artifact's.
    checks = [
        ("implementation_hash", r.rule_hash, art.implementation_hash),
        ("rule transparency", r.rule_hash, rule_hash_claim),
        ("validator_hash", r.validator_hash, art.validator_hash),
        ("decoder_hash", r.decoder_hash, art.decoder_hash),
        ("input_contract_hash", r.contract_hash, art.input_contract_hash),
        ("input_adapter_hash", r.adapter_hash, art.input_adapter_hash),
        ("exec_env_hash", r.exec_env_hash, art.exec_env_hash),
        ("capsule_hash", r.capsule_hash, art.capsule_hash),
        ("envelope capsule_hash", r.capsule_hash, capsule_claim),
        ("rule_id transparency", art.rule_id, rule_id),
    ]
    for name, derived, claimed in checks:
        if derived is None or derived != claimed:
            return {"status": "unverifiable",
                    "reason": f"artifact {name} does not match the re-derived component "
                              f"({derived} != {claimed}) - no trustworthy verdict"}
    # the artifact's OWN decoder is the first deserialisation step (on the payload); schema check.
    meas, dec, est = r.decoder_fn(payload)
    proj = _projection_schema_hash(meas, dec, est)
    if proj != art.canonical_input_projection_hash:
        return {"status": "unverifiable",
                "reason": f"decoder produced an unexpected input projection ({proj} != "
                          f"{art.canonical_input_projection_hash}) - no trustworthy verdict"}
    cerr = r.contract_fn(meas, dec, est)                # the artifact's OWN contract interpreter
    if cerr:
        return {"status": "inconsistent", "reason": "; ".join(cerr)}
    xb = r.validator_fn(meas, dec, est, is_real=True)   # the artifact's OWN validator
    if xb:
        return {"status": "inconsistent", "reason": "; ".join(xb)}
    # the rule decides PURELY from the view the artifact's OWN byte-pinned adapter builds out of the
    # decoder output - no un-attested transform sits between decoder and rule.
    computed = r.rule_fn(r.adapter_fn(meas, dec, est))
    if computed != claimed_verdict:
        return {"status": "inconsistent", "computed": computed, "claimed": claimed_verdict,
                "reason": f"rule computes '{computed}' from the measurement, envelope claims "
                          f"'{claimed_verdict}'"}
    return {"status": "verified", "computed": computed}


def envelope_for_payload(payload: dict, capsule_hash: str, registry=None) -> dict:
    """WRITER-SIDE helper: build the EPISTEMIC evaluation envelope to be STORED with the body. It
    pins the whole-capsule address (``capsule_hash``, mandatory) and the body binding
    (``evaluation_body_hash``). NOT used in replay - replay reads the stored envelope."""
    body = {k: v for k, v in payload.items() if k not in _ENVELOPE_KEYS}
    d = body.get("decision") or {}
    return {"envelope_version": EVALUATION_ENVELOPE_VERSION,
            "schema_version": body.get("schema_version"),
            "rule_id": d.get("decision_rule_id"), "rule_hash": d.get("decision_rule_hash"),
            "capsule_hash": capsule_hash, "claimed_verdict": d.get("verdict"),
            "evaluation_body_hash": evaluation_body_hash(body)}


def operational_envelope_for(payload: dict) -> dict:
    """WRITER-SIDE helper: build the OPERATIONAL envelope for a not-evaluated/technical event. It
    carries NO capsule (there is no decision rule), only the classified operational state and the
    body binding - so an operational move is sealed and stored without inventing a rule."""
    body = {k: v for k, v in payload.items() if k not in _ENVELOPE_KEYS}
    return {"envelope_version": OPERATIONAL_ENVELOPE_VERSION,
            "schema_version": body.get("schema_version"),
            "operational_class": _operational_class(body),
            "evaluation_body_hash": evaluation_body_hash(body)}


def seal_payload(payload: dict, registry=None) -> dict:
    """Seal a v3-style body into a v4 STORED journal object. A rule-evaluable event (a resolvable
    capsule for its decision rule) gets the EPISTEMIC envelope; a not-evaluated/operational event
    gets the OPERATIONAL envelope - so ``to_journal`` ALWAYS produces a v4 the gate accepts (it
    never emits a capsule_hash=null epistemic seal). WRITER-side."""
    reg = DEFAULT_RULE_REGISTRY if registry is None else registry
    body = {k: v for k, v in payload.items() if k not in _ENVELOPE_KEYS}
    body["schema_version"] = JOURNAL_SCHEMA_VERSION
    d = body.get("decision") or {}
    if body.get('epistemic_result') in RULE_EVALUABLE_RESULTS:    # claims a verdict -> EPISTEMIC
        ch = _resolve_capsule_hash(reg, d.get("decision_rule_id"), d.get("decision_rule_hash"))
        return {**body, ENVELOPE_KEY: envelope_for_payload(body, ch, reg)}
    return {**body, OPERATIONAL_ENVELOPE_KEY: operational_envelope_for(body)}   # not_evaluated


# ================================================================================================ #
# JOURNAL MIGRATION - a VERSIONED, fail-closed loader for historical v3 journals, bound to a PINNED
# ALLOWLIST of historical attestations.
#   The kernel write-boundary is deterministic (only sealed v4 is writable), so an old v3
#   METHOD_TRIAL_RECORDED entry is NOT raw-replayable. Backward COMPATIBILITY is an explicit
#   MIGRATION that re-seals each historically-ACCEPTED v3 trial body to v4 (the body verbatim) under
#   its KNOWN capsule, BEFORE replay. It introduces NO submit privilege.
#
#   TRUST MODEL (honest naming). The trust source is a PINNED, internal, immutable ALLOWLIST of
#   historical attestation DIGESTS (``_TRUSTED_HISTORICAL_ATTESTATIONS``), NOT a self-declared field
#   in the untrusted input document and NOT a caller-supplied function. ``attestation_digest`` is
#   a sha256 over the canonical attestation body - it is a PINNED DIGEST, **not a cryptographic
#   signature**: trust derives solely from that digest being allowlisted in the catalog. (A
#   deployment that ingests EXTERNAL historical artifacts must additionally verify a real signature
#   against a pinned public key, or ship the historical kernel/policy artifacts + a hash manifest.)
#
#   A document carries a ``historical_attestation`` whose ``verifier_id`` SELECTS a catalog entry;
#   migration then checks, fail-closed:
#     (1) the attestation is byte-identical to the pinned, allowlisted anchor (its
#         ``attestation_digest`` recomputes from the body AND equals the pinned digest);
#     (2) the attestation BINDS the DELIVERED DOCUMENT CONTENT: ``source_journal_hash`` equals the
#         canonical hash of the document's FULL journal (not just a copied snapshot string), and
#         ``source_snapshot_hash`` equals ``doc.snapshot_hash`` (never silently ignored);
#     (3) each migrated v3 trial entry's FULL canonical JournalEntry hash (operator, proposal_type,
#         payload, proposer, provenance, target_objects, actor, governance_approved, reason, tick)
#         in ``accepted_full_entry_hashes`` - so the actor/provenance/governance metadata of the
#         historical command are attested, not just the trial body;
#     (4) the cited rule resolves to a KNOWN capsule.
#   PRODUCTION DEFAULT: the catalog is EMPTY, so NO v3 trial document is migratable (fail-closed). A
#   deployment installs real, signed historical attestations; tests/dev inject an explicit catalog
#   via ``trusted_attestations=``. The demonstrator anchor lives in the tests, never in production.
# ================================================================================================ #
JOURNAL_MIGRATION_VERSION = "trial_event_journal_migration_v3"
_TRIAL_OPERATOR_VALUE = "method_trial_recorded"
HISTORICAL_ATTESTATION_KEY = "historical_attestation"
_ATTESTATION_BODY_FIELDS = ("verifier_id", "kernel_release", "gate_policy_version",
                            "historical_kernel_artifact_hash", "gate_policy_artifact_hash",
                            "source_document_hash", "source_journal_hash", "source_snapshot_hash",
                            "accepted_full_entry_hashes")
_FULL_ENTRY_FIELDS = ("operator", "proposal_type", "payload", "proposer", "provenance",
                      "target_objects", "actor", "governance_approved", "reason", "tick")


class JournalMigrationError(Exception):
    """A historical v3 trial entry cannot be migrated trustworthily (fail-closed)."""


def _entry_canon(entry: dict) -> dict:
    """The canonical, normalised form of a FULL persisted JournalEntry (every field that becomes
    authoritative on replay), so an attestation binds the actor/provenance/governance metadata - not
    just the trial body."""
    return {
        "operator": entry.get("operator"),
        "proposal_type": entry.get("proposal_type"),
        "payload": entry.get("payload") or {},
        "proposer": entry.get("proposer"),
        "provenance": entry.get("provenance") or {},
        "target_objects": list(entry.get("target_objects") or []),
        "actor": entry.get("actor"),
        "governance_approved": bool(entry.get("governance_approved")),
        "reason": entry.get("reason", ""),
        "tick": int(entry.get("tick", 0)),
    }


def _full_entry_hash(entry: dict) -> str:
    """The canonical hash of a FULL persisted JournalEntry - the unit an attestation lists."""
    return _bytes_hash(_canonical_json_bytes(_entry_canon(entry)))


def _journal_hash(journal: list) -> str:
    """The canonical hash of a FULL journal (list of full canonical entries) - binds the delivered
    document content, so changing ANY entry field (or adding/removing entries) breaks it."""
    return _bytes_hash(_canonical_json_bytes([_entry_canon(e) for e in journal]))


def _attestation_digest(att: dict) -> str:
    """sha256 over the canonical attestation BODY (excludes the digest field). A PINNED DIGEST, NOT
    a signature: a caller cannot forge it for a different body, but its TRUST comes only from being
    allowlisted in the catalog."""
    body = {k: att.get(k) for k in _ATTESTATION_BODY_FIELDS}
    body["accepted_full_entry_hashes"] = sorted(body.get("accepted_full_entry_hashes") or [])
    return _bytes_hash(_canonical_json_bytes(body))


def build_historical_attestation(*, verifier_id: str, kernel_release: str, gate_policy_version: str,
                                 historical_kernel_artifact_hash: str,
                                 gate_policy_artifact_hash: str, source_document_hash: str,
                                 source_journal_hash: str, source_snapshot_hash: str,
                                 accepted_full_entry_hashes: list[str]) -> dict:
    """Construct a historical attestation with its self-consistent ``attestation_digest``. Building
    one does NOT make it trusted: only an attestation whose digest is allowlisted in a catalog (and,
    for external artifacts, signature-verified) is trusted."""
    att = {"verifier_id": verifier_id, "kernel_release": kernel_release,
           "gate_policy_version": gate_policy_version,
           "historical_kernel_artifact_hash": historical_kernel_artifact_hash,
           "gate_policy_artifact_hash": gate_policy_artifact_hash,
           "source_document_hash": source_document_hash, "source_journal_hash": source_journal_hash,
           "source_snapshot_hash": source_snapshot_hash,
           "accepted_full_entry_hashes": sorted(accepted_full_entry_hashes)}
    att["attestation_digest"] = _attestation_digest(att)
    return att


# PRODUCTION DEFAULT: an EMPTY allowlist - no historical v3 trial document is migratable. A
# deployment installs real signed attestations; tests/dev pass an explicit ``trusted_attestations``.
_TRUSTED_HISTORICAL_ATTESTATIONS = MappingProxyType({})


def _document_hash(doc: dict) -> str:
    """Canonical hash of the delivered document's migration-relevant content (journal + snapshot +
    tick), so the attestation binds the actual bytes delivered, not just a copied selector."""
    canon = {"journal": [_entry_canon(e) for e in doc.get("journal", [])],
             "snapshot_hash": doc.get("snapshot_hash"), "tick": int(doc.get("tick", 0))}
    return _bytes_hash(_canonical_json_bytes(canon))


def _resolve_attestation(doc: dict, trusted) -> tuple[dict, set]:
    """Resolve the document's ``historical_attestation`` against the PINNED allowlist and bind it to
    the DELIVERED document. Returns ``(attestation, accepted_full_entry_hashes)`` or raises
    ``JournalMigrationError`` (fail-closed). The caller supplies NO executable - only a verifier_id
    inside the document, and (out of band) the trusted allowlist."""
    att = doc.get(HISTORICAL_ATTESTATION_KEY)
    if not isinstance(att, dict):
        raise JournalMigrationError(
            "no historical_attestation present - a historical v3 trial journal needs an "
            "attestation from the pinned allowlist (fail-closed)")
    pinned = trusted.get(att.get("verifier_id"))
    if pinned is None:
        raise JournalMigrationError(
            f"unknown verifier_id '{att.get('verifier_id')}' - not in the pinned historical "
            "allowlist (fail-closed; the caller cannot bring its own verifier)")
    if _attestation_digest(att) != att.get("attestation_digest"):
        raise JournalMigrationError("attestation_digest does not match its body (forged?)")
    if att.get("attestation_digest") != pinned["attestation_digest"]:
        raise JournalMigrationError(
            "attestation is not the pinned, allowlisted anchor for this verifier_id (fail-closed)")
    # bind the DELIVERED document content (not just a copied snapshot string).
    if att.get("source_journal_hash") != _journal_hash(doc.get("journal", [])):
        raise JournalMigrationError(
            "attestation.source_journal_hash does not match the delivered journal's content "
            "(fail-closed; the journal was altered or is not the attested historical journal)")
    if att.get("source_document_hash") != _document_hash(doc):
        raise JournalMigrationError(
            "attestation.source_document_hash does not match the delivered document (fail-closed)")
    if att.get("source_snapshot_hash") != doc.get("snapshot_hash"):
        raise JournalMigrationError(
            "attestation.source_snapshot_hash does not bind the document's snapshot_hash "
            "(fail-closed; a present snapshot_hash is never ignored)")
    if (att.get("kernel_release") != pinned["kernel_release"]
            or att.get("gate_policy_version") != pinned["gate_policy_version"]):
        raise JournalMigrationError("attestation kernel_release/gate_policy_version mismatch")
    return att, set(att.get("accepted_full_entry_hashes") or [])


def migrate_journal_entries(entries: list[dict], registry=None, *,
                            accepted_full_entry_hashes=None) -> tuple[list[dict], list[dict]]:
    """Migrate persisted journal-entry dicts. A historical v3 METHOD_TRIAL_RECORDED entry becomes a
    SEALED v4 entry (body verbatim) ONLY IF its FULL canonical JournalEntry hash is in
    ``accepted_full_entry_hashes`` (the set ``load_migrated`` resolves from the pinned allowlist)
    AND it resolves to a KNOWN capsule. Returns FULLY DEEP-COPIED ``(migrated, log)`` (no aliasing).
    Fail-closed: a v3 trial whose FULL entry (actor/provenance/governance/tick included) is NOT in
    the attested set (a caller cannot self-declare acceptance, nor swap the actor/provenance of an
    attested body), or an unknown capsule, raises. Non-trial / already-v4 entries pass through
    (deep-copied). Introduces NO submit privilege."""
    import copy
    reg = DEFAULT_RULE_REGISTRY if registry is None else registry
    accepted = set(accepted_full_entry_hashes or [])
    out: list[dict] = []
    log: list[dict] = []
    for e in entries:
        payload = e.get("payload") or {}
        is_v3_trial = (e.get("operator") == _TRIAL_OPERATOR_VALUE
                       and payload.get("schema_version") == SCHEMA_VERSION)
        if not is_v3_trial:
            out.append(copy.deepcopy(e))                 # pass through, fully independent
            continue
        entry_hash = _full_entry_hash(e)
        if entry_hash not in accepted:
            raise JournalMigrationError(
                f"v3 trial '{payload.get('trial_id')}' (full entry) is not in the attested "
                "accepted set - fail-closed (its actor/provenance/governance/tick are bound too)")
        d = payload.get("decision") or {}
        if payload.get("epistemic_result") in RULE_EVALUABLE_RESULTS:
            ch = _resolve_capsule_hash(reg, d.get("decision_rule_id"), d.get("decision_rule_hash"))
            if ch is None:
                raise JournalMigrationError(
                    f"v3 trial '{payload.get('trial_id')}' cites rule "
                    f"'{d.get('decision_rule_id')}'@'{d.get('decision_rule_hash')}' with no known "
                    "capsule - fail-closed (cannot migrate to a trustworthy v4 seal)")
        sealed = copy.deepcopy(seal_payload(copy.deepcopy(payload), reg))
        migrated = {k: copy.deepcopy(v) for k, v in e.items()
                    if k != HISTORICAL_ATTESTATION_KEY}
        migrated["payload"] = sealed
        out.append(migrated)
        log.append({"migration": JOURNAL_MIGRATION_VERSION, "trial_id": payload.get("trial_id"),
                    "from": SCHEMA_VERSION, "to": JOURNAL_SCHEMA_VERSION,
                    "attested_full_entry_hash": entry_hash,
                    "capsule_hash": sealed.get(ENVELOPE_KEY, {}).get("capsule_hash"),
                    "seal": ENVELOPE_KEY if ENVELOPE_KEY in sealed else OPERATIONAL_ENVELOPE_KEY})
    return out, log


def load_migrated(doc: dict, registry=None, *, trusted_attestations=None):
    """Load a persisted Layer-9 document, MIGRATING allowlisted historical v3 trial entries to
    sealed v4, then replaying. The trust source is a PINNED allowlist (``trusted_attestations``,
    defaulting to the EMPTY production catalog ``_TRUSTED_HISTORICAL_ATTESTATIONS``), resolved from
    the document's ``historical_attestation.verifier_id`` - the caller supplies NO executable
    verifier. Fail-closed: a v3 trial journal with no/forged/unpinned attestation, an attestation
    that does not bind the delivered document content (journal hash / document hash / snapshot_hash)
    or whose full entries are not attested, an unknown verifier, or an unknown capsule, all raise. A
    document without v3 trials still has its ``snapshot_hash`` checked against the replayed state.
    The reconstructed state is the UPGRADED (v4) state (the BODY verbatim). Returns
    ``(core, migration_log)``."""
    from desi_layer9 import JournalEntry, persistence
    from desi_layer9.hashing import snapshot_hash
    trusted = (_TRUSTED_HISTORICAL_ATTESTATIONS if trusted_attestations is None
               else trusted_attestations)
    journal = doc.get("journal", [])
    has_v3_trial = any(e.get("operator") == _TRIAL_OPERATOR_VALUE
                       and (e.get("payload") or {}).get("schema_version") == SCHEMA_VERSION
                       for e in journal)
    log: list[dict] = []
    accepted = None
    if has_v3_trial:
        att, accepted = _resolve_attestation(doc, trusted)
        log.append({"migration": JOURNAL_MIGRATION_VERSION, "attestation": {
            "verifier_id": att["verifier_id"], "kernel_release": att["kernel_release"],
            "gate_policy_version": att["gate_policy_version"],
            "historical_kernel_artifact_hash": att.get("historical_kernel_artifact_hash"),
            "gate_policy_artifact_hash": att.get("gate_policy_artifact_hash"),
            "source_document_hash": att.get("source_document_hash"),
            "source_journal_hash": att.get("source_journal_hash"),
            "source_snapshot_hash": att["source_snapshot_hash"],
            "attestation_digest": att["attestation_digest"],
            "accepted_full_entry_hashes": sorted(accepted)}})
    migrated, mlog = migrate_journal_entries(journal, registry,
                                             accepted_full_entry_hashes=accepted)
    log.extend(mlog)
    core = persistence.replay([JournalEntry.from_dict(e) for e in migrated],
                              tick=int(doc.get("tick", 0)))
    # a non-migrated document still never silently ignores its snapshot_hash.
    if (not has_v3_trial and doc.get("snapshot_hash")
            and snapshot_hash(core) != doc["snapshot_hash"]):
        raise JournalMigrationError(
            "replay snapshot hash mismatch on a non-migrated document (fail-closed)")
    return core, log


def evaluate_payload(stored: dict, registry=None) -> dict:
    """Evaluate a STORED journal object from its SEALED envelope (never a live bridge):
    - an EPISTEMIC ``evaluation_envelope`` -> routed/verified via :func:`evaluate_envelope`;
    - an ``operational_envelope`` -> ``operational`` (a sealed technical/not-evaluated move, never a
      verdict and never aggregable);
    - neither (legacy v3) -> ``legacy_unsealed`` (visible, never reconstructed into a verdict)."""
    ep, body = _split_journal(stored)
    if ep is not None:
        return evaluate_envelope(ep, body, registry)
    op = stored.get(OPERATIONAL_ENVELOPE_KEY)
    if isinstance(op, dict):
        if op.get("evaluation_body_hash") != evaluation_body_hash(body):
            return {"status": "unverifiable",
                    "reason": "operational_envelope.evaluation_body_hash does not bind the body"}
        return {"status": "operational", "operational_class": op.get("operational_class")}
    return {"status": "legacy_unsealed",
            "reason": "no stored evaluation/operational envelope - this event was not sealed at "
                      "write; it is not reconstructed into a verdict by current code"}


def evaluate_decision(ev: MethodTrialRecorded, registry=None) -> dict:
    """Convenience wrapper: serialise a LIVE event to its SEALED journal object (v4 body + embedded
    envelope) and evaluate it. The envelope is built once at journaling; replay then uses the stored
    envelope, so a later change to ``envelope_for_payload`` cannot re-route a stored event."""
    return evaluate_payload(ev.to_journal(registry), registry)


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


def _cell_outcome(evs: list[dict]) -> tuple[str, int, int, bool, bool]:
    usable = [e for e in evs if e.get("execution_status") == "completed"
              and e.get("protocol_status") == "valid"]
    unusable = [e for e in evs if e not in usable]
    results = {e.get("epistemic_result") for e in usable if e.get("epistemic_result")
               != "not_evaluated"}
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


def _canonical_payload_str(payload: dict) -> str:
    """Canonical string form of a payload BODY (sans embedded envelope) for attestations."""
    from desi_layer9.trial_event_validation import canonical_payload
    return canonical_payload({k: v for k, v in payload.items() if k != ENVELOPE_KEY})


def _evidence_attestation(payload: dict, verdict: str) -> str:
    """A structural attestation BINDING the verdict to the canonical PAYLOAD. If the payload is
    swapped, this no longer matches - so the token alone is never the integrity root."""
    return "sha256:" + hashlib.sha256(
        (_canonical_payload_str(payload) + "|" + verdict).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerifiedTrialEvidence:
    """A STORED (envelope, payload) pair whose verdict the registered capsule VERIFIED - the
    is the stored pair itself, never a reconstructed dataclass. The private token guards against
    accidental construction; the ``attestation`` BINDS the verdict to the canonical payload so a
    post-hoc substitution is detectable; and ``aggregate`` additionally RE-EVALUATES every pair via
    ``evaluate_envelope`` (never trusting the token or stored verdict as the integrity root)."""

    envelope: dict
    payload: dict
    verdict: str
    attestation: str = ""
    _token: object = None

    def __post_init__(self):
        if self._token is not _EVIDENCE_TOKEN:
            raise TypeError("VerifiedTrialEvidence is created only via verify_payloads()")


def _as_journal(x) -> dict:
    """Accept a stored journal object (dict) or a live event; return the stored journal object."""
    return x.to_journal() if hasattr(x, "to_journal") else x


def verify_payloads(stored: list[dict], registry=None) -> list[VerifiedTrialEvidence]:
    """Turn SEALED STORED journal objects (an embedded envelope + body) into aggregable evidence:
    structurally valid AND verified by the version-pinned capsule via ``evaluate_envelope`` on the
    STORED pair. An envelope-LESS (legacy_unsealed) object NEVER becomes evidence - it carries no
    epistemic weight and is never reconstructed by a live bridge. No dataclass reconstruction is a
    precondition; unverifiable / inconsistent / invalid objects carry no weight."""
    from desi_layer9.trial_event_validation import validate_trial_payload
    out: list[VerifiedTrialEvidence] = []
    for obj in stored:
        env, payload = _split_journal(_as_journal(obj))
        if env is None:                                  # legacy_unsealed: no historical envelope
            continue
        if validate_trial_payload(payload):
            continue
        if evaluate_envelope(env, payload, registry)["status"] == "verified":
            verdict = payload.get("epistemic_result")
            out.append(VerifiedTrialEvidence(
                env, payload, verdict, _evidence_attestation(payload, verdict), _EVIDENCE_TOKEN))
    return out


def verify_events(events, registry=None) -> list[VerifiedTrialEvidence]:
    """Convenience over :func:`verify_payloads` for LIVE events: journals each (payload + embedded
    envelope) and verifies the stored pair."""
    return verify_payloads([_as_journal(e) for e in events], registry)


def aggregate(evidence: list[VerifiedTrialEvidence], registry=None) -> list[VariantScopeOutcome]:
    """Roll VERIFIED evidence up to one outcome per (target, scope, variant) reading fields DIRECTLY
    from the stored payload. The token is NOT trusted as the integrity root: every pair is
    RE-ATTESTED here - its attestation must bind to its current payload, its verdict must equal the
    payload result, and the (envelope, payload) pair must RE-VERIFY via ``evaluate_envelope``. A
    substituted payload (``dataclasses.replace`` keeping the token) is rejected."""
    cells: dict[tuple, list[dict]] = {}
    for ve in evidence:
        if not isinstance(ve, VerifiedTrialEvidence):
            raise TypeError("aggregate() accepts only VerifiedTrialEvidence (see verify_payloads)")
        p = ve.payload
        if ve.verdict != p.get("epistemic_result"):
            raise ValueError("evidence verdict does not match its payload (substituted?)")
        if ve.attestation != _evidence_attestation(p, ve.verdict):
            raise ValueError("evidence attestation does not bind to its payload (substituted?)")
        if evaluate_envelope(ve.envelope, p, registry)["status"] != "verified":
            raise ValueError("evidence pair does not re-verify under the registered capsule")
        cells.setdefault((p.get("target_id"), p.get("scope_id"), p.get("method_id"),
                          p.get("method_variant")), []).append(p)
    out: list[VariantScopeOutcome] = []
    for (target, scope, mid, variant), evs in sorted(cells.items()):
        outcome, n_v, n_u, has_s, has_h = _cell_outcome(evs)
        usable = [e for e in evs if e.get("execution_status") == "completed"
                  and e.get("protocol_status") == "valid"]
        out.append(VariantScopeOutcome(
            target_id=target, scope_id=scope, method_id=mid, method_variant=variant,
            affinities=tuple(sorted({a for e in evs for a in (e.get("affinities") or ())})),
            outcome=outcome,
            n_completed_valid=n_v, n_unusable=n_u, protocol_valid=bool(usable) and n_u == 0,
            models=tuple(sorted({e.get("model") for e in usable})),
            model_families=tuple(sorted({e.get("model_family") for e in usable})),
            implementations=tuple(sorted({e.get("implementation_id") for e in usable})),
            task_samples=tuple(sorted({e.get("task_sample_id") for e in usable})),
            evaluators=tuple(sorted({e.get("evaluator_id") for e in usable})),
            confounders=tuple(sorted({c for e in usable for c in (e.get("confounders") or ())})),
            evidence=tuple(e.get("trial_id") for e in evs), has_success=has_s, has_harmful=has_h))
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


def _operational_class(p: dict) -> str:
    """Classify a non-rule-evaluable payload WITHOUT collapsing all to 'technical_failure'."""
    if p.get("execution_status") == "failed":
        return "technical_failure"
    if p.get("execution_status") == "cancelled":
        return "cancelled"
    if p.get("protocol_status") == "invalid":
        return "protocol_invalid"
    if p.get("execution_status") == "completed" and p.get("protocol_status") == "valid":
        return "unevaluated"                      # ran cleanly but no outcome was evaluated
    return "unknown_operational"


def operational_observations(items) -> list[OperationalTrialObservation]:
    """The operational (non-epistemic) channel: structurally-valid STORED objects that carry NO
    rule-evaluable verdict. They stay VISIBLE as 'a move was attempted but not evaluable', strictly
    separate from verified evidence - never feeding attribution - and CLASSIFIED so DESi can tell a
    technical failure from a merely-unevaluated or cancelled run. Accepts live events or stored
    journal objects."""
    from desi_layer9.trial_event_validation import validate_trial_payload
    out: list[OperationalTrialObservation] = []
    for item in items:
        obj = _as_journal(item)
        _, p = _split_journal(obj)
        if validate_trial_payload(p):
            continue
        if p.get("epistemic_result") not in RULE_EVALUABLE_RESULTS:    # not_evaluated etc.
            op = obj.get(OPERATIONAL_ENVELOPE_KEY)         # prefer the SEALED class if present
            klass = op.get("operational_class") if isinstance(op, dict) else _operational_class(p)
            out.append(OperationalTrialObservation(
                trial_id=p.get("trial_id"), target_id=p.get("target_id"),
                scope_id=p.get("scope_id"), method_id=p.get("method_id"),
                method_variant=p.get("method_variant"),
                affinities=tuple(p.get("affinities") or ()),
                execution_status=p.get("execution_status"),
                protocol_status=p.get("protocol_status"), failure_kind=p.get("failure_kind"),
                desi_result=klass))
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
