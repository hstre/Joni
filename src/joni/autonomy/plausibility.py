"""The reconstruction-trick plausibility ranker for conflict kinds (Auftrag #135).

Paper: *Argumentative Relation Classification as Plausibility Ranking* (arXiv:1909.09031). To
decide whether two opposed claims are a flat **contradiction** or a softer **scope tension**, build
a minimal pair - a "they fit together" reading and a "they clash" reading - and let a language model
rank which reading is more plausible. The more plausible reconstruction names the relation.

Non-core boundary: this only chooses a conflict-KIND marker (``qualify.py``); conflict detection,
the gate, the ledger and the operators are untouched. **Opt-in, default OFF**
(``JONI_PLAUSIBILITY_QUALIFIER=1``) and gated like every model arm
(``JONI_SEMANTIC_PROPOSALS=1``). It uses Joni's own captured ``joni-hard`` model (replay-stable,
budget-metered) and is bounded to a few rankings per cycle, the weekly budget the hard ceiling.
"""

from __future__ import annotations

import os

from desi_layer9 import ConflictKind

from . import model_call, model_profile, projection
from .config import paths

_SYS = (
    "You rank which of two readings of a claim pair is more PLAUSIBLE and coherent. Reading A "
    "treats the second claim as COMPATIBLE with the first (true on a different scope, condition or "
    "exception). Reading B treats the second claim as a DIRECT CONTRADICTION of the first. Judge "
    "which reading a careful reader would find more plausible. Output ONLY the single "
    "letter 'A' or 'B'."
)


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_PLAUSIBILITY_QUALIFIER", "0") == "1"


def _prompt(a: str, b: str) -> str:
    return (
        f"CLAIM 1: {a}\nCLAIM 2: {b}\n\n"
        f"Reading A (compatible): \"{a}\" - and, on a different scope/condition - \"{b}\".\n"
        f"Reading B (contradiction): \"{a}\" - but in direct contradiction - \"{b}\".\n"
        "Which reading is more plausible? Answer with 'A' or 'B' only."
    )


def _rank_once(a: str, b: str, *, budget, runs_per_week: int, cycle: int) -> str | None:
    """One plausibility ranking -> a ConflictKind value, or None (model/ budget unavailable)."""
    out, _ = model_call.call(
        model_profile.profile("joni-hard"), _SYS, _prompt(a, b),
        run_id=f"joni-c{cycle}-plaus", store_dir=paths().model_calls,
        escalation_reason="plausibility-conflict-qualifier",
        budget=budget, runs_per_week=runs_per_week)
    if not out:
        return None
    tok = out.strip().upper()[:1]
    if tok == "B":
        return ConflictKind.CONTRADICTION.value
    if tok == "A":
        return ConflictKind.SCOPE_TENSION.value
    return None


def ranker_for(*, budget=None, runs_per_week: int = 0, cycle: int = 0, max_calls: int = 1):
    """Return a bounded ``callable(a, b) -> kind | None`` that ranks at most ``max_calls`` pairs
    this cycle, or ``None`` when the feature is disabled. The per-cycle cap bounds spend; the weekly
    budget is the hard ceiling (``model_call`` returns nothing once it is reached)."""
    if not enabled():
        return None
    state = {"left": max(0, int(max_calls))}

    def _rank(a: str, b: str) -> str | None:
        if state["left"] <= 0:
            return None
        state["left"] -= 1
        return _rank_once(a, b, budget=budget, runs_per_week=runs_per_week, cycle=cycle)

    return _rank
