from joni.models import ModelTier
from joni.router import Router


def test_no_language_is_deterministic_and_free():
    r = Router()
    d = r.route(needs_language=False)
    assert d.tier is ModelTier.DETERMINISTIC
    assert d.cost == 0.0


def test_routine_language_stays_local():
    r = Router()
    d = r.route(needs_language=True, hard=False)
    assert d.tier is ModelTier.LOCAL_SMALL
    assert d.model_name == "granite-micro"
    assert d.cost == 0.0


def test_hard_task_uses_external_when_budget_allows():
    r = Router(budget=1.0)
    d = r.route(needs_language=True, hard=True)
    assert d.tier is ModelTier.EXTERNAL_API
    assert d.model_name == "deepseek-chat"
    assert d.cost > 0


def test_hard_task_degrades_when_budget_exhausted():
    r = Router(budget=0.0)
    d = r.route(needs_language=True, hard=True)
    assert d.tier is ModelTier.LOCAL_SPECIALIST


def test_charge_reduces_remaining_budget():
    r = Router(budget=0.01)
    d = r.route(needs_language=True, hard=True)
    before = r.remaining()
    r.charge(d)
    assert r.remaining() == round(before - d.cost, 4)
