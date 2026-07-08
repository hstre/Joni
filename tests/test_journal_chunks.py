"""Chunked journal persistence - the repo diet without touching the epistemic contract.

The journal is append-only; storing it as one ever-growing file made every autonomous commit
re-store a multi-MB blob. On disk it is now sealed immutable chunks + a small active tail; in
memory nothing changes (to_doc/from_doc still speak one journal list) and load still verifies
the reassembled journal against the recorded snapshot_hash and the ledger chain.
"""
import json

from desi_layer9 import Operator, ProposalType, make_proposal, persistence
from desi_layer9.hashing import snapshot_hash
from desi_layer9.provenance import Provenance
from joni.autonomy.core_state import CoreState, seed_core


def _grown_state(n: int = 12):
    cs = CoreState(seed_core())
    for i in range(n):
        cs.learn(f"claim number {i} about routing and load", "routing", source_id=f"arxiv:{i}")
    return cs.core


def _save(state, path, chunk, monkeypatch):
    monkeypatch.setenv("JONI_JOURNAL_CHUNK", str(chunk))
    return persistence.save(state, path)


def test_chunked_round_trip_is_identical(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    head = json.loads(p.read_text())
    assert "journal" not in head and head["journal_chunks"]["files"]
    assert (tmp_path / "layer9.journal").is_dir()
    loaded = persistence.load(p, verify=True)             # full verify: hash + chain
    assert snapshot_hash(loaded) == snapshot_hash(state)
    assert len(loaded.journal) == len(state.journal)


def test_sealed_chunks_are_not_rewritten_on_the_next_save(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    cdir = tmp_path / "layer9.journal"
    sealed = sorted(cdir.glob("chunk-*.jsonl"))[0]
    marker = sealed.read_text()
    sealed_stat = sealed.stat().st_mtime_ns
    # grow the journal and save again: the sealed chunk must be byte-identical AND untouched
    cs = CoreState(persistence.load(p))
    cs.learn("one more claim about routing", "routing")
    _save(cs.core, p, 10, monkeypatch)
    assert sealed.read_text() == marker
    assert sealed.stat().st_mtime_ns == sealed_stat       # skipped, not rewritten
    assert snapshot_hash(persistence.load(p)) == snapshot_hash(cs.core)


def test_legacy_inline_file_still_loads_and_migrates_on_save(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    monkeypatch.setenv("JONI_JOURNAL_CHUNK", "0")         # legacy format
    persistence.save(state, p)
    assert "journal" in json.loads(p.read_text())
    monkeypatch.setenv("JONI_JOURNAL_CHUNK", "10")
    legacy = persistence.load(p, verify=True)             # loads fine
    persistence.save(legacy, p)                           # first save migrates to chunks
    head = json.loads(p.read_text())
    assert "journal" not in head and head["journal_chunks"]["files"]
    assert snapshot_hash(persistence.load(p, verify=True)) == snapshot_hash(state)


def test_a_truncated_chunk_refuses_to_load_by_name(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    chunk = sorted((tmp_path / "layer9.journal").glob("chunk-*.jsonl"))[0]
    lines = chunk.read_text().splitlines()
    chunk.write_text("\n".join(lines[:-1]) + "\n")        # drop one entry
    try:
        persistence.load(p, verify=True)
        raise AssertionError("a truncated chunk must not load")
    except ValueError as exc:
        assert chunk.name in str(exc)


def test_a_tampered_chunk_fails_the_seal(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    chunk = sorted((tmp_path / "layer9.journal").glob("chunk-*.jsonl"))[0]
    lines = chunk.read_text().splitlines()
    e = json.loads(lines[1])
    e["payload"]["text"] = "history, edited"              # same count, different content
    lines[1] = json.dumps(e, ensure_ascii=False)
    chunk.write_text("\n".join(lines) + "\n")
    try:
        persistence.load(p, verify=True)
        raise AssertionError("a tampered chunk must not verify")
    except ValueError:
        pass                                              # hash/chain verification caught it


def test_compaction_shrinks_and_prunes_stale_chunks(monkeypatch, tmp_path):
    # a compacted (smaller) journal rewrites its chunks and drops leftover higher ones
    state = _grown_state(25)
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    n_before = len(list((tmp_path / "layer9.journal").glob("chunk-*.jsonl")))
    out = persistence.compact(p)
    assert out["entries"] == len(state.journal)
    reloaded = persistence.load(p, verify=True)
    assert snapshot_hash(reloaded) == snapshot_hash(state)
    assert len(list((tmp_path / "layer9.journal").glob("chunk-*.jsonl"))) <= n_before


def test_repair_reseals_a_chunked_state(monkeypatch, tmp_path):
    state = _grown_state()
    p = tmp_path / "layer9.json"
    _save(state, p, 10, monkeypatch)
    head = json.loads(p.read_text())
    head["snapshot_hash"] = "0" * 64                      # drifted seal, chain intact
    p.write_text(json.dumps(head))
    assert persistence.repair(p) is True
    assert persistence.load(p, verify=True) is not None


def _mint(core, text):
    core.submit(make_proposal(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
                              payload={"text": text, "topic": "routing"}, proposer="source",
                              provenance=Provenance.from_source("arxiv:x")), actor="joni")


def test_empty_state_round_trips_chunked(monkeypatch, tmp_path):
    from desi_layer9 import Layer9
    p = tmp_path / "layer9.json"
    state = Layer9()
    _mint(state, "a single claim")
    _save(state, p, 10, monkeypatch)
    assert snapshot_hash(persistence.load(p, verify=True)) == snapshot_hash(state)
