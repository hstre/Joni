"""Joni strengthens his own ideas: test, vet, and let them earn candidate -> active."""

import desi_layer9 as l9
from joni.autonomy import strengthen
from joni.autonomy.core_state import CoreState
from semantic_stub import StubSemanticLayer


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_a_hypothesis():
    cs = CoreState(l9.Layer9())
    p1 = cs.learn("teams care about routing speed", "routing", source_id="arxiv:p1")
    p2 = cs.learn("sessions benefit from routing choices", "routing", source_id="arxiv:p2")
    # supporting evidence claims from DISTINCT sources (independent origins) that overlap the
    # hypothesis strongly - promotion now requires independent backing, not circularity.
    cs.learn("routing locally reduces latency on small tasks", "routing", source_id="arxiv:1")
    cs.learn("routing reduces latency under heavy load", "routing", source_id="arxiv:2")
    cs.learn("routing decisions drive lower latency overall", "routing", source_id="arxiv:3")
    h = cs.hypothesize("Hypothesis: routing locally reduces latency", "routing",
                       parents=(p1, p2))
    return cs, h


def test_idea_earns_support_and_is_promoted_to_active_not_confirmed(monkeypatch):
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "promising")
    cs, h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto(), layer=StubSemanticLayer())  # governs supports
    assert out["supported"] >= 2
    hc = cs.core.get(h)
    assert hc.status is l9.Status.ACTIVE            # earned its way up...
    assert hc.status is not l9.Status.CONFIRMED     # ...but never auto-confirmed
    assert out["promoted"] >= 1


def test_kevin_rejection_is_advisory_not_a_veto(monkeypatch):
    """Kevin must never decide: even when Kevin calls an idea 'rejected'/thin, an idea that
    earned its support under the rules is still promoted. Kevin's verdict is recorded as advice
    only - it does not block promotion (and elsewhere it does not delete the idea either)."""
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "rejected")
    cs, h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["supported"] >= 2                    # it earned support under the rules...
    assert out["rejected"] >= 1                     # Kevin's reservation is recorded (advisory)
    assert out["promoted"] >= 1                     # ...and Kevin's veto no longer blocks it
    assert cs.core.get(h).status is l9.Status.ACTIVE          # the rules promote it
    assert cs.core.get(h).status is not l9.Status.CONFIRMED   # but never auto-confirmed


def test_circular_same_source_support_does_not_promote(monkeypatch):
    """Claim-to-claim circularity is not evidence: a hypothesis backed only by claims that all
    share one origin (same paper / model run) must NOT be promoted, however many there are."""
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "promising")
    cs = CoreState(l9.Layer9())
    p1 = cs.learn("teams care about routing speed", "routing", source_id="arxiv:same")
    p2 = cs.learn("sessions benefit from routing choices", "routing", source_id="arxiv:same")
    # every supporter shares the SAME source id -> one independent family, not enough
    cs.learn("routing locally reduces latency on small tasks", "routing", source_id="arxiv:same")
    cs.learn("routing reduces latency under heavy load", "routing", source_id="arxiv:same")
    cs.learn("routing decisions drive lower latency overall", "routing", source_id="arxiv:same")
    h = cs.hypothesize("Hypothesis: routing locally reduces latency", "routing", parents=(p1, p2))
    out = strengthen.strengthen(cs, {}, _Proto(), layer=StubSemanticLayer())
    assert out["supported"] >= 2                              # it accrued claim-to-claim support...
    assert cs.core.get(h).status is l9.Status.CANDIDATE       # ...but stayed candidate (no indep.)
    assert out["promoted"] == 0


def test_a_contradicted_idea_is_challenged_not_promoted(monkeypatch):
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "promising")
    cs, h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto(),
                                layer=StubSemanticLayer(audit_a="logically_rejected"))
    assert out["challenged"] >= 1
    assert cs.core.get(h).status is l9.Status.CANDIDATE     # not promoted while contradicted
    assert cs.core.open_conflicts()                         # the challenge is held open


