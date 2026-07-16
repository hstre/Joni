"""Deterministic metrics over resolved episodes - and an honest refusal when data is thin.

Only belastbare BINARY outcomes (success=1 / failure=0) feed calibration; ``mixed`` and
``unknown`` are excluded (never coerced). Below a documented minimum the verdict is
``insufficient_evidence`` - never ``well_calibrated``. No single global number is offered
that would hide domain differences: the caller groups by task_family / decision_seam /
signal_source / model family and calls these per group.
"""
from __future__ import annotations

import os

# fixed, documented ECE binning: 10 equal-width bins over [0, 1]
ECE_BINS = 10


def min_outcomes() -> int:
    return max(1, int(os.getenv("JONI_METACOG_MIN_OUTCOMES", "30")))


def binary_pairs(joined_rows: list[dict]) -> list[tuple[float, int]]:
    """(predicted_success, label) for rows whose effective outcome is success/failure."""
    pairs = []
    for r in joined_rows:
        o = r.get("effective_outcome")
        if o == "success":
            pairs.append((float(r["predicted_success"]), 1))
        elif o == "failure":
            pairs.append((float(r["predicted_success"]), 0))
    return pairs


def brier(pairs: list[tuple[float, int]]) -> float:
    return round(sum((p - y) ** 2 for p, y in pairs) / len(pairs), 6)


def ece(pairs: list[tuple[float, int]], bins: int = ECE_BINS) -> float:
    """Expected Calibration Error with fixed equal-width bins over [0,1]."""
    n = len(pairs)
    tot = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        bucket = [(p, y) for p, y in pairs if (p >= lo and (p < hi or (b == bins - 1 and p <= hi)))]
        if not bucket:
            continue
        conf = sum(p for p, _ in bucket) / len(bucket)
        acc = sum(y for _, y in bucket) / len(bucket)
        tot += (len(bucket) / n) * abs(conf - acc)
    return round(tot, 6)


def auroc(pairs: list[tuple[float, int]]) -> float | None:
    """AUROC via the Mann-Whitney statistic. None unless BOTH classes are present."""
    pos = [p for p, y in pairs if y == 1]
    neg = [p for p, y in pairs if y == 0]
    if not pos or not neg:
        return None                                   # undefined without both classes
    # rank-sum (average ranks for ties)
    scored = sorted((p for p, _ in pairs))
    ranks: dict[float, float] = {}
    i = 0
    while i < len(scored):
        j = i
        while j < len(scored) and scored[j] == scored[i]:
            j += 1
        avg = (i + 1 + j) / 2.0                        # average of 1-based ranks in the tie block
        for k in range(i, j):
            ranks[scored[k]] = avg
        i = j
    rsum = sum(ranks[p] for p in pos)
    auc = (rsum - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))
    return round(auc, 6)


def coverage(joined_rows: list[dict]) -> dict:
    """Meta-metacognition: how observable was this slice at all?"""
    n = len(joined_rows)
    if n == 0:
        return {"n": 0, "outcome_coverage": None, "unknown_rate": None, "monitor_dark_rate": None}
    resolved = sum(1 for r in joined_rows if r.get("resolved"))
    unknown = sum(1 for r in joined_rows if r.get("effective_outcome") == "unknown")
    dark = sum(1 for r in joined_rows if r.get("knowledge_boundary") == "monitor_dark")
    return {"n": n, "resolved": resolved,
            "outcome_coverage": round(resolved / n, 4),
            "unknown_rate": round(unknown / n, 4),
            "monitor_dark_rate": round(dark / n, 4)}


def calibration(joined_rows: list[dict]) -> dict:
    """Calibration over one group - or an explicit refusal when the data cannot bear it."""
    pairs = binary_pairs(joined_rows)
    n = len(pairs)
    if n < min_outcomes():
        return {"verdict": "insufficient_evidence", "n_binary_outcomes": n,
                "min_required": min_outcomes()}
    pos = sum(y for _, y in pairs)
    out = {
        "verdict": "computed", "n_binary_outcomes": n,
        "n_positive": pos, "n_negative": n - pos,
        "brier": brier(pairs), "ece": ece(pairs), "ece_bins": ECE_BINS,
        "auroc": auroc(pairs),                        # None unless both classes present
        "mean_predicted": round(sum(p for p, _ in pairs) / n, 6),
        "base_rate": round(pos / n, 6),
    }
    return out


def control_mix(joined_rows: list[dict]) -> dict:
    """Distribution of chosen controls (proceed vs abstain/defer/escalate ...)."""
    counts: dict[str, int] = {}
    for r in joined_rows:
        counts[r.get("selected_control", "?")] = counts.get(r.get("selected_control", "?"), 0) + 1
    return dict(sorted(counts.items()))


def cost_summary(joined_rows: list[dict]) -> dict:
    exp = [float(r.get("expected_cost", 0.0)) for r in joined_rows]
    act = [float(r.get("actual_cost", 0.0)) for r in joined_rows]
    return {"n": len(joined_rows),
            "expected_cost_total": round(sum(exp), 6),
            "actual_cost_total": round(sum(act), 6)}


def group_by(joined_rows: list[dict], key: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for r in joined_rows:
        groups.setdefault(str(r.get(key, "?")), []).append(r)
    return dict(sorted(groups.items()))


# NOTE: meta-d'/M-ratio are intentionally NOT computed here - they require a controlled
# type-1/type-2 benchmark with clean confidence ratings, not open production tasks.

__all__ = ["ECE_BINS", "min_outcomes", "binary_pairs", "brier", "ece", "auroc",
           "coverage", "calibration", "control_mix", "cost_summary", "group_by"]
