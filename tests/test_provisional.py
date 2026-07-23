"""HindsightTag H0: the provisional-episodic layer object + its first deterministic transition.
Strictly validated, two salience values kept separate, append-only. Nothing consolidates itself;
the ephemeral->provisional move is deterministic and 'unknown stays unknown'."""
from __future__ import annotations

import pytest

from joni.method_trial import provisional as pv


def _entry(**over):
    base = dict(kind=pv.EntryKind.OBSERVATION, content="an odd tool output", source="toolout",
                created_cycle=3, attention_salience=0.5)
    base.update(over)
    return pv.ProvisionalEntry(**base)


def test_a_valid_entry_round_trips_and_ids_deterministically():
    e = _entry()
    assert e.entry_id().startswith("prov-") and len(e.entry_id()) == 21
    assert pv.ProvisionalEntry.from_record(e.to_record()).entry_id() == e.entry_id()
    assert e.stage is pv.LifecycleStage.EPHEMERAL


def test_the_two_salience_values_are_separate_and_bounded():
    e = _entry(attention_salience=0.9, epistemic_significance=0.1)
    assert e.attention_salience == 0.9 and e.epistemic_significance == 0.1   # loud but not weighty
    with pytest.raises(ValueError):
        _entry(attention_salience=1.5)
    with pytest.raises(ValueError):
        _entry(epistemic_significance=True)              # bool is not a significance


def test_strict_validation_rejects_bad_fields():
    with pytest.raises(ValueError):
        _entry(content="  ")                             # blank
    with pytest.raises(ValueError):
        _entry(source="")                                # provenance required
    with pytest.raises(ValueError):
        _entry(ttl=0)                                    # ttl >= 1
    with pytest.raises(ValueError):
        _entry(created_cycle=-1)
    with pytest.raises(ValueError):
        pv.ProvisionalEntry.from_record({**_entry().to_record(), "surprise": 1})


def test_settle_is_deterministic_ephemeral_to_provisional():
    hot = _entry(attention_salience=0.5)
    assert pv.settle(hot).stage is pv.LifecycleStage.PROVISIONAL      # clears the bar -> settles
    cold = _entry(attention_salience=0.1)
    assert pv.settle(cold).stage is pv.LifecycleStage.EPHEMERAL       # below bar -> stays ephemeral
    # a non-ephemeral entry is returned unchanged (settle only acts on ephemeral)
    already = _entry(stage=pv.LifecycleStage.PROVISIONAL)
    assert pv.settle(already) is already


def test_expiry_is_by_the_ttl_clock():
    e = _entry(created_cycle=3, ttl=5)
    assert pv.is_expired(e, current_cycle=8) is False    # exactly at the horizon: still alive
    assert pv.is_expired(e, current_cycle=9) is True
    assert pv.expire(e).stage is pv.LifecycleStage.EXPIRED


def test_record_and_load_are_append_only_and_dedupe(tmp_path):
    store = tmp_path / "provisional.jsonl"
    e = _entry()
    assert pv.record([e, e], store_path=store) == 1                   # de-duped within the write
    assert pv.record([_entry(created_cycle=4)], store_path=store) == 1
    loaded = pv.load(store)
    assert len(loaded) == 2
    # last line wins: a later stage transition supersedes the earlier write of the same entry
    pv.record([pv.settle(e)], store_path=store)
    by_id = {x.entry_id(): x for x in pv.load(store)}
    assert by_id[e.entry_id()].stage is pv.LifecycleStage.PROVISIONAL
    # a malformed line is skipped, never fatal
    store.write_text(store.read_text() + "{ not json\n")
    assert len(pv.load(store)) == 2


def test_record_missing_store_is_a_clean_noop(tmp_path):
    assert pv.record([_entry()], store_path=None) == 0
    assert pv.record([], store_path=tmp_path / "x.jsonl") == 0
    assert pv.load(tmp_path / "nope.jsonl") == []
