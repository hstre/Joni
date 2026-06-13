# Layer 9 — the shared authoritative epistemic core

Layer 9 (`desi_layer9`) is the single, shared, **authoritative epistemic state and
governance core** for the ecosystem. Joni (the operative identity) and Kevin (the
creativity module) both build on it. There is exactly one authoritative core.

## What is authoritative

The objects inside the `desi_layer9.Layer9` store are authoritative. Each carries
governance metadata: a closed **status**, an **authority** level, machine-readable
**provenance**, **derivation**, a validity window, an internal **support** value, and
**taint**. Authoritative state changes only through the **state-update gate** and a
**closed operator** — never by direct mutation.

## Why LLM (and Kevin) output is only a candidate

> No LLM, creativity module or renderer may change authoritative Layer-9 state directly.

Every external or generative contribution enters as a **`Proposal`**. The gate runs:
schema → proposer policy → control/governance → strip controlled fields → operator
(transition + taint + provenance) → ledger event → mutation → `Decision`. A model may
*write* `status: confirmed` in its output; that field is **stripped and audited**, never
adopted. A model-origin proposer (including Kevin) may propose, trial and recall — but
may **not** confirm a claim, promote a method, resolve a conflict, or touch the control
plane. Control-plane changes additionally require **human governance approval**.

## Memory vs. claim vs. evidence vs. narrative

These are distinct object classes on purpose:

- **Claim** — a typed, status-bearing belief. It does **not** contain its own evidence.
- **Evidence** / **EvidenceLink** — separate objects; a claim is `confirmed` only with a
  reviewed support link, no unresolved hard contradiction, present provenance, and a
  permitted operator. (Confirmation is a *governed status*, not truth detection.)
- **MemoryEpisode** — autobiographical salience. A memory does **not** become truer by
  being recalled; recall bumps `retrieval_weight`, never `status`.
- **NarrativeSummary** — language only. It may *describe* state but can never overwrite
  it, and it inherits the taint of what it summarises.

## Operative identity vs. person, and self-model vs. operational state

Joni is an **operative identity**, not a person. Three things are kept apart:

- **OperationalState** — measured system data (the ground truth).
- **SelfModelClaim** — a *provisional* belief Joni holds about itself (e.g. "I tend to
  abandon projects too quickly"), with evidence and counterevidence.
- **NarrativeSummary** — a human-sounding line built from the above.

A narrative may sound personlike; it can always be **dissolved** by the Epistemic View
into the exact claims, evidence, goals, memories, self-model claims, operator, proposal,
decision, taint, review and ledger event behind it.

We make no claim that Joni feels, is conscious, or that "the same self was revived".
After a reload, **Joni continues the same audited operational identity trajectory** —
nothing more.

## How Kevin is bound

Kevin uses the *same* core via `kevin/layer9_link.py`. It submits **method proposals**
(`candidate`); a human/operator promotes `candidate → provisional` (a single gate goes no
further) and, after trials, `provisional → active`. Kevin may report trials and failures;
it may never promote, confirm, change identity/goals, mark a conflict resolved, or
rewrite ledger history.

## Replay and audit

State is a deterministic function of the recorded operations: `state = replay(journal)`.
The ledger is **hash-chained** — `verify_chain()` detects any altered historic event —
and each event records the post-event `snapshot_hash`. Persistence stores the journal +
snapshot hash and refuses to load if the reconstruction or chain does not verify.
Snapshots may accelerate startup but never replace the journal. No events are ever
deleted.

## What a human must approve

- granting `authoritative`/`control` authority (via the permitted operators);
- confirming a claim, promoting a method to active, resolving/​tolerating a conflict;
- any control-plane change (rules, budgets, router/schema) — these also require explicit
  governance approval at the gate.

## Migration

The old Joni state and Kevin methods JSONL are imported into the one core via
`desi_layer9.migration` (deterministic, idempotent): Kevin methods arrive `provisional`,
old Joni claims arrive at most `active` (a previously "confirmed" claim must re-earn
confirmation), and uninterpretable rows are **quarantined and reported**, never dropped.
A backup is taken before originals are touched.

## Remaining limits (honest)

- The live **autonomy loop now runs on the core**: `joni/autonomy/` records claims,
  preferences and conflicts through the gate into `state/layer9.json` (replayable, chain-
  verified), migrating the legacy `joni_state.json` on first run. Conflicts are **opened,
  not force-resolved** — Joni can hold two incompatible explanations open. Time is real:
  the core's `tick` is the wall-clock day count, with no artificial per-cycle jumps. The
  old `joni/state.py` / `operators.py` / `conflict.py` remain as library modules used by
  the migration and detection heuristics, but are no longer the authoritative store.
- `support` / `confidence_or_support` is an internal metric in `[0, 1]` — **not a
  probability**.
- Independent-review enforcement and richer goal/project operational lifecycles are
  modelled but kept minimal; they are the natural next increments.
