"""Priority 5: condense pairwise conflicts into a few thematic Streitfragen (disputes).

Hundreds of pairwise contradictions are not hundreds of questions. Most are facets of a handful of
real disputes. This READ-ONLY pass groups the live conflicts (open + under_review) into their
connected components in the contradiction graph - a tangle of mutually-conflicting claims is ONE
Streitfrage - and for each reports exactly what the operator asked for:

  * **positions** - the distinct claim texts on the sides of the tangle;
  * **shared premises** - the content words the positions have in common (the common ground);
  * **decisive missing evidence** - which positions rest on no independent external source, i.e.
    what a decision is actually waiting on.

It writes only its own artefacts (``docs/streitfragen.md`` + a compact per-cycle count row in
``state/disputes_series.jsonl``) and exposes the disputes in ``extensions['disputes']`` so the
provisional layer can stage the *few* condensed questions instead of the hundreds of pairs. It
never resolves a conflict, never writes Layer 9, and consults no model - the operator decides.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass

import desi_layer9 as l9

from . import quality

_LIVE = frozenset({"open", "under_review"})
MAX_DISPUTES = 12                 # surface the biggest tangles; the rest are summarised as a count
MAX_POSITIONS = 5                 # positions shown per Streitfrage (representative, not exhaustive)
MAX_COMPONENT_CLAIMS = 6          # a coarse tangle larger than this is sub-split by content overlap
MIN_EDGE_OVERLAP = 2              # a conflict is a STRONG (same-subject) edge iff its claims share
                                  # this many content words; weaker 'bridge' edges are cut on split


@dataclass(frozen=True)
class Streitfrage:
    dispute_id: str
    topic: str
    claim_ids: tuple
    positions: tuple                 # representative claim texts (the sides)
    shared_premises: tuple           # content words common to >= 2 positions
    missing_evidence: str            # the decisive gap, deterministically derived
    conflict_ids: tuple
    size: int                        # number of pairwise conflicts this subsumes

    def to_record(self) -> dict:
        return {"dispute_id": self.dispute_id, "topic": self.topic,
                "claim_ids": list(self.claim_ids), "positions": list(self.positions),
                "shared_premises": list(self.shared_premises),
                "missing_evidence": self.missing_evidence,
                "conflict_ids": list(self.conflict_ids), "size": self.size}


def _live_conflicts(cs) -> list:
    out = []
    for cf in cs.core.all(l9.ObjectType.CONFLICT):
        status = getattr(getattr(cf, "conflict_status", None), "value", "") or ""
        if status in _LIVE:
            out.append(cf)
    return out


def _claim_ids(cf) -> list:
    return [str(x) for x in (getattr(cf, "claim_ids", None) or [])]


def _grouping(claim_ids, edges: list):
    """Union-find over ``claim_ids`` with the given (a, b) edges; returns (find, root -> claims)."""
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for cid in claim_ids:
        find(cid)
    for a, b in edges:
        parent[find(a)] = find(b)
    groups: dict = defaultdict(set)
    for cid in claim_ids:
        groups[find(cid)].add(cid)
    return find, groups


def _coarse_components(conflicts: list) -> list:
    """Group by ALL conflict edges (transitive closure). Each: (claim_ids, [conflict objects])."""
    all_claims: set = set()
    edges: list = []
    for cf in conflicts:
        ids = _claim_ids(cf)
        all_claims.update(ids)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                edges.append((ids[i], ids[j]))
    find, groups = _grouping(all_claims, edges)
    by_root: dict = defaultdict(list)
    for cf in conflicts:
        ids = _claim_ids(cf)
        if ids:
            by_root[find(ids[0])].append(cf)
    return [(frozenset(groups[root]), by_root.get(root, [])) for root in groups]


def _subsplit(claim_ids: frozenset, conflicts: list, terms: dict) -> list:
    """Sub-split an over-merged tangle: keep only STRONG conflict edges (claims sharing >=
    MIN_EDGE_OVERLAP content words) - a polysemous bridge claim that weakly links two unrelated
    subjects no longer fuses them. Returns the sub-groups that still hold a strong conflict."""
    strong: list = []
    for cf in conflicts:
        ids = [c for c in _claim_ids(cf) if c in claim_ids]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if len(terms.get(ids[i], set()) & terms.get(ids[j], set())) >= MIN_EDGE_OVERLAP:
                    strong.append((ids[i], ids[j]))
    find, groups = _grouping(claim_ids, strong)
    by_root: dict = defaultdict(list)
    for cf in conflicts:
        ids = [c for c in _claim_ids(cf) if c in claim_ids]
        if len(ids) >= 2 and len({find(c) for c in ids}) == 1:   # both ends in one sub-group
            by_root[find(ids[0])].append(cf)
    return [(frozenset(groups[root]), confs) for root, confs in by_root.items() if confs]


def _family_map(cs) -> dict:
    """claim_id -> set of independent supporting source ids (a cheap 'families' proxy). One pass
    over the evidence links; avoids the per-claim deep-copy cost of single-object reads."""
    ev_source = {e.id: getattr(e, "source_id", None) for e in cs.core.all(l9.ObjectType.EVIDENCE)}
    fam: dict = defaultdict(set)
    for el in cs.core.all(l9.ObjectType.EVIDENCE_LINK):
        cid = getattr(el, "claim_id", None)
        rel = getattr(getattr(el, "relation", None), "value", getattr(el, "relation", ""))
        if not cid or str(rel) not in ("supports", ""):
            continue
        src = ev_source.get(getattr(el, "evidence_id", None))
        if src:
            fam[str(cid)].add(str(src))
    return fam


def _dispute_id(claim_ids: frozenset) -> str:
    blob = json.dumps(sorted(claim_ids), ensure_ascii=False)
    return "dispute-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _shared_premises(texts: list) -> tuple:
    counts: Counter = Counter()
    for t in texts:
        counts.update(set(quality.content_terms(t)))
    return tuple(sorted(w for w, n in counts.items() if n >= 2))[:8]


def _build_streitfrage(cs, claim_ids: frozenset, conflicts: list, fam: dict):
    """Assemble one Streitfrage from a (sub-)group of claims and its conflicts. None if empty."""
    claims = [c for c in (cs.core.get(cid) for cid in sorted(claim_ids)) if c is not None]
    conflict_ids = tuple(str(getattr(cf, "id", "")) for cf in conflicts if getattr(cf, "id", ""))
    if not claims or not conflict_ids:
        return None
    texts = [str(getattr(c, "text", "")) for c in claims]
    topics = Counter(getattr(c, "topic", "") for c in claims if getattr(c, "topic", ""))
    no_ext = [c.id for c in claims if len(fam.get(str(c.id), ())) == 0]
    if no_ext:
        missing = (f"{len(no_ext)}/{len(claims)} Positionen ruhen auf keiner unabhängigen "
                   "externen Quelle - das ist die entscheidende Lücke")
    else:
        missing = "beide Seiten extern gestützt - ein direkter Vergleich entscheidet"
    return Streitfrage(
        dispute_id=_dispute_id(claim_ids),
        topic=(topics.most_common(1)[0][0] if topics else ""),
        claim_ids=tuple(sorted(str(c.id) for c in claims)),
        positions=tuple(dict.fromkeys(t for t in texts if t))[:MAX_POSITIONS],
        shared_premises=_shared_premises(texts), missing_evidence=missing,
        conflict_ids=conflict_ids, size=len(conflict_ids))


def condense(cs, *, max_disputes: int = MAX_DISPUTES) -> list:
    """Group the live conflicts into thematic Streitfragen, biggest tangle first. A coarse tangle
    with more than ``MAX_COMPONENT_CLAIMS`` claims is sub-split by content coherence, so an
    over-merged giant graph component becomes real single questions instead of one grab-bag.
    Read-only."""
    conflicts = _live_conflicts(cs)
    if not conflicts:
        return []
    fam = _family_map(cs)
    all_ids: set = set()
    for cf in conflicts:
        all_ids.update(_claim_ids(cf))
    terms = {cid: set(quality.content_terms(str(getattr(cs.core.get(cid), "text", "") or "")))
             for cid in all_ids}
    units: list = []                                   # (claim_ids, [conflict objects])
    for claim_ids, comp_conflicts in _coarse_components(conflicts):
        if len(claim_ids) <= MAX_COMPONENT_CLAIMS:
            units.append((claim_ids, comp_conflicts))
        else:
            units.extend(_subsplit(claim_ids, comp_conflicts, terms))
    disputes = [d for d in (_build_streitfrage(cs, cids, confs, fam) for cids, confs in units) if d]
    disputes.sort(key=lambda d: (-d.size, -len(d.claim_ids)))
    return disputes[:max_disputes]


def render_sheet(disputes: list, *, total_conflicts: int) -> str:
    lines = [
        "# Joni — Streitfragen (verdichtete Konflikte)",
        "",
        f"**{total_conflicts} paarweise Konflikte → {len(disputes)} Streitfragen**  ",
        "",
        "_Read-only Verdichtung. Nur diese Streitfragen sollten weiter zirkulieren; Joni löst "
        "nichts selbst - entschieden wird über die bestehende Konflikt-Mappe (`to_resolve.md`)._",
        "",
    ]
    if not disputes:
        lines.append("_keine offenen Konflikte_")
    for i, d in enumerate(disputes, 1):
        lines.append(f"## {i}. Streitfrage — Thema „{d.topic or '—'}“ "
                     f"({d.size} Paar-Konflikte, {len(d.claim_ids)} Positionen)")
        lines.append(f"- **Gemeinsame Prämissen:** {', '.join(d.shared_premises) or '—'}")
        lines.append(f"- **Entscheidender fehlender Beleg:** {d.missing_evidence}")
        lines.append("- **Positionen:**")
        for p in d.positions:
            lines.append(f"    - {p[:160]}")
        lines.append("")
    return "\n".join(lines) + "\n"


def run_disputes(cs, extensions: dict, proto, cycle: int = 0, *, paths=None) -> dict:
    """Condense + persist. Writes docs/streitfragen.md and a compact count row; exposes the disputes
    in extensions for the provisional layer. Read-only wrt Layer 9; never raises."""
    try:
        total = len(_live_conflicts(cs))
        disputes = condense(cs)
        extensions["disputes"] = [d.to_record() for d in disputes]
        if paths is not None:
            sheet = getattr(paths, "disputes_sheet", None)
            series = getattr(paths, "disputes_series", None)
            if sheet is not None:
                sheet.parent.mkdir(parents=True, exist_ok=True)
                sheet.write_text(render_sheet(disputes, total_conflicts=total), encoding="utf-8")
            if series is not None:
                series.parent.mkdir(parents=True, exist_ok=True)
                row = {"cycle": cycle, "conflicts": total, "disputes": len(disputes),
                       "largest": disputes[0].size if disputes else 0}
                with series.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        proto.record(cycle, "streitfragen",
                     f"{total} Paar-Konflikte → {len(disputes)} Streitfragen "
                     f"(größte {disputes[0].size if disputes else 0})")
        return {"conflicts": total, "disputes": len(disputes)}
    except Exception as exc:  # noqa: BLE001 - a read-only condensation must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "streitfragen", f"[disputes error, skipped] {type(exc).__name__}")
        return {"conflicts": 0, "disputes": 0}


__all__ = ["Streitfrage", "condense", "render_sheet", "run_disputes", "MAX_DISPUTES"]
