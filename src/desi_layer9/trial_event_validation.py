"""Structural validation + canonicalisation for METHOD_TRIAL_RECORDED payloads, AT THE GATE.

Layer 9 checks STRUCTURE and forbidden axis-combinations only - NOT the epistemic verdict (the
decision rule) or generalisation (the independence policy), which stay OUTSIDE the core. One
supported schema version; an unknown version is rejected, never stored.

``canonical_payload`` produces a deterministic, deep, plain-data canonical form so the stored record
is immutable (a string), tamper-evident (hashable), and comparable for idempotency.
"""

from __future__ import annotations

import json

SUPPORTED_TRIAL_SCHEMA_VERSIONS = ("method_trial_recorded_v3",)

_EXEC = ("completed", "failed", "cancelled")
_PROTO = ("valid", "invalid", "unknown")
_RESULT = ("success", "partial_success", "no_benefit", "harmful", "inconclusive", "not_evaluated")
_REQUIRED = ("trial_id", "schema_version", "target_type", "target_id",
             "execution_status", "protocol_status", "epistemic_result")


def canonical_payload(payload: dict) -> str:
    """Deterministic canonical JSON of a payload (sorted keys, compact, deep). Round-tripping
    through json also yields plain, fully-detached data - no shared nested references survive."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def validate_trial_payload(p: dict) -> list[str]:
    """Return structural violations (empty == structurally valid). An unsupported schema version is
    reported alone - the core records only versions it understands."""
    if not isinstance(p, dict):
        return ["payload must be an object"]
    if p.get("schema_version") not in SUPPORTED_TRIAL_SCHEMA_VERSIONS:
        return [f"unsupported schema_version {p.get('schema_version')!r} "
                f"(supported: {SUPPORTED_TRIAL_SCHEMA_VERSIONS})"]
    errs: list[str] = []
    for k in _REQUIRED:
        if k not in p:
            errs.append(f"missing required field '{k}'")
    if p.get("execution_status") not in _EXEC:
        errs.append(f"execution_status {p.get('execution_status')!r} invalid")
    if p.get("protocol_status") not in _PROTO:
        errs.append(f"protocol_status {p.get('protocol_status')!r} invalid")
    if p.get("epistemic_result") not in _RESULT:
        errs.append(f"epistemic_result {p.get('epistemic_result')!r} invalid")
    # forbidden combinations (STRUCTURAL only - no statistics here)
    if p.get("execution_status") != "completed" and p.get("epistemic_result") != "not_evaluated":
        errs.append("forbidden: non-completed execution requires epistemic_result 'not_evaluated'")
    if p.get("protocol_status") == "invalid" and p.get("epistemic_result") != "not_evaluated":
        errs.append("forbidden: invalid protocol requires epistemic_result 'not_evaluated'")
    if not p.get("trial_id"):
        errs.append("trial_id is required (non-empty)")
    return errs
