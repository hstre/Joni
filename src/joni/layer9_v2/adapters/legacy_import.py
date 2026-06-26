"""Phase 2 — read-only import of the legacy Layer-9 snapshot into the v2 store.

Reads ``state/layer9.snapshot.json`` (the old custom-serialised state: ``__c__`` class / ``f``
fields / ``__e__`` enum / ``__t__`` tuple / ``__d__`` dict) and writes v2 ``objects``. It is
strictly one-directional and additive: the legacy file is never modified, and nothing here calls
back into the live Layer-9.

Two deliberate choices:
  * **Space mapping is explicit** (``SPACE_MAP``). Anything not in the map lands in Content Space
    with status ``needs_review`` and type ``unknown_legacy`` — flagged, never silently dropped or
    guessed into the wrong space. The legacy data has no Question Space objects, so Question Space
    is intentionally left sparse rather than fabricated.
  * **One summary journal event, not 22k.** Bulk import inserts objects directly and records a
    single ``legacy_import`` event with counts + a content digest. Per-object journalling would
    bloat the chain with history the legacy system never had; the import is one auditable act.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from ..journal import events
from ..storage.sqlite import canonical_json, content_hash, new_id, now_iso

# object_type → space. Unlisted types → Content Space, status needs_review, type unknown_legacy.
SPACE_MAP: dict[str, str] = {
    # Method Space — HOW.
    "method": "method",
    "method_trial_event": "method",
    "select_mode": "method",
    # Content Space — WHAT.
    "claim": "content",
    "evidence": "content",
    "evidence_link": "content",
    "source": "content",
    "conflict": "content",
    "decision": "content",
    "proposal": "content",
    "semantic_cluster": "content",
    "self_model_claim": "content",
    "narrative_summary": "content",
    "preference": "content",
    # Question Space — WHY. (None present in legacy data, but mapped for forward compatibility.)
    "research_question": "question",
    "open_problem": "question",
    "next_test": "question",
}


def decode(node):
    """Flatten the legacy custom serialisation into plain JSON-able Python.

    ``{__e__,v}`` → v (enum value); ``{__c__,f}`` → decode(f) (class → fields);
    ``{__t__:[...]}`` → list; ``{__d__:{...}}`` → dict; recurse through dicts/lists.
    """
    if isinstance(node, dict):
        if "__e__" in node and "v" in node:
            return node["v"]
        if "__c__" in node and "f" in node:
            return decode(node["f"])
        if "__t__" in node:
            return [decode(x) for x in node["__t__"]]
        if "__d__" in node:
            return {k: decode(v) for k, v in node["__d__"].items()}
        return {k: decode(v) for k, v in node.items()}
    if isinstance(node, list):
        return [decode(x) for x in node]
    return node


@dataclass
class ImportReport:
    total: int = 0
    imported: int = 0
    skipped: int = 0
    by_space: dict = field(default_factory=dict)
    by_type: dict = field(default_factory=dict)
    needs_review: int = 0
    unknown_types: dict = field(default_factory=dict)
    links: int = 0
    by_relation: dict = field(default_factory=dict)
    dangling_link_targets: int = 0
    unmapped_relations: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total": self.total, "imported": self.imported, "skipped": self.skipped,
            "by_space": self.by_space, "by_type": self.by_type, "needs_review": self.needs_review,
            "links": self.links, "by_relation": self.by_relation,
            "dangling_link_targets": self.dangling_link_targets,
            "unmapped_relations": self.unmapped_relations, "errors": self.errors[:50],
        }


def _bump(d: dict, key) -> None:
    d[key] = d.get(key, 0) + 1


def _evidence_relation(rel: str | None) -> str | None:
    """Map a legacy ``evidence_link.relation`` onto the closed v2 vocabulary, or None if it doesn't
    cleanly map (e.g. 'contextualizes'). We never fabricate support/contradiction semantics — an
    unmapped relation is counted and left as the imported ``evidence_link`` object + its provenance
    edges, not invented into a typed edge."""
    r = (rel or "").lower()
    if any(x in r for x in ("contradict", "refut", "conflict", "against", "tension", "disagree")):
        return "contradicts"
    if any(x in r for x in ("support", "confirm", "corrobor", "strengthen", "evidence_for")):
        return "supports"
    return None


def import_snapshot(conn: sqlite3.Connection, snapshot_path: str | Path,
                    *, actor: str = "legacy_import") -> ImportReport:
    """Import every object from a legacy snapshot into v2 ``objects``. Read-only on the source.

    The whole import runs in ONE transaction: it commits as a unit and rolls back wholesale on any
    failure, leaving the v2 store untouched. Returns an :class:`ImportReport`.
    """
    raw = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    state = raw.get("state_snapshot", raw)
    objects = state.get("objects", {})
    rep = ImportReport(total=len(objects))
    ts = now_iso()
    digest = hashlib.sha256()
    decoded: dict[str, dict] = {}  # id -> decoded fields, reused for the link pass

    with conn:  # atomic: all-or-nothing (objects AND links commit/roll back together)
        for legacy_id, wrapper in objects.items():
            try:
                fields = decode(wrapper)
                otype = fields.get("object_type") or "unknown"
                title = (fields.get("topic") or fields.get("text") or "")[:200] or None
                space = SPACE_MAP.get(otype)
                status = str(fields.get("status") or "active")
                store_type = otype
                if space is None:
                    space, store_type, status = "content", "unknown_legacy", "needs_review"
                    _bump(rep.unknown_types, otype)
                    rep.needs_review += 1
                payload = {"legacy_id": legacy_id, "legacy_type": otype, "fields": fields}
                chash = content_hash(space, store_type, title, payload)
                conn.execute(
                    "INSERT INTO objects (id, space, type, title, payload_json, status, "
                    "created_at, updated_at, version, content_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?) "
                    "ON CONFLICT(id) DO NOTHING",
                    (str(legacy_id), space, store_type, title,
                     json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                     status, ts, ts, chash),
                )
                rep.imported += 1
                decoded[str(legacy_id)] = fields
                _bump(rep.by_space, space)
                _bump(rep.by_type, store_type)
                digest.update(chash.encode("utf-8"))
            except Exception as exc:  # noqa: BLE001 — record & continue; the txn still commits the rest
                rep.skipped += 1
                rep.errors.append({"id": str(legacy_id), "error": repr(exc)})

        _reconstruct_links(conn, decoded, rep, ts)

        events.append_event(
            conn, "legacy_import", actor=actor, object_id=None,
            payload={"source": str(snapshot_path), "total": rep.total, "imported": rep.imported,
                     "skipped": rep.skipped, "needs_review": rep.needs_review,
                     "links": rep.links, "by_space": rep.by_space, "by_relation": rep.by_relation,
                     "digest": digest.hexdigest()},
        )
    return rep


def _reconstruct_links(conn: sqlite3.Connection, decoded: dict[str, dict],
                       rep: ImportReport, ts: str) -> None:
    """Rebuild the typed graph from the legacy reference fields, bulk-inserted (no per-link journal
    event — they fold into the single import event). Edges are only created when BOTH endpoints were
    imported; references to missing objects are counted as ``dangling_link_targets``, never forced.

    Legacy field  →  v2 relation
      derived_from[]            → derives_from   (the explicit provenance the old store recorded)
      decision.proposal_id      → derives_from   (a decision derives from its proposal)
      evidence_link.relation    → supports / contradicts  (mapped; unmapped relations counted)
      conflict.claim_ids[]      → contradicts    (pairwise, so conflicts surface as contested)
    """
    present = set(decoded)

    def edge(src: str, rel: str, dst: str, prov: dict) -> None:
        if src not in present or dst not in present or src == dst:
            if dst not in present or src not in present:
                rep.dangling_link_targets += 1
            return
        cur = conn.execute(
            "INSERT INTO links (id, from_object_id, to_object_id, relation_type, status, weight, "
            "provenance_json, created_at) VALUES (?, ?, ?, ?, 'active', ?, ?, ?) "
            "ON CONFLICT(from_object_id, to_object_id, relation_type) DO NOTHING",
            (new_id("lnk"), src, dst, rel, float(prov.get("strength", 1.0)),
             json.dumps(prov, ensure_ascii=False, separators=(",", ":")), ts),
        )
        if cur.rowcount:
            rep.links += 1
            _bump(rep.by_relation, rel)

    for oid, f in decoded.items():
        otype = f.get("object_type")
        for ref in f.get("derived_from") or []:
            edge(oid, "derives_from", str(ref), {"via": "derived_from"})

        if otype == "decision" and f.get("proposal_id"):
            edge(oid, "derives_from", str(f["proposal_id"]), {"via": "decision.proposal_id"})

        elif otype == "evidence_link":
            rel = _evidence_relation(f.get("relation"))
            ev, claim = f.get("evidence_id"), f.get("claim_id")
            if ev and claim:
                if rel is None:
                    _bump(rep.unmapped_relations, str(f.get("relation") or "?"))
                else:
                    edge(str(ev), rel, str(claim),
                         {"via": "evidence_link", "legacy_relation": f.get("relation"),
                          "strength": f.get("strength", 1.0)})

        elif otype == "conflict":
            claim_ids = [str(c) for c in (f.get("claim_ids") or [])]
            for a, b in zip(claim_ids, claim_ids[1:], strict=False):  # pairwise: c0↔c1, c1↔c2, …
                edge(a, "contradicts", b, {"via": "conflict", "conflict_id": oid,
                                           "conflict_kind": f.get("conflict_kind")})


def import_report_text(rep: ImportReport) -> str:
    """A short human-readable summary for the import doc / CLI output."""
    lines = [f"Legacy import: {rep.imported}/{rep.total} objects imported "
             f"({rep.skipped} skipped, {rep.needs_review} need review).",
             f"  by space: {canonical_json(rep.by_space)}",
             f"  links rebuilt: {rep.links}  by relation: {canonical_json(rep.by_relation)}"]
    if rep.dangling_link_targets:
        lines.append(f"  dangling link refs skipped: {rep.dangling_link_targets}")
    if rep.unmapped_relations:
        lines.append(f"  unmapped evidence relations: {canonical_json(rep.unmapped_relations)}")
    if rep.unknown_types:
        lines.append(f"  unknown legacy types: {canonical_json(rep.unknown_types)}")
    if rep.errors:
        lines.append(f"  first error: {rep.errors[0]}")
    return "\n".join(lines)
