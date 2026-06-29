"""Deterministic subject-key for a claim — a finer 'scope' than topic, with no model.

The real-data shadow showed the supersession check (#5) and scope check (#6) firing uselessly
because **topic is far too coarse a stand-in for scope**: every claim not the newest of its
*topic* looked superseded. A scope needs to be about the same *subject*, not merely the same broad
area. This derives a deterministic subject key from the text — "rules for logic", no embedding,
replay-stable — so two claims about the SAME subject share a key while same-topic-different-
subject claims do not.

It is a lexical proxy, honestly imperfect: paraphrases with different salient words land in other
keys (the check then under-fires, the safe direction), and two unrelated claims sharing a rare long
word can collide. The point is a strict, measurable improvement over topic-only — the shadow reports
whether it turns #5 from over-firing into selective. A richer key could cluster by embedding;
that is a separate, non-deterministic choice.
"""
from __future__ import annotations

import re
import unicodedata

_TOK = re.compile(r"[a-z][a-z0-9\-]{3,}")
# generic words carrying no subject identity (small + deterministic; mirrors quality.STOPWORDS)
_STOP = frozenset((
    "this", "that", "these", "those", "there", "their", "them", "then", "than", "with", "without",
    "from", "into", "onto", "over", "under", "about", "above", "below", "between", "through",
    "have", "has", "had", "having", "been", "being", "does", "doing", "done", "will", "would",
    "should", "could", "must", "may", "might", "can", "cannot", "shall", "such", "some", "many",
    "more", "most", "much", "very", "also", "only", "even", "still", "just", "much", "they",
    "track", "topic", "claim", "thing", "things", "stuff", "really", "always", "never", "often",
    "uses", "used", "using", "make", "makes", "made", "need", "needs", "want", "like", "good",
    "bad", "best", "better", "worse", "high", "low", "large", "small", "same", "different",
))


def _fold(s: str) -> str:
    """Canonicalise to a stable ASCII-lexical form. NFKD-decompose, drop combining marks, lowercase.

    This closes a real determinism hole. The ASCII ``_TOK`` regex tokenises canonically-EQUAL
    strings differently by Unicode form: an accented word in NFC (one precomposed codepoint) breaks
    the token run at the accent, while the same word in NFD (base letter + combining mark) keeps the
    base letter in the run -- so the two yield different tokens. Source text arrives in either form
    (NFD on macOS, NFC elsewhere), so without folding two byte-different-but-identical inputs would
    get different subject keys -- the silent non-determinism this key exists to remove. Folding also
    lets accented Latin words take part via their base letters instead of being truncated, a strict
    improvement on the multilingual text CLSP feeds. Deterministic, stdlib-only, no model."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def subject_key(text: str | None, topic: str | None = None) -> str:
    """A stable subject signature: topic plus the few most salient content tokens of the text
    (salient = longest, ties broken alphabetically), de-duped and sorted so order does not matter.
    Same subject -> same key, regardless of phrasing order. Empty text falls back to the topic."""
    tl = _fold(topic or "").strip()
    toks = [t for t in _TOK.findall(_fold(text or "")) if t not in _STOP and t != tl]
    if not toks:
        return f"topic:{tl}"
    salient = sorted(set(toks), key=lambda w: (-len(w), w))[:3]
    return f"topic:{tl}|" + "+".join(sorted(salient))
