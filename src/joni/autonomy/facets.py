"""Facet decomposition for candidate extraction (Auftrag #136, after FaBle).

FaBle's idea is to make the semantic-measurement channel facet-aware. Joni's runtime cannot
fine-tune an embedding projector (no training infrastructure), so this lands the faithful part that
*does* fit: before projecting a source into candidate claims, **decompose it into its distinct
facets** - the separate aspects, conditions or sub-claims it actually contains (a method, its scope,
a result, a limitation) - and project each facet on its own. A faceted source then yields faceted
candidates instead of one blurred whole, so a facet-conditioned topic is matched on the facet that
actually carries it.

Non-core (only the candidate-extraction front of ``semantics-measurement``; the gate, ledger and
operators are untouched). Opt-in (``JONI_FACET_DECOMP=1``), gated like every model arm, budget-
metered via Joni's own ``joni-hard`` model and captured. One-facet text is returned as-is.

Note on the acceptance metric (+5% Precision@k on a FaBle-style benchmark): that needs a labelled
faceted-retrieval test set, which Joni does not have; this lands the mechanism + a mechanism test.
"""

from __future__ import annotations

import json
import os

from . import model_call, model_profile, projection
from .config import paths

_SYS = (
    "You split a short research text into its distinct FACETS - the separate aspects, conditions "
    "or sub-claims it actually contains (the method, its scope/condition, a result, a limitation). "
    "Output ONLY a JSON array of 2-4 short strings, each a self-contained facet in the text's own "
    "terms - no invention, no overlap. If the text has only one facet, return one element."
)


def enabled() -> bool:
    from . import extension_review
    return (projection.enabled() and os.getenv("JONI_FACET_DECOMP", "0") == "1"
            and extension_review.active("facet_decomp"))


def decompose(text: str, *, budget=None, runs_per_week: int = 0, cycle: int = 0,
              store_dir=None) -> list[str]:
    """Split ``text`` into 2-4 facet-unit strings, or [] when disabled / unavailable / empty (the
    caller then projects the whole text as before). Captured and budget-metered."""
    if not enabled() or not (text or "").strip():
        return []
    out, _cap = model_call.call(
        model_profile.profile("joni-hard"), _SYS, f"TEXT:\n{text[:1800]}\n\nFacets?",
        run_id=f"joni-c{cycle}-facets", store_dir=store_dir or paths().model_calls,
        escalation_reason="facet-decomposition", budget=budget, runs_per_week=runs_per_week)
    if not out:
        return []
    try:
        arr = json.loads(out)
    except json.JSONDecodeError:
        start, end = out.find("["), out.rfind("]")
        if start == -1 or end <= start:
            return []
        try:
            arr = json.loads(out[start:end + 1])
        except json.JSONDecodeError:
            return []
    if not isinstance(arr, list):
        return []
    return [str(x).strip() for x in arr if str(x).strip()][:4]
