# Design / core-ask: move Joni's state persistence to SQLite

> **Status:** proposal — this is a **protected-core** change (`persistence.py`, `state.py`,
> `models.py`, `operators.py` are in `joni_core.lock`). Under Joni's rule it is **human-gated**,
> never self-applied. This doc is the worked-out ask; a human approves and re-`lock`s the core.

## 1. The problem this fixes (for good)

Joni's state is an **append-only JSON journal** (`state/layer9.json`) that is **fully replayed on
load**, and every emitted event recomputes a `snapshot_hash` over **all** objects. That is two
compounding failures:

- **Bloat.** The journal grows monotonically (the dead `measurement.pairs` log was the worst driver),
  hitting GitHub's 100 MB/file limit and producing multi-MB files.
- **O(n²) cold load.** A fresh job replays the whole journal; with ~22 k objects × ~15 k events the
  per-event `snapshot_hash` over all objects makes the cold load hang past a cycle's budget — which is
  exactly the recurring incident where the loop stops committing. The git-ignored fast-load *sidecar*
  papers over it inside a job, but a stale/absent cache drops back to the cold replay.

Journal **compaction** (`python -m joni.autonomy compact`) is the **band-aid** — it strips dead blobs
and re-seals so the replay fits a cycle again. It does not remove the design that re-creates the
problem. SQLite removes it at the root.

## 2. What must stay invariant (non-negotiable)

A persistence change may not touch the epistemics. The migration is only correct if it preserves:

1. **Replay-stability** — the design invariant verified across 38 phases. The events are still the
   source of truth and still replayable for audit; the same inputs produce the same `snapshot_hash`.
2. **The hash-chained ledger** — tamper-evidence: each event keeps `before/after_hash`,
   `prev_event_hash`, `event_hash`, chained. Verifiable end to end.
3. **The immutable-core / human-gate boundary** — peripheral modules evolve; the core does not
   self-modify; core changes are asks.
4. **The epistemic semantics** — gate-on-admit, conflicts stay OPEN, nothing auto-confirms.
5. **Determinism** — byte-identical reconstruction; no `Date.now()`/`Math.random()` in the path.

## 3. The O(n²) is not inherent to a journal

Worth stating plainly: the quadratic cost is **the per-emit full `snapshot_hash` over all objects**,
not "replaying a journal". Replay is O(events) *if* the snapshot hash is maintained **incrementally**
(a running hash updated as objects change) instead of recomputed over everything per event. So there
are two separable wins:

- **Incremental snapshot hashing** → replay becomes linear. (A core change to `core`/`hashing`.)
- **SQLite storage + materialised state** → no full-file rewrite, no replay-on-load, indexed queries.

The migration should do both; incremental hashing alone already de-fangs the incident.

## 4. The design

**`events` table — the journal (source of truth).** One row per `LedgerEvent`: `seq, tick, operator,
actor, decision, input_refs, output_refs, before_hash, after_hash, prev_event_hash, event_hash,
payload(JSON), timestamp`. Append = `INSERT`. The chain is unchanged; `verify_chain` becomes an
ordered scan.

**`objects` table — the materialised current state.** `id, object_type, status, authority, topic,
payload(JSON)`, indexed on `(object_type)`, `(topic)`, `(status)`. Maintained as events apply. **Load
= `SELECT`**, no replay. `claims_on(topic)` etc. become indexed queries (also kills the per-cycle
full-scan in the retire/site passes).

**`meta` table** — `tick`, the current `snapshot_hash` (maintained incrementally), schema version.

**Replay / audit** stays available: re-apply the `events` table in order to reconstruct `objects`, and
assert the rebuilt `snapshot_hash` equals `meta.snapshot_hash`. Used by the equivalence test, not the
hot load path.

### The git question (the real wrinkle)

The loop commits state to `main`, so the on-disk form must be git-friendly. A binary `.db` in git is
bad (no diff, merge hazards). Recommendation:

- **Git source of truth: `state/events.jsonl`** — the hash-chained journal, one event per line.
  Appends are clean one-line diffs; no file rewrite, no bloat spike, no 100 MB cliff.
- **Runtime store: SQLite**, built/maintained from `events.jsonl`. The `.db` is **git-ignored** and
  **cached across jobs** (like today's sidecar) — but rebuilding it from `events.jsonl` on a cache
  miss is now **O(events) linear** (incremental hashing), so a cache miss costs seconds–minutes, never
  the O(n²) hang.
- Optionally also commit a small **materialised `state/objects.snapshot`** for an instant cold load
  without touching SQLite at all.

This keeps the audit trail diffable in git, the runtime fast, and removes every failure mode above.

## 5. Migration path (flag-gated, equivalence-proven)

1. **`JONI_PERSISTENCE=json|sqlite`**, default `json` — zero behaviour change until proven.
2. **Converter + equivalence test:** read the current `layer9.json` → build the SQLite store; assert
   the SQLite-loaded state has the **identical object set and `snapshot_hash`** as the JSON-loaded
   state. This is the replay-stability proof; it gates everything.
3. **Dual-run in CI** behind the flag for N cycles: each cycle loads/writes both paths and asserts the
   hashes match. Any divergence hard-stops.
4. **Flip the default to `sqlite`** only after the equivalence holds across many cycles; re-`lock` the
   core (a human action).

## 6. Risks

- **Chain fidelity:** the `event_hash` inputs must be byte-identical to today, or the chain breaks.
  Mitigation: the converter re-derives hashes and the equivalence test fails on any mismatch.
- **Schema drift:** versioned `meta.schema_version` + a forward-only migration.
- **Scope creep into semantics:** none allowed — gate/conflict/scoring logic is untouched; only how
  bytes are stored and how state is loaded changes.

## 7. Why this is a core-ask, not a peripheral build

It edits `persistence.py` / `state.py` / `models.py` / `operators.py` (all locked) and re-freezes the
lock. Per Joni's constitution that is the human's call. The peripheral side (the `compact` command,
this doc, the converter/equivalence harness) can be built freely; the *flip* is the gated step.
