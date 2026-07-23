"""Priority 3: a hypothesis is not a word that recurs in a template.

The operator's diagnosis is exact: many "hypotheses" are lexical recurrence - ``'electrical'``,
``'ransomware'``, ``'archaeological'`` offered as a shared factor in a fixed schema. That is a
*pattern hint* (Musterhinweis), not a hypothesis, and it must not consume a reflection cycle.

This module draws the line deterministically (no LLM, no embedding - a transparent lexical gate,
like ``quality.is_good_topic``). A well-formed hypothesis must carry all four of:

  * a **claimed mechanism** - a causal/explanatory link, not just "X recurs";
  * a **scope** (Geltungsbereich) - where/when it is meant to hold;
  * an **expected observation** - what we should see if it is true;
  * a **possible refutation** - what would show it false.

Miss any of these and it is not yet *well-formed*: ``completeness(text)`` scores it 0-4 so the gap
is measured and visible (the scoreboard shows the distribution), not hidden.

Two distinct notions, deliberately kept apart:

  * ``well_formed`` - the full 4-component bar (the quality standard we measure every hypothesis
    against and want producers to reach);
  * ``is_reflection_barred`` - the *targeted* bar actually enforced at the reflection boundary: it
    fires only on the clear junk (a bare word / a fixed recurrence template - the emerge/invent
    "term X recurs", "pattern behind X might apply to Y" shapes the operator flagged), so a
    substantive-but-plainly-phrased hypothesis still earns reflection while lexical recurrence does
    not. Producers are then moved toward ``well_formed`` separately.

The gate is honest about being lexical - it reports exactly which components are present/missing.
"""
from __future__ import annotations

import re

COMPONENTS = ("mechanism", "scope", "expected_observation", "refutation")

# Each component is evidenced by explicit causal / conditional / predictive / falsification language
# (English + German - German is a first-class output language here). Word-boundary matched, so
# 'unless' never fires inside another word. These are markers of a *claim shape*, not of content.
_MARKERS: dict[str, tuple[str, ...]] = {
    "mechanism": (
        "because", "since", "due to", "causes", "cause", "caused by", "drives", "driven by",
        "leads to", "results in", "gives rise to", "mediates", "mediated by", "via", "through",
        "mechanism", "explains", "explained by", "underlying", "responsible for",
        "weil", "da", "wegen", "verursacht", "führt zu", "bewirkt", "durch", "mechanismus",
        "erklärt", "zugrunde",
    ),
    "scope": (
        # deliberately NOT bare "in"/"for" (too common to mean anything) - a scope marker names a
        # condition or restriction, so the component is real rather than trivially satisfied
        "when", "whenever", "among", "within", "under", "only if", "only when", "restricted to",
        "limited to", "holds for", "applies to", "in the case of", "specifically", "for cases",
        "wenn", "falls", "bei", "unter", "innerhalb", "gilt für", "beschränkt auf", "im fall",
        "speziell", "sofern",
    ),
    "expected_observation": (
        "expect", "expected", "predict", "predicts", "predicted", "should observe", "should show",
        "should find", "would show", "would see", "we would observe", "measurable", "testable",
        "observable", "then we", "should correlate",
        "erwarten", "erwartet", "vorhersage", "vorhersagen", "sollte zeigen", "sollte sich",
        "messbar", "beobachtbar", "prüfbar", "dann sollte",
    ),
    "refutation": (
        "falsified if", "refuted if", "refuted by", "would be wrong if", "wrong if", "unless",
        "ruled out if", "disconfirm", "disconfirmed", "counterexample", "counter-example",
        "fails if", "would fail if", "no such", "absence of",
        "widerlegt", "falsifiziert", "gegenbeispiel", "wäre falsch", "ausgeschlossen wenn",
        "scheitert wenn", "falls nicht",
    ),
}

# Known template shapes emerge/invent emit - reported as recurrence so the log can name the cause.
_RECURRENCE_TEMPLATES = (
    re.compile(r"\bthe term\b.{0,40}\brecurs\b", re.I),
    re.compile(r"\brecurs\b", re.I),
    re.compile(r"remains untested", re.I),
    re.compile(r"might also apply", re.I),
    re.compile(r"the pattern behind", re.I),
    re.compile(r"whether this reflects", re.I),
    re.compile(r"shared (?:mechanism|factor|cause) remains", re.I),
)


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    low = f" {(text or '').lower()} "
    for m in markers:
        # word-boundary match for single tokens; phrase match (with spaces) for multiword markers
        if " " in m:
            if m in low:
                return True
        elif re.search(rf"(?<![\w-]){re.escape(m)}(?![\w-])", low):
            return True
    return False


def classify(text: str) -> dict:
    """Which of the four components the text evidences, which are missing, and whether it looks like
    a bare recurrence template. Deterministic and transparent - it shows its work."""
    present = [c for c in COMPONENTS if _has_marker(text, _MARKERS[c])]
    missing = [c for c in COMPONENTS if c not in present]
    is_recurrence = any(p.search(text or "") for p in _RECURRENCE_TEMPLATES)
    return {"present": present, "missing": missing, "well_formed": not missing,
            "is_recurrence_template": is_recurrence}


def well_formed(text: str) -> bool:
    """True iff the text states a real, testable proposition: a claimed mechanism, a scope, an
    expected observation AND a possible refutation. The full quality standard (measured, wanted)."""
    return not classify(text)["missing"]


def completeness(text: str) -> int:
    """How many of the four components the text evidences (0-4). The measured well-formedness score
    shown per hypothesis on the scoreboard - a hypothesis with 0 is bare, 4 is fully operational."""
    return len(classify(text)["present"])


# Frame words: template scaffolding that must not count as content, so a bare recurrence claim
# ('the term X recurs') is seen for what it is - one content word dressed in a schema.
_FRAME_WORDS = frozenset({
    "the", "term", "recurs", "across", "claims", "claim", "this", "that", "whether", "reflects",
    "shared", "mechanism", "remains", "untested", "hypothesis", "pattern", "behind", "might",
    "also", "apply", "applies", "from", "and", "for", "with", "about", "common", "factor",
    "under", "over", "may", "could", "would", "some", "many", "several", "there", "their",
})
_WORD = re.compile(r"[A-Za-z][A-Za-z-]{2,}")


def _content_word_count(text: str) -> int:
    """Distinct content words (>=3 letters, not template scaffolding). A bare word-repetition
    'hypothesis' collapses to <=1 here - which is the whole point."""
    words = {w.lower() for w in _WORD.findall(text or "")}
    return len(words - _FRAME_WORDS)


def is_reflection_barred(text: str) -> bool:
    """The TARGETED bar enforced at the reflection boundary: bar the clear junk only - a fixed
    recurrence template, or a bare word-repetition with <=1 real content word. A substantive but
    plainly-phrased hypothesis is NOT barred (it still earns reflection); only lexical recurrence
    is. This is narrower than ``not well_formed`` on purpose (see the module docstring)."""
    if any(p.search(text or "") for p in _RECURRENCE_TEMPLATES):
        return True
    return _content_word_count(text) <= 1


def is_pattern_hint(text: str) -> bool:
    """A hypothesis that has not reached the full 4-component standard - the complement of
    ``well_formed``. (Reflection uses the narrower ``is_reflection_barred``, not this.)"""
    return not well_formed(text)


__all__ = ["COMPONENTS", "classify", "well_formed", "completeness", "is_reflection_barred",
           "is_pattern_hint"]
