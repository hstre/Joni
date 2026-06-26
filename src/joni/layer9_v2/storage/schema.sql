-- REFERENCE COPY of the full materialised schema (current head = migration 0001).
-- The migration runner (storage/sqlite.py) applies migrations/NNNN_*.sql, NOT this file.
-- This copy exists for humans/tools that want the whole schema at a glance; keep it in sync
-- with the latest migration.

-- Layer 9 v2 — initial schema (migration 0001).
-- Three separated epistemic spaces (method / content / question) joined ONLY by typed links and
-- by user/project overlays. The objects/links tables are the MATERIALISED operational state; the
-- journal_events table is the append-only, hash-chained audit log. Startup reads the materialised
-- state directly — it does NOT replay the journal.
--
-- schema_version is bootstrapped by the migration runner (storage/sqlite.py), not here.

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- objects: one row per epistemic object, partitioned by `space`.
CREATE TABLE objects (
    id            TEXT    PRIMARY KEY,
    space         TEXT    NOT NULL CHECK (space IN ('method', 'content', 'question')),
    type          TEXT    NOT NULL,
    title         TEXT,
    payload_json  TEXT    NOT NULL DEFAULT '{}',
    status        TEXT    NOT NULL DEFAULT 'active',
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    content_hash  TEXT    NOT NULL
);
CREATE INDEX ix_objects_space        ON objects (space);
CREATE INDEX ix_objects_type         ON objects (type);
CREATE INDEX ix_objects_status       ON objects (status);
CREATE INDEX ix_objects_space_status ON objects (space, status);
CREATE INDEX ix_objects_space_type   ON objects (space, type, status);
CREATE INDEX ix_objects_hash         ON objects (content_hash);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- links: typed, directional pointers — the ONLY way the three spaces connect.
CREATE TABLE links (
    id              TEXT    PRIMARY KEY,
    from_object_id  TEXT    NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    to_object_id    TEXT    NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    relation_type   TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active',
    weight          REAL    NOT NULL DEFAULT 1.0,
    provenance_json TEXT    NOT NULL DEFAULT '{}',
    created_at      TEXT    NOT NULL,
    valid_from      TEXT,
    valid_until     TEXT
);
CREATE INDEX ix_links_from          ON links (from_object_id);
CREATE INDEX ix_links_to            ON links (to_object_id);
CREATE INDEX ix_links_relation      ON links (relation_type);
CREATE INDEX ix_links_from_relation ON links (from_object_id, relation_type, status);
CREATE INDEX ix_links_to_relation   ON links (to_object_id, relation_type, status);
CREATE UNIQUE INDEX ux_links_edge   ON links (from_object_id, to_object_id, relation_type);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- user_overlays: per-user (and optionally per-project) relevance — NEVER baked into the global object.
CREATE TABLE user_overlays (
    id              TEXT    PRIMARY KEY,
    user_id         TEXT    NOT NULL,
    project_id      TEXT,
    object_id       TEXT    NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    visibility      TEXT    NOT NULL DEFAULT 'visible',
    personal_status TEXT,
    personal_weight REAL,
    trust_level     TEXT,
    last_used       TEXT,
    notes_json      TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_user_overlays_user    ON user_overlays (user_id);
CREATE INDEX ix_user_overlays_project ON user_overlays (project_id);
CREATE INDEX ix_user_overlays_object  ON user_overlays (object_id);
CREATE UNIQUE INDEX ux_user_overlays  ON user_overlays (user_id, project_id, object_id);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- project_overlays: per-project relevance / active subgraph membership.
CREATE TABLE project_overlays (
    id             TEXT    PRIMARY KEY,
    project_id     TEXT    NOT NULL,
    object_id      TEXT    NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    project_status TEXT,
    project_weight REAL,
    active         INTEGER NOT NULL DEFAULT 1,
    notes_json     TEXT    NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_project_overlays_project ON project_overlays (project_id);
CREATE INDEX ix_project_overlays_object  ON project_overlays (object_id);
CREATE INDEX ix_project_overlays_active  ON project_overlays (project_id, active);
CREATE UNIQUE INDEX ux_project_overlays  ON project_overlays (project_id, object_id);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- status_history: every status transition of an object, with reason + actor.
CREATE TABLE status_history (
    id          TEXT PRIMARY KEY,
    object_id   TEXT NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    reason      TEXT,
    evidence_ref TEXT,
    actor       TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX ix_status_history_object ON status_history (object_id);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- journal_events: APPEND-ONLY, hash-chained audit log. Not FK'd to objects on purpose — the audit
-- trail must survive even if an object is later removed, and must never be rewritten.
CREATE TABLE journal_events (
    id          TEXT    PRIMARY KEY,
    tick        INTEGER NOT NULL,
    event_type  TEXT    NOT NULL,
    actor       TEXT,
    object_id   TEXT,
    payload_json TEXT   NOT NULL DEFAULT '{}',
    prev_hash   TEXT    NOT NULL,
    event_hash  TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL
);
CREATE INDEX ix_journal_tick   ON journal_events (tick);
CREATE INDEX ix_journal_object ON journal_events (object_id);
CREATE INDEX ix_journal_type   ON journal_events (event_type);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- snapshots: periodic checkpoints of the materialised state (a payload hash + tick), so a reader
-- can confirm the live tables match a known-good point without replaying the journal.
CREATE TABLE snapshots (
    id             TEXT    PRIMARY KEY,
    tick           INTEGER NOT NULL,
    snapshot_type  TEXT    NOT NULL,
    payload_hash   TEXT    NOT NULL,
    created_at     TEXT    NOT NULL,
    schema_version INTEGER NOT NULL
);
CREATE INDEX ix_snapshots_tick ON snapshots (tick);

-- ─────────────────────────────────────────────────────────────────────────────────────────────
-- embeddings (optional): a vector per object+model, stored as JSON for portability.
CREATE TABLE embeddings (
    id         TEXT    PRIMARY KEY,
    object_id  TEXT    NOT NULL REFERENCES objects (id) ON DELETE CASCADE,
    model      TEXT    NOT NULL,
    vector_json TEXT,
    dimension  INTEGER,
    created_at TEXT    NOT NULL
);
CREATE INDEX ix_embeddings_object ON embeddings (object_id);
CREATE UNIQUE INDEX ux_embeddings_object_model ON embeddings (object_id, model);
