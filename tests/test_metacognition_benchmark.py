"""The offline benchmark: task performance and metacognitive performance are distinct."""

from joni.autonomy.metacognition import benchmark, metrics
from joni.autonomy.metacognition.models import Episode, Outcome


def test_fifteen_fixtures_cover_the_required_scenarios():
    assert len(benchmark.FIXTURES) == 15
    ids = {f.id for f in benchmark.FIXTURES}
    for needed in ("known_knows", "unknown_knows", "unknown_overconfident",
                   "known_needless_holdback", "stale_knowledge", "conflicting_evidence",
                   "missing_provenance", "tool_required", "budget_exhausted",
                   "fluent_unsupported", "guard_disabled", "correct_proceed",
                   "correct_abstain", "wrong_proceed", "needless_abstain"):
        assert any(needed in i for i in ids), needed


def test_every_fixture_builds_a_valid_episode():
    for f in benchmark.FIXTURES:
        ep = benchmark.to_episode(f)
        assert isinstance(ep, Episode)
        assert 0.0 <= ep.to_record()["predicted_success"] <= 1.0


def test_task_and_metacognitive_accuracy_diverge():
    ev = benchmark.evaluate()
    # the whole point: the two numbers measure different things and are not equal here
    assert ev["task_accuracy"] != ev["metacog_accuracy"]
    # a task solved right but monitored badly, AND a task failed but monitored well
    assert ev["good_task_bad_metacog"]        # e.g. needless holdback / needless abstain
    assert ev["bad_task_good_metacog"]        # e.g. recognised-unknown -> correct abstain


def test_unknown_outcomes_are_not_coerced_and_gold_labels_are_robust():
    rows = benchmark.joined_rows()
    assert len(rows) == 15
    # withheld (abstain/defer/escalate/verify) items stay unknown, never invented
    withheld = [r for r in rows if r["effective_outcome"] == "unknown"]
    assert withheld and all(r["resolved"] is False for r in withheld)
    # answered items carry a belastbares success/failure
    answered = [r for r in rows if r["effective_outcome"] in ("success", "failure")]
    assert answered and all(r["resolved"] for r in answered)


def test_calibration_runs_over_the_benchmark(monkeypatch):
    monkeypatch.setenv("JONI_METACOG_MIN_OUTCOMES", "4")
    out = metrics.calibration(benchmark.joined_rows())
    assert out["verdict"] == "computed"
    assert out["n_binary_outcomes"] == sum(
        1 for f in benchmark.FIXTURES if f.task_outcome in (Outcome.SUCCESS, Outcome.FAILURE))
    assert out["auroc"] is not None          # both success and failure fixtures are present
