"""The audited escalation from Granite to DeepSeek: rule-based decision, named reason, captured.

DeepSeek is reached ONLY through a deterministic, named rule - never a silent fallback, never a
parallel vote. Its output enters Layer 9 as candidate SOURCE proposals; the reason is persisted.
"""

import desi_layer9 as l9
from joni.autonomy import escalation, model_call
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_reason_is_ordered_by_stakes():
    # a risky transition outranks everything, even a high conflict load
    sig = escalation.Signals(conflict_load=99, risky_transition=True)
    assert escalation.reason(sig) == escalation.RISKY_STATUS_TRANSITION
    # then conflict load, then contested, then coverage, then thin/scope
    assert escalation.reason(escalation.Signals(conflict_load=3)) == escalation.HIGH_CONFLICT_LOAD
    assert escalation.reason(escalation.Signals(hard_conflict=True)) == escalation.CONTESTED
    assert escalation.reason(
        escalation.Signals(evidence_coverage=0.0, coverage_measured=True)
    ) == escalation.LOW_EVIDENCE_COVERAGE
    assert escalation.reason(escalation.Signals(underspecified=True)) == escalation.UNDERSPECIFIED
    assert escalation.reason(escalation.Signals(unclear_scope=True)) == escalation.UNCLEAR_SCOPE


def test_no_rule_no_escalation():
    # a calm state: nothing fires, DeepSeek is never reached
    assert escalation.reason(escalation.Signals()) is None
    # low coverage that is NOT measured (too few claims) does not fire
    assert escalation.reason(escalation.Signals(evidence_coverage=0.0, coverage_measured=False)) \
        is None


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    cs = CoreState(seed_core())
    out = escalation.escalate_if_needed(cs, {}, _Proto(), 1)
    assert out == {"escalated": 0, "reason": None, "claims": 0}


def test_escalation_calls_deepseek_with_a_recorded_reason(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_ESCALATE_CONFLICT_LOAD", "1")     # one open conflict is enough here
    seen = {}

    def fake(profile, system, user):
        seen["served"] = profile.served_slug
        seen["provider"] = profile.provider
        return '[{"text":"Remote routing trades latency for privacy","topic":"routing"}]'
    monkeypatch.setattr(model_call, "_complete", fake)

    cs = CoreState(seed_core())
    # manufacture an open contradiction so a rule fires (via the real detection path)
    cs.learn("routing must always be remote", "routing")
    cs.learn("routing must never be remote", "routing")
    opened = cs.detect_and_open_conflicts()
    assert opened, "expected an open contradiction to drive the escalation"

    ext: dict = {}
    out = escalation.escalate_if_needed(cs, ext, _Proto(), 7)
    assert out["escalated"] == 1
    assert out["reason"] in (escalation.HIGH_CONFLICT_LOAD, escalation.CONTESTED)
    assert out["claims"] == 1
    assert seen["provider"] == "deepseek"                      # routed to DeepSeek, not Granite
    # the proposal entered as a candidate SOURCE via the gate, tagged deepseek:<call_id>
    new = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if any(s.startswith("deepseek:") for s in (c.provenance.source_ids or ()))]
    assert len(new) == 1
    assert new[0].provenance.origin_type.value == "source"
    assert new[0].authority.value == "candidate"
    # the escalation reason is captured for audit
    assert ext["escalations"][0]["reason"] == out["reason"]


def test_same_conflict_is_not_escalated_twice_and_backs_off(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_ESCALATE_BACKOFF", "2")
    # DeepSeek returns nothing useful (0 claims) - exactly the '14 escalations, 0 claims' case
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u: "[]")

    cs = CoreState(seed_core())
    cs.learn("local routing reduces latency", "routing")
    cs.learn("local routing does not reduce latency", "routing")
    assert cs.detect_and_open_conflicts()                  # one hard contradiction
    ext: dict = {}
    first = escalation.escalate_if_needed(cs, ext, _Proto(), 1)
    assert first["escalated"] == 1                          # the new hard conflict is escalated
    assert ext["escalated_conflicts"]                       # and recorded so it is not repeated
    # no NEW hard conflict + repeated empty rounds -> it stands down instead of re-spending
    ext.setdefault("escalations", []).append({"claims": 0})
    second = escalation.escalate_if_needed(cs, ext, _Proto(), 2)
    assert second["escalated"] == 0


def test_capture_persists_the_escalation_reason(monkeypatch, tmp_path):
    from joni.autonomy import model_profile

    def fake(profile, system, user):
        return "analysis"
    monkeypatch.setattr(model_call, "_complete", fake)
    prof = model_profile.profile("joni-hard")
    _out, cap = model_call.call(prof, "sys", "u", run_id="r1", store_dir=tmp_path,
                                escalation_reason="high_conflict_load")
    assert cap.escalation_reason == "high_conflict_load"
