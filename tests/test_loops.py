from joni import Joni
from joni.loops import ResearchHarvester, run_tick
from joni.models import ClaimStatus
from joni.router import Router
from joni.seed import seed_identity


def test_tick_advances_and_audits():
    s = seed_identity()
    events = run_tick(s, Router(), ResearchHarvester())
    assert s.tick == 1
    assert events  # the tick produced ledger events
    assert all(e.tick == 1 for e in events)


def test_living_overturns_a_weak_seed_belief():
    """Over several ticks the harvester must contradict and reject a weak seed claim."""
    j = Joni()
    seed_privacy = next(c for c in j.state.claims.values() if c.topic == "privacy")
    assert seed_privacy.status is ClaimStatus.ACTIVE
    j.live(ticks=8)
    # The weak privacy belief should have been rejected via conflict resolution.
    assert j.state.claims[seed_privacy.id].status is ClaimStatus.REJECTED
    last = j.state.claims[seed_privacy.id].history[-1]
    assert last.operator.value == "conflict_resolution"
    assert last.trigger.value == "contradictory_evidence"


def test_living_is_replay_stable():
    a, b = Joni(), Joni()
    a.live(ticks=10)
    b.live(ticks=10)
    assert [e.id for e in a.state.ledger] == [e.id for e in b.state.ledger]
    assert [e.summary for e in a.state.ledger] == [e.summary for e in b.state.ledger]
    assert a.snapshot() == b.snapshot()


def test_spend_is_bounded_by_budget():
    j = Joni(budget=0.005)
    j.live(ticks=20)
    assert j.router.remaining() >= 0
    assert j.state.total_spend() <= 0.005 + 1e-9
