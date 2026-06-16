# Read-only trial-event projector — rules & mapping

**Status:** prepared on the feature branch, **read-only, no writer hookup, no production
activation, no Kevin consumer.** Module: `joni/autonomy/trial_event_projector.py`. The controlled
connection from the *stored* event to *external* epistemic evaluation.

## Hard rules

1. The **only** new trial source is `core.method_trial_events()`. Legacy `Method` counters
   (`success_count` …) are **never** re-read as scope-bound trial history.
2. Envelope, `schema_version`, `record_authority` and `epistemic_authority` are evaluated
   **separately** from the reported payload.
3. Decision verdicts are verified by the **registered, versioned** rule (`decision_rule_id` +
   `decision_rule_hash`) via `trial_event_schema.evaluate_decision`. An unknown/non-reproducible
   hash → `unverifiable`.
4. The independence policy is applied **versioned** (`attribute_to_affinity`, carrying `policy_id`).
5. `unverifiable` and `insufficient` are kept **visible**, never filtered — negative transparency is
   a result.
6. An unknown/invalid field is **never** read as a zero signal (missing → explicit `unknown`/`None`).
7. No verified scope-bound events → verdict **INSUFFICIENT**.

Nothing writes to the core, mutates an object, or activates a writer/DESi/Kevin path.

## Per-event mapping

For each envelope from `method_trial_events()`:

| field | derivation |
|---|---|
| `record_status` | always `registered` (Layer 9 confirms the event exists) |
| `schema_status` | `supported` iff `schema_version ∈ SUPPORTED_TRIAL_SCHEMA_VERSIONS`, else `unsupported` (kept visible) |
| `decision_status` | `evaluate_decision(record)` → `verified` \| `inconsistent` \| `unverifiable` \| `not_applicable` |
| `epistemic_weight` | `verified_scope_bound` **iff** `decision_status==verified` **and** `execution_status==completed` **and** `protocol_status==valid`; otherwise `none` |
| `record_authority` / `epistemic_authority` | copied from the envelope, kept distinct |
| `reported_result` | the payload's `epistemic_result` (reported, not adjudicated) |

Only events with `epistemic_weight==verified_scope_bound` feed `aggregate()` →
`verified_scope_bound_outcomes` → (if DESi available) `desi_method_trials`. Everything else stays in
`events` with `epistemic_weight: none`.

## Decision-status → treatment

| decision_status | meaning | counted? | visible? |
|---|---|---|---|
| `verified` | registered rule reproduces the verdict from the inputs | yes (scope-bound) | yes |
| `inconsistent` | rule computes a different verdict than claimed | **no** | yes |
| `unverifiable` | rule id/hash not registered/reproducible | **no** | yes |
| `not_applicable` | no real verdict (not_evaluated / failed / invalid / unsupported schema) | no | yes |

## The mandatory transparency case (test-enforced)

A correctly **registered** event with `epistemic_result=success` but an **unknown decision-rule
hash** must appear as:

```yaml
record_status: registered
decision_status: unverifiable
epistemic_weight: none
```

It is **neither counted as a success nor silently removed** — it stays in `events`, and
`data_sufficiency.unverifiable_events` increments. (`test_success_with_unknown_rule_hash_is_
registered_but_unverifiable`.)

## Output shape

```python
{
  "events": [ {object_id, trial_id, record_status, schema_status, decision_status,
               epistemic_weight, record_authority, epistemic_authority, target, scope_id,
               reported_result, note}, ... ],
  "verified_scope_bound_outcomes": [ {target_id, scope_id, method_variant, outcome, ...}, ... ],
  "affinity_attributions": [ {affinity, strength, policy_id, independent, reason, ...}, ... ],
  "desi_method_trials": [ ... ] | None,     # None if DESi unavailable - never fabricated
  "data_sufficiency": { registered_events, verified_events, unverifiable_events,
                        inconsistent_events, verdict },
}
```

## Frozen tests (`tests/test_trial_event_projector.py`)

- **mandatory:** success + unknown rule hash → registered / unverifiable / weight none, visible,
  verdict INSUFFICIENT;
- verified success → `verified_scope_bound`, sufficiency flips to `sufficient`;
- a verdict the rule contradicts (claims `no_benefit`, rule computes `harmful`) → `inconsistent`,
  weight none, still visible;
- failed/`not_evaluated` event → registered / `not_applicable` / weight none;
- empty of new events but with a **legacy** trial recorded → `events == []`, INSUFFICIENT (legacy
  counters are not trial history);
- determinism.

## Still not done (gated)

No Kevin writer, no production trial events, no Kevin consumer of the projection. The Layer-9
kernel lock is **not** created (awaits a human-reviewed baseline commit). The projector is prepared
only — wiring it into a live path is a separate, gated step.
