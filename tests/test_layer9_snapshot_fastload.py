"""The snapshot fast-load is a VERIFIED cache: opt-in, byte-identical to replay, and it falls back
to a full replay on any mismatch (it can only skip work, never change the result)."""

import json

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9 import hashing, make_proposal, persistence
from desi_layer9.provenance import Provenance


def _core(n=6):
    core = l9.Layer9()
    for i in range(n):
        core.submit(make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_CREATE,
                    payload={"text": f"c{i}", "topic": "t"}, proposer="s",
                    provenance=Provenance.from_source("p")), actor="j")
    return core


def test_fast_load_is_opt_in_off_by_default(monkeypatch):
    monkeypatch.delenv("JONI_FAST_LOAD", raising=False)
    doc = persistence.to_doc(_core())
    assert "state_snapshot" not in doc                  # nothing written when off
    state = persistence.from_doc(doc)                   # replays - the source of truth
    assert hashing.snapshot_hash(state) == doc["snapshot_hash"]


def test_fast_load_reproduces_replay_byte_identically(monkeypatch):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    core = _core(8)
    doc = persistence.to_doc(core)
    assert "state_snapshot" in doc
    fast = persistence.from_doc(doc, verify=True)       # fast path
    replayed = persistence.replay([l9.JournalEntry.from_dict(e) for e in doc["journal"]])
    assert hashing.snapshot_hash(fast) == doc["snapshot_hash"]
    assert hashing.snapshot_hash(fast) == hashing.snapshot_hash(replayed)
    assert hashing.verify_chain(fast)[0]
    assert len(fast.objects) == len(replayed.objects)
    # enums and tuples survived the round-trip (behaviour, not just hash)
    c = next(o for o in fast.all(l9.ObjectType.CLAIM))
    assert isinstance(c.status, l9.Status) and isinstance(c.derived_from, tuple)


def test_fast_load_falls_back_when_the_snapshot_is_tampered(monkeypatch):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    doc = persistence.to_doc(_core())
    # corrupt the cached snapshot's objects; the journal is intact
    doc = json.loads(json.dumps(doc))                   # deep copy
    some = next(iter(doc["state_snapshot"]["objects"].values()))
    some["f"]["confidence_or_support"] = 0.999999       # tamper a field
    state = persistence.from_doc(doc, verify=True)      # snapshot_hash mismatch -> replay fallback
    # the loaded state is the CORRECT one (from replay), not the tampered snapshot
    assert hashing.snapshot_hash(state) == doc["snapshot_hash"]


def test_fast_load_round_trips_through_save_load(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    core = _core(7)
    p = persistence.save(core, tmp_path / "l9.json")
    loaded = persistence.load(p, verify=True)
    assert hashing.snapshot_hash(loaded) == hashing.snapshot_hash(core)
    assert hashing.verify_chain(loaded)[0]
