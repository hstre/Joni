# Layer 9 v2 — SQLite-backed epistemic storage

> Status: **additive, read-only through Phase 5.** Built next to the live Layer-9, not replacing it.
> The legacy JSON store stays the source of truth until v2 is deliberately promoted. Nothing in this
> layer writes back into the live system.

This document explains *why* Layer 9 is being re-grounded on SQLite, *why not* MongoDB or Neo4j,
how the three epistemic spaces stay separated, how overlays keep per-user opinion out of the global
graph, the journal-vs-materialised-state split, the migration plan, and what is intentionally left
as legacy.

---

## 1. Why the JSON store failed

The legacy Layer-9 persisted its entire state as one JSON document (`state/layer9.json` /
`state/layer9.snapshot.json`, ~22 000 objects, ~45 MB) plus an append-only ledger. Two structural
problems followed from "one big JSON blob + replayable ledger":

1. **O(n²) journal replay.** State was rebuilt by replaying the ledger, and each emitted event
   hashed a snapshot over *all* objects. As the graph grew, every event did O(n) work over the whole
   state, so a run did O(n²) total — the loop stalled for hours and eventually wedged. (The
   `faulthandler` stack confirmed the hang was inside the replay/hash path.)
2. **No indexes, no partial reads.** Any question ("all active claims", "links into claim C-12")
   meant loading and walking the whole document. There is no way to ask SQLite-style indexed
   questions of a JSON blob, so every read paid the full-load cost.

A JSON document is a *serialisation format*, not a *database*. We were using it as both.

## 2. Why SQLite (and why not Mongo / Neo4j)

**SQLite** — the authoritative local store:

- **No replay on startup.** The materialised tables *are* the current state; opening the DB is a
  `SELECT`, not a replay. This directly kills the O(n²) incident.
- **Indexed, partial reads.** `objects(space, type, status)`, `links(from, relation, status)` etc.
  are indexed, so the common queries are logarithmic, not full-scan.
- **Transactional integrity.** `WAL` + `PRAGMA foreign_keys=ON` give atomic multi-row writes and
  referential integrity for free. A failed write rolls back wholesale (tested).
- **Zero-ops, in-stdlib, file-based.** No server, no daemon, ships with Python, one file to back up,
  trivially reproducible in CI. For a single-writer local agent this is exactly the right weight.
- **Deterministic migrations + schema versioning.** Plain `NNNN_*.sql` files applied once in order.

**Not MongoDB.** Mongo is a networked document server — it reintroduces "documents" (the thing that
just failed us) and adds an operational dependency (a running server, connection management, a
deploy story) for no benefit at single-writer local scale. We do not need horizontal sharding; we
need indexes and transactions, which SQLite has.

**Not Neo4j as primary.** The data *is* a graph, and Neo4j is tempting — but making it the source of
truth means a running database server, a second query language, and a heavyweight dependency for a
local agent. We keep the graph **relational** (an indexed `links` table with a closed relation
vocabulary), which is enough for the bounded traversals we actually run. Neo4j remains a *possible
future projection* (export the `links` table into a graph DB for visualisation / heavy graph
queries), never the authority.

## 3. The three epistemic spaces — separated, not soup

The core design rule: **do not mix methods, contents, and questions into one semantic graph.** Each
object lives in exactly one space (`objects.space`, `CHECK IN ('method','content','question')`):

| Space | Question it answers | Examples |
|---|---|---|
| **Method** | *How* is work done? | DESi operators, router policies, verifier/extraction methods, correction-packet templates, scoring rules |
| **Content** | *What* is worked on? | claims, evidence, sources, conflicts, decisions, proposals, semantic clusters, narrative summaries, invalidated/superseded claims |
| **Question** | *Why* — what are we trying to find out? | research questions, subquestions, open problems, hypothesis spaces, next-test questions |

They are one physical table partitioned by `space`, with thin typed wrappers
(`spaces/methods.py`, `contents.py`, `questions.py`) that pin the space and refuse cross-space
access (`methods.get_method` returns `None` for a content object). This keeps storage uniform (one
link table, one overlay model, one journal) while the API still refuses to confuse a method with a
claim.

**Spaces connect ONLY through typed links** (`graph/links.py`) and through overlays. There is no
implicit join, no "topically similar so probably related" edge. The relation vocabulary is closed:

```
supports · contradicts · derives_from · supersedes · invalidates · answers · tests ·
uses_method · requires_method · generated_by · belongs_to_question · blocks · motivates · cites_source
```

A claim `answers` a question; evidence `supports`/`contradicts` a claim; a claim is `generated_by`
a method. Each relation is queried differently, so the graph stays interpretable.

## 4. Overlays — per-user / per-project relevance off the global object

Relevance, trust, and visibility are **not** properties of a claim — they are properties of *a
user's or a project's relationship to* a claim. Baking them into the global object forces a fork
every time two users disagree.

- `user_overlays` — per `(user_id, project_id, object_id)`: visibility, personal status, personal
  weight, trust level, last-used, free-form notes.
- `project_overlays` — per `(project_id, object_id)`: project status/weight and an `active` flag
  that defines the project's working subgraph.

