import pytest

from joni import desi_link

# Skip the whole module unless a DESi checkout is reachable (import desi_router, or
# DESI_ROOT pointing at one). CI without DESi skips; locally, set DESI_ROOT.
if not desi_link.available():
    pytest.skip("DESi not available (set DESI_ROOT to a DESi checkout)",
                allow_module_level=True)


def test_disabled_without_flag(monkeypatch):
    monkeypatch.delenv("JONI_USE_DESI", raising=False)
    assert desi_link.enabled() is False
    assert desi_link.try_tool("2+2") is None
    assert desi_link.route_model("scientific_claim", budget_usd=0.01) is None
    assert desi_link.routing_engine() == "joni-builtin"


def test_enabled_uses_real_desi_router(monkeypatch):
    monkeypatch.setenv("JONI_USE_DESI", "1")
    assert desi_link.enabled() is True
    assert desi_link.routing_engine() == "DESi"
    route = desi_link.route_model("scientific_claim", budget_usd=0.01)
    assert route is not None
    assert route["model"]                       # a concrete model was chosen
    assert route["cost_usd"] >= 0
    assert "reason" in route


def test_uses_non_math_tools_too(monkeypatch):
    """The user's ask: Joni may plug in DESi modules beyond arithmetic."""
    monkeypatch.setenv("JONI_USE_DESI", "1")
    # math
    assert desi_link.try_tool("2+2*5")["result"] == 12
    # date math (a non-math module)
    dm = desi_link.try_tool("days between 2026-06-06 and 2026-06-13")
    assert dm["tool"] == "date_math" and dm["result"] == 7
    # unit conversion (another non-math module)
    uc = desi_link.try_tool("100 km in miles")
    assert uc["task_class"] == "unit_conversion"


def test_unknown_task_class_falls_back(monkeypatch):
    monkeypatch.setenv("JONI_USE_DESI", "1")
    assert desi_link.route_model("not_a_real_class", budget_usd=0.01) is None


def test_cycle_routes_through_desi_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_USE_DESI", "1")
    monkeypatch.delenv("JONI_ONLINE", raising=False)   # offline mock sources
    from joni.autonomy.run import one_cycle

    summary = one_cycle()
    assert summary["routing"] == "DESi"
    protocol = (tmp_path / "protocol" / "protocol.jsonl").read_text()
    assert '"kind": "routed"' in protocol          # DESi model-routing decision logged
    assert '"kind": "tooled"' in protocol          # DESi tool used (runtime age)
    assert "DESi" in (tmp_path / "docs" / "index.html").read_text()
