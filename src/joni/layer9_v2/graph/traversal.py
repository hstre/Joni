"""Read-only graph traversal over the typed links.

Bounded breadth-first walks plus a few named slices the adapters need (evidence supporting a claim,
content answering a question, methods that produced a claim). Everything here is a SELECT — no
mutation, no journal. Traversals are depth-bounded and cycle-safe so a malformed graph can't hang a
reader.
"""
from __future__ import annotations

import sqlite3

from ..spaces import _base
from . import links


def neighbours(conn: sqlite3.Connection, object_id: str, *, relation_type: str | None = None,
               direction: str = "out") -> list[dict]:
    """The objects one hop away along (optionally) a given relation. direction = out|in|both."""
    edges: list[dict] = []
    if direction in ("out", "both"):
        edges += [e["to_object_id"]
                  for e in links.out_links(conn, object_id, relation_type=relation_type)]
    if direction in ("in", "both"):
        edges += [e["from_object_id"]
                  for e in links.in_links(conn, object_id, relation_type=relation_type)]
    out = []
    for oid in edges:
        obj = _base.get_object(conn, oid)
        if obj is not None:
            out.append(obj)
    return out


def walk(conn: sqlite3.Connection, start_id: str, *, relation_type: str | None = None,
         direction: str = "out", max_depth: int = 3) -> list[dict]:
    """Bounded, cycle-safe BFS from ``start_id``. Returns reached objects (excluding the start),
    each annotated with the depth at which it was first reached."""
    seen = {start_id}
    frontier = [start_id]
    reached: list[dict] = []
    for depth in range(1, max_depth + 1):
        nxt: list[str] = []
        for node in frontier:
            for obj in neighbours(conn, node, relation_type=relation_type, direction=direction):
                if obj["id"] in seen:
                    continue
                seen.add(obj["id"])
                reached.append({**obj, "_depth": depth})
                nxt.append(obj["id"])
        if not nxt:
            break
        frontier = nxt
    return reached


def supporting_evidence(conn: sqlite3.Connection, claim_id: str) -> list[dict]:
    """Content objects that ``supports`` the given claim (incoming support edges)."""
    return [_base.get_object(conn, e["from_object_id"])
            for e in links.in_links(conn, claim_id, relation_type="supports")]


def contradicting(conn: sqlite3.Connection, claim_id: str) -> list[dict]:
    """Content objects that ``contradicts`` the given claim (incoming contradiction edges)."""
    return [_base.get_object(conn, e["from_object_id"])
            for e in links.in_links(conn, claim_id, relation_type="contradicts")]


def answers_for(conn: sqlite3.Connection, question_id: str) -> list[dict]:
    """Content that ``answers`` a question (incoming answer edges)."""
    return [_base.get_object(conn, e["from_object_id"])
            for e in links.in_links(conn, question_id, relation_type="answers")]


def methods_for(conn: sqlite3.Connection, object_id: str) -> list[dict]:
    """Methods that ``generated_by``/``uses_method`` produced or drove this object (outgoing)."""
    out: list[dict] = []
    for rel in ("generated_by", "uses_method"):
        out += [_base.get_object(conn, e["to_object_id"])
                for e in links.out_links(conn, object_id, relation_type=rel)]
    return [o for o in out if o is not None]
