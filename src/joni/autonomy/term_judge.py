"""A small LLM 'in-doubt' term-judge for the emergence selection points.

The lexical floor (``quality.is_meaningful_term``) rejects stopwords/artifacts for free, and
``quality.on_domain`` measures off-domain *concepts* with embeddings. What neither reliably
catches is the fuzzy residual: real-looking words that are not transferable analytical
concepts - a place/language/name ('uzbek', 'quispe-colca'), a repo/product slug, generic
filler that survived both gates. This asks a cheap model ONE yes/no question about the single
winning term at a selection point (a topic or an '<term>-as-a-lens' method), and only ever
*removes* a doubtful candidate - it never adds one.

Design (matches Joni's other LLM arms):
  * OFF by default (``JONI_TERM_JUDGE=0``) - a dormant capability until the operator flips it on
    and watches, exactly like every other arm;
  * budget-gated + content-addressed cache (via ``model_call.call``): a term is judged live at
    most once, then replayed for free;
  * **fails to the rule**: disabled / over budget / model unavailable / unparseable all return
    ``None``, and the caller then KEEPS the rule's decision. It never fails *open* into junk (the
    bug that let the stopword lenses through) and never *freezes* emergence when the model is gone.
"""

from __future__ import annotations

import os

from . import model_call, model_profile
from .config import paths

_SYS = (
    "You are a strict terminology filter for a research agent. Reply with exactly one word: "
    "'yes' or 'no'. Answer 'yes' only if the given single term names a genuine, transferable "
    "analytical or scientific concept worth developing as a lens on a new problem. Answer 'no' "
    "for function words, names of people/places/languages, repository or product slugs, and "
    "generic filler."
)


def enabled() -> bool:
    """Dormant until the operator opts in (JONI_TERM_JUDGE=1)."""
    return os.getenv("JONI_TERM_JUDGE", "0") == "1"


def judge(term: str, *, budget=None, cycle: int = 0, runs_per_week: int = 0) -> bool | None:
    """True/False when the model gives a clear verdict on `term`; None otherwise (disabled,
    over budget, model unavailable, or an unparseable answer) - the caller then keeps the
    rule's decision. Never fails open into junk; never freezes on the model's absence."""
    t = (term or "").strip()
    if not enabled() or not t:
        return None
    out, _cap = model_call.call(
        model_profile.joni_semantic(), _SYS,
        f"Term: {t}\nIs this a genuine, transferable analytical concept? Answer yes or no.",
        run_id=f"termjudge-c{cycle}", store_dir=paths().model_calls,
        budget=budget, runs_per_week=runs_per_week)
    if not out:
        return None                      # over budget / failed / no model -> defer to the rule
    a = out.strip().lower()
    if a.startswith("yes"):
        return True
    if a.startswith("no"):
        return False
    return None                          # unparseable -> defer to the rule


__all__ = ["enabled", "judge"]
