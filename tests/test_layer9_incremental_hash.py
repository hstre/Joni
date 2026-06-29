"""Phase A — the incrementally-maintained snapshot hash must ALWAYS equal a full recompute.

This is the oracle that makes the change safe: ``snapshot_hash`` (O(1), running) must equal
``snapshot_hash_full`` (O(n), from scratch) after every state mutation. If ``_emit`` ever fails to
rehash an object a submit touched, the running value drifts and these assertions fail — so a missed
mutation site cannot pass silently. The guarded test replays real production operator sequences.
"""
from __future__ import annotations

from pathlib import Path

import desi_layer9 as l9
from desi_layer9.core import JournalEntry, Layer9
from desi_layer9.hashing import snapshot_hash, snapshot_hash_full, verify_chain

OP, PT = l9.Operator, l9.ProposalType


def _consistent(core) -> bool:
    return snapshot_hash(core) == snapshot_hash_full(core)


def _model(core, op, payload, targets=()):
    p = l9.make_proposal(PT.CLAIM_PROPOSAL, op, payload=payload, proposer="joni",
                         provenance=l9.Provenance.from_operator(), target_objects=tuple(targets))
    return core.submit(p, actor="joni")


def test_running_equals_full_across_every_operator():
    core = Layer9()
    assert _consistent(core)                                  # empty state

    # create + revise + confirm a claim, with evidence
    _model(core, OP.CLAIM_CREATE, {"text": "x", "topic": "t"})
    assert _consistent(core)
    cid = core.all(l9.ObjectType.CLAIM)[-1].id
    _model(core, OP.CLAIM_REVISE, {"to_status": "active"}, targets=(cid,))
    assert _consistent(core)
    _model(core, OP.EVIDENCE_ATTACH, {"content": "ev", "kind": "statement"}, targets=(cid,))
    assert _consistent(core)
    _model(core, OP.CLAIM_CONFIRM, {}, targets=(cid,))
    assert _consistent(core)

    # a second claim + a method proposed and promoted
    _model(core, OP.CLAIM_CREATE, {"text": "y", "topic": "t"})
    assert _consistent(core)
    _model(core, OP.METHOD_PROPOSE, {"name": "m", "steps": ["a"]})
    assert _consistent(core)
    mid = core.all(l9.ObjectType.METHOD)[-1].id
    _model(core, OP.METHOD_PROMOTE, {}, targets=(mid,))
    assert _consistent(core)

    # memory + a narrative render (a read-shaped op) — still consistent
    _model(core, OP.MEMORY_RECORD, {"summary": "s"})
    assert _consistent(core)
    _model(core, OP.NARRATIVE_RENDER, {"text": "a calm neutral summary"})
    assert _consistent(core)

    ok, problems = verify_chain(core)
    assert ok, problems


def test_save_load_and_restore_rebuild_the_running_hash(tmp_path):
    from desi_layer9 import persistence, snapshot
    core = Layer9()
    for i in range(6):
        _model(core, OP.CLAIM_CREATE, {"text": f"c{i}", "topic": "t"})
    sealed = snapshot_hash(core)

    p = tmp_path / "layer9.json"
    persistence.save(core, p)
    reloaded = persistence.load(p)                  # replay path -> rebuilds incrementally
    assert snapshot_hash(reloaded) == sealed and _consistent(reloaded)

    snap = snapshot.capture(core)
    restored = snapshot.restore(snap, core.journal, tick=core.tick)   # restore -> rebuild
    assert snapshot_hash(restored) == sealed and _consistent(restored)


def test_real_journal_replay_stays_consistent():
    """Guarded: replay the first slice of the REAL journal and assert the running hash equals a full
    recompute throughout — real conflict/evidence/method operator sequences, not synthetic ones."""
    import json
    real = Path(__file__).resolve().parent.parent / "state" / "layer9.json"
    if not real.exists():
        import pytest
        pytest.skip("real journal not present")
    entries = json.loads(real.read_text())["journal"][:2000]
    core = Layer9()
    for i, e in enumerate(entries):
        je = JournalEntry.from_dict(e)
        core._tick = je.tick
        prop = l9.make_proposal(je.proposal_type, je.operator, payload=dict(je.payload),
                                proposer=je.proposer,
                                provenance=l9.Provenance.from_dict(je.provenance),
                                reason=je.reason, target_objects=je.target_objects)
        core.submit(prop, actor=je.actor, governance_approved=je.governance_approved)
        if i % 200 == 0:                                     # full check is O(n); sample it
            assert _consistent(core), f"drift at entry {i}"
    assert _consistent(core)
    assert verify_chain(core)[0]
