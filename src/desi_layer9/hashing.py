"""Hashing: snapshot integrity and a tamper-evident ledger chain.

``snapshot_hash`` is a deterministic hash of the authoritative *objects* (not the
ledger). Each ledger event carries the snapshot hash after it ran plus a hash chain over
the previous event - so altering any historic event (or any object it touched) breaks
``verify_chain``. Combined with replay (persistence.py), this gives: the state is exactly
what the recorded operations produce, and the audit trail cannot be silently edited.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from enum import Enum

from .base import EpistemicObject
from .ledger import LedgerEvent


def _encode(value):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):              # Provenance, Taint
        return value.to_dict()
    if isinstance(value, (tuple, list)):
        return [_encode(v) for v in value]
    if isinstance(value, dict):
        return {k: _encode(v) for k, v in sorted(value.items())}
    return value


def object_canonical(obj: EpistemicObject) -> str:
    body = {f.name: _encode(getattr(obj, f.name)) for f in fields(obj)}
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Phase A — incremental snapshot hashing.
# The old scheme hashed the sorted concatenation of all object canonicals: O(n) per ledger emit, so
# a replay (~15k emits over ~22k objects) was O(n^2) and a fresh cold start hung for hours. The new
# scheme is an ORDER-INDEPENDENT additive set hash (AdHash): the snapshot value is the sum, mod
# 2^256, of sha256(object_canonical(o)) over all objects. Add/change/remove of an object updates
# the running sum in O(1) (subtract its old contribution, add its new), so each emit is O(1) and
# replay is O(n). Collision resistance: forging a colliding state means finding a multiset of object
# canonicals summing to the same 256-bit value — as hard as for the underlying sha256.
_MASK = (1 << 256) - 1


def object_int(obj: EpistemicObject) -> int:
    """One object's contribution to the additive snapshot hash: int(sha256(canonical))."""
    return int(_sha(object_canonical(obj)), 16)


def running_from_objects(objects) -> int:
    """The full additive snapshot value over an object collection (O(n) — used by restore and the
    equivalence oracle, never on the per-emit hot path)."""
    total = 0
    for o in objects:
        total += object_int(o)
    return total & _MASK


def snapshot_hash_full(state) -> str:
    """O(n) recomputation of the snapshot hash directly from ``_objects`` — the value the
    incrementally-maintained running sum must always equal. Used by restore, the oracle, and as a
    fallback for states that predate the incremental machinery."""
    return format(running_from_objects(state._objects.values()), "064x")


def snapshot_hash(state) -> str:
    """Deterministic hash of all authoritative objects (ledger excluded). O(1) when the kernel
    maintains the running value; falls back to a full recompute for states without it."""
    running = getattr(state, "_running", None)
    if running is None:
        return snapshot_hash_full(state)
    return format(running & _MASK, "064x")


def event_canonical(ev: LedgerEvent) -> str:
    """Canonical form of an event for the chain - excludes the chain fields themselves.

    Includes ``sampling_provenance`` (which model/sampling config produced the event): in a system
    that pins models and claims reproducibility, that provenance is exactly what must be tamper-
    evident, so it is covered by the chain hash. (``timestamp`` stays excluded by design.)"""
    body = {
        "id": ev.id, "sequence": ev.sequence, "tick": ev.tick,
        "operator": ev.operator.value, "actor": ev.actor, "decision": ev.decision,
        "reason": ev.reason, "input_refs": list(ev.input_refs),
        "output_refs": list(ev.output_refs), "reviewed_by": ev.reviewed_by,
        "cost": ev.cost, "after_hash": ev.after_hash,
        "sampling_provenance": json.dumps(ev.sampling_provenance or {}, sort_keys=True),
    }
    return json.dumps(body, sort_keys=True, ensure_ascii=False)


def chain_event(ev: LedgerEvent, previous: LedgerEvent | None, state) -> None:
    """Fill an event's hash-chain fields in place (called at emit time)."""
    ev.after_hash = snapshot_hash(state)
    ev.before_hash = previous.after_hash if previous else ""
    ev.previous_event_hash = previous.event_hash if previous else ""
    ev.event_hash = _sha(ev.previous_event_hash + "|" + event_canonical(ev))


def verify_chain(state) -> tuple[bool, list[str]]:
    """Recompute the ledger chain and report any break (tampering)."""
    problems: list[str] = []
    prev_hash = ""
    for ev in state._ledger:
        expected = _sha(prev_hash + "|" + event_canonical(ev))
        if ev.event_hash != expected:
            problems.append(f"{ev.id}: event_hash mismatch (tampered?)")
        if ev.previous_event_hash != prev_hash:
            problems.append(f"{ev.id}: broken previous_event_hash link")
        prev_hash = ev.event_hash
    return (not problems), problems
