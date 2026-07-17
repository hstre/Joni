"""Adapter A (literature arm) + the PR-outcome parsers + the observer."""

from joni.autonomy.metacognition import (
    doktores_literature_gate as lit,
)
from joni.autonomy.metacognition import (
    pr_outcomes,
    supervisor,
)
from joni.autonomy.metacognition.audit import AuditLog
from joni.autonomy.metacognition.models import KnowledgeBoundary, Outcome, SelectedControl


def test_build_episode_carries_review_signals():
    ep = lit.build_episode(lit.ReviewSignal("sources", True, "deepseek-v4-pro", "arxiv", True),
                           cycle=2, tick=2, config_hash="c").to_record()
    assert ep["task_family"] == "doktores_literature"
    assert ep["decision_seam"] == "doktores.literature_review"
    assert ep["selected_control"] == SelectedControl.ASK_HUMAN.value
    assert ep["signals"] == {"applicable": 1.0, "is_fulltext": 1.0, "is_hard_model": 1.0}
    assert ep["knowledge_boundary"] == KnowledgeBoundary.INSIDE.value
    thin = lit.build_episode(lit.ReviewSignal("x", False, "granite", "openalex", False),
                             cycle=1, tick=1, config_hash="c")
    assert thin.knowledge_boundary is KnowledgeBoundary.INSUFFICIENT_EVIDENCE


def test_outcome_for_maps_index_values():
    assert lit.outcome_for("success") is Outcome.SUCCESS
    assert lit.outcome_for("failure") is Outcome.FAILURE
    assert lit.outcome_for("") is None


def test_index_from_commissions_done_is_success_only():
    rows = [{"component": "the reading layer (sources.py / reader.py)", "ref": "sources.py",
             "title": "Erweitere meine Quellen"}]
    idx = pr_outcomes.index_from_commissions_done(rows, ["sources", "router"])
    assert idx == {"sources": "success"}                       # matched; router absent


def test_index_from_issues_maps_merged_and_closed():
    issues = [
        {"labels": [{"name": "joni-auftrag"}], "state": "closed", "title": "sources fix",
         "body": "component sources", "pull_request": {"merged_at": "2026-01-01"}},
        {"labels": [{"name": "joni-auftrag"}], "state": "closed", "title": "router change",
         "body": "component router", "pull_request": {}},                       # closed, unmerged
        {"labels": [{"name": "joni-auftrag"}], "state": "open", "title": "reader",
         "body": "component reader", "pull_request": {}},                       # still open
        {"labels": [{"name": "other"}], "state": "closed", "title": "sources",
         "body": "sources", "pull_request": {"merged_at": "x"}},               # not an Auftrag
    ]
    idx = pr_outcomes.index_from_issues(issues, ["sources", "router", "reader"])
    assert idx == {"sources": "success", "router": "failure"}   # open skipped, non-auftrag skipped


def test_observe_doktores_literature_logs_applicable_and_resolves_from_index(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    review = [
        {"cycle": 4, "source": "arxiv", "served_model": "deepseek", "applicable": True,
         "component_key": "sources"},
        {"cycle": 4, "source": "openalex", "served_model": "granite", "applicable": False,
         "component_key": ""},                                  # not applicable -> not logged
    ]
    s = supervisor.observe_doktores_literature(None, ext, 5, 5, log, review_entries=review,
                                               done_index={})
    assert s["logged"] == 1 and len(log.pending_episode_ids()) == 1

    # later a PR outcome becomes observable -> resolves (append-only)
    s2 = supervisor.observe_doktores_literature(None, ext, 9, 9, log, review_entries=review,
                                                done_index={"sources": "success"})
    assert s2["resolved"] == 1
    assert log.joined()[0]["effective_outcome"] == "success"
    assert log.episodes()[0]["outcome"] == "unknown"           # never rewritten


def test_observe_doktores_literature_never_coerces_unmatched(tmp_path):
    log = AuditLog(tmp_path / "metacognition.jsonl")
    ext: dict = {}
    review = [{"cycle": 1, "source": "arxiv", "served_model": "deepseek", "applicable": True,
               "component_key": "router"}]
    supervisor.observe_doktores_literature(None, ext, 1, 1, log, review_entries=review,
                                           done_index={"sources": "success"})     # no match
    assert log.outcome_events() == []
    assert log.joined()[0]["effective_outcome"] == "unknown"
