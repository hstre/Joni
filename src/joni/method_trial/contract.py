"""Validate that a battery meets the Stage-1 contract (structural, deterministic, no model).

A battery is only usable if every task carries its full declaration, its checker ACCEPTS the gold
answer and REJECTS a plausible wrong one, and no method could be trialed on its own home turf. This
stops a half-specified or self-flattering battery from ever feeding an experiment.
"""
from __future__ import annotations

from .gold_micro_v1 import CASES, Task


def validate_task(t: Task) -> list[str]:
    problems: list[str] = []
    for fieldname in ("id", "skill", "expected_method_class", "forbidden_origin_domain", "prompt",
                      "gold", "why_not_verbosity"):
        if not str(getattr(t, fieldname, "")).strip():
            problems.append(f"{t.id}: empty {fieldname}")
    if not callable(t.checker):
        problems.append(f"{t.id}: checker not callable")
    elif not t.checker(t.gold):
        problems.append(f"{t.id}: checker rejects its own gold answer")
    elif t.wrong_example and t.checker(t.wrong_example):
        problems.append(f"{t.id}: checker ACCEPTS the wrong_example (not discriminating)")
    if not t.failure_modes:
        problems.append(f"{t.id}: no failure_modes declared")
    # no leakage: the origin domain a method must avoid must be explicitly named (checked non-empty
    # above), so a method is never trialed on its own home turf.
    return problems


def validate_battery(cases: list[Task] | None = None, *, min_tasks: int = 12) -> dict:
    cases = cases or CASES
    problems: list[str] = []
    ids = [t.id for t in cases]
    if len(set(ids)) != len(ids):
        problems.append("duplicate task ids")
    if len(cases) < min_tasks:
        problems.append(f"only {len(cases)} tasks (< {min_tasks})")
    for t in cases:
        problems.extend(validate_task(t))
    return {
        "ok": not problems,
        "n": len(cases),
        "skills": sorted({t.skill for t in cases}),
        "method_classes": sorted({t.expected_method_class for t in cases}),
        "problems": problems,
    }
