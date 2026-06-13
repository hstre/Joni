"""Deterministic, dependency-free text utilities for the semantic layer.

Tokenisation, a tiny lemmatiser, content-word filtering, n-grams and negation/antonym
signals. No third-party NLP: Layer 9 stays dependency-free and replay-stable.
"""

from __future__ import annotations

NEGATIONS = frozenset({
    "not", "no", "never", "without", "cannot", "can't", "isn't", "won't", "don't",
    "doesn't", "shouldn't", "n't", "lacks", "absent", "fails",
})

STOPWORDS = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "but", "with", "as",
    "is", "are", "was", "were", "be", "been", "being", "that", "this", "these", "those",
    "it", "its", "which", "what", "when", "during", "than", "then", "into", "from", "by",
    "at", "we", "i", "they", "he", "she", "you", "more", "less", "most", "some", "any",
    "test", "tests", "number", "paper", "study", "shows", "show", "using", "based",
})

_ANTONYMS = (
    ("increase", "decrease"), ("increased", "decreased"), ("more", "less"),
    ("more", "fewer"), ("better", "worse"), ("good", "bad"), ("local", "external"),
    ("fast", "slow"), ("simple", "complex"), ("keep", "drop"), ("rise", "fall"),
    ("open", "closed"), ("improves", "worsens"), ("reduces", "increases"),
    ("up", "down"), ("high", "low"), ("enable", "disable"),
)


def tokens(text: str) -> list[str]:
    return [w.strip(".,;:!?'\"()[]{}").lower() for w in text.split()]


def lemmatize(word: str) -> str:
    """A deliberately small, deterministic stemmer (plurals / common verb endings)."""
    w = word.lower()
    for suf in ("ization", "isation", "ations", "ation", "ingly", "edly"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[: -len(suf)]
    for suf in ("’s", "'s", "ies", "es", "ing", "ed", "s"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[:-3] + "y" if suf == "ies" else w[: -len(suf)]
    return w


def content_tokens(text: str) -> list[str]:
    """Lemmatised content words (len>2, not stopword/negation), order preserved, deduped."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in tokens(text):
        if len(raw) <= 2 or raw in STOPWORDS or raw in NEGATIONS:
            continue
        lem = lemmatize(raw)
        if len(lem) <= 2 or lem in seen:
            continue
        seen.add(lem)
        out.append(lem)
    return out


def trigrams(text: str) -> set[str]:
    s = "".join(ch for ch in text.lower() if ch.isalnum() or ch == " ")
    return {s[i:i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}


def is_negated(text: str) -> bool:
    return bool(set(tokens(text)) & NEGATIONS)


def antonym_clash(a: str, b: str) -> bool:
    ta, tb = set(tokens(a)), set(tokens(b))
    return any((x in ta and y in tb) or (y in ta and x in tb) for x, y in _ANTONYMS)


def token_overlap(a: str, b: str) -> float:
    ta, tb = set(content_tokens(a)), set(content_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
