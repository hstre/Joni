"""Method Space — HOW work is done.

DESi operators, router policies, verifier methods, extraction methods, correction-packet
templates, scoring rules. Methods describe procedure; they never carry a per-user opinion (that
lives in overlays) and never carry a claim about the world (that lives in Content Space). A method
connects to content/questions only through typed links (``uses_method``, ``requires_method``,
``generated_by``).
"""
from __future__ import annotations

import sqlite3

from . import _base

SPACE = "method"

# Known method types (advisory — the column is free-text so the catalogue can grow freely).
METHOD_TYPES = (
    "desi_operator", "router_policy", "verifier_method", "extraction_method",
    "correction_template", "scoring_rule", "select_mode",
)


def put_method(conn: sqlite3.Connection, *, type: str, title: str | None = None,
               payload: dict | None = None, status: str = "active",
               object_id: str | None = None, actor: str | None = None) -> dict:
    return _base.put_object(conn, space=SPACE, type=type, title=title, payload=payload,
                            status=status, object_id=object_id, actor=actor)


def get_method(conn: sqlite3.Connection, object_id: str) -> dict | None:
    obj = _base.get_object(conn, object_id)
    return obj if obj and obj["space"] == SPACE else None


def list_methods(conn: sqlite3.Connection, *, type: str | None = None,
                 status: str | None = None, limit: int | None = None) -> list[dict]:
    return _base.list_objects(conn, space=SPACE, type=type, status=status, limit=limit)
