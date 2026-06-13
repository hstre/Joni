"""Autobiographical memory - the continuity the outside reads as 'a life'.

Recording happens in the operators (a change that matters leaves an episode).
Retrieval lives here, and it is deterministic: relevance is token overlap with the
query, ties broken by recency then id. No model, no embeddings - the continuity is
real state, not a vibe.
"""

from __future__ import annotations

from .models import MemoryEpisode
from .state import Layer9


def _tokens(text: str) -> set[str]:
    return {w.strip(".,;:!?'\"()").lower() for w in text.split() if len(w) > 3}


def recall(state: Layer9, query: str, *, limit: int = 3) -> list[MemoryEpisode]:
    """Most relevant episodes for a query, most relevant first."""
    q = _tokens(query)
    if not q:
        return recent(state, limit)

    def score(ep: MemoryEpisode) -> tuple:
        overlap = len(q & _tokens(ep.summary))
        return (-overlap, -ep.tick, ep.id)

    ranked = sorted(state.memory, key=score)
    return [ep for ep in ranked if (q & _tokens(ep.summary))][:limit] or recent(state, limit)


def recent(state: Layer9, n: int = 5) -> list[MemoryEpisode]:
    """The last ``n`` episodes, newest first."""
    return list(reversed(state.memory[-n:]))


def autobiography(state: Layer9) -> list[str]:
    """A deterministic chronological self-narrative - one line per episode."""
    return [f"t{ep.tick} · {ep.kind}: {ep.summary}" for ep in state.memory]
