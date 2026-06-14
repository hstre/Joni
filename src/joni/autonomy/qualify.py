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

from desi_layer9 import ConflictKind

_SCOPE_NORMAL = ("most", "usually", "typically", "generally", "in general", "commonly",
                 "mostly", "often", "many", "for most", "meist", "meisten", "in der regel")
_SCOPE_NOVEL = ("novel", "new ", "unseen", "unfamiliar", "rare", "edge case", "edge-case",
                "out of distribution", "out-of-distribution", "ood", "never seen",
                "uncommon", "exceptional", "without a pretrained", "without pretrained",
                "no pretrained", "neuartig", "unbekannt", "selten")
_EXCEPTION = ("unless", "except", "but not", "does not hold", "apart from", "other than",
              "fails when", "breaks down", "no longer holds", "außer", "ausgenommen")
_CONDITIONAL = ("if ", "when ", "whenever", "provided", "depends on", "as long as",
                "given that", "in cases where", "conditional", "falls", "sofern", "wenn ")


def _has(markers, text: str) -> bool:
    return any(m in text for m in markers)


def qualify_conflict(a_text: str, b_text: str, *, severity: str = "soft",
                     contradictory: bool = False) -> str:
    """Return the ConflictKind value for the incompatibility between two claims."""
    ta, tb = (a_text or "").lower(), (b_text or "").lower()
    both = ta + " || " + tb

    normal_vs_novel = (
        (_has(_SCOPE_NORMAL, ta) and _has(_SCOPE_NOVEL, tb))
        or (_has(_SCOPE_NORMAL, tb) and _has(_SCOPE_NOVEL, ta))
        or (_has(_SCOPE_NORMAL, both) and _has(_SCOPE_NOVEL, both))
    )
    if normal_vs_novel:
        return ConflictKind.SCOPE_TENSION.value
    if _has(_EXCEPTION, both):
        return ConflictKind.EXCEPTION.value
    if _has(_CONDITIONAL, both):
        return ConflictKind.CONDITIONAL_COMPATIBILITY.value
    if contradictory or severity == "hard":
        return ConflictKind.CONTRADICTION.value
    return ConflictKind.SCOPE_TENSION.value