Alice can trust a claim and Bob can hide the same claim without either mutating it (tested). The
router adapter uses a project overlay to *narrow what the router sees* without touching any global
object. The global object answers "what is this?"; the overlay answers "what does *this* user/project
think of it?".

## 5. Journal vs materialised state

Two representations, one source of truth for each concern:

- **`objects` / `links` / overlays** — the **materialised operational state**. Fast, indexed, read
  directly. This is what every reader and adapter queries.
- **`journal_events`** — the **append-only, hash-chained audit log**. Every mutation appends exactly
  one event *inside the same transaction* as the state change, so they commit or roll back together
  (tested). Each event carries `prev_hash` and an `event_hash = sha256(prev_hash + canonical(core))`;
  altering any past event breaks every later hash (tested). The journal is *never* replayed to derive
  state — it exists to be *verified* (`journal/hashchain.verify_chain`).
- **`snapshots`** — periodic integrity checkpoints: a hash over the current `objects`+`links` at a
  tick, so a reader can confirm the live tables still match a known-good point (`storage/snapshots`),
  cheaply and without walking the journal.

Hashes are **content/semantic**, not time-based: `content_hash` covers `space/type/title/payload`
only — identical content yields an identical hash regardless of timestamps, so duplicates and
equivalence are detectable, and re-importing is stable.

## 6. Migration plan (6 phases) and current status

| Phase | What | Status |
|---|---|---|
| 1 | Schema + storage foundation (migrations, pragmas, hashing) + tests | ✅ done |
| 2 | Legacy read-only import with import report; ambiguous → `needs_review`/`unknown_legacy` | ✅ done |
| 3 | Read-model APIs (spaces getters/listers, link traversal) + tests | ✅ done |
| 4 | DESi adapter (read-only slice) | ✅ done |
| 5 | Router adapter (read-only slice, project-overlay aware) | ✅ done |
| 6 | Controlled write path: every mutation → state + journal event + status_history, atomic, rollback-tested | ✅ implemented; not yet wired as Joni's source of truth |

**Import status.** `adapters/legacy_import.import_snapshot` decodes the legacy custom serialisation
(`__c__`/`f`/`__e__`/`__t__`/`__d__`) and maps each object to a space via an explicit `SPACE_MAP`.
The full real snapshot (21 987 objects) imports cleanly: every object lands in a valid space, the
import runs in one transaction, and it records **one** `legacy_import` summary event (not 22k events)
with counts + a content digest. Unknown legacy types are never guessed into the wrong space — they
land in Content with `type=unknown_legacy`, `status=needs_review`. Legacy data has no Question-Space
objects, so Question Space is intentionally left sparse rather than fabricated.

### Converter CLI and link reconstruction

`python -m joni.layer9_v2.convert` (also installed as `joni-layer9-convert`) is the runnable
front door: it reads the materialised snapshot — **not** the live journal, so no replay — opens/
creates `state/layer9_v2.sqlite`, migrates, imports, and prints the report. `--reset` rebuilds from
scratch; `--verify` re-checks an existing db's hash chain. Re-running is idempotent (objects and
links upsert), and the generated `.sqlite` is a git-ignored cache, never the source of truth.

The importer does not just load nodes — it **rebuilds the typed graph** from the legacy reference
fields, in the same transaction, bulk-inserted (folded into the one import event):

| Legacy field | v2 relation |
|---|---|
| `derived_from[]` | `derives_from` (the explicit provenance the old store recorded) |
| `decision.proposal_id` | `derives_from` |
| `evidence_link.relation` | `supports` / `contradicts` (mapped; unmappable relations like *contextualizes* are **counted, never invented**) |
| `conflict.claim_ids[]` | `contradicts` (pairwise, so conflicts surface as contested claims) |

Edges are created only when **both endpoints were imported**; references to missing objects are
counted as `dangling_link_targets`, never forced (which would also violate the FK). On the real
snapshot this rebuilds **26 031 links** (25 214 `derives_from`, 739 `supports`, 78 `contradicts`),
with 288 `contextualizes` relations honestly left unmapped.

One thing the real data surfaced: legacy conflict resolution marks the involved claims
**`contested`**, not `active`. The DESi/router read slices therefore treat a claim as *live* when its
status is `active` **or** `contested` — otherwise 78 real conflicts would sit invisible and the
router would report `idle`. After the fix the router surfaces 48 contested claims and hints
`resolve_conflict`.

## 7. Limits and what stays legacy

- **The three-space store is read-only w.r.t. the running system.** Promotion of *that* model to the
  runtime is a deliberate, separate step (see §8). A bounded SQLite *persistence backend* for the
  loop's existing model is available behind a flag (see §9).
- **No production UI, no Neo4j, no new router, no DESi rewrite.** Out of scope by design.
- **Embeddings table is present but unused** — a forward hook, not a feature yet.
- **Question Space is sparse** until questions are authored or derived; the legacy data didn't model
  them.
- The legacy `state/layer9.json` and its ledger remain the authority and are untouched by this layer.

## 8. Before v2 becomes the source of truth

