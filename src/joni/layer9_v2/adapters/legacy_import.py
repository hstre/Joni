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
from ..storage.sqlite import canonical_json, content_hash, now_iso

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
    errors: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "total": self.total, "imported": self.imported, "skipped": self.skipped,
            "by_space": self.by_space, "by_type": self.by_type, "needs_review": self.needs_review,
            "unknown_types": self.unknown_types, "errors": self.errors[:50],
        }


def _bump(d: dict, key) -> None:
    d[key] = d.get(key, 0) + 1


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

    with conn:  # atomic: all-or-nothing
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
                _bump(rep.by_space, space)
                _bump(rep.by_type, store_type)
                digest.update(chash.encode("utf-8"))
            except Exception as exc:  # noqa: BLE001 — record & continue; the txn still commits the rest
                rep.skipped += 1
                rep.errors.append({"id": str(legacy_id), "error": repr(exc)})

        events.append_event(
            conn, "legacy_import", actor=actor, object_id=None,
            payload={"source": str(snapshot_path), "total": rep.total, "imported": rep.imported,
                     "skipped": rep.skipped, "needs_review": rep.needs_review,
                     "by_space": rep.by_space, "digest": digest.hexdigest()},
        )
    return rep


def import_report_text(rep: ImportReport) -> str:
    """A short human-readable summary for the import doc / CLI output."""
    lines = [f"Legacy import: {rep.imported}/{rep.total} objects imported "
             f"({rep.skipped} skipped, {rep.needs_review} need review).",
             f"  by space: {canonical_json(rep.by_space)}"]
    if rep.unknown_types:
        lines.append(f"  unknown legacy types: {canonical_json(rep.unknown_types)}")
    if rep.errors:
        lines.append(f"  first error: {rep.errors[0]}")
    return "\n".join(lines)
