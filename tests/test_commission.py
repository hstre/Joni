"""Joni commissions his own non-core extensions - Aufträge an Claude.

Each commission must be: deterministic, grounded in his own measured state, *non-core*
(targets only an extensible module), sustained before it fires, and de-duplicated by a
cooldown so a long run never spams Claude.
"""

from desi_layer9.semantics import adapter
from joni.autonomy import commission, homeostasis
from joni.autonomy.commission import _EXTENSIBLE
from joni.autonomy.core_state import CoreState, seed_core
from semantic_stub import StubSemanticLayer


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _non_core(c):
    assert c["touches_core"] is False
    assert c["component_key"] in _EXTENSIBLE
    assert c["addressed_to"] == "Claude"


# --- unqualified conflicts -> qualifier extension -----------------------------------------

def _open_unqualified(cs, n):
    for i in range(n):
        a = cs.learn(f"claim A{i} about routing", "routing")
        b = cs.learn(f"claim B{i} about memory", "memory")
        cs.open_conflict([a, b])                       # conflict_kind defaults to 'unqualified'


def test_unqualified_conflicts_commission_fires_after_it_is_sustained():
    cs = CoreState(seed_core())
    ext = {}
    _open_unqualified(cs, 4)
    proto = _Proto()

    first = commission.assess(cs, ext, proto, cycle=1)
    assert first == []                                 # sustain=2: one cycle is not enough

    out = commission.assess(cs, ext, proto, cycle=2)
    assert len(out) == 1
    c = out[0]
    assert c["kind"] == "unqualified_conflicts"
    assert c["component_key"] == "conflict-qualifier"
    _non_core(c)
    assert "4" in c["motivation"]                      # grounded in the real count
    assert c["evidence"]["unqualified_open"] == 4


def test_a_commission_is_not_re_filed_within_the_cooldown():
    cs = CoreState(seed_core())
    ext = {}
    _open_unqualified(cs, 5)
    proto = _Proto()
    commission.assess(cs, ext, proto, cycle=1)
    fired = commission.assess(cs, ext, proto, cycle=2)
    assert len(fired) == 1
    # next cycle, condition still holds, but it was just commissioned -> stays quiet
    again = commission.assess(cs, ext, proto, cycle=3)
    assert again == []
    # ... and only one full order is kept in the page log
    assert len([x for x in ext["commissions"] if x.get("title")]) == 1


def test_signal_resets_when_the_gap_closes():
    cs = CoreState(seed_core())
    ext = {}
    p = cs.learn("routing parent claim", "routing")
    hs = [cs.hypothesize(f"H{i}: routing relates X{i}", "routing", parents=(p,)) for i in range(3)]
    proto = _Proto()
    commission.assess(cs, ext, proto, cycle=1)         # starved signal -> 1
    assert ext["commission_signals"]["starved_topic"] == 1
    # the gap closes: one hypothesis earns evidence, so the topic is no longer starved
    ev = cs.learn("routing runs on device", "routing")
    cs.corroborate(hs[0], cs.core.get(ev), relation="supports")
    commission.assess(cs, ext, proto, cycle=2)
    assert ext["commission_signals"]["starved_topic"] == 0   # no longer counting


# --- starved topic -> reader/sources extension --------------------------------------------

def test_starved_topic_commission_when_a_topic_has_hypotheses_but_no_evidence():
    cs = CoreState(seed_core())
    ext = {}
    p = cs.learn("routing parent claim", "routing")
    for i in range(3):
        cs.hypothesize(f"Hypothesis {i}: routing relates to X{i}", "routing", parents=(p,))
    proto = _Proto()
    out = []
    for cyc in range(1, 4):                             # sustain = 3
        out = commission.assess(cs, ext, proto, cycle=cyc)
    assert len(out) == 1
    c = out[0]
    assert c["kind"] == "starved_topic"
    assert c["component_key"] == "reader-sources"
    _non_core(c)
    assert c["evidence"]["topic"] == "routing"
    assert c["evidence"]["hypotheses"] >= 3


def test_a_topic_that_earned_support_is_not_starved():
    cs = CoreState(seed_core())
    ext = {}
    p = cs.learn("routing parent claim", "routing")
    hs = [cs.hypothesize(f"Hypothesis {i}: routing relates to X{i}", "routing", parents=(p,))
          for i in range(3)]
    ev = cs.learn("routing runs on device", "routing")
    cs.corroborate(hs[0], cs.core.get(ev), relation="supports")   # it earned evidence
    proto = _Proto()
    for cyc in range(1, 5):
        out = commission.assess(cs, ext, proto, cycle=cyc)
    assert all(c["kind"] != "starved_topic" for c in out)


# --- semantic blind spot -> measurement extension -----------------------------------------

def test_semantic_blind_spot_commission_when_cosine_keeps_returning_insufficient():
    cs = CoreState(seed_core())
    ext = {}
    # build >=5 real cosine clusters that all land 'insufficient' (borderline band 0.55)
    for i in range(6):
        a = cs.learn(f"claim about routing variant {i}", "routing")
        b = cs.learn(f"claim about memory variant {i}", "memory")
        adapter.analyse_pair(cs.core, cs.core.get(a), cs.core.get(b),
                             layer=StubSemanticLayer(cosine_distance=0.55))
    proto = _Proto()
    out = []
    for cyc in range(1, 5):                             # sustain = 4
        homeostasis.vitality(cs, ext, proto, cyc)      # populates usable_semantic_rate (0.0)
        out = commission.assess(cs, ext, proto, cycle=cyc)
    assert ext["vitality"]["usable_semantic_rate"] == 0.0
    assert len(out) == 1
    c = out[0]
    assert c["kind"] == "semantic_blind_spot"
    assert c["component_key"] == "semantics-measurement"
    _non_core(c)
    assert c["evidence"]["insufficient"] >= 5


# --- stalled development -> emergence extension --------------------------------------------

def test_stalled_development_commission_after_a_long_stagnation():
    cs = CoreState(seed_core())
    ext = {"vitality": {"verdict": "steady", "stagnation_cycles": 12,
                        "unsupported_hypotheses": 3, "usable_semantic_rate": 0.5}}
    proto = _Proto()
    out = commission.assess(cs, ext, proto, cycle=1)   # sustain = 1
    assert len(out) == 1
    c = out[0]
    assert c["kind"] == "stalled_development"
    assert c["component_key"] == "emergence"
    _non_core(c)
