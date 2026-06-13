import json

import pytest

from joni.autonomy import governance


def test_core_hashes_cover_all_protected_modules():
    hashes = governance.compute_core_hashes()
    assert set(hashes) == set(governance.PROTECTED_CORE)
    assert all(len(h) == 64 for h in hashes.values())


def test_lock_roundtrip_verifies_clean(tmp_path):
    governance.write_lock(tmp_path)
    ok, changed = governance.verify_core(tmp_path)
    assert ok and changed == []


def test_missing_lock_is_treated_as_unfrozen(tmp_path):
    ok, changed = governance.verify_core(tmp_path)
    assert ok and changed == []


def test_tampered_lock_is_a_violation(tmp_path):
    path = governance.write_lock(tmp_path)
    d = json.loads(path.read_text())
    d["operators.py"] = "0" * 64
    path.write_text(json.dumps(d))
    ok, changed = governance.verify_core(tmp_path)
    assert not ok and "operators.py" in changed
    with pytest.raises(governance.CoreChangeBlocked):
        governance.assert_core_unchanged(tmp_path)


def test_kind_classification_enforces_the_rule():
    assert governance.is_autonomous("track_topic")
    assert governance.is_autonomous("note_capability")
    assert not governance.is_autonomous("core_change")
    assert governance.requires_human("core_change")
    assert not governance.requires_human("track_topic")


def test_write_allowlist():
    assert governance.is_peripheral_path("state/joni_state.json")
    assert governance.is_peripheral_path("docs/index.html")
    assert governance.is_peripheral_path("protocol/protocol.jsonl")
    assert not governance.is_peripheral_path("src/joni/operators.py")
    assert not governance.is_peripheral_path("src/joni/autonomy/run.py")
