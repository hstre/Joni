"""Measure the discoverer (Baustein C) against a KNOWN ground truth — the falsification of the mechanism.

Same discipline as the method-trial batteries, one level up: instead of trusting that
``discover_affinities`` finds real edges, we plant a ground truth (some (method_kind, gap_kind) pairs
truly succeed at ``p_true``; the rest are noise at ``p_noise``), synthesise a trial history from it, run
the discoverer, and score its CONFIRMED edges against the truth on the held-out split — a confusion
matrix with the false-positive rate called out (a false discovery ≫ a missed one, per the pre-registration).
Deterministic given a seed. If the discoverer cannot recover planted edges while rejecting noise here, it
cannot be trusted on real trials — a valid, recorded outcome.
"""

from __future__ import annotations

import random

from .discovery import discover_affinities
from .operators import DeepMethodTrial

# one real deep-method id per kind, so discover_affinities' method_id -> kind lookup resolves
_METHOD_BY_KIND = {
    "proof_technique": "proof_by_contradiction",
    "counting": "inclusion_exclusion",
    "invariant": "conservation_law",
    "estimation": "dimensional_analysis",
    "reduction": "reduction",
}
_GAP_KINDS = ("gk_a", "gk_b", "gk_c")
# synthetic gap-kinds (not in the a-priori taxonomy) so this measures the DISCOVERY mechanism cleanly
DEFAULT_TRUE_EDGES = frozenset({("proof_technique", "gk_a"), ("counting", "gk_b"),
                                ("reduction", "gk_c")})


def synthesise_trials(rng, *, true_edges, n_gaps: int, reps: int, p_true: float,
                      p_noise: float) -> list[DeepMethodTrial]:
    trials: list[DeepMethodTrial] = []
    gid = 0
    for gk in _GAP_KINDS:
        for _ in range(n_gaps):
            target = f"{gk}:g{gid}"
            gid += 1
            for mk, mid in _METHOD_BY_KIND.items():
                p = p_true if (mk, gk) in true_edges else p_noise
                for _r in range(reps):
                    res = "success" if rng.random() < p else "no_benefit"
                    trials.append(DeepMethodTrial(method_id=mid, target=target, result=res,
                                                  gap_kind=gk))
    return trials


def measure(*, seed: int = 20260702, true_edges=DEFAULT_TRUE_EDGES, n_gaps: int = 20, reps: int = 2,
            p_true: float = 0.85, p_noise: float = 0.12, holdout_pct: int = 30,
            min_support: int = 4, min_rate: float = 0.6) -> dict:
    """Plant ``true_edges``, synthesise a history, discover, and score CONFIRMED edges vs the truth.
    Returns a confusion matrix + precision / recall / false-positive rate."""
    rng = random.Random(seed)
    trials = synthesise_trials(rng, true_edges=true_edges, n_gaps=n_gaps, reps=reps,
                               p_true=p_true, p_noise=p_noise)
    disc = discover_affinities(trials, holdout_pct=holdout_pct, min_support=min_support,
                               min_rate=min_rate)
    confirmed = {(d.method_kind, d.gap_kind) for d in disc if d.confirmed}
    universe = {(mk, gk) for mk in _METHOD_BY_KIND for gk in _GAP_KINDS}
    truth = set(true_edges)
    tp = len(confirmed & truth)
    fp = len(confirmed - truth)
    fn = len(truth - confirmed)
    tn = len(universe - confirmed - truth)
    prec = tp / (tp + fp) if (tp + fp) else 1.0
    rec = tp / (tp + fn) if (tp + fn) else 1.0
    fp_rate = fp / (fp + tn) if (fp + tn) else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(prec, 3), "recall": round(rec, 3), "false_positive_rate": round(fp_rate, 3),
        "confirmed_edges": sorted(confirmed), "true_edges": sorted(truth),
        "params": {"n_gaps": n_gaps, "reps": reps, "p_true": p_true, "p_noise": p_noise,
                   "holdout_pct": holdout_pct, "min_support": min_support, "min_rate": min_rate},
    }


def main() -> int:
    clean = measure()
    hard = measure(p_true=0.68, p_noise=0.32)          # a noisier regime: the gate should still hold FP low
    for label, r in (("clean (p=.85/.12)", clean), ("hard (p=.68/.32)", hard)):
        print(f"{label}: recall={r['recall']} precision={r['precision']} "
              f"FP-rate={r['false_positive_rate']}  (tp={r['tp']} fp={r['fp']} fn={r['fn']} tn={r['tn']})")
        print(f"    confirmed: {r['confirmed_edges']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
