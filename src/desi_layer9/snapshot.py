"""Snapshot fast-load: a VERIFIED cache that skips the O(n^2) full replay.

``persistence`` reconstructs state by replaying the whole journal - and because the tamper-
evident ledger records ``snapshot_hash`` after EVERY event (a hash over all objects), full replay
O(entries x objects) = O(n^2). On a long-lived journal that becomes the dominant cost of every load.

This module captures the fully-replayed state as a DATA-ONLY snapshot (no pickle, no code) and
restores it directly. It NEVER replaces the journal as the source of truth: ``from_doc``
restores the snapshot, then re-derives ``snapshot_hash`` and runs ``verify_chain``; on ANY
mismatch (or a missing/old-format snapshot) it falls back to the full replay. So the fast path can
only ever produce a state byte-identical to replay - worst case it is skipped, never wrong.

Serialisation is a generic dataclass/enum/tuple encoder so new object types need no code; the
round-trip preserves exact types (enums stay enums, tuples stay tuples) so behaviour and hashes are
identical to replay.
"""

from __future__ import annotations

import dataclasses
from enum import Enum

from . import enums, ledger, objects
from .ids import IdMinter
from .provenance import Provenance
from .taint import Taint

SNAPSHOT_VERSION = "layer9_state_snapshot_v1"

# The closed registry of dataclasses / enums a snapshot may reconstruct. Reconstruction is by name
# against THIS allowlist only - an unknown name fails the restore (-> fall back to replay), so a
# snapshot can never instantiate an arbitrary class.
_OBJECT_CLASSES = (
    objects.Claim, objects.Evidence, objects.EvidenceLink, objects.Constraint, objects.Goal,
    objects.Preference, objects.Project, objects.Method, objects.MethodTrialEvent,
    objects.MemoryEpisode, objects.Conflict, objects.Source, objects.Proposal, objects.Review,
    objects.Decision, objects.OperationalState, objects.SelfModelClaim, objects.NarrativeSummary,
    objects.SemanticCluster,
)
_DATACLASSES = {c.__name__: c for c in (*_OBJECT_CLASSES, Provenance, Taint, ledger.LedgerEvent)}
_ENUMS = {e.__name__: e for e in (
    enums.ObjectType, enums.Status, enums.Authority, enums.SemanticState, enums.SemanticDecision,
    enums.OriginType, enums.RelationType, enums.ConflictStatus, enums.ConflictKind,
    enums.MemoryKind,
    enums.ProposalType, enums.Operator,
)}


def _ser(v):
    """Recursively encode to JSON-safe data, tagging types so the round-trip is exact."""
    if isinstance(v, Enum):
        return {"__e__": type(v).__name__, "v": v.value}
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        flds = {f.name: _ser(getattr(v, f.name)) for f in dataclasses.fields(v)}
        return {"__c__": type(v).__name__, "f": flds}
    if isinstance(v, tuple):
        return {"__t__": [_ser(x) for x in v]}
    if isinstance(v, dict):
        return {"__d__": {k: _ser(x) for k, x in v.items()}}
    if isinstance(v, list):
        return [_ser(x) for x in v]
    return v                                    # str / int / float / bool / None


def _deser(v):
    """Inverse of :func:`_ser`. Reconstructs only allowlisted dataclasses/enums; an unknown tag
    raises ``KeyError`` -> the caller falls back to replay."""
    if isinstance(v, dict):
        if "__e__" in v:
            return _ENUMS[v["__e__"]](v["v"])
        if "__c__" in v:
            cls = _DATACLASSES[v["__c__"]]
            return cls(**{k: _deser(x) for k, x in v["f"].items()})
        if "__t__" in v:
            return tuple(_deser(x) for x in v["__t__"])
        if "__d__" in v:
            return {k: _deser(x) for k, x in v["__d__"].items()}
        return v
    if isinstance(v, list):
        return [_deser(x) for x in v]
    return v


def capture(state) -> dict:
    """A DATA-ONLY snapshot of the authoritative state (objects + ledger + tick + minter + seq).
    The journal is stored separately by ``persistence`` and stays the source of truth."""
    return {
        "version": SNAPSHOT_VERSION,
        "tick": state._tick,
        "seq": state._seq,
        "minter_counters": dict(state._minter.counters),
        "objects": {oid: _ser(o) for oid, o in state._objects.items()},
        "ledger": [_ser(ev) for ev in state._ledger],
    }


def restore(snap: dict, journal_entries, *, tick: int = 0):
    """Reconstruct a ``Layer9`` from a snapshot + the journal (for ``_journal``). Raises on any
    malformed/old snapshot so the caller falls back to replay."""
    from .core import Layer9
    if not isinstance(snap, dict) or snap.get("version") != SNAPSHOT_VERSION:
        raise ValueError("snapshot missing or wrong version")
    core = Layer9(_tick=int(snap.get("tick", tick)))
    core._seq = int(snap["seq"])
    core._minter = IdMinter(counters=dict(snap["minter_counters"]))
    core._objects = {oid: _deser(o) for oid, o in snap["objects"].items()}
    core._ledger = [_deser(ev) for ev in snap["ledger"]]
    core._journal = list(journal_entries)
    return core
