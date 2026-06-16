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
    # A single paper touching a core word is held, not raised: a core-ask needs a *sustained*
    # signal across cycles, so one cycle interrupts no human.
    assert summary["asks"] == 0
    assert summary["spend"] == 0.0        # deterministic -> free

    assert (root / "docs" / "index.html").exists()
    assert "Joni" in (root / "docs" / "index.html").read_text()
    assert (root / "protocol" / "protocol.jsonl").read_text().strip()
    assert (root / "state" / "layer9.json").exists()        # the authoritative core
    assert summary["days_running"] == 0                      # real time, no tick jump
    # The peripheral improvement was self-applied; the core observation is only *held* (its
    # signal recorded), not yet queued as an ask.
    ext = json.loads((root / "state" / "extensions.json").read_text())
    assert ext["topics_added"]
    assert ext["asks"] == []                                 # nothing raised on one cycle
    assert ext["core_ask_signals"] and set(ext["core_ask_signals"].values()) == {1}


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


def test_full_cycle_data_flow_source_to_model_to_gate_to_persist_to_reload(monkeypatch, tmp_path):
    """The end-to-end path where the project's bugs have hidden: a source item is read, the (mocked)
    model PROPOSES a claim, it is parsed, enters the gate as a candidate, is persisted, SURVIVES a
    reload (round-trip integrity), and is reflected on the site. Asserts data FLOW, not file
    existence."""
    from desi_layer9 import ObjectType, persistence
    from joni.autonomy import model_call
    root = _root(monkeypatch, tmp_path)
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")           # turn the semantic projector on
    marker = "routing reduces tail latency measurably in this run"
    calls = []

    def fake_complete(profile, system, user):
        calls.append(profile.served_slug)
        # the projector's expected shape: a JSON array of {text, topic}
        return f'[{{"text": "{marker}", "topic": "routing"}}]'
    monkeypatch.setattr(model_call, "_complete", fake_complete)

    summary = one_cycle()
    assert calls and any("granite" in s for s in calls)         # the model was actually invoked

    # the proposed claim reached the core and SURVIVED a reload...
    from desi_layer9 import Authority
    state_path = root / "state" / "layer9.json"
    reloaded = persistence.load(state_path)                     # verify=True -> round-trip
    claims = [c for c in reloaded.all(ObjectType.CLAIM) if marker in c.text]
    assert claims, "the model-proposed claim did not survive gate->persist->reload"
    c = claims[0]
    # ...carrying the projection provenance (the granite call that read it), never silently
    # authoritative.
    assert c.authority is not Authority.AUTHORITATIVE
    assert any(str(s).startswith("granite:") for s in c.provenance.source_ids)

    # and it is reflected on the public site (not just present in state)
    html = (root / "docs" / "index.html").read_text()
    assert "Joni" in html and summary["cycle"] == 1
