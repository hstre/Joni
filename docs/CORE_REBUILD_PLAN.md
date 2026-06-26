# Core-ask: the Joni core rebuild (phases A–D)

> **Status:** proposal — gated. This plans changes to the **protected, vendored core**
> (`desi_layer9` kernel + `joni_core.lock` files). Under Joni's rule it is **human-gated**, never
> self-applied and never done by the autonomous loop. This doc is the worked-out ask; a human
> approves each phase and re-`lock`s the core afterwards.
>
> **Companion docs:** `docs/sqlite_migration.md` (#167, the persistence-specific ask),
> `docs/layer9_v2_sqlite.md` (the staging already built), `docs/TECH_DEBT.md`.

## 0. Why this exists

So far the SQLite work has been deliberately **additive** — built *next to* the running system,
behind flags, never touching the locked/vendored core:

- a three-space store + converter (`joni-layer9-convert`),
- a materialised SQLite **persistence backend** for the loop (`JONI_PERSISTENCE=sqlite`), proven
  equivalent to the JSON path.

That is **staging, not the rebuild.** It de-risks the rebuild (it gives us an equivalence yardstick),
but it does not remove the core debt. This doc names the debt honestly and sequences the actual
rebuild. The additive work is the *measuring stick* every phase below must prove itself against:
**byte-identical `snapshot_hash`, verified chain, same gate decisions.**

## 1. The debt, stated plainly

1. **Per-emit O(n²) hashing (the real in-cycle hang).** Every `core.submit` recomputes
   `snapshot_hash` over **all** objects. With ~22 k objects that is the quadratic cost *inside a
   running cycle*. The persistence backend fixed cold **load** (replay → `restore`, >200 s → ~4.5 s);
   it did **not** touch this. This is the single highest-impact core change.
2. **Replay is the source-of-truth derivation.** `state = replay(journal)` is the kernel's defining
   invariant. While it holds, every materialised store is only a *cache* and the replay debt lurks
   behind a stale/absent sidecar. Truly removing it means the kernel holding materialised state as
   **authoritative**, with the journal demoted to audit/recovery.
3. **Three parallel models of the same knowledge.** `joni.state.Layer9` (cli/api),
   `desi_layer9.Layer9` (the loop's runtime), and the three-space `layer9_v2` store (projection).
   Three representations that must eventually converge to one.
4. **`desi_layer9` is frozen vendored code.** "Ported verbatim — do not refactor casually" +
   `joni_core.lock` protect it, but they also block exactly the changes in (1)–(3). At some point the
   kernel must become an owned, refactorable part instead of a vendored blob.

## 2. Invariants every phase must preserve (non-negotiable)

Identical to #167 §2, restated because they bind the whole rebuild:

1. **Replay-stability / auditability** — the journal stays a complete, replayable audit trail; the
   same inputs reproduce the same `snapshot_hash`.
2. **Hash-chained ledger** — tamper-evidence end to end (`prev_hash`/`event_hash`).
3. **Immutable-core / human-gate boundary** — peripheral modules evolve; the core does not
   self-modify; core changes are gated asks.
4. **Epistemic semantics** — gate-on-admit, conflicts stay OPEN, nothing auto-confirms; "LLM for
   language, rules for logic."
5. **Determinism** — byte-identical reconstruction; no wall-clock/PRNG in the state path.

## 3. The phases

Each phase is independently shippable, flag-guarded where possible, and ends with a re-`lock`. Do
them in order; do **not** drip-feed them into unrelated work.

### Phase A — incremental snapshot hashing (kernel)

- **Goal:** kill the in-cycle O(n²). Maintain the snapshot hash **incrementally** as objects change
  instead of re-hashing all objects per emit.
- **Change:** `desi_layer9/hashing.py` + the `submit`/emit path in `desi_layer9/core.py` — keep a
  running hash (e.g. an order-independent fold over per-object content hashes) updated on each object
  mutation; `snapshot_hash(state)` returns the maintained value.
- **Locked/vendored files:** `desi_layer9/hashing.py`, `desi_layer9/core.py`. (Not in
  `joni_core.lock` today — but core in spirit; treat as gated.)
- **Risk:** medium. The hash definition must stay **bit-compatible** with the current full-recompute,
  or every recorded `snapshot_hash` in history breaks. Mitigation: implement incremental alongside
  the full version and assert equality across the whole real journal before switching.
- **Equivalence proof:** for every entry of the real 13 651-entry journal, incremental hash ==
  full-recompute hash. Cycle wall-time drops from quadratic to linear.

### Phase B — materialised state becomes authoritative; replay → audit only

- **Goal:** remove replay-on-load as the source of truth. The kernel loads materialised state
  (SQLite-native) and uses replay only for verification/recovery.
- **Change:** make `desi_layer9.persistence` SQLite-native (promote `layer9_v2/runtime/desi_store`
  from opt-in backend to the default), and adjust `load` to trust the materialised store with a
  cheap chain/hash check rather than a full replay. The journal table stays the audit log.
- **Locked files:** `persistence.py` (in `joni_core.lock`), plus `desi_layer9/persistence.py`.
- **Risk:** medium–high. Recovery semantics must be airtight: a corrupt materialised store must fall
  back to journal replay, never silently load wrong state. Mitigation: Phase A first (so replay
  fallback is affordable), keep `JONI_PERSISTENCE=json` as the escape hatch for one release.
- **Equivalence proof:** load(materialised) == replay(journal) on the real state; deliberate
  corruption triggers the replay fallback and is detected by the chain check.

### Phase C — model convergence (the big decision)

- **Goal:** collapse the three models to one. The open architectural choice: does the **three-space**
  store (`method`/`content`/`question`) become the runtime model, or stay a projection while
  `desi_layer9.Layer9` remains runtime?
- **Change (if three-space becomes runtime):** port `operators.py`, `conflict.py`, `router.py` and
  the object model onto the three-space representation; the converter's mapping becomes the
  migration. **This is the large refactor** the additive work was explicitly built to avoid doing
  prematurely.
- **Locked files:** `models.py`, `operators.py`, `conflict.py`, `router.py`, `state.py`,
  `identity.py` — most of `joni_core.lock`.
- **Risk:** high. This is a re-architecture, not a change. It should be its own project with its own
  phased asks, not a single PR. A real option is to **decide it stays a projection** — converging
  only `joni.state.Layer9` into `desi_layer9` and keeping three-space as analytics. That is the
  cheaper, lower-risk convergence and may be the right answer.
- **Equivalence proof:** the converter already maps legacy → three-space; the proof is that a full
  cycle on the new model reproduces the same claims/conflicts/decisions and `snapshot_hash`-class
  invariants as today.

### Phase D — de-vendor `desi_layer9`

- **Goal:** make the kernel an owned, refactorable part of Joni so A–C are maintainable rather than
  one-off forks of frozen code.
- **Change:** fold `desi_layer9` from "vendored verbatim" into a first-class, tested module with its
  own `joni_core.lock` coverage and a clear ownership boundary vs the upstream DESi repo.
- **Risk:** low technically, high in **policy** — it changes the "do not refactor casually" contract,
  so it must be an explicit, documented operator decision.

## 4. Required `joni_core.lock` changes

Today the lock covers `src/joni/*.py` only; the `desi_layer9` kernel is **not** in it. The rebuild
needs the lock to actually cover the engine it claims to protect:

- Extend `PROTECTED_CORE` (in `autonomy/governance.py`) to include the touched `desi_layer9/*.py`
  (`core.py`, `hashing.py`, `persistence.py`, `snapshot.py`).
- After each phase: a human re-runs the lock so the new hashes are recorded and the freeze re-arms.
- The governance guard itself (`autonomy/governance.py`) is already self-protecting; extending its
  list is itself a gated core change.

## 5. Explicitly NOT in scope

- The autonomous loop performing any of this. All four phases are human-gated.
- Doing A–D as one change. Each is a separate ask with its own equivalence proof and re-`lock`.
- Touching the epistemics (gate-on-admit, OPEN conflicts, no auto-confirm) — the rebuild is
  mechanical (storage/hashing/model), never semantic.

## 6. Recommended first step

**Phase A only.** It is the smallest gated change with the largest payoff (removes the in-cycle
quadratic that the persistence backend did not), it is provable bit-for-bit against the existing
hash, and it unblocks Phase B. Everything after A is a deliberate, separately-approved step.
