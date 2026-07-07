"""Qualify *what kind* of incompatibility two claims have - deterministically.

Not every flagged opposition is a flat contradiction. The clearest case: "most requests
are served by a small local model" and "for novel problems without a matching pretrained
pattern, parametric knowledge is not enough" are both true - they speak about different
scopes. Calling that a contradiction would be wrong; calling it a *scope tension* is right,
and Joni then need not feel pressed to resolve it.

Pure surface heuristics over the two claim texts (English + a few German markers). Returns
a ``ConflictKind`` value. Conservative order: a clear normal-vs-novel split is a scope
tension; an explicit exception / condition is named as such; a genuine negation or a hard
signal is a contradiction; an unmarked soft tension defaults to *scope tension*, not
contradiction - so the system does not over-state opposition.
"""

from __future__ import annotations

import re

from desi_layer9 import ConflictKind

_SCOPE_NORMAL = ("most", "usually", "typically", "generally", "in general", "commonly",
                 "mostly", "often", "many", "for most", "meist", "meisten", "in der regel")
_SCOPE_NOVEL = ("novel", "new", "unseen", "unfamiliar", "rare", "edge case", "edge-case",
                "out of distribution", "out-of-distribution", "ood", "never seen",
                "uncommon", "exceptional", "without a pretrained", "without pretrained",
                "no pretrained", "neuartig", "unbekannt", "selten")
_EXCEPTION = ("unless", "except", "but not", "does not hold", "apart from", "other than",
              "fails when", "breaks down", "no longer holds", "außer", "ausgenommen")
_CONDITIONAL = ("if", "when", "whenever", "provided", "depends on", "as long as",
                "given that", "in cases where", "conditional", "falls", "sofern", "wenn")


def _compile(markers) -> re.Pattern:
    # Match markers on WORD BOUNDARIES, not as substrings: 'ood' (the OOD acronym) must not fire on
    # good/food/blood/understood, nor 'many' on Germany/humanity - which mis-classified a genuine
    # A/not-A contradiction as a scope tension before the contradiction check was ever reached.
    return re.compile(r"\b(?:" + "|".join(re.escape(m.strip()) for m in markers if m.strip())
                      + r")\b")


_SCOPE_NORMAL_RE = _compile(_SCOPE_NORMAL)
_SCOPE_NOVEL_RE = _compile(_SCOPE_NOVEL)
_EXCEPTION_RE = _compile(_EXCEPTION)
_CONDITIONAL_RE = _compile(_CONDITIONAL)


def _has(rx: re.Pattern, text: str) -> bool:
    return bool(rx.search(text))


def qualify_conflict(a_text: str, b_text: str, *, severity: str = "soft",
                     contradictory: bool = False, ranker=None) -> str:
    """Return the ConflictKind value for the incompatibility between two claims.

    When the surface heuristics are inconclusive (the soft, unmarked default) and a plausibility
    ``ranker`` is supplied (the reconstruction trick, ``plausibility.ranker_for``), let it decide
    between a flat contradiction and a scope tension. The ranker is opt-in and never overrides a
    clear marker-based decision."""
    ta, tb = (a_text or "").lower(), (b_text or "").lower()
    both = ta + " || " + tb

    normal_vs_novel = (
        (_has(_SCOPE_NORMAL_RE, ta) and _has(_SCOPE_NOVEL_RE, tb))
        or (_has(_SCOPE_NORMAL_RE, tb) and _has(_SCOPE_NOVEL_RE, ta))
        or (_has(_SCOPE_NORMAL_RE, both) and _has(_SCOPE_NOVEL_RE, both))
    )
    if normal_vs_novel:
        return ConflictKind.SCOPE_TENSION.value
    if _has(_EXCEPTION_RE, both):
        return ConflictKind.EXCEPTION.value
    if _has(_CONDITIONAL_RE, both):
        return ConflictKind.CONDITIONAL_COMPATIBILITY.value
    if contradictory or severity == "hard":
        return ConflictKind.CONTRADICTION.value
    # Ambiguous soft tension with no marker: the reconstruction-trick plausibility ranker decides
    # (if provided), else the conservative default - a scope tension, not an over-stated clash.
    if ranker is not None:
        refined = ranker(a_text, b_text)
        if refined:
            return refined
    return ConflictKind.SCOPE_TENSION.value
