"""The snapshot fast-load is a VERIFIED cache in a git-ignored SIDECAR file (never inside the
committed state file): opt-in, byte-identical to replay, and it falls back to a full replay on any
mismatch (it can only skip work, never change the result)."""

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


def test_committed_doc_is_always_journal_only(monkeypatch):
    # The snapshot is NEVER embedded in the committed doc - on or off, it stays small.
    for val in (None, "1"):
        if val is None:
            monkeypatch.delenv("JONI_FAST_LOAD", raising=False)
        else:
            monkeypatch.setenv("JONI_FAST_LOAD", val)
        doc = persistence.to_doc(_core())
        assert "state_snapshot" not in doc
        state = persistence.from_doc(doc)               # replays - the source of truth
        assert hashing.snapshot_hash(state) == doc["snapshot_hash"]


def test_sidecar_is_written_only_when_fast_load_is_on(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_FAST_LOAD", raising=False)
    p = persistence.save(_core(), tmp_path / "l9.json")
    assert not (tmp_path / "l9.snapshot.json").exists()  # off: no sidecar
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    persistence.save(_core(), p)
    assert (tmp_path / "l9.snapshot.json").exists()      # on: sidecar appears beside the file


def test_fast_load_reproduces_replay_byte_identically(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    core = _core(8)
    p = persistence.save(core, tmp_path / "l9.json")
    sidecar = json.loads((tmp_path / "l9.snapshot.json").read_text())
    assert "state_snapshot" in sidecar
    fast = persistence.load(p, verify=True)             # fast path via sidecar
    replayed = persistence.replay(
        [l9.JournalEntry.from_dict(e) for e in json.loads(p.read_text())["journal"]])
    assert hashing.snapshot_hash(fast) == hashing.snapshot_hash(core)
    assert hashing.snapshot_hash(fast) == hashing.snapshot_hash(replayed)
    assert hashing.verify_chain(fast)[0]
    assert len(fast.objects) == len(replayed.objects)
    # enums and tuples survived the round-trip (behaviour, not just hash)
    c = next(o for o in fast.all(l9.ObjectType.CLAIM))
    assert isinstance(c.status, l9.Status) and isinstance(c.derived_from, tuple)


def test_fast_load_falls_back_when_the_sidecar_is_tampered(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    p = persistence.save(_core(), tmp_path / "l9.json")
    sc = tmp_path / "l9.snapshot.json"
    sidecar = json.loads(sc.read_text())
    some = next(iter(sidecar["state_snapshot"]["objects"].values()))
    some["f"]["confidence_or_support"] = 0.999999       # tamper a field; journal stays intact
    sc.write_text(json.dumps(sidecar))
    state = persistence.load(p, verify=True)            # snapshot_hash mismatch -> replay fallback
    # the loaded state is the CORRECT one (from replay), not the tampered sidecar
    assert hashing.snapshot_hash(state) == json.loads(p.read_text())["snapshot_hash"]


def test_fast_load_falls_back_when_the_sidecar_is_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    core = _core(5)
    p = persistence.save(core, tmp_path / "l9.json")
    (tmp_path / "l9.snapshot.json").unlink()            # sidecar lost (fresh job, gitignored)
    loaded = persistence.load(p, verify=True)           # replays cleanly, no sidecar needed
    assert hashing.snapshot_hash(loaded) == hashing.snapshot_hash(core)


def test_fast_load_round_trips_through_save_load(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_FAST_LOAD", "1")
    core = _core(7)
    p = persistence.save(core, tmp_path / "l9.json")
    loaded = persistence.load(p, verify=True)
    assert hashing.snapshot_hash(loaded) == hashing.snapshot_hash(core)
    assert hashing.verify_chain(loaded)[0]
