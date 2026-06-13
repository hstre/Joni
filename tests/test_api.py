import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from joni import api  # noqa: E402

client = TestClient(api.app)


def setup_function():
    # Each test starts from a fresh identity (the app holds a shared one).
    client.post("/api/reset")


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "Joni" in r.text


def test_live_then_respond_returns_both_views():
    client.post("/api/live", json={"ticks": 8})
    r = client.post("/api/respond", json={"prompt": "what's your take on privacy?"})
    assert r.status_code == 200
    d = r.json()
    assert d["conversation"]
    e = d["epistemic"]
    # After living, the privacy turn should report a reasoned change of mind.
    assert e["operator"] == "conflict_resolution"
    assert e["trigger"] == "contradictory_evidence"
    assert e["ledger_event"] and e["ledger_event"].startswith("L9-")


def test_respond_requires_a_prompt():
    assert client.post("/api/respond", json={"prompt": ""}).status_code == 422


def test_cited_ledger_event_exists_in_ledger():
    client.post("/api/live", json={"ticks": 8})
    e = client.post("/api/respond", json={"prompt": "privacy?"}).json()["epistemic"]
    ledger_ids = {ev["id"] for ev in client.get("/api/ledger").json()["ledger"]}
    assert e["ledger_event"] in ledger_ids


def test_state_exposes_rejected_claims_after_living():
    client.post("/api/live", json={"ticks": 8})
    claims = client.get("/api/state").json()["claims"]
    assert any(c["status"] == "rejected" for c in claims)
    assert any(c["changes"] >= 1 for c in claims)


def test_tick_advances_and_returns_events():
    d = client.post("/api/tick").json()
    assert d["snapshot"]["tick"] == 1
    assert isinstance(d["events"], list)
