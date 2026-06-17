"""Replay must reproduce a journal that spans a tick change (the midnight-rollover bug)."""

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, make_proposal, persistence
from desi_layer9.provenance import Provenance


def _add_claim(core, text, tick):
    core._tick = tick                                # white-box: advance the internal logical tick
    core.submit(make_proposal(
        ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
        payload={"text": text, "topic": "t"}, proposer="source",
        provenance=Provenance.from_source("s")), actor="joni")


def test_round_trip_across_a_tick_change(tmp_path):
    core = l9.Layer9()
    _add_claim(core, "made on day zero", 0)
    _add_claim(core, "made on day one", 1)          # the tick advanced mid-journal
    _add_claim(core, "made on day two", 2)
    path = tmp_path / "l9.json"
    persistence.save(core, path)
    loaded = persistence.load(path)                 # strict load re-verifies the hash
    assert loaded is not None
    # each object kept the tick it was actually created at
    ticks = sorted(c.created_tick for c in loaded.all(l9.ObjectType.CLAIM))
    assert ticks == [0, 1, 2]


def test_repair_fixes_a_legacy_state_without_per_entry_ticks(tmp_path):
    import json

    # simulate a pre-fix state: a journal whose entries have no 'tick', but whose snapshot
    # hash was computed with a later tick (as the live midnight rollover produced).
    core = l9.Layer9()
    _add_claim(core, "a", 0)
    core._tick = 1
    _add_claim(core, "b", 1)
    doc = persistence.to_doc(core)
    for e in doc["journal"]:
        e.pop("tick", None)                         # strip per-entry ticks (legacy format)
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(doc))

    import pytest
    with pytest.raises(ValueError):
        persistence.load(path)                      # strict load fails (the reported bug)
    assert persistence.repair(path) is True         # repair re-records a consistent hash
    assert persistence.load(path) is not None       # now it loads cleanly
