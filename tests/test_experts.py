"""Joni's Alexandria panel: assessors, not authorities - they advise; Joni decides."""

from joni.autonomy import experts
from joni.autonomy.budget import Budget
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _enable(monkeypatch):
    monkeypatch.setenv("JONI_EXPERTS", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")


def _mock_ask(monkeypatch):
    def fake(expert, system, user, *, temperature=0.3):
        phase = "x" if "Cross-reconstruction" in system else "1"
        return f"[{expert['name']}/{expert['role']}/p{phase}] consistent under assumption A."
    monkeypatch.setattr(experts, "_ask", fake)


def test_convene_runs_two_phases_with_functionally_distinct_roles(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    rec = experts.convene("Is X consistent?", context="topic: routing")
    assert set(rec["experts"]) == {"claude", "chatgpt", "deepseek"}
    # functional diversity (Alexandria IV.3): strictly separated roles
    assert rec["roles"] == {"claude": "assessor", "chatgpt": "adversarial",
                            "deepseek": "consistency"}
    assert rec["phase1"] and rec["phase3"]            # parallel assessment + cross-reconstruction
    assert rec["calls"] == 6                          # 3 phase-1 + 3 cross


def _make_uncertain(cs, pos="routing should be local-first",
                    neg="routing should never be local-first"):
    """Put Joni in a genuinely unsure state: two claims he holds that the deterministic detector
    opens as a hard contradiction (the way conflicts really arise)."""
    a = cs.learn(pos, "routing")
    b = cs.learn(neg, "routing")
    cs.detect_and_open_conflicts()
    return a, b


def test_convenes_when_unsure_takes_assessments_as_sources_and_never_decides(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    a, b = _make_uncertain(cs)
    budget = Budget(week_start="2026-06-14T00:00:00", spent_eur=0.0, runs=0, cap_eur=20.0)
    out = experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)
    assert out["convened"] is True
    # the panel did NOT decide: the conflict is still open, neither claim resolved
    assert any(x.conflict_status.value == "open" for x in cs.core.open_conflicts())
    # advice entered as SOURCES (never the privileged HUMAN origin)
    panel_claims = [c for c in cs.active_claims()
                    if any("panel:expert:" in s for s in c.provenance.source_ids)]
    assert panel_claims
    assert all(c.provenance.origin_type.value == "source" for c in panel_claims)
    assert budget.spent_eur > 0                        # the round was charged to the budget


def test_no_panel_when_nothing_to_assess(monkeypatch):
    """No open conflict and no fresh suggestion (a plain single-topic hypothesis is neither) ->
    no panel, no spend."""
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=())
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    out = experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)
    assert out["convened"] is False
    assert budget.spent_eur == 0.0


def test_panel_convenes_on_a_kevin_suggestion_and_explains_it(monkeypatch):
    """No uncertainty, but Kevin proposed a method/lens -> the panel assesses whether it is a
    good idea (advice, not a decision), and that explanation enters as a SOURCE."""
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    cs.propose_method(name="latency-as-a-lens",
                      summary="treat latency as a transferable lens across topics",
                      applicable_to=("routing", "memory"), origin="joni:emergent")
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    out = experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)
    assert out["convened"] is True
    panel_claims = [c for c in cs.active_claims()
                    if any("panel:expert:" in s for s in c.provenance.source_ids)]
    assert panel_claims                                  # the good/bad assessment is recorded
    assert all(c.provenance.origin_type.value == "source" for c in panel_claims)


def test_an_invented_cross_topic_hypothesis_is_assessed_as_a_suggestion(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    p1 = cs.learn("routing reduces latency", "routing")
    p2 = cs.learn("memory continuity matters", "memory")
    cs.hypothesize("Hypothesis: the latency pattern from routing may carry to memory",
                   "routing+memory", parents=(p1, p2))     # a '+' topic = an invented leap
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    assert experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)["convened"] is True


def test_panel_respects_a_cooldown_between_uncertainties(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    _make_uncertain(cs)
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    ext: dict = {}
    assert experts.maybe_convene(cs, ext, _Proto(), budget, cycle=10)["convened"] is True
    # a second, distinct uncertainty appears immediately - but the cooldown holds the panel
    _make_uncertain(cs, "routing must always be remote", "routing must never be remote")
    assert experts.maybe_convene(cs, ext, _Proto(), budget, cycle=12)["convened"] is False
    # once the cooldown elapses, the new uncertainty is assessed
    assert experts.maybe_convene(cs, ext, _Proto(), budget, cycle=16)["convened"] is True


def test_panel_is_off_by_default(monkeypatch):
    monkeypatch.delenv("JONI_EXPERTS", raising=False)
    cs = CoreState(seed_core())
    _make_uncertain(cs)
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    assert experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)["convened"] is False


def test_panel_deferred_when_weekly_budget_is_exhausted(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    _make_uncertain(cs)                                                   # he IS unsure...
    budget = Budget(week_start="t", spent_eur=19.99, runs=0, cap_eur=20.0)   # ...but < 0.15 left
    assert experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)["convened"] is False
