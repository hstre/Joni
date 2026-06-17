"""Structural validation + canonicalisation for METHOD_TRIAL_RECORDED payloads, AT THE GATE.

Layer 9 validates the FULL v3 structural schema here - required fields, types, sub-structures and
the forbidden axis-combinations - so that ``schema_version=method_trial_recorded_v3`` actually
guarantees v3's mandatory structure before an event enters the IRREVERSIBLE journal. It does NOT
compute the epistemic verdict (no statistics): that stays with the registered decision rule,
outside the core. One supported schema version; an unknown version is rejected, never stored.

Unknown EXTRA top-level fields are consciously ALLOWED (forward-compatible additions): they are not
interpreted and are preserved verbatim in the canonical payload. The mandatory fields below are
required and type-checked.

``canonical_payload`` produces a deterministic, deep, plain-data canonical form so the stored record
is immutable (a string), tamper-evident (hashable), and comparable for idempotency.
"""

from __future__ import annotations

import json
import math
from numbers import Number

SUPPORTED_TRIAL_SCHEMA_VERSIONS = ("method_trial_recorded_v3",)

# Per-rule STRUCTURAL input contracts: which measurement fields a real verdict under a given rule
# must carry before it may enter the journal. The core does NOT compute the verdict - it only
# refuses to store a success/harmful/no_benefit claim that the declared rule could not even
# evaluate. (rule_v2 decides from the confidence interval, so it needs effect_size AND a CI.)
RULE_INPUT_CONTRACTS = {
    "rule_v2": {"require_effect": True, "require_confidence_interval": True},
}
_DEFAULT_RULE_INPUT = {"require_effect": True, "require_confidence_interval": False}

_EXEC = ("completed", "failed", "cancelled")
_PROTO = ("valid", "invalid", "unknown")
_KINDS = ("none", "technical", "timeout", "parser", "model", "dependency", "infrastructure")
_RESULT = ("success", "partial_success", "no_benefit", "harmful", "inconclusive", "not_evaluated")
_REAL = ("success", "partial_success", "no_benefit", "harmful")
_TARGETS = ("conflict", "open_question", "evidence_gap")
_DIRECTIONS = ("higher_is_better", "lower_is_better")
_ATTR_LEVELS = ("variant", "method")

# v3 mandatory top-level fields (structure that schema_version=v3 must guarantee).
_REQUIRED = (
    "trial_id", "schema_version", "target_type", "target_id", "scope_id",
    "method_id", "method_variant", "estimand", "measurement", "decision",
    "model", "evaluator_id", "baseline_id",
    "execution_status", "protocol_status", "failure_kind", "epistemic_result",
)
_ESTIMAND_REQUIRED = ("outcome_metric", "direction", "minimum_effect", "decision_rule_id")
_DECISION_REQUIRED = ("decision_rule_id", "decision_rule_hash", "verdict")
_MEASUREMENT_KEYS = ("metric_name", "baseline_value", "intervention_value", "effect_size",
                     "uncertainty")