def test_hypothesis_becomes_a_search_query():
    cs, h = _cs_with_a_hypothesis()
    ext: dict = {}
    strengthen.strengthen(cs, ext, _Proto(), layer=StubSemanticLayer())
    assert ext.get("learned_queries")               # Joni now actively seeks evidence for it


def test_without_semantic_layer_nothing_is_asserted():
    cs, h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto())   # NullSemanticLayer default -> insufficient
    assert out["supported"] == 0 and out["promoted"] == 0
    assert cs.core.get(h).status is l9.Status.CANDIDATE


def test_a_non_judgment_is_retried_not_permanently_burned(monkeypatch):
    """A layer-absent 'insufficient' must not consume a pair forever: when the Semantic
    Layer comes back, the same pair can still earn a real, governed support."""
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "promising")
    cs, h = _cs_with_a_hypothesis()
    ext: dict = {}
    # 1) layer absent -> only non-judgments; nothing is finalised as tested
    out1 = strengthen.strengthen(cs, ext, _Proto())          # NullSemanticLayer -> insufficient
    assert out1["supported"] == 0 and out1["promoted"] == 0
    assert out1["insufficient"] > 0
    assert not ext.get("hyp_tested")                         # pairs were NOT burned...
    assert ext.get("hyp_insufficient")                       # ...they are queued for retry
    # 2) the layer is available -> the very same pairs now earn support and promote
    out2 = strengthen.strengthen(cs, ext, _Proto(), layer=StubSemanticLayer())
    assert out2["supported"] >= 2
    assert cs.core.get(h).status is l9.Status.ACTIVE


def test_rotation_is_fair_no_hypothesis_starves(monkeypatch):
    """The least-recently-strengthened hypotheses are attended first, so a stuck oldest idea
    can't hog the single slot every cycle while the rest never get tested."""
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "rejected")  # all hollow
    cs = CoreState(l9.Layer9())
    p = cs.learn("a parent claim about routing", "routing")
    hyps = [cs.hypothesize(f"Hypothesis number {i} about routing latency", "routing",
                           parents=(p,)) for i in range(4)]
    ext: dict = {}
    attended: set[str] = set()
    # one hypothesis attended per cycle; over 4 cycles every hypothesis must get a turn
    for c in range(4):
        before = dict(ext.get("hyp_seen_cycle", {}))
        strengthen.strengthen(cs, ext, _Proto(), cycle=c, layer=StubSemanticLayer(), max_hyp=1)
        now = ext["hyp_seen_cycle"]
        attended |= {hid for hid, cyc in now.items() if before.get(hid) != cyc}
    assert set(hyps) <= attended            # all four were strengthened, none starved


def test_non_judgment_retries_are_bounded(monkeypatch):
    """Insufficient is retried, but not forever - after a bounded number it is finalised."""
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: "promising")
    cs, h = _cs_with_a_hypothesis()
    ext: dict = {}
    for _ in range(strengthen._MAX_INSUFFICIENT_RETRIES + 1):
        strengthen.strengthen(cs, ext, _Proto())             # always insufficient
    assert ext.get("hyp_tested")                             # gave up after a fair number of tries


def test_llm_judge_lets_an_idea_earn_support_when_the_layer_is_insufficient(monkeypatch, tmp_path):
    # #132: with the deterministic layer 'insufficient' (NullSemanticLayer), a gated LLM relation
    # judge renders the relation so development happens - from REAL evidence, never confirmed.
    from joni.autonomy import model_call
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_STRENGTHEN_LLM", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: "SUPPORTS")
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: None)
    cs, h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto(), cycle=1)      # layer=None -> insufficient
    assert out["supported"] >= 1                                # earned support via the LLM judge
    assert cs.core.get(h).status is not l9.Status.CONFIRMED     # still never auto-confirmed


def test_llm_judge_is_off_unless_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)   # gate closed
    monkeypatch.setattr(strengthen, "_kevin_verdict", lambda text, topic: None)
    cs, _h = _cs_with_a_hypothesis()
    out = strengthen.strengthen(cs, {}, _Proto(), cycle=1)
    assert out["supported"] == 0 and out["insufficient"] >= 1     # falls back to the bounded retry
