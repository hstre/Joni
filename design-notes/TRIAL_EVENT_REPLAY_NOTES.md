# Trial-event replay & coexistence — operational invariants (Package A)

Two limits bound the proofs in `tests/test_trial_event_replay_coexistence.py`. They are
**operational invariants**, not bugs — but they must be explicit **before the writer is activated**.

## 1. `trial_id` uniqueness is atomic **per Layer-9 instance**, not global

`submit()` is fully synchronous, serial and non-reentrant (no `async`/`await`/`threading`/`Lock` in
`core.py` or `persistence.py`; persistence is single-writer journal replay). So within **one**
running Layer-9 instance, no second `submit` can interleave between the `trial_id` lookup and the
mint — uniqueness/idempotency is atomic there.

The correct claim is therefore scoped:

> `trial_id` uniqueness is atomic **within a single synchronous Layer-9 instance** — not globally.

```yaml
concurrency_model:
  writer_mode: single_process_single_writer
  trial_id_uniqueness_scope: layer9_instance
  multi_writer_safe: false
```

**Not** safe without further work: two Joni processes against the same store, multiple workers,
parallel API servers, separate instances in front of a shared database, or concurrent journal
merges. `tests/...::test_BOUNDARY_forced_reentrancy_would_break_uniqueness` demonstrates that a
forced interleave between lookup and mint double-mints — i.e. the guarantee *is* the serial model.

**If a multi-writer / concurrent store is ever introduced** (tracked as TD-2), `trial_id` uniqueness
must move to a persistent **unique constraint** or **compare-and-swap** at the storage layer; a
pre-mint lookup is then insufficient. Not built now; documented as a standing operating invariant.

## 2. Journal compatibility is one-directional and **irreversible after the first new event**

`JournalEntry.from_dict` does `Operator(d["operator"])`, so a runtime whose `Operator` enum lacks
`method_trial_recorded` raises at **load** — fail-closed, never a silent drop/misread.

Precise terms:

| property | value |
|---|---|
| backward-readable (new software reads old journals) | **yes** |
| forward-readable (old software reads new journals) | **no** |
| failure mode | **fail-closed at load** (`ValueError` in `from_dict`) |
| downgrade after the first `METHOD_TRIAL_RECORDED` entry | **not possible** with the same journal |

```yaml
journal_compatibility:
  backward_readable: true        # new code, old journal
  forward_readable: false        # old code, new journal
  failure_mode: fail_closed_at_load
  downgrade_after_first_new_event: blocked   # IRREVERSIBLE compatibility boundary
```

This is acceptable, but it is an **irreversible compatibility boundary**: once a journal contains a
`METHOD_TRIAL_RECORDED` entry, rolling back to a software version without that operator can no longer
load that journal. This must be acknowledged **before** the writer starts emitting the new operator
in production — there is no clean downgrade path afterward for the same journal.

## What is proven (Package A)

- legacy-only / new-only / mixed journals replay to identical snapshot hashes; the two worlds never
  touch (legacy counters vs. new events);
- new software replays old journals unchanged;
- unknown operator → fail-closed at load; known-but-unhandled → audited gate reject, nothing minted;
- identical retry and divergent-same-`trial_id` survive save/load (idempotent / rejected);
- `record_object_hash` and `snapshot_hash` route through **one** `object_canonical` serializer
  (same function object; patching it changes the snapshot) — no drift-prone parallel field list.

Replay/coexistence is complete **subject to the two invariants above**. The projector stays on hold
until Package B's protection zones are conceptually decided.
