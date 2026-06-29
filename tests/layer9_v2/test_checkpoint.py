"""Cold-start checkpoint: restore the materialised state without replaying the journal."""
from __future__ import annotations

from desi_layer9.hashing import snapshot_hash
from joni.autonomy.core_state import seed_core
from joni.layer9_v2.runtime import desi_store


def test_checkpoint_round_trip_skips_replay(tmp_path):
    core = seed_core()
    # the committed JSON journal (source of truth) and a checkpoint written from the same state
    from desi_layer9 import persistence
    json_path = tmp_path / "layer9.json"
    persistence.save(core, json_path)
    ckpt = tmp_path / "layer9.checkpoint.json"
    desi_store.write_checkpoint(core, ckpt)

    restored = desi_store.load_via_checkpoint(json_path, ckpt)
    assert restored is not None
    assert snapshot_hash(restored) == snapshot_hash(core)     # exact materialised state, no replay


def test_stale_checkpoint_is_rejected(tmp_path):
    core = seed_core()
    from desi_layer9 import persistence
    json_path = tmp_path / "layer9.json"
    persistence.save(core, json_path)
    ckpt = tmp_path / "layer9.checkpoint.json"
    desi_store.write_checkpoint(core, ckpt)
    # corrupt the checkpoint's sealed hash -> must be rejected (caller replays), never trusted
    import json
    d = json.loads(ckpt.read_text())
    d["snapshot_hash"] = "0" * 64
    ckpt.write_text(json.dumps(d))
    assert desi_store.load_via_checkpoint(json_path, ckpt) is None


def test_missing_checkpoint_returns_none(tmp_path):
    out = desi_store.load_via_checkpoint(tmp_path / "absent.json", tmp_path / "absent.ckpt")
    assert out is None
