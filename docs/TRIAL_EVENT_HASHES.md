# Trial-event hash semantics

Four distinct hashes touch a `METHOD_TRIAL_RECORDED` record. They mean different things and must
**not** be conflated under a generic word like "integrity hash". The per-event envelope from
`core.method_trial_events()` exposes the first two by name; the last two are global and read
separately.

| name | over what material | covers | where |
|---|---|---|---|
| `payload_hash` | the canonical payload string **only** | the writer-REPORTED content (trial_id, axes, measurement, decision, estimand …). **Not** who recorded it. | envelope `hashes.payload_hash`; `core.trial_event_hashes(o)` |
| `record_object_hash` | `object_canonical(MethodTrialEvent)` — the **full record object** | the payload **plus** Layer-9 provenance: `created_by` (actor), `provenance`, `record_authority` **and** `epistemic_authority`, `schema_version`, `derived_from`, `status`, `authority`, ticks | envelope `hashes.record_object_hash`; `core.trial_event_hashes(o)` |
| `state_snapshot_hash` | **all** authoritative objects | the entire in-force state; the per-object material it folds in for this record **is exactly** `object_canonical(o)` (so a record tamper shows here too) | `hashing.snapshot_hash(core)` |
| `ledger_chain_hash` | the hash-chained ledger | the tamper-evident order of every accepted/rejected operator application; each event also stores the `after_hash` (snapshot at emit) | `core.ledger[-1].event_hash` |

Key relationships, all asserted in `tests/test_method_trial_event_recording.py`:

- `payload_hash` is **invariant** under changes to actor / provenance / either authority level /
  schema_version — it hashes only the reported content. So it must **never** be presented as proof
  that *Layer 9 recorded this*; it only fixes *what was reported*.
- `record_object_hash` **changes** when any of those provenance/authority/schema fields change. It
  is the same material `state_snapshot_hash` uses for this object, so a record tamper is reflected
  in both `record_object_hash` and the global snapshot, and is therefore caught on replay
  (`state = f(journal)`): the tampered in-memory state diverges from the journal-replayed state.

Practical rule: use `payload_hash` to dedupe/compare reported content (it underlies `trial_id`
idempotency); use `record_object_hash` / `state_snapshot_hash` / `ledger_chain_hash` for integrity
of the *registration*. Picking the wrong one as an "integrity proof" would attest the wrong thing.
