"""P1 of the method-sandbox (design-notes/METHOD_SANDBOX_AUFTRAG.md §6): a GENERALISED real trial.

The measured protocol used to be hard-wired to one method (the conflict trial). This opens it to an
**arbitrary** ``(method, task set, baseline, intervention, metric)`` and measures it through the P0
sandbox harness - the shelf-iterating trial path the loop has been missing. The three solvers run as
isolated, untrusted code (``sandbox.run_solver``); the verdict rests on the **metric alone**, with a
mandatory **negative control** so the apparatus can tell a real effect from noise.

A ``TrialSpec`` is fully self-contained and content-hashable, so a run is reproducible and can be
sealed as an idempotent event through the existing ``kevin_trial_bridge`` path (``record``). The
result dict matches the shape that bridge consumes, so **no change to Kevin is needed**.

Anti-circularity (Auftrag §5): the gold labels are **hand-curated and frozen** here - the code that
runs a solver never also labels its own test cases. Phase 1 uses only such curated sets.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from . import sandbox

EVAL_MODE = "sandbox_trial_v1"


@dataclass(frozen=True)
class TrialSpec:
    """A complete, reproducible trial. ``cases`` is a tuple of ``{"payload": dict, "gold": label}``;
    each solver is Python source defining ``solve(payload) -> {label_key: label}``."""

    method_id: str
    task_set: str
    cases: tuple
    baseline_src: str
    intervention_src: str
    negative_control_src: str
    label_key: str = "label"
    metric_name: str = "misclassification_rate"
    lower_is_better: bool = True
    min_effect: float = 0.15
    affinities: tuple = ()
    cpu_seconds: int = 2
    wall_seconds: float = 5.0

    def sha(self) -> str:
        blob = json.dumps({"cases": list(self.cases), "b": self.baseline_src,
                           "i": self.intervention_src, "n": self.negative_control_src,
                           "k": self.label_key}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _misclassification_rate(spec: TrialSpec, solver_src: str) -> float:
    """Fraction of cases the solver labels wrong (a sandbox failure counts as wrong - a solver that
    crashes/blocks/times out is not correct). Empty case set -> 1.0 (nothing solved)."""
    if not spec.cases:
        return 1.0
    errs = 0
    for c in spec.cases:
        res = sandbox.run_solver(solver_src, c["payload"],
                                 cpu_seconds=spec.cpu_seconds, wall_seconds=spec.wall_seconds)
        pred = res.answer.get(spec.label_key) if (res.ok and res.answer is not None) else None
        if pred != c["gold"]:
            errs += 1
    return round(errs / len(spec.cases), 4)


def run(spec: TrialSpec) -> dict:
    """Run the three solvers over the frozen set in the sandbox and produce a sealed-event-ready
    result. ``passed`` iff the intervention beats the baseline by at least ``min_effect`` AND the
    negative control does NOT (else the measured 'effect' is apparatus noise)."""
    base = _misclassification_rate(spec, spec.baseline_src)
    interv = _misclassification_rate(spec, spec.intervention_src)
    neg = _misclassification_rate(spec, spec.negative_control_src)
    delta = round(base - interv, 4)                 # positive = intervention has fewer errors
    neg_delta = round(base - neg, 4)
    passed = (delta >= spec.min_effect) and (neg_delta < spec.min_effect)
    return {
        "method_id": spec.method_id,
        "task_set": spec.task_set,
        "task_set_sha": spec.sha(),
        "metric": spec.metric_name,
        "lower_is_better": spec.lower_is_better,
        "baseline": base, "intervention": interv, "negative_control": neg,
        "delta": delta, "negative_control_delta": neg_delta,
        "effect_se": 0.0,                            # deterministic solvers -> no sampling variance
        "confidence_interval": [delta, delta],
        "min_effect": spec.min_effect,
        "repetitions": 1,
        "affinities": list(spec.affinities),
        "processor_model": "none",
        "evaluation_mode": EVAL_MODE,
        "epistemic_weight": "provisional",
        "passed": passed,
    }


def record(cs, spec: TrialSpec, *, run_id: str = "joni-sandbox") -> dict:
    """Run ``spec`` and seal the result as an idempotent Layer-9 trial event via the existing
    ``kevin_trial_bridge`` (the same writer the conflict trial uses; the verdict is rule_v2's).
    Fail-open: returns ``{"ran": False}`` if the bridge/core is unavailable."""
    result = run(spec)
    try:
        from ..autonomy import kevin_trial_bridge as bridge
        rec = bridge.record_real_trial(cs, result, run_id=run_id)
        bridge.project(cs)
    except Exception:  # noqa: BLE001 - a trial must never break the caller
        return {"ran": True, "result": result, "sealed": False}
    return {"ran": True, "result": result, "sealed": True, "event": rec}


# --------------------------------------------------------------------------- #
# A second, hand-curated real trial (the P1 acceptance case): unit-canonicalised numeric equality.
# The METHOD is "normalise the unit before comparing" - a real transferable procedure. It measurably
# beats a naive string-equality baseline on the cases where two strings denote the same quantity
# ("5 km" == "5000 m"); the negative control (a structure-free hash-parity guess) does not.
# --------------------------------------------------------------------------- #

_BASELINE = '''
def solve(payload):
    return {"label": "same" if payload["a"].strip().lower() == payload["b"].strip().lower()
            else "different"}
'''

_INTERVENTION = '''
def solve(payload):
    import re
    units = {"m":(1.0,"len"),"km":(1000.0,"len"),"cm":(0.01,"len"),"mm":(0.001,"len"),
             "g":(1.0,"mass"),"kg":(1000.0,"mass"),"mg":(0.001,"mass"),
             "s":(1.0,"time"),"min":(60.0,"time"),"h":(3600.0,"time")}
    def canon(x):
        m = re.match(r"^\\s*([0-9]+(?:\\.[0-9]+)?)\\s*([a-z]+)\\s*$", x.strip().lower())
        if not m:
            return None
        u = m.group(2)
        if u not in units:
            return None
        factor, dim = units[u]
        return (round(float(m.group(1)) * factor, 9), dim)
    ca, cb = canon(payload["a"]), canon(payload["b"])
    if ca is None or cb is None:
        return {"label": "unknown"}
    return {"label": "same" if ca == cb else "different"}
'''

_NEGATIVE = '''
def solve(payload):
    h = sum(ord(c) for c in (payload["a"] + payload["b"]))
    return {"label": "same" if h % 2 == 0 else "different"}
'''

_UNIT_CASES = (
    # same quantity, different string -> the baseline gets these WRONG, the method right
    {"payload": {"a": "5 km", "b": "5000 m"}, "gold": "same"},
    {"payload": {"a": "2 kg", "b": "2000 g"}, "gold": "same"},
    {"payload": {"a": "1 h", "b": "3600 s"}, "gold": "same"},
    {"payload": {"a": "100 cm", "b": "1 m"}, "gold": "same"},
    {"payload": {"a": "500 mg", "b": "0.5 g"}, "gold": "same"},
    # genuinely different quantities
    {"payload": {"a": "2 kg", "b": "3 kg"}, "gold": "different"},
    {"payload": {"a": "5 km", "b": "6 km"}, "gold": "different"},
    {"payload": {"a": "1 h", "b": "1 min"}, "gold": "different"},
    # equal number, different dimension -> different
    {"payload": {"a": "5000 m", "b": "5000 g"}, "gold": "different"},
    # string-identical -> same (baseline gets this right too)
    {"payload": {"a": "2 kg", "b": "2 kg"}, "gold": "same"},
    {"payload": {"a": "10 s", "b": "10 s"}, "gold": "same"},
    {"payload": {"a": "3 mm", "b": "4 mm"}, "gold": "different"},
)


def unit_equality_spec() -> TrialSpec:
    return TrialSpec(
        method_id="unit-canonicalised-equality",
        task_set="frozen_unit_equality_v1",
        cases=_UNIT_CASES,
        baseline_src=_BASELINE, intervention_src=_INTERVENTION, negative_control_src=_NEGATIVE,
        min_effect=0.15, affinities=("normalisation",),
    )


__all__ = ["TrialSpec", "run", "record", "unit_equality_spec", "EVAL_MODE"]
