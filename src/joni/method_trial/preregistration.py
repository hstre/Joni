"""Stage 0 — the PRE-REGISTRATION of the method-transfer experiment (frozen before any data).

Per the plan (``docs/METHOD_TRIAL_MEASUREMENT_PLAN.md`` v2), the analysis is locked *before* a single
task meets a solver, so results cannot be rationalised after the fact. This module IS that lock: the
spec below is content-hashed, and a test pins the hash — any change to the pre-registration must be a
deliberate, reviewed edit that updates the pinned hash, never a silent post-hoc tweak.
"""
from __future__ import annotations

import hashlib
import json

# The frozen decisions. Read-only by contract; change only via a reviewed edit + a new pinned hash.
SPEC: dict = {
    "version": "method_transfer_prereg_v1",
    "registered": "2026-07-02",
    "claim": (
        "Disciplining a solving attempt with stored method M improves accuracy on tasks OUTSIDE M's "
        "origin domain, by more than EACH control (neutral preamble, scrambled method, irrelevant "
        "plausible method) — on independent data points."
    ),
    "primary_metric": {
        "name": "task_accuracy",
        "definition": "fraction of tasks whose deterministic checker returns True",
        "range": [0.0, 1.0],
        "higher_is_better": True,
    },
    "min_effect_delta": 0.15,          # absolute accuracy gain worth acting on (pilot direction gate)
    "ci_method": "bootstrap_percentile_95_over_independence_unit",
    "independence_unit": {
        "micro_battery": "task",
        # a retain/retire decision requires the larger held-out battery + variance across these:
        "decision": ["task", "task_variant", "prompt_template", "model_family"],
        "note": "deterministic repetitions of one setup are NOT independent data points",
    },
    "controls": [
        "plain_baseline",
        "length_matched_neutral_preamble",
        "scrambled_method",
        "irrelevant_plausible_method",
    ],
    "success_rule": (
        "intervention accuracy CI must exclude 0 in the helpful direction vs EACH control, not only "
        "vs plain_baseline"
    ),
    "false_positive_policy": (
        "a false promotion (keeping a worthless method) is worse than a false retirement; every "
        "threshold protects against false positives first; the false-positive rate governs adoption"
    ),
    "proxy_acceptability": {
        "max_false_positive_rate_on_holdout": 0.10,   # fixed before Stage 4 results exist
        "requires_heldout_methods_and_task_sets": True,
        "report_fp_and_fn_separately": True,
    },
    "method_plausibility": (
        "a method counts as a-priori plausible ONLY via a rationale recorded before it meets any task "
        "(independent judgement or a cited external result), NEVER derived from a trial outcome"
    ),
    "solver_protocol": "each attempt must end with a line 'Answer: <x>' (checkers read that region)",
    "honesty": [
        "no LLM judge: answers are machine-checkable",
        "no self-grading: the solving call is never the grading call",
        "no leakage: a method is never trialed on a task inside its own origin domain",
        "a null result at any gate is a valid, recorded outcome",
        "the micro battery falsifies; it is NOT an authority for retain/retire (use the holdout)",
    ],
}


def canonical() -> str:
    return json.dumps(SPEC, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash() -> str:
    return hashlib.sha256(canonical().encode("utf-8")).hexdigest()
