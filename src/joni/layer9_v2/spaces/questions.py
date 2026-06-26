"""Question Space — WHY work is done.

Research questions, subquestions, open problems, hypothesis spaces, next-test questions. Questions
drive the work: content ``answers`` them, methods ``test`` them, and a question may ``motivate`` or
``block`` another. Keeping questions separate from content stops "what we believe" and "what we are
trying to find out" from collapsing into one undifferentiated graph.
"""
from __future__ import annotations

import sqlite3

from . import _base

SPACE = "question"

QUESTION_TYPES = (
    "research_question", "subquestion", "open_problem", "hypothesis_space", "next_test",
)


def put_question(conn: sqlite3.Connection, *, type: str, title: str | None = None,
                 payload: dict | None = None, status: str = "open",
                 object_id: str | None = None, actor: str | None = None) -> dict:
    return _base.put_object(conn, space=SPACE, type=type, title=title, payload=payload,
                            status=status, object_id=object_id, actor=actor)


def get_question(conn: sqlite3.Connection, object_id: str) -> dict | None:
    obj = _base.get_object(conn, object_id)
    return obj if obj and obj["space"] == SPACE else None


def list_questions(conn: sqlite3.Connection, *, type: str | None = None,
                   status: str | None = None, limit: int | None = None) -> list[dict]:
    return _base.list_objects(conn, space=SPACE, type=type, status=status, limit=limit)
