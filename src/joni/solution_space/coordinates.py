"""Data plumbing for the cartographer: turn real records into ``SolutionPoint``s.

The cartographer (Baustein A) needs each point's two coordinates: the 9-dim governance vector (DESi
``StateVector.to_tuple()``) and a semantic embedding of the point's text. This supplies the second
and normalises the first:

  * ``embed_texts`` uses ``fastembed`` (the ``embed`` extra) for real semantics when available, and
    otherwise falls back to a DETERMINISTIC lexical hash — clearly labelled, because lexical overlap
    is NOT semantics; install the extra for the real thing. Either way the cartography runs offline
    and deterministically, and swaps to real embeddings the moment fastembed is present.
  * ``state_vector_of`` accepts a DESi ``StateVector`` (``.to_tuple()``), a raw 9-tuple, or a dict,
    and returns a plain float tuple.
  * ``build_points`` assembles ``SolutionPoint``s from records (id / text / state_vector /
    anchored).

No model call in the hot path unless fastembed is installed AND its model loads; any failure
(including an offline model-download failure) degrades to the lexical fallback rather than raising.
"""

from __future__ import annotations

import hashlib
import re

from .cartography import SolutionPoint

_TOKEN = re.compile(r"\w+")


def embeddings_backend() -> str:
    """Which embedding backend ``embed_texts`` will use: 'fastembed' (real semantics) or
    'lexical-hash-fallback' (deterministic, NOT semantic)."""
    try:
        import fastembed  # noqa: F401
        return "fastembed"
    except Exception:  # noqa: BLE001
        return "lexical-hash-fallback"


def _lexical_embed(text: str, dim: int) -> tuple[float, ...]:
    vec = [0.0] * dim
    for tok in _TOKEN.findall((text or "").lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim   # noqa: S324 (not security)
        vec[h] += 1.0
    return tuple(vec)


def embed_texts(texts, *, dim: int = 64, allow_model: bool = True) -> list[tuple[float, ...]]:
    """Embed each text. Uses fastembed if it is installed, ``allow_model`` is set, AND its model
    loads; otherwise a deterministic lexical hash of dimension ``dim``. Never raises on a backend
    failure. Pass ``allow_model=False`` to force the deterministic fallback (tests / offline)."""
    texts = list(texts)
    if allow_model and embeddings_backend() == "fastembed":
        try:
            from fastembed import TextEmbedding
            model = TextEmbedding()
            return [tuple(float(x) for x in v) for v in model.embed(texts)]
        except Exception:  # noqa: BLE001 -> offline / model-download failure: fall back, don't crash
            pass
    return [_lexical_embed(t, dim) for t in texts]


def state_vector_of(x) -> tuple[float, ...]:
    """Normalise a governance coordinate to a plain float tuple. Accepts a DESi ``StateVector``
    (has ``.to_tuple()``), a raw sequence, or a dict of the 9 named axes (DESi order)."""
    if hasattr(x, "to_tuple"):
        return tuple(float(v) for v in x.to_tuple())
    if isinstance(x, dict):
        order = ("frame_id", "contradiction_load", "anchor_density", "source_quality", "novelty",
                 "confidence", "branch_cost", "support_state", "routing_state")
        return tuple(float(x.get(k, 0.0)) for k in order)
    return tuple(float(v) for v in x)


def build_points(records, *, dim: int = 64, allow_model: bool = True) -> list[SolutionPoint]:
    """Assemble ``SolutionPoint``s from ``records``. Each record is a dict (or object) carrying
    ``id``, ``text``, ``state_vector`` (StateVector / tuple / dict), and optional ``label`` /
    ``anchored``. Embeddings are computed in one batch so a real backend loads its model once."""
    recs = list(records)

    def g(r, k, default=None):
        return r.get(k, default) if isinstance(r, dict) else getattr(r, k, default)

    texts = [str(g(r, "text", "")) for r in recs]
    embs = embed_texts(texts, dim=dim, allow_model=allow_model)
    points: list[SolutionPoint] = []
    for r, emb in zip(recs, embs, strict=False):
        points.append(SolutionPoint(
            id=str(g(r, "id", "")),
            state_vector=state_vector_of(g(r, "state_vector", ())),
            embedding=emb,
            label=str(g(r, "label", "") or ""),
            anchored=bool(g(r, "anchored", False))))
    return points
