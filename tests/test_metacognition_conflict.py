"""The conflict-resolution adapter (a second real seam) + its shadow observer."""

from types import SimpleNamespace

from joni.autonomy.metacognition import conflict_gate, supervisor
from joni.autonomy.metacognition.audit import AuditLog
from joni.autonomy.metacognition.conflict_gate import ConflictView
from joni.autonomy.metacognition.models import KnowledgeBoundary, Outcome, SelectedControl


def _cv(**over):
    base = dict(id="c1", conflict_status="open", severity="hard", conflict_kind="negation",
                n_claims=2)
    base.update(over)
    return ConflictView(**base)


def _obj(**over):
    base = dict(id="c1", conflict_status="open", severity="hard", conflict_kind="negation",
                claim_ids=("a", "b"))
    base.update(over)
    return SimpleNamespace(**base)


def test_build_episode_is_a_conflict_seam_episode():
    ep = conflict_gate.build_episode(_cv(), cycle=1, tick=1, config_hash="cfg")
    r = ep.to_record()
    assert r["task_family"] == "conflict_gate" and r["decision_seam"] == "conflict.resolution"
    assert r["knowledge_boundary"] == KnowledgeBoundary.CONFLICTING.value
    assert r["selected_control"] == SelectedControl.VERIFY.value
    assert all(0.0 <= v <= 1.0 for v in r["signals"].values())
    assert 0.0 <= r["predicted_success"] <= 1.0


def test_resolve_maps_status_and_staleness_to_both_classes():
    assert conflict_gate.resolve(_cv(conflict_status="resolved"), age=0, stale_cycles=5) \
        is Outcome.SUCCESS
    assert conflict_gate.resolve(_cv(conflict_status="open"), age=9, stale_cycles=5) \
        is Outcome.FAILURE
    assert conflict_gate.resolve(_cv(conflict_status="open"), age=2, stale_cycles=5) is None


def test_observe_conflicts_resolves_success_on_resolution(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    s1 = supervisor.observe_conflicts(None, ext, 1, 1, log, objects=[_obj()], stale_cycles=5)
    assert s1 == {"logged": 1, "resolved": 0, "conflicts_seen": 1}
    assert len(log.pending_episode_ids()) == 1

    s2 = supervisor.observe_conflicts(None, ext, 3, 3, log,
                                      objects=[_obj(conflict_status="resolved")], stale_cycles=5)
    assert s2["resolved"] == 1
    assert log.joined()[0]["effective_outcome"] == "success"


def test_observe_conflicts_fails_a_stale_open_conflict(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    supervisor.observe_conflicts(None, ext, 1, 1, log, objects=[_obj()], stale_cycles=5)
    # still open many cycles later -> failure (the seam never resolved it)
    s = supervisor.observe_conflicts(None, ext, 10, 10, log, objects=[_obj()], stale_cycles=5)
    assert s["resolved"] == 1
    assert log.joined()[0]["effective_outcome"] == "failure"


def test_observe_conflicts_never_coerces_a_recent_open_conflict(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    supervisor.observe_conflicts(None, ext, 1, 1, log, objects=[_obj()], stale_cycles=5)
    supervisor.observe_conflicts(None, ext, 2, 2, log, objects=[_obj()], stale_cycles=5)
    assert log.outcome_events() == []
    assert log.joined()[0]["effective_outcome"] == "unknown"
