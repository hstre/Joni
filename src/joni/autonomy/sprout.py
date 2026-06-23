"""SproutRAG-style multi-granular candidate extraction (Auftrag #160, after SproutRAG 2606.18381).

SproutRAG builds a hierarchical tree over sentence chunks and beam-searches it across granularity
levels, so a LONG source yields cross-sentence, semantically coherent candidate passages instead of
a flat sentence list - lifting retrieval recall without any external LLM call. Joni's runtime cannot
LEARN which attention heads carry semantics (no training infrastructure), so - exactly as facets.py
landed the part of FaBle that fits - this lands the faithful, fitting part: the tree is built with
the existing pinned EMBEDDING projector (cosine similarity stands in for the learned attention
guidance), and a coherence-ranked, de-nested selection keeps the most internally-coherent spans
across levels (the hierarchical beam).

The output is a small set of passages at MIXED granularity - the most coherent multi-sentence spans
plus the single most central sentence - de-overlapped and deterministic, ready for the normal
projection arm exactly where ``facets.decompose`` plugs in.

Non-core (only the candidate-extraction front of semantics-measurement; the gate, ledger and
operators are untouched). Opt-in (``JONI_SPROUTRAG=1``), embeddings-only (no model budget),
benefit-reviewed (``sprout_log``). Unavailable embeddings or a short source -> ``[]`` (the caller
then projects the source exactly as before).

Acceptance note (+3pp Recall@5 on long scientific documents): that needs a labelled long-document
retrieval benchmark, which Joni does not have; this lands the mechanism + a recall-proxy test.
"""

from __future__ import annotations

import math
import os
import re

from . import embeddings

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MIN_SENTENCES = 4          # below this a source is not "long" - nothing to tree, project as-is
_MAX_CANDIDATES = 5         # top-k passages returned (mirrors the paper's @5)


def enabled() -> bool:
    from . import extension_review
    return (os.getenv("JONI_SPROUTRAG", "0") == "1" and embeddings.available()
            and extension_review.active("sproutrag"))


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split((text or "").strip()) if s.strip()]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tree_spans(vecs: list[list[float]]) -> list[tuple[int, int, float]]:
    """Agglomeratively merge the most similar ADJACENT pair (contiguous merges keep every span a
    coherent run of sentences), recording each internal node as ``(start, end, coherence)``.
    Coherence is the cosine similarity of the two children's centroids at the moment they merged -
    SproutRAG's progressive-embedding signal. Deterministic: ``>`` keeps the leftmost pair on ties.
    """
    # each frontier node carries [start, end, summed_vector, leaf_count] so a centroid is sum/count
    frontier: list[list] = [[i, i, list(v), 1] for i, v in enumerate(vecs)]
    spans: list[tuple[int, int, float]] = []
    while len(frontier) > 1:
        best_sim, best_j = None, 0
        for j in range(len(frontier) - 1):
            a, b = frontier[j], frontier[j + 1]
            ca = [x / a[3] for x in a[2]]
            cb = [x / b[3] for x in b[2]]
            sim = _cos(ca, cb)
            if best_sim is None or sim > best_sim:
                best_sim, best_j = sim, j
        a, b = frontier[best_j], frontier[best_j + 1]
        start, end = a[0], b[1]
        merged = [start, end, [x + y for x, y in zip(a[2], b[2], strict=False)], a[3] + b[3]]
        spans.append((start, end, float(best_sim)))
        frontier = frontier[:best_j] + [merged] + frontier[best_j + 2:]
    return spans


def _most_central(sents: list[str], vecs: list[list[float]]) -> str | None:
    """The single sentence closest to the document centroid - the leaf-granularity pick."""
    n = len(vecs)
    centroid = [sum(v[d] for v in vecs) / n for d in range(len(vecs[0]))]
    best_i, best_sim = None, None
    for i, v in enumerate(vecs):
        sim = _cos(v, centroid)
        if best_sim is None or sim > best_sim:
            best_i, best_sim = i, sim
    return sents[best_i] if best_i is not None else None


def extract(text: str, *, max_candidates: int = _MAX_CANDIDATES) -> list[str]:
    """Return up to ``max_candidates`` mixed-granularity coherent passages from a long source, or
    ``[]`` when disabled / embeddings unavailable / the source is too short to tree."""
    if not enabled():
        return []
    sents = _sentences(text)
    if len(sents) < _MIN_SENTENCES:
        return []
    vecs = [embeddings.embed(s) for s in sents]
    if any(v is None for v in vecs):
        return []
    # most coherent multi-sentence spans first, then keep only NON-overlapping ones so the result
    # spans the document at varying granularities rather than re-emitting one region many times.
    multi = sorted((s for s in _tree_spans(vecs) if s[1] - s[0] + 1 >= 2),
                   key=lambda s: (-s[2], s[0]))
    kept: list[tuple[int, int]] = []
    out: list[str] = []
    for start, end, _coh in multi:
        if any(not (end < ks or start > ke) for ks, ke in kept):   # overlaps a kept span -> skip
            continue
        kept.append((start, end))
        out.append(" ".join(sents[start:end + 1]))
        if len(out) >= max_candidates - 1:      # leave room for the single-sentence granularity
            break
    central = _most_central(sents, vecs)         # granularity diversity: one leaf representative
    if central is not None and central not in out:
        out.append(central)
    return out[:max_candidates]
