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
   `decision_rule_hash`) via `trial_event_schema.evaluate_decision`, which computes the verdict
   from the **stored measurement** against the **pre-registered estimand threshold** — never from
   the decision block's own duplicated numbers. A decision that contradicts the measurement, or
   overrides `minimum_effect`, is `inconsistent` — never `verified`; an unknown/non-reproducible
   hash → `unverifiable`. The one canonical `cross_block_consistency` (in
   `desi_layer9.trial_event_validation`) is shared by the gate and the rule evaluator, so the two
   cannot drift.
4. The independence policy is applied **versioned** (`attribute_to_affinity`, carrying `policy_id`).
5. `unverifiable` / `inconsistent` / `unsupported_schema` / `insufficient` are kept **visible**,
   never filtered — negative transparency is a result.
6. An unknown/invalid field is **never** read as a zero signal (missing → explicit `unknown`/`None`).
7. Dataset sufficiency is judged against **real open-conflict + scope coverage and comparative
   depth**, never against event count; a single verified event is never sufficient.
8. A verified verdict is a **measured candidate**, not authoritative.

Nothing writes to the core, mutates an object, or activates a writer/DESi/Kevin path.

## Three separated axes

A single rule-verified event must **not** be read as "enough data". The projector keeps three
questions distinct:

1. **`event_usability`** — is a single event structurally usable? (`usable` / `unusable`)
2. **`decision_status`** — is its verdict reproducible via the registered rule?
3. **`dataset_sufficiency`** — is the whole conflict-/scope history enough for a gap analysis?

## Per-event mapping

| field | derivation |
|---|---|
| `record_status` | always `registered` (Layer 9 confirms the event exists) |
| `projection_status` | `projected`; `unsupported_schema` if the projector cannot interpret the schema version; or **`invalid_payload`** if the (accepted) payload cannot be parsed/cast — the projector **never crashes** on a registered event, and one bad event cannot stop the others |
| `event_usability` | `usable` iff `projected` **and** the reconstructed record passes structural `validate`; else `unusable` |
| `decision_status` | `evaluate_decision` → `verified` \| `inconsistent` \| `unverifiable` \| `not_applicable`; **`not_evaluated`** for `unsupported_schema` |
| `epistemic_weight` | **`measured_candidate`** iff `decision_status==verified` **and** `completed` **and** `valid`; otherwise `none` |
| `record_authority` / `epistemic_authority` | copied from the envelope, kept distinct |
| `reported_result` | the payload's `epistemic_result` (reported, not adjudicated) |

**Semantics — verified ≠ authoritative.** A reproducible verdict is a *measured candidate*:

```yaml
record_authority:   authoritative      # Layer 9 confirms the record was registered
decision_status:    verified           # the rule reproduces the verdict from the stored numbers
epistemic_authority: none              # the scientific conclusion is NOT thereby confirmed
epistemic_weight:   measured_candidate # DESi may use it; expert review / governance still required
```

Only `measured_candidate` events feed `aggregate()` → `verified_scope_bound_outcomes` → (if DESi
available) `desi_method_trials`. Everything else stays visible in `events` with weight `none`.

`unsupported_schema` is reported distinctly (not folded into `not_applicable`) so a projector
limitation is never mistaken for missing scientific relevance.

## Dataset sufficiency (versioned: `gap_analysis_sufficiency_v1`)

Sufficiency is **not** "≥1 verified event", and it is judged **per `(conflict, scope)`** — never
across scopes of the same conflict. A `(conflict, scope)` pair is *analysis-ready* only with
≥ `_MIN_INDEPENDENT_VARIANTS` (=2) sufficiently-**independent** verified variants within that single
stable scope; `SUFFICIENT_FOR_GAP_ANALYSIS` requires ≥1 analysis-ready pair on an **open** conflict.
The report lists the ready pairs explicitly in `analysis_ready_conflict_scopes`.

Independence is real **overlap detection**, not a `len(union) ≥ n` count: two variants that share
*any* implementation, model-family, task-sample or evaluator are **not** independent (a value
appearing in ≥2 variants is a shared dependency). It is also **fail-closed on unknowns**: a
dimension whose value is `unknown`/missing for any compared variant is **not** distinct (unknown ≠
independent), and the policy reports `independence metadata incomplete`. The structured report
carries:

