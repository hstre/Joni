"""A local sentence-embedding projector - the missing *general* semantic measure.

DESi/Alexandria have the √JSD math but no domain-agnostic projector for Joni's claims. This
supplies one *inside* the existing DESi binding (not a parallel semantic system): a small,
pinned local model turns each claim into a vector, and the **cosine distance** between two
claims is a genuine meaning-level distance. It is explicitly cosine - never reported as
Π/√JSD. It is only an additional measurement channel; frames/logic/tension stay.

Pinned identity (model name, revision, dim, normalisation, metric) is returned with every
measurement, so a result is reproducible and a model change is visible. Embeddings are
cached by ``sha256(claim) + revision`` so a model change invalidates the cache. Local and
offline (``fastembed`` preferred, ``sentence-transformers`` fallback); a failed/absent model
makes the channel fail closed - it never substitutes a lexical distance dressed as semantics.
"""

from __future__ import annotations

import hashlib
import math

# Pinned models (small, deterministic - no sampling). Revisions are our provenance label.
_FASTEMBED_MODEL = "BAAI/bge-small-en-v1.5"
_FASTEMBED_REV = "bge-small-en-v1.5"
_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_ST_REV = "all-MiniLM-L6-v2"
METRIC = "cosine"

_EMBED = None            # callable(text)->list[float], or None (untried), or False (absent)
_NAME = "none"
_REVISION = "0"
_DIM = 0
_NORMALIZED = False
_CACHE: dict[str, list[float]] = {}


def _load():
    global _EMBED, _NAME, _REVISION, _DIM, _NORMALIZED
    if _EMBED is not None:
        return _EMBED or None
    try:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=_FASTEMBED_MODEL)

        def fn(text: str) -> list[float]:
            return [float(x) for x in next(iter(model.embed([text])))]

        _EMBED, _NAME, _REVISION = fn, _FASTEMBED_MODEL, _FASTEMBED_REV
        _NORMALIZED = True            # bge-small is L2-normalised
        _DIM = len(fn("probe"))
        return _EMBED
    except Exception:  # noqa: BLE001
        pass
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(_ST_MODEL)

        def fn(text: str) -> list[float]:
            return [float(x) for x in model.encode(text, normalize_embeddings=True)]

        _EMBED, _NAME, _REVISION, _NORMALIZED = fn, _ST_MODEL, _ST_REV, True
        _DIM = len(fn("probe"))
        return _EMBED
    except Exception:  # noqa: BLE001
        _EMBED = False                # tried and unavailable (e.g. failed download)
        return None


def available() -> bool:
    return _load() is not None


def info() -> dict:
    _load()
    return {"model": _NAME, "revision": _REVISION, "dim": _DIM,
            "normalized": _NORMALIZED, "metric": METRIC}


def _key(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest() + "@" + _REVISION


def embed(text: str) -> list[float] | None:
    fn = _load()
    if fn is None:
        return None
    key = _key(text)
    if key not in _CACHE:
        try:
            _CACHE[key] = fn(text.strip())
        except Exception:  # noqa: BLE001 - a broken model must fail closed, not crash
            return None
    return _CACHE[key]


def cosine_distance(a_text: str, b_text: str) -> float | None:
    """Cosine distance in [0,1] between two claims, or None if no model is available."""
    va, vb = embed(a_text), embed(b_text)
    if va is None or vb is None or len(va) != len(vb):
        return None
    dot = sum(x * y for x, y in zip(va, vb, strict=False))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return None
    sim = dot / (na * nb)
    return round(min(1.0, max(0.0, 1.0 - sim)), 6)


def cache_size() -> int:
    return len(_CACHE)


def _reset_for_tests(embed_fn=None, *, name="test-embed", revision="t", dim=3,
                     normalized=False) -> None:
    """Inject a deterministic embedder in tests (or reset to 'unavailable')."""
    global _EMBED, _NAME, _REVISION, _DIM, _NORMALIZED, _CACHE
    _EMBED = embed_fn if embed_fn is not None else None
    _NAME, _REVISION, _DIM, _NORMALIZED, _CACHE = name, revision, dim, normalized, {}