The write path (Phase 6) exists and is rollback-tested, but is **not** wired into Joni. Before
flipping the authority:

1. **Equivalence check** — run legacy and v2 in shadow over the same inputs and assert the derived
   state matches (object counts per space/status, link sets, conflict sets).
2. **Wire one writer behind a flag** (e.g. `JONI_PERSISTENCE=sqlite`) so the cutover is reversible.
3. **Round-trip the real snapshot** and confirm `needs_review`/`unknown_legacy` items are triaged
   (every legacy type either mapped or consciously accepted as content-needs-review).
4. **Snapshot + chain verification in CI** — `verify_chain` green and a fresh snapshot matching live
   state on every build.
5. **Backfill Question Space** intentionally if the router is to consume open questions in anger.

Until those are done, treat the three-space store as a verified parallel projection, not the authority.

## 9. Runtime backend: SQLite as the loop's source of truth (opt-in)

There are **two distinct "layer9" stores**, and it matters which one the loop runs on:

- The **three-space store** (everything above) — a re-grounded projection for analytics, fed by the
  converter. Making *it* the literal runtime model would mean rewriting the `desi_layer9` kernel
  (operators, replay, hashing) — a large refactor of a vendored engine. That is deliberately **not**
  done.
- The **autonomy loop** actually runs on `desi_layer9.Layer9`, whose state is derived by **replaying
  the journal** (`state = replay(journal)`). On the real state that replay re-emits **13 651**
  journal entries, each re-computing a snapshot hash — minutes-to-hours of work, the cold-start
  *hang* that parked the loop.

`src/joni/layer9_v2/runtime/desi_store.py` is the bounded fix for **that** store: a SQLite
persistence backend for the **existing** `desi_layer9` model. It reuses the kernel's own
`snapshot.capture`/`restore` and `snapshot_hash`/`verify_chain` verbatim — **no kernel change** — and
only swaps the storage medium. `load` is a SELECT of the materialised objects + `restore`, **not a
replay**:

| Operation | JSON journal (current) | SQLite backend |
|---|---|---|
| **load** (real 21 987-object state) | replay 13 651 entries → **>200 s (the hang)** | **~4.5 s** |
| save | small journal doc | ~6.6 s (materialise 22 k rows) |
| equivalence | — | **identical `snapshot_hash`, chain verified** |

It is wired at the **unlocked** seam `autonomy/core_state.py` (not a `joni_core.lock` file) and is
**off by default**:

```bash
JONI_PERSISTENCE=sqlite   # load/save via state/layer9.sqlite; default 'json' is unchanged
```

The first run with the flag on **adopts the existing `state/layer9.json`** (no reseed, nothing
lost); thereafter it reads/writes the SQLite store. The committed JSON journal stays the portable,
verifiable source of truth; the SQLite file is a git-ignored runtime store. Reversible by unsetting
the flag.

What this does **not** do: the per-emit O(n²) snapshot hashing *inside a running cycle* is a kernel
concern (`desi_layer9.hashing` / the submit path) and is out of scope here — this backend fixes the
load/replay hang and the multi-MB JSON rewrite, not the kernel's in-cycle hashing.

### 9a. Cold-start checkpoint — the first load without a replay

The SQLite backend fixes **warm** loads (restore from the store). But the *first* adoption goes
JSON→SQLite via `persistence.load`, which **replays the journal** unless the fast-load sidecar
matches — and on a fresh CI runner it never does, so the cold start re-hits the >100-min replay that
parked the loop. Root cause, confirmed in the kernel: `hashing.chain_event` sets
`after_hash = snapshot_hash(state)` on **every** ledger emit, and `snapshot_hash` hashes all ~22k
objects — so a full replay (≈15k emits) is **O(n²)**. (`verify_chain` is O(n) and does not recompute
`after_hash`, so verifying a checkpoint is cheap; only *producing* the state by replay is expensive.)

The fix is a **committed, compact materialised checkpoint** — the journal stays the source of truth,
the checkpoint is a *verified cache*:

- `desi_store.write_checkpoint(state, path)` — the kernel's snapshot (dead `measurement.pairs` blobs
  stripped to stay git-friendly) + the `snapshot_hash` it seals to.
- `desi_store.load_via_checkpoint(json, checkpoint)` — restore **without replay**, accepted **only**
  if its hash matches the committed journal's recorded `snapshot_hash` **and** `verify_chain` passes;
  otherwise `None` → the caller replays. A stale/absent checkpoint is never trusted, only ever skips
  work.
- `core_state` cold-start order: SQLite store → checkpoint → (last resort) full replay. `save()`
  re-seals the checkpoint **every cycle** and writes the journal, so a fresh CI job restores the
  committed `state/layer9.checkpoint.json` (≈0.8 s) instead of cold-replaying.
- `python -m joni.autonomy checkpoint` — the one-time bootstrap / manual re-seal.

The one-time bootstrap pays a single full replay (done once, locally, and committed); **CI then never
replays**. This is what makes unparking the loop safe — the separate, operator-gated next step. It is
still **not** the root fix: the per-emit O(n²) inside a running cycle remains the kernel's Phase A.
