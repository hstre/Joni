"""PR 3 - hash-chained ledger, replay equality, snapshot equality, migration."""

import json

import pytest

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9 import migration, persistence
from desi_layer9.provenance import Provenance


def _seed_core() -> l9.Layer9:
    core = l9.Layer9()
    p = l9.make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_CREATE,
                         payload={"text": "x", "topic": "t"},
                         proposer="joni", provenance=Provenance.from_operator())
    core.submit(p)
    cid = core.all(l9.ObjectType.CLAIM)[0].id
    core.submit(l9.make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_REVISE,
                                 payload={"to_status": "active"},
                                 proposer="joni", provenance=Provenance.from_operator(),
                                 target_objects=(cid,)))
    return core


# -- hash chain ------------------------------------------------------------- #

def test_ledger_chain_verifies():
    core = _seed_core()
    ok, problems = l9.verify_chain(core)
    assert ok and problems == []


def test_tampering_a_past_event_breaks_the_chain():
    core = _seed_core()
    # the PUBLIC ledger hands back deep copies, so an external edit cannot reach the chain...
    core.ledger[0].reason = "tampered"
    ok, _ = l9.verify_chain(core)
    assert ok
    # ...but STORAGE-level tampering of the internal ledger is still detected.
    core._ledger[0].reason = "tampered"         # edit a historic event in place
    ok2, problems = l9.verify_chain(core)
    assert not ok2 and problems


# -- replay ----------------------------------------------------------------- #

def test_replay_reconstructs_the_same_state():
    core = _seed_core()
    replayed = persistence.replay(core.journal)
    assert l9.snapshot_hash(replayed) == l9.snapshot_hash(core)
    assert [e.event_hash for e in replayed.ledger] == [e.event_hash for e in core.ledger]


def test_persistence_roundtrip_continues_the_trajectory(tmp_path):
    core = _seed_core()
    path = persistence.save(core, tmp_path / "state.json")
    loaded = persistence.load(path)
    assert l9.snapshot_hash(loaded) == l9.snapshot_hash(core)
    # the loaded core keeps writing onto the same audited trajectory
    cid = loaded.all(l9.ObjectType.CLAIM)[0].id
    loaded.submit(l9.make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_CONTEST, payload={},
                                   proposer="joni", provenance=Provenance.from_operator(),
                                   target_objects=(cid,)))
    assert loaded.get(cid).status is l9.Status.CONTESTED


def test_load_detects_a_corrupted_snapshot(tmp_path):
    core = _seed_core()
    path = persistence.save(core, tmp_path / "s.json")
    doc = json.loads(path.read_text())
    doc["snapshot_hash"] = "deadbeef"
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        persistence.load(path)


# -- migration -------------------------------------------------------------- #

_KEVIN_JSONL = (
    '{"name": "red_flags_first", "origin": "medicine", "summary": "s", "steps": ["a", "b"]}\n'
    '{"name": "claim_splitting", "origin": "DESi", "summary": "s2", "steps": ["c"]}\n'
    'this is not json\n'                          # -> quarantine
)
_JONI_STATE = {
    "claims": [{"id": "C-1", "text": "local-first is private", "topic": "privacy",
                "status": "confirmed"}],
    "goals": [{"id": "G-1", "text": "run locally", "horizon": "long", "priority": 0.8}],
    "memory": [{"id": "M-1", "summary": "learned X", "refs": ["C-1"]}],
}


def test_migration_imports_kevin_methods_as_provisional():
    core, report = migration.migrate(kevin_jsonl=_KEVIN_JSONL)
    methods = core.all(l9.ObjectType.METHOD)
    assert len(methods) == 2
    assert all(m.status is l9.Status.PROVISIONAL for m in methods)   # never straight to active
    assert report.quarantined                                        # the bad line was caught


def test_migration_imports_joni_state_conservatively():
    core, report = migration.migrate(joni_state=_JONI_STATE)
    claim = core.all(l9.ObjectType.CLAIM)[0]
    # an old "confirmed" claim comes in at most active - it must re-earn confirmation
    assert claim.status is l9.Status.ACTIVE
    assert claim.provenance.origin_type is l9.OriginType.IMPORTED_STATE
    assert report.counts.get("claims") == 1 and report.counts.get("goals") == 1


def test_migration_is_deterministic_and_idempotent():
    a, _ = migration.migrate(joni_state=_JONI_STATE, kevin_jsonl=_KEVIN_JSONL)
    b, _ = migration.migrate(joni_state=_JONI_STATE, kevin_jsonl=_KEVIN_JSONL)
    assert l9.snapshot_hash(a) == l9.snapshot_hash(b)


def test_migrated_state_is_replayable():
    core, _ = migration.migrate(joni_state=_JONI_STATE, kevin_jsonl=_KEVIN_JSONL)
    replayed = persistence.replay(core.journal)
    assert l9.snapshot_hash(replayed) == l9.snapshot_hash(core)
    ok, _ = l9.verify_chain(core)
    assert ok
