"""Autobiographical memory - the continuity the outside reads as 'a life'.

Recording happens in the operators (a change that matters leaves an episode).
Retrieval lives here, and it is deterministic: relevance is token overlap with the
query, ties broken by recency then id. No model, no embeddings - the continuity is
real state, not a vibe.
"""

from __future__ import annotations

from .models import Basis, MemoryEpisode
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


# --------------------------------------------------------------------------- #
# Grundlagenpruefung - Klasse A: Feldpraesenz, keine Semantik, kein Modell
# --------------------------------------------------------------------------- #


def undeclared(state: Layer9) -> list[MemoryEpisode]:
    """Episoden, die ueber eine aeussere Quelle etwas behaupten, ohne ihre Grundlage zu nennen.

    Das ist die ganze Regel: ``sources`` gefuellt und ``basis`` gleich UNDECLARED. Kein Urteil
    darueber, ob die Aussage stimmt - nur, dass niemand gesagt hat, woher sie kommt.

    Der Fall, aus dem sie stammt: Ueber ein Papier wurde geurteilt, das nie geoeffnet worden war;
    die Grundlage war ein gleichnamiges Modul im Repository. Fuenfmal in einer Sitzung, mit den
    vorangegangenen Korrekturen sichtbar im Verlauf. Ein Gedaechtnis haette das nicht verhindert -
    das Gedaechtnis war da. Was fehlte, war das Feld.
    """
    return [ep for ep in state.memory if ep.sources and ep.basis is Basis.UNDECLARED]


def inferred(state: Layer9) -> list[MemoryEpisode]:
    """Episoden, die sich ausdruecklich als erschlossen ausweisen.

    Kein Fehler - erschliessen ist erlaubt und oft richtig. Aber es ist die Menge, die ein
    Pruefer zuerst ansieht, und sie muss deshalb abrufbar sein statt im Fliesstext zu verschwinden.
    """
    return [ep for ep in state.memory if ep.basis is Basis.INFERRED]


def basis_report(state: Layer9) -> dict:
    """Abzaehlung je Grundlage plus die beiden Mengen, auf die es ankommt. Rein deskriptiv."""
    counts: dict[str, int] = {}
    for ep in state.memory:
        counts[str(ep.basis)] = counts.get(str(ep.basis), 0) + 1
    return {
        "episodes": len(state.memory),
        "by_basis": counts,
        "undeclared_with_sources": [ep.id for ep in undeclared(state)],
        "inferred": [ep.id for ep in inferred(state)],
    }
