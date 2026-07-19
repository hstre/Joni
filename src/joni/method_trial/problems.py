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


def match(name: str, summary: str) -> Problem | None:
    """The first library problem whose keywords appear in the method's name+summary, else None
    (the method is not trialable yet - left honestly untested)."""
    text = f"{name or ''} {summary or ''}".lower()
    for problem in LIBRARY:
        if any(k in text for k in problem.keywords):
            return problem
    return None


__all__ = ["Problem", "LIBRARY", "match"]
