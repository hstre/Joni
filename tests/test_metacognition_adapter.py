"""The method-gate adapter + the shadow observer: real path -> episode -> later outcome."""

from types import SimpleNamespace

from joni.autonomy.metacognition import method_gate, supervisor
from joni.autonomy.metacognition.audit import AuditLog
from joni.autonomy.metacognition.method_gate import MethodView
from joni.autonomy.metacognition.models import KnowledgeBoundary, Outcome, SelectedControl


def _view(**over):
    base = dict(id="7", name="attention-as-a-lens", status="candidate", trial_count=0,
                success_count=0, failure_count=0, n_topics=3, origin="joni:emergent")
    base.update(over)
    return MethodView(**base)


def _obj(**over):
    base = dict(id="7", name="attention-as-a-lens", status="candidate", trial_count=0,
                success_count=0, failure_count=0, applicable_to=("a", "b", "c"),
                origin="joni:emergent")
    base.update(over)
    return SimpleNamespace(**base)


# ---- pure adapter --------------------------------------------------------------

def test_build_episode_signals_are_bounded_and_boundary_is_derived():
    ep = method_gate.build_episode(_view(), cycle=5, tick=5, config_hash="cfg")
    r = ep.to_record()
    assert r["task_family"] == "method_gate" and r["decision_seam"] == "emerge.method_lens"
    assert r["selected_control"] == SelectedControl.PROCEED.value
    assert all(0.0 <= v <= 1.0 for v in r["signals"].values())
    assert 0.0 <= r["predicted_success"] <= 1.0
    assert r["knowledge_boundary"] == KnowledgeBoundary.INSIDE.value          # n_topics >= 2
    thin = method_gate.build_episode(_view(n_topics=1), cycle=1, tick=1, config_hash="c")
    assert thin.knowledge_boundary is KnowledgeBoundary.INSUFFICIENT_EVIDENCE
    dark = method_gate.build_episode(_view(), cycle=1, tick=1, config_hash="c", boundary_dark=True)
    assert dark.knowledge_boundary is KnowledgeBoundary.MONITOR_DARK


def test_resolve_maps_only_belastbare_terminal_statuses():
    assert method_gate.resolve(_view(status="rejected")) is Outcome.FAILURE
    assert method_gate.resolve(_view(status="retired")) is Outcome.FAILURE
    assert method_gate.resolve(_view(status="active")) is Outcome.SUCCESS
    assert method_gate.resolve(_view(status="provisional", success_count=3, failure_count=1)) \
        is Outcome.SUCCESS
    assert method_gate.resolve(_view(status="candidate")) is None                # still unknown
    assert method_gate.resolve(_view(status="provisional")) is None              # maturing


# ---- shadow observer (injected objects -> no desi_layer9) ----------------------

def test_observe_logs_once_then_resolves_on_terminal_status(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}

    # cycle 1: a fresh candidate -> one episode, still pending (unknown, not coerced)
    s1 = supervisor.observe(None, ext, 1, 1, log, objects=[_obj()])
    assert s1 == {"logged": 1, "resolved": 0, "methods_seen": 1}
    assert len(log.pending_episode_ids()) == 1

    # cycle 2: same candidate again -> no new episode, still pending
    s2 = supervisor.observe(None, ext, 2, 2, log, objects=[_obj()])
    assert s2["logged"] == 0 and s2["resolved"] == 0
    assert len(log.pending_episode_ids()) == 1

    # cycle 3: the method was rejected -> the pending episode resolves to failure (append-only)
    s3 = supervisor.observe(None, ext, 3, 3, log, objects=[_obj(status="rejected")])
    assert s3["resolved"] == 1
    assert log.pending_episode_ids() == set()
    joined = log.joined()
    assert len(joined) == 1
    assert joined[0]["effective_outcome"] == "failure"
    assert joined[0]["effective_outcome_source"] == "later_layer9_status"
    # the original episode line still says unknown - it was never rewritten
    assert log.episodes()[0]["outcome"] == "unknown"


def test_observe_never_coerces_a_still_pending_method(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    supervisor.observe(None, ext, 1, 1, log, objects=[_obj()])
    supervisor.observe(None, ext, 2, 2, log, objects=[_obj()])         # still candidate
    assert log.outcome_events() == []                                 # nothing invented
    assert log.joined()[0]["effective_outcome"] == "unknown"
