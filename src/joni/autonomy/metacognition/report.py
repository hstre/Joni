"""Bounded shadow-evaluation projection over logged metacognition episodes.

Pure: takes the joined episode+outcome rows and returns a grouped report - overall coverage,
unknown / monitor_dark rates, per-task-family and per-seam calibration (which REFUSES when thin),
the control mix, and cost. No global calibration score is offered that would hide domain
differences; each group is reported on its own and marked ``insufficient_evidence`` when it cannot
be interpreted. There is no plain baseline path yet, so the plain-vs-shadow comparison is
explicitly ``not_available``.
"""
from __future__ import annotations

from . import metrics


def build_report(joined_rows: list[dict]) -> dict:
    def group_report(rows: list[dict]) -> dict:
        return {"coverage": metrics.coverage(rows),
                "calibration": metrics.calibration(rows),
                "control_mix": metrics.control_mix(rows),
                "cost": metrics.cost_summary(rows)}

    by_family = {k: group_report(v)
                 for k, v in metrics.group_by(joined_rows, "task_family").items()}
    by_seam = {k: group_report(v)
               for k, v in metrics.group_by(joined_rows, "decision_seam").items()}
    return {
        "n_episodes": len(joined_rows),
        "overall_coverage": metrics.coverage(joined_rows),
        "control_mix": metrics.control_mix(joined_rows),
        "cost": metrics.cost_summary(joined_rows),
        "by_task_family": by_family,
        "by_decision_seam": by_seam,
        "plain_vs_shadow": "not_available_no_plain_path",
    }


def render_markdown(report: dict) -> str:
    lines = ["# Metacognition shadow report", ""]
    cov = report["overall_coverage"]
    lines.append(f"- episodes: **{report['n_episodes']}**")
    lines.append(f"- outcome coverage: {cov.get('outcome_coverage')} · "
                 f"unknown: {cov.get('unknown_rate')} · "
                 f"monitor_dark: {cov.get('monitor_dark_rate')}")
    lines.append(f"- control mix: {report['control_mix']}")
    lines.append(f"- cost (expected/actual): {report['cost']['expected_cost_total']} / "
                 f"{report['cost']['actual_cost_total']}")
    lines.append(f"- plain vs shadow: {report['plain_vs_shadow']}")
    lines.append("")
    lines.append("## Calibration per task family (refused when thin)")
    for fam, g in report["by_task_family"].items():
        cal = g["calibration"]
        if cal.get("verdict") == "computed":
            lines.append(f"- **{fam}**: n={cal['n_binary_outcomes']} · Brier {cal['brier']} · "
                         f"ECE {cal['ece']} (bins {cal['ece_bins']}) · AUROC {cal['auroc']}")
        else:
            lines.append(f"- **{fam}**: {cal['verdict']} "
                         f"(n={cal.get('n_binary_outcomes')}/{cal.get('min_required')})")
    return "\n".join(lines) + "\n"


__all__ = ["build_report", "render_markdown"]
