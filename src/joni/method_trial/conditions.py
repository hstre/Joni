"""Build the five conditions per task — the intervention plus the four pre-registered controls.

For each task, the *intervention* prepends the a-priori-appropriate method; the controls prepend
nothing / a length-matched neutral preamble / the scrambled method / an irrelevant real method. The
solver prompt always keeps the task's own 'End with Answer: <x>' instruction, so the deterministic
checker can grade any condition identically. No model here — just prompt construction.
"""
from __future__ import annotations

from . import methods
from .gold_micro_v1 import Task

# the pre-registered condition set: intervention + 4 controls (order fixed for replay-stable output)
CONDITIONS = ("intervention", "plain_baseline", "neutral_preamble", "scrambled_method",
              "irrelevant_method")


def _wrap(preamble: str, task: Task) -> str:
    return f"{preamble}\n\n{task.prompt}" if preamble else task.prompt


def build(task: Task) -> dict[str, str]:
    """Return {condition_name: full_prompt} for one task, using the task's expected method class."""
    mc = task.expected_method_class
    return {
        "intervention": _wrap(methods.method_text(mc), task),
        "plain_baseline": _wrap("", task),
        "neutral_preamble": _wrap(methods.neutral_preamble(mc), task),
        "scrambled_method": _wrap(methods.scrambled(mc), task),
        "irrelevant_method": _wrap(methods.irrelevant_for(mc), task),
    }


def build_deep(task: Task) -> dict[str, str]:
    """Conditions for a DEEP-method task: the intervention supplies the method's real procedure from
    the deep-methods database; controls neutralise length / structure / relevance the same way."""
    from . import deep_methods as D
    mid = task.expected_method_class
    return {
        "intervention": _wrap(D.as_preamble(mid), task),
        "plain_baseline": _wrap("", task),
        "neutral_preamble": _wrap(D.neutral_deep(mid), task),
        "scrambled_method": _wrap(D.scrambled_deep(mid), task),
        "irrelevant_method": _wrap(D.irrelevant_deep(mid), task),
    }
