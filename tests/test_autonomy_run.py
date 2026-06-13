import json
from datetime import UTC, datetime, timedelta

import pytest

from joni.autonomy import governance
from joni.autonomy.run import one_cycle


def _root(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.delenv("JONI_ONLINE", raising=False)  # offline -> MockFetcher
    return tmp_path


def test_one_cycle_produces_protocol_site_and_state(monkeypatch, tmp_path):
    root = _root(monkeypatch, tmp_path)
    summary = one_cycle()
    assert summary["new_items"] > 0
    assert summary["asks"] >= 1          # the conflict-operator paper raises an ask
    assert summary["spend"] == 0.0        # deterministic -> free

    assert (root / "docs" / "index.html").exists()
    assert "Joni" in (root / "docs" / "index.html").read_text()
    assert (root / "protocol" / "protocol.jsonl").read_text().strip()
    assert (root / "state" / "joni_state.json").exists()
    # The peripheral improvement was self-applied; the ask was queued for a human.
    ext = json.loads((root / "state" / "extensions.json").read_text())
    assert ext["topics_added"]
    assert ext["asks"]


def test_second_cycle_dedups(monkeypatch, tmp_path):
    _root(monkeypatch, tmp_path)
    one_cycle()
    second = one_cycle()
    assert second["cycle"] == 2
    assert second["new_items"] == 0


def test_runtime_window_retires_after_a_week(monkeypatch, tmp_path):
    root = _root(monkeypatch, tmp_path)
    (root / "state").mkdir(parents=True, exist_ok=True)
    old = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    (root / "state" / "run_window.json").write_text(
        json.dumps({"start": old, "runs": 5, "retired": False}))
    summary = one_cycle()
    assert summary["retired"] is True
    assert "RETIRED" in (root / "docs" / "index.html").read_text()


def test_tampered_core_stops_the_cycle(monkeypatch, tmp_path):
    root = _root(monkeypatch, tmp_path)
    path = governance.write_lock(root)
    d = json.loads(path.read_text())
    d["operators.py"] = "0" * 64
    path.write_text(json.dumps(d))
    with pytest.raises(governance.CoreChangeBlocked):
        one_cycle()
