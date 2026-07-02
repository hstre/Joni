"""(a) Live coordinate source: derive a governance StateVector per Layer-9 object, build points.

The cartographer needs a 9-dim governance vector per solution point. DESi computes StateVectors from
*trajectories* via the compression Φ; a single claim has no trajectory. So this DERIVES the nine axes
directly from the object's Layer-9 facts (confidence_or_support, status, provenance, derived_from, the
conflicts it sits in), in the same 'derive real facts, mark what's unknown, never fabricate' spirit as
the epistemic_gap_projector. Two axes (branch_cost, routing_state) have no honest per-object source and
are left 0.0 — a point-projection into the governance space, NOT the trajectory Φ.

Read-only, fail-open: no Layer-9 available -> []. Embeddings via ``coordinates.build_points``.
"""

from __future__ import annotations

import hashlib

from .cartography import SolutionPoint
from .coordinates import embed_texts

# status -> a support-state scalar in [0,1] (higher = more established)
_STATUS_SUPPORT = {
    "candidate": 0.2, "provisional": 0.5, "active": 0.7, "confirmed": 1.0,
    "contested": 0.4, "rejected": 0.0, "superseded": 0.1, "quarantined": 0.0,
}
_ANCHORED_STATUS = frozenset({"confirmed", "active"})


def _hash01(s: str) -> float:
    return (int(hashlib.sha256((s or "").encode()).hexdigest()[:8], 16) % 1000) / 1000.0


def _enum_val(x, default=""):
    return getattr(x, "value", x) if x is not None else default


def state_vector_from_object(obj, *, conflict_count: int = 0, current_tick: int = 0,
                             novelty_window: int = 50) -> tuple[float, ...]:
    """Derive the 9 governance axes (DESi order) from one Layer-9 object's facts. ``conflict_count``
    is how many OPEN conflicts touch it; ``current_tick`` anchors novelty. Deterministic, [0,1] each."""
    prov = getattr(obj, "provenance", None)
    source_ids = tuple(getattr(prov, "source_ids", ()) or ()) if prov else ()
    n_anchor = len(getattr(obj, "derived_from", ()) or ()) + len(source_ids)
    created = int(getattr(obj, "created_tick", 0) or 0)
    age = max(0, current_tick - created)
    novelty = max(0.0, 1.0 - age / novelty_window) if current_tick > 0 else 0.5
    status = str(_enum_val(getattr(obj, "status", None), "candidate"))
    authority = str(_enum_val(getattr(obj, "authority", None), "untrusted"))
    return (
        _hash01(str(getattr(obj, "topic", "")) or str(getattr(obj, "id", ""))),  # frame_id
        min(conflict_count, 5) / 5.0,                                            # contradiction_load
        min(n_anchor, 5) / 5.0,                                                  # anchor_density
        (0.5 if authority == "untrusted" else 1.0) * min(1.0, 0.3 + 0.2 * len(source_ids)),  # source_q
        novelty,                                                                 # novelty
        float(getattr(obj, "confidence_or_support", 0.5) or 0.0),               # confidence
        0.0,                                                                     # branch_cost (unknown)
        _STATUS_SUPPORT.get(status, 0.3),                                        # support_state
        0.0,                                                                     # routing_state (unknown)
    )


def _open_conflict_counts(core) -> dict[str, int]:
    counts: dict[str, int] = {}
    for c in core.open_conflicts():
        for cid in getattr(c, "claim_ids", ()) or getattr(c, "scope", ()) or ():
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def points_from_core(core, *, allow_model: bool = True) -> list[SolutionPoint]:
    """Build ``SolutionPoint``s from a Layer-9 core's CLAIMS: text -> embedding, facts -> StateVector,
    ``anchored`` iff the claim's status is established. Read-only; fail-open ([] on any error)."""
    try:
        from desi_layer9 import ObjectType
    except Exception:  # noqa: BLE001
        return []
    try:
        claims = list(core.all(ObjectType.CLAIM))
        tick = int(getattr(core, "tick", 0) or getattr(core, "_tick", 0) or 0)
        conflict_counts = _open_conflict_counts(core)
        texts = [str(getattr(c, "text", "")) for c in claims]
        embs = embed_texts(texts, allow_model=allow_model)
        points: list[SolutionPoint] = []
        for c, emb in zip(claims, embs, strict=False):
            status = str(_enum_val(getattr(c, "status", None), "candidate"))
            sv = state_vector_from_object(c, conflict_count=conflict_counts.get(c.id, 0),
                                          current_tick=tick)
            points.append(SolutionPoint(
                id=c.id, state_vector=sv, embedding=emb,
                label=str(getattr(c, "text", ""))[:60], anchored=status in _ANCHORED_STATUS))
        return points
    except Exception:  # noqa: BLE001 -> read-only source must never crash a caller
        return []
