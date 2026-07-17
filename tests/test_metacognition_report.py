"""The bounded shadow-evaluation report over the benchmark."""

from joni.autonomy.metacognition import benchmark, report


def test_report_shape_over_the_benchmark():
    rep = report.build_report(benchmark.joined_rows())
    assert rep["n_episodes"] == 15
    assert "benchmark" in rep["by_task_family"]
    assert set(rep["overall_coverage"]) >= {"outcome_coverage", "unknown_rate", "monitor_dark_rate"}
    assert rep["plain_vs_shadow"] == "not_available_no_plain_path"          # no plain path yet


def test_report_calibration_computes_with_enough_and_refuses_when_thin(monkeypatch):
    monkeypatch.setenv("JONI_METACOG_MIN_OUTCOMES", "4")
    rep = report.build_report(benchmark.joined_rows())
    assert rep["by_task_family"]["benchmark"]["calibration"]["verdict"] == "computed"

    monkeypatch.setenv("JONI_METACOG_MIN_OUTCOMES", "9999")
    rep2 = report.build_report(benchmark.joined_rows())
    assert rep2["by_task_family"]["benchmark"]["calibration"]["verdict"] == "insufficient_evidence"


def test_render_markdown_is_a_bounded_string():
    md = report.render_markdown(report.build_report(benchmark.joined_rows()))
    assert "Metacognition shadow report" in md
    assert "Calibration per task family" in md
    assert isinstance(md, str) and len(md) < 20000
