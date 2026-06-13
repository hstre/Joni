"""Cheap lexical candidate generation - the trigger, nothing more.

This is the *only* thing the old word-overlap mechanism is still allowed to do: cheaply
nominate claim pairs (and groups) that *might* be related, so the real DESi Semantic Layer
runs on a handful of candidates instead of every pair. It draws **no** conclusions - it
never decides that two claims support, duplicate, or belong together. That judgement is the
Semantic Layer's, governed by Layer 9.

Purely lexical: shared lemmatised content tokens / Jaccard overlap. No concept
normalisation, no senses, no embeddings - those belong to the DESi Semantic Layer, not here.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

from .text import content_tokens, token_overlap

# tokens too generic to anchor a candidate group
_GENERIC = frozenset({
    "topic", "track", "tracking", "claim", "claims", "pattern", "hypothesis", "across",
    "approach", "method", "system", "model", "result", "data", "thing", "worth", "recurs",
})


def _is_synthetic(text: str) -> bool:
    t = text.lower()
    return (t.startswith("hypothesis:") or t.startswith("across my")
            or "is a topic i track" in t or "is worth tracking" in t
            or "keeps recurring" in t or "recurs as a through-line" in t)


def lexical_overlap(a_text: str, b_text: str) -> float:
    """The cheap trigger score in [0,1] - Jaccard over lemmatised content tokens."""
    return round(token_overlap(a_text, b_text), 4)


@dataclass(frozen=True)
class CandidatePair:
    a_id: str
    b_id: str
    lexical_trigger: float


def candidate_pairs(claims, *, trigger: float = 0.3, same_topic_only: bool = True):
    """Nominate claim pairs whose lexical overlap clears ``trigger``. Deterministic order."""
    items = sorted(claims, key=lambda c: c.id)
    out: list[CandidatePair] = []
    for a, b in combinations(items, 2):
        if _is_synthetic(a.text) or _is_synthetic(b.text):
            continue
        if same_topic_only and getattr(a, "topic", "") != getattr(b, "topic", ""):
            continue
        score = lexical_overlap(a.text, b.text)
        if score >= trigger:
            out.append(CandidatePair(a_id=a.id, b_id=b.id, lexical_trigger=score))
    out.sort(key=lambda p: (-p.lexical_trigger, p.a_id, p.b_id))
    return out


@dataclass(frozen=True)
class CandidateGroup:
    surface_term: str
    member_ids: tuple[str, ...]


def candidate_groups(claims, *, min_claims: int = 3):
    """Nominate groups of claims sharing a lemmatised content token. No interpretation."""
    by_term: dict[str, list[str]] = defaultdict(list)
    for c in claims:
        if _is_synthetic(c.text):
            continue
        for tok in set(content_tokens(c.text)):
            if tok in _GENERIC:
                continue
            by_term[tok].append(c.id)
    groups = [
        CandidateGroup(surface_term=term, member_ids=tuple(sorted(set(ids))))
        for term, ids in by_term.items() if len(set(ids)) >= min_claims
    ]
    groups.sort(key=lambda g: (g.surface_term, g.member_ids))
    return groups
