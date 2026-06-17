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
    """Reconstruct state from a journal. Deterministic - no PRNG anywhere.

    Each entry restores the core tick it ran at (legacy entries default to 0), so a journal
    that spans a tick change reproduces the exact historical ``created_tick`` values - and
    therefore its own snapshot hash.
    """
    core = Layer9(tick=tick)
    for entry in journal:
        core.tick = entry.tick
        proposal = make_proposal(
            entry.proposal_type, entry.operator, payload=dict(entry.payload),
            proposer=entry.proposer, provenance=Provenance.from_dict(entry.provenance),
            reason=entry.reason, target_objects=entry.target_objects,
        )
        core.submit(proposal, actor=entry.actor, governance_approved=entry.governance_approved,
                    replaying=True)
    if journal:
        core.tick = journal[-1].tick
    return core


def to_doc(state: Layer9) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "tick": state.tick,
        "snapshot_hash": snapshot_hash(state),
        "journal": [e.to_dict() for e in state.journal],
    }


def from_doc(doc: dict, *, verify: bool = True) -> Layer9:
    journal = [JournalEntry.from_dict(e) for e in doc.get("journal", [])]
    state = replay(journal, tick=int(doc.get("tick", 0)))
    if verify:
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


def load(path: str | Path, *, verify: bool = True) -> Layer9 | None:
    path = Path(path)
    if not path.exists():
        return None
    return from_doc(json.loads(path.read_text(encoding="utf-8")), verify=verify)


def repair(path: str | Path) -> bool:
    """Re-seal a state whose recorded SNAPSHOT hash drifted while the ledger chain is still intact.

    The only legitimate case is a snapshot-hash mismatch with an unbroken chain (e.g. a state
    written before per-entry ticks were journalled, after a midnight tick rollover). A BROKEN CHAIN
    means possible tampering and must hard-stop, never be silently re-blessed: a blanket
    ``except ValueError: re-save`` would launder a corrupted journal into a self-consistent file.
    Returns True if a repair was needed; raises if the state is not safely repairable.
    """
    path = Path(path)
    if not path.exists():
        return False
    doc = json.loads(path.read_text(encoding="utf-8"))
    try:
        from_doc(doc, verify=True)
        return False                                  # already loads cleanly - nothing to do
    except ValueError:
        pass
    state = from_doc(doc, verify=False)               # replay-only; deterministic
    ok, problems = verify_chain(state)
    if not ok:                                        # tampering, not drift - refuse to re-bless
        raise ValueError("ledger chain broken - refusing to repair (possible tampering): "
                         + "; ".join(problems))
    recorded = doc.get("snapshot_hash")
    if not (recorded and snapshot_hash(state) != recorded):
        # chain intact AND snapshot already matches: the load failed for some other reason we do
        # not understand - do not paper over it.
        raise ValueError("repair: verify failed but chain intact and snapshot matches - refusing")
    save(state, path)                                 # the one safe case: re-seal the snapshot hash
    from_doc(json.loads(path.read_text(encoding="utf-8")), verify=True)  # must load cleanly now
    return True
