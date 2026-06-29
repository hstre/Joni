"""Scan the v2 graph for the three plausible-wrong-slice signals around a slice of claims.

Given a slice (the claim ids a router would answer from) and the v2 store, this runs the
slice-INDEPENDENT graph scan and returns exactly the inputs DESi's ``report_from_snapshot`` takes:

  * ``graph_opposition_ids`` / ``_texts`` — claims that CONTRADICT / SUPERSEDE / INVALIDATE a slice
    claim (either edge direction) and are NOT themselves in the slice, plus open questions linked to
    a slice claim. The omission of these is the missing-opposition signal.
  * ``provenance_sources`` / ``derived_flags`` — one source-family key per slice claim (mirrors the
    loop's ``_source_family``) and whether the claim is derived — the provenance-entropy inputs.
  * ``claim_scopes`` — the scope tag per slice claim — the scope-match input.

It is read-only and DESi-free: it returns plain data; the routing decision stays in DESi. Empty/zero
signals mean the graph genuinely holds nothing — the checks then degrade to "clean", never invent.
"""
from __future__ import annotations

import json
import sqlite3

from ..graph import links

_OPPOSITION_RELS = ("contradicts", "supersedes", "invalidates")


def _fields(conn: sqlite3.Connection, oid: str) -> dict:
    row = conn.execute("SELECT payload_json FROM objects WHERE id = ?", (oid,)).fetchone()
    if not row:
        return {}
    p = json.loads(row[0]) or {}
    # converter objects nest the legacy fields under "fields"; objects written directly carry them
    # at the top level — accept either so the scan works on real and synthetic stores alike.
    return p.get("fields", p)


def source_family(provenance: dict | None) -> str:
    """A stable key for a claim's independent origin — mirrors the loop's ``_source_family`` on the
    v2 payload dict. First explicit source id wins; else origin type + the producing run/call."""
    prov = provenance or {}
    sids = tuple(prov.get("source_ids") or ())
    if sids:
        return f"src:{sids[0]}"
    origin = prov.get("origin_type") or "unknown"
    return f"origin:{origin}:{prov.get('run_id') or prov.get('call_id') or ''}"


def _opposition_for(conn: sqlite3.Connection, claim_id: str) -> list[tuple[str, str]]:
    """(opposition_id, relation) for a claim: neighbours across an opposition relation, either way.
    A ``contradicts`` edge is symmetric in meaning, so both endpoints count as opposition."""
    out: dict[str, str] = {}
    for rel in _OPPOSITION_RELS:
        for e in links.out_links(conn, claim_id, relation_type=rel):
            out.setdefault(e["to_object_id"], rel)
        for e in links.in_links(conn, claim_id, relation_type=rel):
            out.setdefault(e["from_object_id"], rel)
    # open questions this claim is linked to (answers / belongs_to_question), if any
    for rel in ("answers", "belongs_to_question"):
        for e in links.out_links(conn, claim_id, relation_type=rel):
            out.setdefault(e["to_object_id"], "open_question")
    return list(out.items())


def scan_slice(conn: sqlite3.Connection, slice_ids: list[str] | tuple[str, ...]) -> dict:
    """Produce the report scan inputs for a slice. ``slice_ids`` are the claims the answer would
    use (e.g. the active claims of a topic). Returns kwargs for ``report_from_snapshot``."""
    slice_set = {s for s in slice_ids if s}
    opp_ids: dict[str, str] = {}            # opposition id -> short text
    for cid in slice_set:
        for oid, rel in _opposition_for(conn, cid):
            if oid in slice_set:
                continue                    # surfaced in the slice already, not omitted
            if oid not in opp_ids:
                f = _fields(conn, oid)
                txt = (f.get("text") or f.get("topic") or oid)
                opp_ids[oid] = f"{rel}: {str(txt)[:120]}"

    sources: list[str] = []
    derived: list[bool] = []
    scopes: list[str] = []
    for cid in slice_ids:
        f = _fields(conn, cid)
        sources.append(source_family(f.get("provenance")))
        derived.append(bool(f.get("derived_from")))
        sc = f.get("scope") or []
        scopes.append(str(sc[0]) if sc else "")

    return {
        "graph_opposition_ids": tuple(opp_ids),
        "graph_opposition_texts": tuple(opp_ids.values()),
        "provenance_sources": tuple(sources),
        "derived_flags": tuple(derived),
        "claim_scopes": tuple(scopes),
    }
