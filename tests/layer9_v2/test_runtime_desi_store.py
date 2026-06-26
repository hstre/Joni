"""The desi_layer9 SQLite runtime backend: materialised round-trip equals the kernel's own state,
and the core_state seam selects it only under JONI_PERSISTENCE=sqlite (default JSON unchanged)."""
from __future__ import annotations

import pytest

from desi_layer9.hashing import snapshot_hash, verify_chain
from joni.autonomy import core_state
from joni.autonomy.config import Paths
from joni.layer9_v2.runtime import desi_store


def _core():
    """A small but non-trivial real desi_layer9 state (seeded claims + journal + ledger)."""
    return core_state.seed_core()


def test_roundtrip_is_byte_for_byte_equivalent(tmp_path):
    core = _core()
    db = tmp_path / "layer9.sqlite"
    desi_store.save(core, db)
    restored = desi_store.load(db)
    assert snapshot_hash(restored) == snapshot_hash(core)     # kernel's own hash, unchanged
    assert verify_chain(restored)[0]
    assert len(restored._objects) == len(core._objects)
    assert len(restored.journal) == len(core.journal)


def test_load_no_replay_uses_materialised_objects(tmp_path):
    """The store must reconstruct via snapshot.restore (materialised), never re-run the journal —
    proven by loading with an EMPTY journal still yielding the full object set."""
    core = _core()
    db = tmp_path / "layer9.sqlite"
    desi_store.save(core, db)
    # wipe the journal rows: a replay-based loader would now lose all objects; restore must not
    import sqlite3
    con = sqlite3.connect(db)
    con.execute("DELETE FROM journal")
    con.commit()
    con.close()
    restored = desi_store.load(db, verify=False)
    assert len(restored._objects) == len(core._objects)       # from the snapshot, not replay


def test_load_missing_store_returns_none(tmp_path):
    assert desi_store.load(tmp_path / "absent.sqlite") is None


def test_verify_detects_a_tampered_object(tmp_path):
    core = _core()
    db = tmp_path / "layer9.sqlite"
    desi_store.save(core, db)
    import sqlite3
    con = sqlite3.connect(db)
    # drop one materialised object so the restored snapshot hash no longer matches the sealed one
    con.execute("DELETE FROM objects WHERE id = (SELECT id FROM objects LIMIT 1)")
    con.commit()
    con.close()
    with pytest.raises(ValueError):
        desi_store.load(db, verify=True)


def test_core_state_selects_sqlite_only_when_flagged(tmp_path, monkeypatch):
    paths = Paths(tmp_path)
    (tmp_path / "state").mkdir()
    cs = core_state.CoreState(_core())

    # default (json): writes the JSON core, no sqlite store
    monkeypatch.delenv("JONI_PERSISTENCE", raising=False)
    core_state.save(cs, paths)
    assert paths.core.exists()
    assert not paths.core_sqlite.exists()

    # sqlite: writes the sqlite store, and load_or_migrate restores an equivalent state
    monkeypatch.setenv("JONI_PERSISTENCE", "sqlite")
    core_state.save(cs, paths)
    assert paths.core_sqlite.exists()
    resumed = core_state.load_or_migrate(paths)
    assert snapshot_hash(resumed.core) == snapshot_hash(cs.core)


def test_sqlite_backend_adopts_existing_json_on_first_run(tmp_path, monkeypatch):
    """Flipping the flag on for the first time (sqlite store absent) must adopt the existing JSON
    core, not seed a fresh state — so the cutover loses nothing."""
    paths = Paths(tmp_path)
    (tmp_path / "state").mkdir()
    cs = core_state.CoreState(_core())
    monkeypatch.delenv("JONI_PERSISTENCE", raising=False)
    core_state.save(cs, paths)                       # only the JSON core exists

    monkeypatch.setenv("JONI_PERSISTENCE", "sqlite")
    resumed = core_state.load_or_migrate(paths)      # sqlite absent -> adopt JSON
    assert snapshot_hash(resumed.core) == snapshot_hash(cs.core)
