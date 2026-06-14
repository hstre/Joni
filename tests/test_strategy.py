"""Joni improves his own research strategy from his own results (the insufficient signal)."""

import desi_layer9 as l9
from joni.autonomy import strategy
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_insufficient(n):
    """Build a core whose recent semantic clusters are mostly 'insufficient'."""
    cs = CoreState(seed_core())
    from desi_layer9.semantics import adapter
    from desi_layer9.semantics.ports import NullSemanticLayer
    ids = [cs.learn(f"claim number {i} about routing under load", "routing") for i in range(n + 1)]
    live = {c.id: c for c in cs.active_claims()}
    for i in range(n):                                   # null layer -> insufficient
        adapter.analyse_pair(cs.core, live[ids[i]], live[ids[i + 1]], layer=NullSemanticLayer())
    return cs


def test_adapt_does_nothing_on_too_few_samples():
    cs = CoreState(seed_core())
    out = strategy.adapt(cs, {}, _Proto())
    assert out["changed"] is False and out["gap"] is None


def test_underframed_signal_changes_strategy_and_learns_queries():
    cs = _cs_with_insufficient(10)
    ext: dict = {}
    out = strategy.adapt(cs, ext, _Proto())
    assert out["gap"] == "underframed" and out["changed"] is True
    assert out["insufficient_rate"] >= 0.6
    # he now prefers full text and has learned framing-refined queries for next cycle
    assert ext["read_fulltext_priority"] is True
    assert ext["learned_queries"] and any("mechanism" in q for q in ext["learned_queries"])
    # and he recorded a provisional self-model claim about it (not a fact)
    sm = cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM)
    assert sm and any("under-framed" in s.text for s in sm)
    assert all(s.status is l9.Status.CANDIDATE for s in sm)


def test_strategy_is_self_limiting_no_duplicate_self_model():
    cs = _cs_with_insufficient(10)
    ext: dict = {}
    strategy.adapt(cs, ext, _Proto())
    before = len(cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM))
    strategy.adapt(cs, ext, _Proto())                    # same signal -> no new self-model claim
    assert len(cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM)) == before
