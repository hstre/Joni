"""Adapter A: the Doktores coherence verifier -> episode -> hypothesis Layer-9 outcome."""

from types import SimpleNamespace

from joni.autonomy.metacognition import doktores_gate, supervisor
from joni.autonomy.metacognition.audit import AuditLog
from joni.autonomy.metacognition.doktores_gate import ClaimView, DoktoresVerdict
from joni.autonomy.metacognition.models import KnowledgeBoundary, Outcome, SelectedControl


def _claim(cid, status):
    return SimpleNamespace(id=cid, status=status)


def test_build_episode_reflects_the_coherence_verdict():
    ok = doktores_gate.build_episode(DoktoresVerdict("claim-5", True, "routing"),
                                     cycle=1, tick=1, config_hash="c").to_record()
    assert ok["task_family"] == "doktores_coherence"
    assert ok["decision_seam"] == "doktores.coherence"
    assert ok["subject_refs"] == ["claim:claim-5"]
    assert ok["selected_control"] == SelectedControl.VERIFY.value
    assert ok["signals"]["coherent"] == 1.0 and ok["predicted_success"] == 0.7
    assert ok["knowledge_boundary"] == KnowledgeBoundary.INSIDE.value

    bad = doktores_gate.build_episode(DoktoresVerdict("claim-6", False, "memory"),
                                      cycle=1, tick=1, config_hash="c")
    assert bad.knowledge_boundary is KnowledgeBoundary.CONFLICTING
    assert bad.to_record()["predicted_success"] == 0.2


def test_resolve_maps_claim_status_to_both_classes():
    assert doktores_gate.resolve(ClaimView("claim-5", "active")) is Outcome.SUCCESS
    assert doktores_gate.resolve(ClaimView("claim-5", "confirmed")) is Outcome.SUCCESS
    assert doktores_gate.resolve(ClaimView("claim-5", "rejected")) is Outcome.FAILURE
    assert doktores_gate.resolve(ClaimView("claim-5", "superseded")) is Outcome.FAILURE
    assert doktores_gate.resolve(ClaimView("claim-5", "candidate")) is None


def test_observe_doktores_logs_then_resolves_from_the_claim_status(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    entry = {"cycle": 2, "hypothesis": "claim-5", "topic": "routing", "coherent": True}

    s1 = supervisor.observe_doktores(None, ext, 3, 3, log, log_entries=[entry],
                                     claim_objects=[_claim("claim-5", "candidate")])
    assert s1 == {"logged": 1, "resolved": 0, "doktores_seen": 1}
    assert len(log.pending_episode_ids()) == 1                      # still candidate -> unknown

    s2 = supervisor.observe_doktores(None, ext, 9, 9, log, log_entries=[entry],
                                     claim_objects=[_claim("claim-5", "active")])
    assert s2["resolved"] == 1
    assert log.joined()[0]["effective_outcome"] == "success"
    assert log.episodes()[0]["outcome"] == "unknown"               # episode never rewritten


def test_observe_doktores_reads_the_extensions_log_by_default(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext = {"doktores_hyp_log": [{"cycle": 1, "hypothesis": "claim-9", "topic": "t",
                                 "coherent": False}]}
    s = supervisor.observe_doktores(None, ext, 1, 1, log,
                                    claim_objects=[_claim("claim-9", "candidate")])
    assert s["logged"] == 1 and s["doktores_seen"] == 1
    assert log.outcome_events() == []                              # candidate -> stays unknown