```yaml
dataset_sufficiency:
  policy_id: gap_analysis_sufficiency_v1
  registered_events / structurally_usable_events / rule_verified_events
  covered_open_conflicts / open_conflicts_without_trial_history / analysis_ready_conflicts
  analysis_ready_conflict_scopes: [ {target_id, scope_id}, ... ]   # the ready (conflict, scope) pairs
  scope_coverage: none|low|medium|high
  independent_method_variants
  comparison_possible
  affinity_attribution_known
  unverifiable_events / inconsistent_events / unsupported_schema_events
  verdict: SUFFICIENT_FOR_GAP_ANALYSIS | insufficient
  reasons: [ concrete reasons ... ]
```

So a single verified success on a covered conflict reports `covered_open_conflicts:[X]` but
`verdict: insufficient` (one variant = no comparative depth).

**Sufficiency does not depend on successes.** It counts rule-verified *variants* of any outcome —
`no_benefit`, `harmful`, `success` — because differing results (A `no_benefit`, B `harmful`,
C untried) are often more informative for a solution-space analysis than two successes. What matters
is valid + rule-verified results, scope compatibility, sufficient independence, and a real
comparison — never the sign of the outcome. (Test:
`test_sufficiency_from_independent_negative_results_without_global_demotion`.)

**What `SUFFICIENT_FOR_GAP_ANALYSIS` explicitly does NOT mean** (also emitted in the report's
`interpretation.does_not_mean`):

```yaml
does_not_mean:
  - conflict resolved
  - affinity validated
  - comprehensive solution-space coverage
  - DESi added value demonstrated
  - epistemic authority
```

It is **only** an operational minimum threshold: for at least one open conflict there is enough
comparable, rule-verified, scope-bound trial history to *attempt* a state-dependent gap analysis.
Any affinity attribution it produces is **scope-bound** (tied to that conflict + scope), never a
global demotion or an epistemic confirmation.

## Decision-status → treatment

| decision_status | meaning | feeds aggregation? | visible? |
|---|---|---|---|
| `verified` | registered rule reproduces the verdict | yes (as `measured_candidate`) | yes |
| `inconsistent` | rule computes a different verdict than claimed | **no** | yes |
| `unverifiable` | rule id/hash not registered/reproducible | **no** | yes |
| `not_applicable` | no real verdict (not_evaluated / failed / invalid) | no | yes |
| `not_evaluated` | projector could not interpret the schema (`unsupported_schema`) | no | yes |

## The mandatory transparency case (test-enforced)

A correctly **registered** event with `epistemic_result=success` but an **unknown decision-rule
hash** must appear as:

```yaml
record_status: registered
decision_status: unverifiable
epistemic_weight: none
```

It is **neither counted as a success nor silently removed** — it stays in `events` as `usable` /
`unverifiable` / weight `none`, and `dataset_sufficiency.unverifiable_events` increments.

## Output shape

```python
{
  "events": [ {object_id, trial_id, schema_version, record_status, projection_status,
               event_usability, decision_status, epistemic_weight, record_authority,
               epistemic_authority, target, scope_id, reported_result, note}, ... ],
  "verified_scope_bound_outcomes": [ {target_id, scope_id, method_variant, outcome, ...}, ... ],
  "affinity_attributions": [ {affinity, strength, policy_id, independent, reason, ...}, ... ],
  "desi_method_trials": [ ... ] | None,     # None if DESi unavailable - never fabricated
  "dataset_sufficiency": { ...structured report (see above)... },
}
```

## Frozen tests (`tests/test_trial_event_projector.py`)

- **mandatory:** success + unknown rule hash → registered / usable / unverifiable / weight none,
  visible;
- a single **verified** success on a covered conflict stays **INSUFFICIENT** (one variant = no
  comparative depth);
- events in another scope/conflict do **not** satisfy the target conflict;
- a verified event is a **`measured_candidate`**, `epistemic_authority: none` (not authoritative);
- ≥2 **independent** verified variants on one open conflict reach
  **`SUFFICIENT_FOR_GAP_ANALYSIS`**;
- an **unsupported schema** stays visible (`projection_status: unsupported_schema`,
  `decision_status: not_evaluated`, weight none), not silently dropped;
- adding a second independent trial flips the verdict **traceably** (variant count 1 → 2);
- determinism.

## Still not done (gated)

No Kevin writer, no production trial events, no Kevin consumer of the projection. The Layer-9
kernel lock is **not** created (awaits a human-reviewed baseline commit). The projector is prepared
only — wiring it into a live path is a separate, gated step.
