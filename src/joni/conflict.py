"""Conflict engine - deterministic contradiction detection between claims.

This is pure logic, no model. It finds pairs of live claims on the same topic that
cannot both stand, and registers them as conflicts. The improvement loop later
resolves each by rejecting the weaker claim - which is exactly what surfaces, on the
outside, as "I have since changed my mind."

Two rules, both deterministic:
  * negation        - same topic, overlapping wording, but opposite polarity
                      (one carries a negation marker the other lacks);
  * stance_opposition - same topic, and the two carry an antonym pair.
"""

from __future__ import annotations

from .operators import open_conflict
from .state import Layer9

_NEGATIONS = {
    "not", "no", "never", "without", "cannot", "stop", "avoid", "n't",
    "isn't", "won't", "don't", "doesn't", "shouldn't", "can't",
}

_ANTONYMS = (
    ("increase", "decrease"), ("more", "less"), ("more", "fewer"),
    ("better", "worse"), ("good", "bad"), ("local", "external"),
    ("fast", "slow"), ("simple", "complex"), ("keep", "drop"),
    ("centralise", "decentralise"), ("trust", "distrust"), ("open", "closed"),
)


def _tokens(text: str) -> set[str]:
    return {w.strip(".,;:!?'\"()").lower() for w in text.split()}


def _content(text: str) -> set[str]:
    return {w for w in _tokens(text) if len(w) > 3 and w not in _NEGATIONS}


def _overlap(a: str, b: str) -> float:
    ta, tb = _content(a), _content(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _polarity(text: str) -> int:
    """-1 if the claim is negated, +1 otherwise. Deterministic surface heuristic."""
    return -1 if (_tokens(text) & _NEGATIONS) else 1


def _antonym_clash(a: str, b: str) -> bool:
    ta, tb = _tokens(a), _tokens(b)
    return any(
        (x in ta and y in tb) or (y in ta and x in tb) for x, y in _ANTONYMS
    )


def detect_conflicts(state: Layer9, *, overlap_threshold: float = 0.34) -> list:
    """Scan live claims and open conflicts for any new contradictions.

    Idempotent: a pair already registered as a conflict is not opened again. Order is
    deterministic (claims compared in id order), so the same state always yields the
    same conflicts in the same sequence.
    """
    live = sorted(state.active_claims(), key=lambda c: c.id)
    existing = {
        frozenset((x.claim_a, x.claim_b)) for x in state.conflicts.values()
    }
    opened = []
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            if a.topic != b.topic:
                continue
            pair = frozenset((a.id, b.id))
            if pair in existing:
                continue
            kind = None
            if _antonym_clash(a.text, b.text):
                kind = "stance_opposition"
            elif _overlap(a.text, b.text) >= overlap_threshold and \
                    _polarity(a.text) != _polarity(b.text):
                kind = "negation"
            if kind:
                opened.append(open_conflict(state, a.id, b.id, kind))
                existing.add(pair)
    return opened


def weaker_claim(state: Layer9, conflict) -> str:
    """Which claim loses: lower support, then older, then higher id (deterministic)."""
    a = state.claims[conflict.claim_a]
    b = state.claims[conflict.claim_b]
    # Sort key: prefer to KEEP higher support / newer; reject the other.
    loser = min(
        (a, b),
        key=lambda c: (c.support, -c.created_tick, _neg_id(c.id)),
    )
    return loser.id


def _neg_id(cid: str) -> int:
    # Higher numeric id => newer; reject the *lower* id on a full tie.
    try:
        return -int(cid.split("-")[1])
    except (IndexError, ValueError):
        return 0
