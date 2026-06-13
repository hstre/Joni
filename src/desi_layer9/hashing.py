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


def snapshot_hash(state) -> str:
    """Deterministic hash of all authoritative objects (ledger excluded)."""
    parts = [object_canonical(o) for o in sorted(state.objects.values(), key=lambda o: o.id)]
    return _sha("\n".join(parts))


def event_canonical(ev: LedgerEvent) -> str:
    """Canonical form of an event for the chain - excludes the chain fields themselves."""
    body = {
        "id": ev.id, "sequence": ev.sequence, "tick": ev.tick,
        "operator": ev.operator.value, "actor": ev.actor, "decision": ev.decision,
        "reason": ev.reason, "input_refs": list(ev.input_refs),
        "output_refs": list(ev.output_refs), "reviewed_by": ev.reviewed_by,
        "cost": ev.cost, "after_hash": ev.after_hash,
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
    for ev in state.ledger:
        expected = _sha(prev_hash + "|" + event_canonical(ev))
        if ev.event_hash != expected:
            problems.append(f"{ev.id}: event_hash mismatch (tampered?)")
        if ev.previous_event_hash != prev_hash:
            problems.append(f"{ev.id}: broken previous_event_hash link")
        prev_hash = ev.event_hash
    return (not problems), problems
