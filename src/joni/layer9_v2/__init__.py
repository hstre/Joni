"""Layer 9 v2 — SQLite-backed epistemic storage (method / content / question spaces).

Built NEXT TO the legacy Layer-9, not replacing it. The legacy JSON store stays the source of truth
until v2 passes its tests and is deliberately promoted; everything here is additive and (through
Phase 5) read-only with respect to the live system. See ``docs/layer9_v2_sqlite.md``.

Quick start::

    from joni.layer9_v2 import open_db
    from joni.layer9_v2.spaces import contents, questions
    from joni.layer9_v2.graph import links

    conn = open_db("state/layer9_v2.sqlite")          # opens + migrates
    with conn:                                          # one transaction
        c = contents.put_content(conn, type="claim", title="…", payload={...})
        q = questions.put_question(conn, type="research_question", title="…")
        links.add_link(conn, c["id"], "answers", q["id"])
"""
from .storage.sqlite import open_db, schema_version

__all__ = ["open_db", "schema_version"]
