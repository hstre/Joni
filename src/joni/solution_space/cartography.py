"""Baustein A — the product-space cartographer (design-notes/SOLUTION_SPACE_PIPELINE.md).

Places solution points in the PRODUCT of two real spaces — DESi's 9-dim governance StateVector (the
*how*: in what epistemic state the reasoning sits) and a semantic embedding (the *what*: which
topic) — and maps the terrain into:

  * **islands**  — clusters of points (single-linkage over the combined distance);
  * **unanchored islands** — clusters holding NO known/training solution (an anchor); the prime
    'unreached island' the deep-method operators (Baustein B) then target;
  * **bridge candidates** — pairs of islands CLOSE semantically but FAR in governance (or the
    caller's chosen asymmetry): topically related yet epistemically disconnected — the 'Verknüpfung
    zwischen Lösungsräumen'.

Deterministic, stdlib-only (``math``), no model. HONEST scope: it does NOT invent void/empty regions
between sparse points (unreliable in high dimensions) — a gap here is an *unanchored cluster* or a
*bridge*, both grounded in actual points. Coordinates come in from the caller (StateVector.to_tuple
for governance; an embedding model for semantics); this is the geometry, not the data capture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SolutionPoint:
    """One point in the product space. ``state_vector`` is the 9-dim governance vector (DESi
    ``StateVector.to_tuple()``); ``embedding`` is the semantic vector. ``anchored`` = a known
    solution sits here (vs. an open candidate/question)."""

    id: str
    state_vector: tuple[float, ...]
    embedding: tuple[float, ...]
    label: str = ""
    anchored: bool = False


@dataclass(frozen=True)
class Island:
    id: str
    member_ids: tuple[str, ...]
    anchored: bool                     # any member is a known solution
    size: int


@dataclass(frozen=True)
class BridgeCandidate:
    island_a: str
    island_b: str
    semantic_distance: float
    governance_distance: float
    reason: str


@dataclass(frozen=True)
class Cartography:
    islands: tuple[Island, ...]
    unanchored_islands: tuple[str, ...]
    bridges: tuple[BridgeCandidate, ...]
    params: dict = field(default_factory=dict)


def _ranges(points: list[SolutionPoint]) -> list[tuple[float, float]]:
    dims = len(points[0].state_vector) if points else 0
    out = []
    for d in range(dims):
        vals = [p.state_vector[d] for p in points]
        out.append((min(vals), max(vals)))
    return out


def _gov_dist(a: SolutionPoint, b: SolutionPoint, ranges: list[tuple[float, float]]) -> float:
    """Mean per-dimension range-normalised absolute difference over the 9 axes -> [0, 1]."""
    if not ranges:
        return 0.0
    total = 0.0
    for d, (lo, hi) in enumerate(ranges):
        span = hi - lo
        total += 0.0 if span == 0 else abs(a.state_vector[d] - b.state_vector[d]) / span
    return total / len(ranges)


def _sem_dist(a: SolutionPoint, b: SolutionPoint) -> float:
    """Cosine distance mapped to [0, 1]: (1 - cos_sim) / 2."""
    va, vb = a.embedding, b.embedding
    if not va or not vb:
        return 0.0
    dot = sum(x * y for x, y in zip(va, vb, strict=False))
    na = math.sqrt(sum(x * x for x in va))
    nb = math.sqrt(sum(y * y for y in vb))
    if na == 0 or nb == 0:
        return 1.0
    cos = max(-1.0, min(1.0, dot / (na * nb)))
    return (1.0 - cos) / 2.0


def _combined(a, b, ranges, w_gov, w_sem) -> float:
    return w_gov * _gov_dist(a, b, ranges) + w_sem * _sem_dist(a, b)


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)      # deterministic: lower index becomes root


def cartograph(points, *, tau: float = 0.35, w_gov: float = 0.5, w_sem: float = 0.5,
               bridge_sem_max: float = 0.25, bridge_gov_min: float = 0.5) -> Cartography:
    """Cluster ``points`` into islands (single-linkage under combined distance ``tau``), flag the
    unanchored ones, and find bridge candidates (island centroids close in semantics but far in
    governance). Deterministic; empty input -> empty cartography."""
    pts = list(points)
    n = len(pts)
    if n == 0:
        return Cartography(islands=(), unanchored_islands=(), bridges=(),
                           params={"tau": tau, "w_gov": w_gov, "w_sem": w_sem})
    ranges = _ranges(pts)

    uf = _UnionFind(n)
    for i in range(n):
        for j in range(i + 1, n):
            if _combined(pts[i], pts[j], ranges, w_gov, w_sem) <= tau:
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    islands: list[Island] = []
    idx_to_island: dict[int, str] = {}
    for k, (_root, members) in enumerate(sorted(groups.items())):
        iid = f"island_{k}"
        anchored = any(pts[m].anchored for m in members)
        islands.append(Island(id=iid, member_ids=tuple(pts[m].id for m in members),
                              anchored=anchored, size=len(members)))
        for m in members:
            idx_to_island[m] = iid

    unanchored = tuple(i.id for i in islands if not i.anchored)

    # bridge candidates: centroid semantic vs governance distance between island pairs
    members_by_island = {i.id: [pts[k] for k in range(n) if idx_to_island[k] == i.id]
                         for i in islands}
    bridges: list[BridgeCandidate] = []
    ids = [i.id for i in islands]
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            ga, gb = members_by_island[ids[a]], members_by_island[ids[b]]
            sem = _centroid_dist(ga, gb, ranges, kind="sem")
            gov = _centroid_dist(ga, gb, ranges, kind="gov")
            if sem <= bridge_sem_max and gov >= bridge_gov_min:
                bridges.append(BridgeCandidate(
                    island_a=ids[a], island_b=ids[b],
                    semantic_distance=round(sem, 4), governance_distance=round(gov, 4),
                    reason=(f"semantically close (d={sem:.2f} <= {bridge_sem_max}) but "
                            f"governance-far (d={gov:.2f} >= {bridge_gov_min}): related topic, "
                            "disconnected reasoning")))

    return Cartography(islands=tuple(islands), unanchored_islands=unanchored,
                       bridges=tuple(bridges),
                       params={"tau": tau, "w_gov": w_gov, "w_sem": w_sem,
                               "bridge_sem_max": bridge_sem_max, "bridge_gov_min": bridge_gov_min})


def _centroid(members: list[SolutionPoint], attr: str) -> tuple[float, ...]:
    vecs = [getattr(m, attr) for m in members]
    dims = len(vecs[0])
    return tuple(sum(v[d] for v in vecs) / len(vecs) for d in range(dims))


def _centroid_dist(ga, gb, ranges, *, kind: str) -> float:
    ca_s, cb_s = _centroid(ga, "state_vector"), _centroid(gb, "state_vector")
    ca_e, cb_e = _centroid(ga, "embedding"), _centroid(gb, "embedding")
    pa = SolutionPoint(id="ca", state_vector=ca_s, embedding=ca_e)
    pb = SolutionPoint(id="cb", state_vector=cb_s, embedding=cb_e)
    return _gov_dist(pa, pb, ranges) if kind == "gov" else _sem_dist(pa, pb)
