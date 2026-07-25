"""P3: a small library of hand-curated trial problems, and a matcher from a shelf method to one.

To trial a shelf method for real it needs a **matching gold benchmark**. Most harvested methods
have none - and that is fine: they stay **honestly untested** rather than trialed against an
irrelevant set (which would only manufacture a false signal). This library holds a few frozen,
hand-curated problems (task set + baseline + negative control, gold labels independent of any
model), each tagged with the keywords a method's text must mention to be paired with it.

Growing this library is how the backlog is drained over time: each new (method-type -> gold set)
pair makes another class of shelf methods really trialable.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import sandbox_trial


@dataclass(frozen=True)
class Problem:
    spec: sandbox_trial.TrialSpec
    task_desc: str
    keywords: tuple


_UNIT_EQUALITY = Problem(
    spec=sandbox_trial.unit_equality_spec(),
    task_desc=("payload has keys 'a' and 'b' (measurement strings like '5 km'); return\n"
               "{'label': 'same'} if they denote the same quantity else {'label': 'different'}."),
    keywords=("unit", "units", "normalis", "normaliz", "canonical", "convert", "conversion",
              "dimension", "dimensional", "measure", "measurement", "quantit", "equivalen"),
)

_DEDUP = Problem(
    spec=sandbox_trial.dedup_spec(),
    task_desc=("payload has keys 'a' and 'b' (short texts); return {'label': 'duplicate'} if they "
               "are the same text up to case and punctuation else {'label': 'distinct'}."),
    keywords=("duplicate", "dedup", "deduplicat", "near-duplicate", "near duplicate", "redundan",
              "identical text", "same text", "canonical", "collision"),
)

_TEMPORAL = Problem(
    spec=sandbox_trial.temporal_order_spec(),
    task_desc=("payload has keys 'a' and 'b' (dates, ISO YYYY-MM-DD or German DD.MM.YYYY); return "
               "{'label': 'before' | 'after' | 'same'} for how 'a' relates to 'b' in time."),
    keywords=("temporal", "chronolog", "date", "dates", "timestamp", "time order", "ordering",
              "sequence", "sort by time", "earlier", "later", "recency"),
)

LIBRARY: tuple[Problem, ...] = (_UNIT_EQUALITY, _DEDUP, _TEMPORAL)


_MAX_NAME_TOKENS = 4          # a micro-benchmark is for a SHORT procedure, not a paper title


def _name_core(name: str) -> str:
    n = name or ""
    return n[: -len("-as-a-lens")] if n.endswith("-as-a-lens") else n


def match(name: str, summary: str) -> Problem | None:
    """The first library problem this method can be *meaningfully* trialed against, else None
    (left honestly untested). A method qualifies only if it is a SHORT procedure/lens - a
    micro-benchmark tests a micro-procedure, not a harvested paper title. This is the fix for the
    live finding that long paper titles ('...Long Video Temporal Reasoning...') were being
    keyword-matched to the date-ordering benchmark and 'trialed' meaninglessly. A keyword still has
    to appear, but only short-named candidates are eligible - a title with an incidental keyword is
    not. (The deeper validity limit - a fully-described benchmark lets the solver bypass the method
    text - is why the Skill Consolidator wants richer methods; see the design note.)
    """
    if len(_name_core(name).split()) > _MAX_NAME_TOKENS:
        return None
    text = f"{name or ''} {summary or ''}".lower()
    for problem in LIBRARY:
        if any(k in text for k in problem.keywords):
            return problem
    return None


def is_short_procedure_name(name: str) -> bool:
    """Whether ``name`` reads as a SHORT procedure/lens rather than a harvested paper title - the
    same gate ``match`` applies. Exposed so a diagnostic can tell 'not a procedure' (a long title)
    apart from 'a real short procedure that just has no benchmark'."""
    return len(_name_core(name or "").split()) <= _MAX_NAME_TOKENS


def by_task_set(task_set: str) -> Problem | None:
    """The library problem whose frozen task set has this name, else None. S4 uses it to re-trial a
    probationary skill against its **own** stored verification (``SkillCandidate.verification`` is
    the ``task_set`` name), so maturation measures the same benchmark that first crystallised it."""
    for problem in LIBRARY:
        if problem.spec.task_set == task_set:
            return problem
    return None


__all__ = ["Problem", "LIBRARY", "match", "by_task_set", "is_short_procedure_name"]
