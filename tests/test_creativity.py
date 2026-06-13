import pytest

from joni.creativity import LocalCreativity, ProjectIdea, get_default_creativity
from joni.seed import seed_identity


def test_local_creativity_is_grounded_and_deterministic():
    s = seed_identity()
    eng = LocalCreativity()
    a = eng.propose(s, "routing")
    b = eng.propose(s, "routing")
    assert isinstance(a, ProjectIdea)
    assert a.engine == "local-creativity"
    assert a.title == b.title          # deterministic
    assert a.topic == "routing"


def test_default_engine_is_local_without_the_flag(monkeypatch):
    monkeypatch.delenv("JONI_USE_KEVIN", raising=False)
    assert get_default_creativity().name == "local-creativity"


def test_kevin_engine_proposes_when_enabled_and_available(monkeypatch):
    pytest.importorskip("kevin")
    monkeypatch.setenv("JONI_USE_KEVIN", "1")
    eng = get_default_creativity()
    assert eng.name == "kevin"
    idea = eng.propose(seed_identity(), "routing")
    assert idea.engine == "kevin"
    assert idea.title
    assert "Kevin" in idea.rationale


def test_kevin_backed_identity_is_replay_stable(monkeypatch):
    pytest.importorskip("kevin")
    from joni import Joni
    from joni.creativity import KevinCreativity

    a = Joni(creativity=KevinCreativity())
    b = Joni(creativity=KevinCreativity())
    a.live(ticks=8)
    b.live(ticks=8)
    assert [e.summary for e in a.state.ledger] == [e.summary for e in b.state.ledger]
    # A Kevin-proposed project should be present and credited to the kevin engine.
    assert any(e.reviewed_by == "kevin" for e in a.state.ledger)