def canonical_payload(payload: dict) -> str:
    """Deterministic canonical JSON of a payload (sorted keys, compact, deep). Round-tripping
    through json also yields plain, fully-detached data - no shared nested references survive."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and bool(v)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v) -> bool:
    return isinstance(v, Number) and not isinstance(v, bool)


def _finite(v) -> bool:
    return _is_num(v) and math.isfinite(v)


_EPS = 1e-9


def _ci_errors(label: str, ci) -> list[str]:
    if ci is None:
        return []
    if not (isinstance(ci, (list, tuple)) and len(ci) == 2 and all(_finite(x) for x in ci)):
        return [f"{label} must be a finite [low, high] pair"]
    if ci[0] > ci[1]:
        return [f"{label} lower bound must be <= upper bound"]
    return []


def cross_block_consistency(measurement: dict, decision: dict, estimand: dict, *,
                            is_real: bool, has_effect_derivation: bool = False) -> list[str]:
    """The ONE canonical structural-consistency check shared by the gate AND the rule evaluator.

    It binds ``verified`` to the actual OBSERVATION: the statistical evidence (effect, uncertainty,
    confidence interval) lives in the MEASUREMENT; the decision block is non-authoritative and may
    only MIRROR it, never diverge; the measurement is internally consistent (effect derived from the
    raw values under the contrast/direction, and lying within its own interval); and all numbers are
    finite and well-ordered. It computes NO verdict (no statistics) - only equalities, ranges,
    finiteness and the deterministic effect derivation."""
    errs: list[str] = []
    m_eff, m_unc, m_ci = (measurement.get("effect_size"), measurement.get("uncertainty"),
                          measurement.get("confidence_interval"))
    base, inter = measurement.get("baseline_value"), measurement.get("intervention_value")
    d_eff, d_min, d_ci = (decision.get("effect_size"), decision.get("minimum_effect"),
                          decision.get("confidence_interval"))
    est_min, contrast = estimand.get("minimum_effect"), estimand.get("contrast")
    direction = estimand.get("direction")

    for name, v in (("measurement.effect_size", m_eff), ("measurement.uncertainty", m_unc),
                    ("measurement.baseline_value", base), ("measurement.intervention_value", inter),
                    ("estimand.minimum_effect", est_min), ("decision.effect_size", d_eff),
                    ("decision.minimum_effect", d_min)):
        if v is not None and not _finite(v):
            errs.append(f"{name} must be a finite number (no NaN/Infinity)")
    errs += _ci_errors("measurement.confidence_interval", m_ci)
    errs += _ci_errors("decision.confidence_interval", d_ci)
    if m_unc is not None and _finite(m_unc) and m_unc < 0:
        errs.append("measurement.uncertainty must be >= 0")
    # NOTE: ``uncertainty`` is an UNINTERPRETED descriptive scalar (its kind - SE, SD, MAD, ... - is
    # not declared), so it is deliberately NOT cross-checked against the CI. rule_v2 ignores it; the
    # CI is the sole statistical authority. (No fake consistency check is performed.)
    if errs:
        return errs

    # the statistical interval belongs to the MEASUREMENT; the decision may only mirror it.
    if d_ci is not None:
        if m_ci is None:
            errs.append("confidence_interval must live in the measurement, not the decision")
        elif list(d_ci) != list(m_ci):
            errs.append("decision.confidence_interval must equal measurement.confidence_interval "
                        "(the decision may not supply its own interval)")
    # the decision may not change the pre-registered threshold or contradict the measured effect.
    if d_min is not None and est_min is not None and d_min != est_min:
        errs.append("decision.minimum_effect must equal estimand.minimum_effect "
                    "(no post-hoc threshold change)")
    if d_eff is not None and m_eff is not None and d_eff != m_eff:
        errs.append("decision.effect_size must equal measurement.effect_size "
                    "(the decision may not contradict the measurement)")
    # the effect must lie within its own interval.
    if m_ci is not None and m_eff is not None and not (m_ci[0] - _EPS <= m_eff <= m_ci[1] + _EPS):
        errs.append("measurement.effect_size must lie within measurement.confidence_interval")
    # the measurement must be internally consistent: effect derived from the raw values.
    if base is not None and inter is not None and m_eff is not None:
        if contrast == "intervention_minus_baseline":
            oriented = (inter - base) if direction == "higher_is_better" else (base - inter)
            if abs(m_eff - oriented) > 1e-6:
                errs.append("measurement.effect_size is inconsistent with baseline/intervention "
                            "under the estimand contrast/direction")
        elif is_real and not has_effect_derivation:
            errs.append(f"contrast '{contrast}' requires an effect_derivation (id + hash) to "
                        "verify the effect against the raw values")
    if is_real:
        m_name, o_metric = measurement.get("metric_name"), estimand.get("outcome_metric")
        if m_name is not None and o_metric and m_name != o_metric:
            errs.append("measurement.metric_name must equal estimand.outcome_metric")
        if est_min is not None and (not _finite(est_min) or est_min <= 0):
            errs.append("estimand.minimum_effect must be > 0 for a real result")
    return errs


def validate_trial_payload(p: dict) -> list[str]:
    """Return structural violations (empty == structurally valid v3). Validates the full mandatory
    structure + forbidden combinations; never computes the verdict from the numbers."""
    if not isinstance(p, dict):
        return ["payload must be an object"]
    if p.get("schema_version") not in SUPPORTED_TRIAL_SCHEMA_VERSIONS:
        return [f"unsupported schema_version {p.get('schema_version')!r} "
                f"(supported: {SUPPORTED_TRIAL_SCHEMA_VERSIONS})"]

    errs: list[str] = []
    for k in _REQUIRED:
        if k not in p:
            errs.append(f"missing required field '{k}'")
    if errs:
        return errs                                  # don't probe sub-structure of a torso payload

    # -- enums + simple types ------------------------------------------------------------------- #
    if p["execution_status"] not in _EXEC:
        errs.append(f"execution_status {p['execution_status']!r} invalid")
    if p["protocol_status"] not in _PROTO:
        errs.append(f"protocol_status {p['protocol_status']!r} invalid")
    if p.get("failure_kind", "none") not in _KINDS:
        errs.append(f"failure_kind {p.get('failure_kind')!r} invalid")
    if p["epistemic_result"] not in _RESULT:
        errs.append(f"epistemic_result {p['epistemic_result']!r} invalid")
    if p["target_type"] not in _TARGETS:
        errs.append(f"target_type {p['target_type']!r} invalid")
    if not _nonempty_str(p.get("trial_id")):
        errs.append("trial_id must be a non-empty string")
    if not _nonempty_str(p.get("scope_id")):
        errs.append("scope_id must be a non-empty string ('unknown' explicitly, never empty)")
    if not _nonempty_str(p.get("method_variant")):
        errs.append("method_variant must be a non-empty string")
    if not _nonempty_str(p.get("model")):
        errs.append("model (sampling provenance) must be a non-empty string")
    if not _nonempty_str(p.get("evaluator_id")):
        errs.append("evaluator_id must be a non-empty string")
    if not _nonempty_str(p.get("baseline_id")):
        errs.append("baseline_id must be a non-empty string")
    if "attribution_level" in p and p["attribution_level"] not in _ATTR_LEVELS:
        errs.append(f"attribution_level {p['attribution_level']!r} not in {_ATTR_LEVELS}")
    if p.get("attribution_strength", "none") != "none":
        errs.append("attribution_strength must be 'none' on a raw event")

    # -- sub-structures ------------------------------------------------------------------------- #
    est, dec, meas = p.get("estimand"), p.get("decision"), p.get("measurement")
    if not isinstance(est, dict):
        errs.append("estimand must be an object")
    else:
        for k in _ESTIMAND_REQUIRED:
            if k not in est:
                errs.append(f"estimand missing '{k}'")
        if est.get("direction") not in _DIRECTIONS:
            errs.append(f"estimand.direction {est.get('direction')!r} invalid")
        if not isinstance(est.get("minimum_effect"), Number):
            errs.append("estimand.minimum_effect must be numeric")
    if not isinstance(dec, dict):
        errs.append("decision must be an object")
    else:
        for k in _DECISION_REQUIRED:
            if k not in dec:
                errs.append(f"decision missing '{k}'")
        if dec.get("verdict") not in _RESULT:
            errs.append(f"decision.verdict {dec.get('verdict')!r} invalid")
    if not isinstance(meas, dict):
        errs.append("measurement must be an object")
    elif any(k not in meas for k in _MEASUREMENT_KEYS):
        errs.append(f"measurement must carry the keys {_MEASUREMENT_KEYS} (values may be null)")
    if errs:
        return errs

    # -- TYPE-check every field the projector later casts (an accepted event cannot crash it) -- #
    if "method_version" in p and not _is_int(p["method_version"]):
        errs.append("method_version must be an integer")
    if "ledger_tick" in p and not _is_int(p["ledger_tick"]):
        errs.append("ledger_tick must be an integer")
    for k in ("baseline_value", "intervention_value", "effect_size", "uncertainty"):
        if meas.get(k) is not None and not _is_num(meas[k]):
            errs.append(f"measurement.{k} must be numeric or null")
    if meas.get("metric_name") is not None and not isinstance(meas["metric_name"], str):
        errs.append("measurement.metric_name must be a string or null")
    for k in ("effect_size", "minimum_effect"):
        if dec.get(k) is not None and not _is_num(dec[k]):
            errs.append(f"decision.{k} must be numeric or null")
    for blk, key in ((dec, "decision.confidence_interval"),
                     (meas, "measurement.confidence_interval")):
        ci = blk.get("confidence_interval")
        if ci is not None and not (isinstance(ci, (list, tuple)) and len(ci) == 2
                                   and all(_is_num(x) for x in ci)):
            errs.append(f"{key} must be null or a [low, high] pair of numbers")
    if "affinities" in p and not (isinstance(p["affinities"], list)
                                  and all(isinstance(a, str) for a in p["affinities"])):
        errs.append("affinities must be a list of strings")
    if errs:
        return errs

    # -- forbidden combinations (structural; NO statistics) ------------------------------------- #
    exec_s, proto, result = p["execution_status"], p["protocol_status"], p["epistemic_result"]
    real = result in _REAL
    if exec_s != "completed" and result != "not_evaluated":
        errs.append("forbidden: non-completed execution requires epistemic_result 'not_evaluated'")
    if exec_s == "failed" and p.get("failure_kind", "none") == "none":
        errs.append("forbidden: execution_status 'failed' requires a failure_kind != 'none'")
    if exec_s != "failed" and p.get("failure_kind", "none") != "none":
        errs.append("forbidden: failure_kind set without execution_status 'failed'")
    if proto == "invalid" and result != "not_evaluated":
        errs.append("forbidden: invalid protocol requires epistemic_result 'not_evaluated'")
    if proto == "unknown" and real:
        errs.append("forbidden: a real result requires protocol_status 'valid' (got 'unknown')")
    if p["target_type"] == "conflict" and not p.get("claim_ids"):
        errs.append("a conflict trial must carry non-empty claim_ids")

    # decision.verdict is the recorded verdict; it must match the event's epistemic_result.
    if dec.get("verdict") != result:
        errs.append(f"decision.verdict {dec.get('verdict')!r} must equal epistemic_result "
                    f"{result!r}")

    if real:
        if exec_s != "completed" or proto != "valid":
            errs.append("a real result requires execution 'completed' + protocol 'valid'")
        for k in ("metric_name", "baseline_value", "intervention_value"):
            if meas.get(k) is None:
                errs.append(f"a real result requires measurement.{k}")
        # the independence-relevant provenance must be PRESENT for an evaluable real verdict (an
        # explicit 'unknown' is allowed here, but is then treated as non-independent downstream).
        for k in ("implementation_id", "model_family", "task_sample_id"):
            if not _nonempty_str(p.get(k)):
                errs.append(f"a real result requires '{k}' (independence provenance; "
                            "'unknown' explicitly, never empty)")
        if not _nonempty_str(est.get("decision_rule_id")) or \
                not isinstance(est.get("minimum_effect"), Number) or est["minimum_effect"] <= 0:
            errs.append("a real result requires estimand.decision_rule_id + minimum_effect > 0")
        if not _nonempty_str(dec.get("decision_rule_id")) or \
                not _nonempty_str(dec.get("decision_rule_hash")):
            errs.append("a real result requires a decision with decision_rule_id + "
                        "decision_rule_hash (a registered, versioned rule)")
        if est.get("decision_rule_id") and dec.get("decision_rule_id") and \
                est["decision_rule_id"] != dec["decision_rule_id"]:
            errs.append("decision.decision_rule_id must match estimand.decision_rule_id")
        # the declared rule's INPUT CONTRACT: a real verdict may not be stored unless the
        # measurement
        # carries the fields its rule structurally needs (the core does NOT compute the verdict).
        contract = RULE_INPUT_CONTRACTS.get(est.get("decision_rule_id"), _DEFAULT_RULE_INPUT)
        if contract.get("require_effect") and meas.get("effect_size") is None:
            errs.append(f"a real result under rule '{est.get('decision_rule_id')}' requires "
                        "measurement.effect_size")
        if contract.get("require_confidence_interval") and meas.get("confidence_interval") is None:
            errs.append(f"a real result under rule '{est.get('decision_rule_id')}' requires "
                        "measurement.confidence_interval")

    # cross-block consistency + numeric/interval invariants + measurement-internal derivation.
    errs += cross_block_consistency(
        meas, dec, est, is_real=real, has_effect_derivation=bool(p.get("effect_derivation")))
    return errs
