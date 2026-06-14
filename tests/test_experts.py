"""Joni's Alexandria panel: assessors, not authorities - they advise; Joni decides."""

import desi_layer9 as l9
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


def test_maybe_convene_takes_assessments_as_sources_and_never_decides(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    h = cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    budget = Budget(week_start="2026-06-14T00:00:00", spent_eur=0.0, runs=0, cap_eur=20.0)
    out = experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)
    assert out["convened"] is True
    # the panel did NOT decide: the hypothesis is still a candidate, never confirmed/promoted
    assert cs.core.get(h).status is l9.Status.CANDIDATE
    # advice entered as SOURCES (never the privileged HUMAN origin)
    panel_claims = [c for c in cs.active_claims()
                    if any("panel:expert:" in s for s in c.provenance.source_ids)]
    assert panel_claims
    assert all(c.provenance.origin_type.value == "source" for c in panel_claims)
    assert budget.spent_eur > 0                        # the round was charged to the budget


def test_panel_is_off_by_default(monkeypatch):
    monkeypatch.delenv("JONI_EXPERTS", raising=False)
    cs = CoreState(seed_core())
    cs.hypothesize("Hypothesis: x", "routing", parents=())
    budget = Budget(week_start="t", spent_eur=0.0, runs=0, cap_eur=20.0)
    assert experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)["convened"] is False


def test_panel_deferred_when_weekly_budget_is_exhausted(monkeypatch):
    _enable(monkeypatch)
    _mock_ask(monkeypatch)
    cs = CoreState(seed_core())
    cs.hypothesize("Hypothesis: x", "routing", parents=())
    budget = Budget(week_start="t", spent_eur=19.99, runs=0, cap_eur=20.0)   # < 0.15 left
    assert experts.maybe_convene(cs, {}, _Proto(), budget, cycle=20)["convened"] is False
