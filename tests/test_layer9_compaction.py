"""Journal compaction: drop the dead, derived ``measurement.pairs`` blob (the O(n²) per-pair log
the semantic adapter used to store but no logic ever reads), re-derive and re-seal. The file and the
replay shrink; the claim graph and every decision are preserved; the result loads + verifies."""

import json

import desi_layer9 as l9
from desi_layer9 import Operator as OP
from desi_layer9 import ProposalType as PT
from desi_layer9 import hashing, make_proposal, persistence
from desi_layer9.provenance import Provenance


def _core_with_fat_semantic(n_claims=4, blow=200):
    core = l9.Layer9()
    cids = []
    for i in range(n_claims):
        core.submit(make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_CREATE,
                    payload={"text": f"c{i}", "topic": "t"}, proposer="s",
                    provenance=Provenance.from_source(f"s{i}")), actor="j")
        cids.append(core.all(l9.ObjectType.CLAIM)[-1].id)
    # an OLD-style fat semantic annotation: the full O(n²) pair log in measurement.pairs, blown up
    # to simulate a large cluster (this is exactly the field that ballooned the live journal).
    pairs = [{"a": cids[i], "b": cids[k], "decision": "supports", "frame_a": "f", "frame_b": "f",
              "frame_tension": 0.0, "lexical_trigger": 0.5}
             for i in range(len(cids)) for k in range(i + 1, len(cids))] * blow
    core.submit(make_proposal(
        PT.SEMANTIC_PROPOSAL, OP.SEMANTIC_CLUSTER_PROPOSE,
        payload={"members": cids, "surface_terms": ["t"], "lexical_trigger": 0.5,
                 "measurement": {"pairs": pairs}, "decision": "supports",
                 "semantic_state": "semantic-measured", "decision_rationale": "r",
                 "semantic_layer": "stub", "semantic_layer_version": "0.1.0"},
        proposer="semantic_layer", provenance=Provenance.from_operator("run"),
        target_objects=tuple(cids)), actor="semantic_layer")
    return core, cids


def test_compaction_shrinks_file_preserves_graph_and_reseals(tmp_path):
    core, cids = _core_with_fat_semantic()
    p = tmp_path / "l9.json"
    persistence.save(core, p)
    big = p.stat().st_size
    before_claims = sorted(c.id for c in core.all(l9.ObjectType.CLAIM))
    cluster = core.all(l9.ObjectType.SEMANTIC_CLUSTER)[0]
    before_decision = cluster.decision

    info = persistence.compact(p)
    assert info["fields_stripped"] == 1
    assert p.stat().st_size < big                          # the dead blob is gone -> file shrank

    doc = json.loads(p.read_text())
    assert all("pairs" not in (e.get("payload") or {}).get("measurement", {})
               for e in doc["journal"])                    # no pairs anywhere in the slim journal

    loaded = persistence.load(p, verify=True)              # reloads + verify_chain clean
    assert loaded is not None
    ok, problems = hashing.verify_chain(loaded)
    assert ok, problems
    # the claim graph is unchanged, and the semantic verdict is preserved (only dead detail dropped)
    assert sorted(c.id for c in loaded.all(l9.ObjectType.CLAIM)) == before_claims
    assert loaded.all(l9.ObjectType.SEMANTIC_CLUSTER)[0].decision == before_decision


def test_compaction_is_a_noop_when_there_is_nothing_to_strip(tmp_path):
    core = l9.Layer9()
    for i in range(5):
        core.submit(make_proposal(PT.CLAIM_PROPOSAL, OP.CLAIM_CREATE,
                    payload={"text": f"c{i}", "topic": "t"}, proposer="s",
                    provenance=Provenance.from_source(f"s{i}")), actor="j")
    p = tmp_path / "l9.json"
    persistence.save(core, p)
    info = persistence.compact(p)
    assert info["fields_stripped"] == 0
    assert hashing.snapshot_hash(persistence.load(p, verify=True)) == hashing.snapshot_hash(core)
