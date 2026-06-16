"""Read-only projector: Layer 9 -> a typed EpistemicGapSnapshot for DESi's gap analysis.

The data source defines the contract, not the convenient demo input. This projector ONLY reads the
authoritative core and copies/derives facts into DESi's stable snapshot schema. It NEVER writes to
the core, never mutates an object, and - crucially - **never invents a signal that Layer 9 does not
hold**. Every projected field is marked ``direct`` (copied), ``derived`` (deterministically computed
from Layer-9 facts), or ``unknown`` (Layer 9 does not record it) in ``provenance.field_sources``.
Missing data is ``unknown``, never a silent empty/zero that a consumer could mistake for evidence.

This is also a measuring instrument: where it has to mark fields ``unknown``, it is telling us the
data capture is insufficient for the analysis to beat a static table - a legitimate result, not a
licence to fill the gap with plausible heuristics.
"""

from __future__ import annotations


def available() -> bool:
    try:
        import desi.solution_space_gap  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def project(core, *, core_commit: str = "unknown"):
    """Project a Layer-9 ``core`` into an ``EpistemicGapSnapshot``. Read-only.

    Returns ``None`` if the DESi schema is unavailable (no silent fallback)."""
    from desi.solution_space_gap import (
        SCHEMA_VERSION,
        ConflictGap,
        EpistemicGapSnapshot,
        EvidenceGap,
        MethodRecord,
        SnapshotProvenance,
    )

    from desi_layer9 import ObjectType
    from desi_layer9.hashing import snapshot_hash

    sources: dict = {}

    # -- conflicts: DIRECT from the open Conflict objects (id/kind/severity/scope/status) -------- #
    conflicts = []
    for x in core.open_conflicts():
        conflicts.append(ConflictGap(
            id=x.id,
            kind=getattr(getattr(x, "conflict_kind", None), "value", "unqualified"),
            severity=getattr(x, "severity", "soft"),
            scope=tuple(getattr(x, "claim_ids", ())),
            # Layer 9 does NOT record which thinking-moves were tried on a given conflict.
            attempted_affinities=(),
            unresolved_since=int(getattr(x, "created_tick", 0) or 0)))
    sources["conflicts.id|kind|severity|scope"] = {
        "source": "Conflict objects", "confidence": "direct"}
    sources["conflicts.attempted_affinities"] = {
        "source": "n/a", "confidence": "unknown",
        "note": "Layer 9 does not bind attempted thinking-moves to a conflict"}

    # -- method repertoire: DIRECT (affinities a method carries; stored in applicable_to) -------- #
    methods = core.all(ObjectType.METHOD)
    method_history = tuple(
        MethodRecord(method_id=m.id, affinities=tuple(getattr(m, "applicable_to", ()) or ()))
        for m in methods)
    sources["method_history.affinities"] = {
        "source": "Method.applicable_to", "confidence": "direct"}

    # -- method_trials (scope-bound, per-conflict, result-kind): UNKNOWN in Layer 9 today -------- #
    # Methods carry GLOBAL success/failure counts and run-ids, but nothing binds a trial to a
    # conflict, a scope, a method-variant, or a result KIND (no_benefit vs technical_failure...).
    # So we project NOTHING here and say so - rather than fabricate scope-bound outcomes.
    method_trials = ()
    sources["method_trials"] = {
        "source": "n/a", "confidence": "unknown",
        "note": "Layer 9 records global Method.success/failure_count + run-ids only - NOT "
                "scope-bound outcomes with a result kind. The analysis cannot beat a static table "
                "without this; the data capture must be added first."}

    # -- evidence gaps: DERIVED (active claims with thin / single-source support) ---------------- #
    evidence_gaps = []
    for c in core.all(ObjectType.CLAIM):
        srcs = {str(s).split(":", 1)[0] for s in (getattr(c.provenance, "source_ids", ()) or ())}
        if 0 < len(srcs) <= 1:
            evidence_gaps.append(EvidenceGap(
                claim_id=c.id, missing_evidence_type="independent_corroboration",
                source_independence=0.0, downstream_importance=0.0))
    sources["evidence_gaps"] = {
        "source": "Claim.provenance.source_ids (single-source)", "confidence": "derived"}
    sources["evidence_gaps.downstream_importance"] = {
        "source": "n/a", "confidence": "unknown", "note": "not yet computed from the claim graph"}

    snap_hash = snapshot_hash(core)
    ledger_seq = len(getattr(core, "ledger", []) or [])
    prov = SnapshotProvenance(
        snapshot_hash=snap_hash, layer9_sequence=ledger_seq, core_commit=core_commit,
        schema_version=SCHEMA_VERSION, field_sources=sources)
    return EpistemicGapSnapshot(
        conflicts=tuple(conflicts), evidence_gaps=tuple(evidence_gaps),
        method_history=method_history, method_trials=method_trials, provenance=prov)


def data_sufficiency(snapshot) -> dict:
    """Honest read-out of whether the projected snapshot carries enough real signal for DESi to do
    more than a static conflict-kind table. The decisive checkpoint: without scope-bound trial
    outcomes, it cannot."""
    fs = snapshot.provenance.field_sources
    return {
        "conflicts": len(snapshot.conflicts),
        "has_attempted_affinities": fs.get("conflicts.attempted_affinities", {}).get(
            "confidence") == "direct",
        "has_scope_bound_trials": bool(snapshot.method_trials),
        "method_trials_confidence": fs.get("method_trials", {}).get("confidence"),
        "beats_static_table_possible": bool(snapshot.method_trials),
        "verdict": ("sufficient" if snapshot.method_trials else
                    "insufficient: no scope-bound trial outcomes - DESi degrades to the static "
                    "conflict-kind table; improve Layer-9 trial capture before claiming value"),
    }

