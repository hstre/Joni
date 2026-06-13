"""Persistence and replay.

The authoritative state is a deterministic function of the recorded operations:
``state = replay(journal)``. So persistence stores the **journal** (plus the seed tick
and schema version); loading replays it to reconstruct the identical objects, ledger and
hash chain. A snapshot may accelerate startup but never replaces the journal.
"""

from __future__ import annotations

import json
from pathlib import Path

from .core import JournalEntry, Layer9, make_proposal
from .hashing import snapshot_hash, verify_chain
from .provenance import Provenance

SCHEMA_VERSION = 1


def replay(journal: list[JournalEntry], *, tick: int = 0) -> Layer9:
    """Reconstruct state from a journal. Deterministic - no PRNG anywhere."""
    core = Layer9(tick=tick)
    for entry in journal:
        proposal = make_proposal(
            entry.proposal_type, entry.operator, payload=dict(entry.payload),
            proposer=entry.proposer, provenance=Provenance.from_dict(entry.provenance),
            reason=entry.reason, target_objects=entry.target_objects,
        )
        core.submit(proposal, actor=entry.actor, governance_approved=entry.governance_approved)
    return core


def to_doc(state: Layer9) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tick": state.tick,
        "snapshot_hash": snapshot_hash(state),
        "journal": [e.to_dict() for e in state.journal],
    }


def from_doc(doc: dict) -> Layer9:
    journal = [JournalEntry.from_dict(e) for e in doc.get("journal", [])]
    state = replay(journal, tick=int(doc.get("tick", 0)))
    # Integrity: the reconstructed state must match the recorded snapshot.
    recorded = doc.get("snapshot_hash")
    if recorded and snapshot_hash(state) != recorded:
        raise ValueError("replay snapshot hash mismatch - journal or snapshot corrupted")
    ok, problems = verify_chain(state)
    if not ok:
        raise ValueError("ledger chain broken on load: " + "; ".join(problems))
    return state


def save(state: Layer9, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_doc(state), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load(path: str | Path) -> Layer9 | None:
    path = Path(path)
    if not path.exists():
        return None
    return from_doc(json.loads(path.read_text(encoding="utf-8")))
