"""User and project overlays — relevance/trust/visibility that must NOT be baked into the object.

The global object answers "what is this and is it globally active?". An overlay answers "what does
THIS user / THIS project think of it?" — personal status, personal weight, trust level, visibility,
last-used. Two users can disagree about the same claim without forking it; a project can hide or
re-weight a global claim without mutating it. Overlays are upserted by (user, project, object) or
(project, object); writes are journalled like any other mutation.
"""
from __future__ import annotations

import json
import sqlite3

from ..journal import events
from ..storage.sqlite import new_id, now_iso


def set_user_overlay(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    object_id: str,
    project_id: str | None = None,
    visibility: str = "visible",
    personal_status: str | None = None,
    personal_weight: float | None = None,
    trust_level: str | None = None,
    notes: dict | None = None,
    actor: str | None = None,
) -> dict:
    """Upsert this user's overlay for an object. Journalled. Returns the stored overlay row."""
    oid = new_id("uov")
    ts = now_iso()
    conn.execute(
        "INSERT INTO user_overlays (id, user_id, project_id, object_id, visibility, "
        "personal_status, personal_weight, trust_level, last_used, notes_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, project_id, object_id) DO UPDATE SET "
        "visibility=excluded.visibility, personal_status=excluded.personal_status, "
        "personal_weight=excluded.personal_weight, trust_level=excluded.trust_level, "
        "last_used=excluded.last_used, notes_json=excluded.notes_json",
        (oid, user_id, project_id, object_id, visibility, personal_status, personal_weight,
         trust_level, ts, json.dumps(notes or {}, ensure_ascii=False)),
    )
    events.append_event(
        conn, "user_overlay_set", actor=actor or user_id, object_id=object_id,
        payload={"user_id": user_id, "project_id": project_id, "visibility": visibility})
    return get_user_overlay(conn, user_id=user_id, object_id=object_id,
                            project_id=project_id)  # type: ignore[return-value]


def get_user_overlay(conn: sqlite3.Connection, *, user_id: str, object_id: str,
                     project_id: str | None = None) -> dict | None:
    row = conn.execute(
        "SELECT * FROM user_overlays WHERE user_id = ? AND object_id = ? "
        "AND ((project_id IS NULL AND ? IS NULL) OR project_id = ?)",
        (user_id, object_id, project_id, project_id),
    ).fetchone()
    return _overlay_row(row)


def set_project_overlay(
    conn: sqlite3.Connection,
    *,
    project_id: str,
    object_id: str,
    project_status: str | None = None,
    project_weight: float | None = None,
    active: bool = True,
    notes: dict | None = None,
    actor: str | None = None,
) -> dict:
    """Upsert a project's overlay for an object. Journalled. Returns the stored overlay row."""
    oid = new_id("pov")
    conn.execute(
        "INSERT INTO project_overlays (id, project_id, object_id, project_status, project_weight, "
        "active, notes_json) VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(project_id, object_id) DO UPDATE SET project_status=excluded.project_status, "
        "project_weight=excluded.project_weight, active=excluded.active, "
        "notes_json=excluded.notes_json",
        (oid, project_id, object_id, project_status, project_weight, 1 if active else 0,
         json.dumps(notes or {}, ensure_ascii=False)),
    )
    events.append_event(conn, "project_overlay_set", actor=actor, object_id=object_id,
                        payload={"project_id": project_id, "active": active})
    return get_project_overlay(conn, project_id=project_id, object_id=object_id)  # type: ignore[return-value]


def get_project_overlay(conn: sqlite3.Connection, *, project_id: str,
                        object_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM project_overlays WHERE project_id = ? AND object_id = ?",
        (project_id, object_id),
    ).fetchone()
    return _overlay_row(row)


def _overlay_row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    d = dict(row)
    d["notes"] = json.loads(d.pop("notes_json") or "{}")
    if "active" in d:
        d["active"] = bool(d["active"])
    return d
