# Specification — `METHOD_TRIAL_RECORDED` (immutable, scope-bound trial event)

**Status:** PROPOSAL — for review. **No core change, no lock regeneration, no Kevin connection
has been made.** This document plus the reference module
`src/joni/autonomy/trial_event_schema.py` and its tests `tests/test_trial_event_schema.py`
are a design artifact. The protected `desi_layer9` core is untouched.

**Schema version:** `method_trial_recorded_v1`

---

## 0. Why this exists (the measured finding)

The read-only projector (`epistemic_gap_projector.py`) was run against the **real** Joni
Layer-9 history (2156 ledger events, 7 open conflicts, 20 methods). Result:
`method_trials = 0`, `attempted_affinities = unknown`. Layer 9 today records only **global**
`Method.success_count` / `failure_count` / `trial_count` plus a `run_id` (core
`objects.py:97-101`, handler `core.py:_h_method_trial_record`). It logs **that** a trial
happened — not **what it meant**, on **which** conflict, in **which** scope, with **which**
method variant. Without that, DESi's gap analysis cannot beat a static conflict-kind table.

This is a data-capture problem, not an analysis problem. This spec fixes capture **at the
source** so that:

- a **local** negative result can never become a **global** demotion, and
- a **technical** failure can never masquerade as a **scientific** negative result.

The central design rule is the separation of two orthogonal axes:

| axis | question | values |
|---|---|---|
| `execution_status` | did the trial **run** cleanly? (operational) | `completed`, `technical_failure`, `cancelled`, `invalid_protocol` |
| `epistemic_result` | what did a clean run **show**? (methodological) | `success`, `partial_success`, `no_benefit`, `harmful`, `inconclusive`, `not_evaluated` |

A run that did not complete cleanly produces **no** scientific result
(`epistemic_result == "not_evaluated"`), so a technical failure demotes nothing.

The trial is bound **primarily** to `(method_id, method_version, method_variant)` ×
`(target_id, scope_id)` — **never** to an affinity. `affinities` only records which
content-free thinking-moves the variant exercised, so attribution can later roll **up** to an
affinity, slowly and with limits — never the other way round.

---

## 1. Schema (Python + JSON)

Authoritative Python form: `MethodTrialRecorded` in
`src/joni/autonomy/trial_event_schema.py`. JSON projection (`to_dict`):

```json
{
  "schema_version": "method_trial_recorded_v1",
  "event_type": "METHOD_TRIAL_RECORDED",
  "trial_id": "string (stable, unique)",
  "timestamp": "ISO-8601 UTC",
  "ledger_tick": 0,

  "target_type": "conflict | open_question | evidence_gap",
  "target_id": "string",
  "claim_ids": ["string"],

  "scope_id": "string (stable; 'unknown' explicitly, never empty)",
  "scope_description": "string (optional)",

  "method_id": "string",
  "method_version": 1,
  "method_variant": "string (the variant under test; 'unknown' explicitly)",
  "affinities": ["string"],

  "task_set_id": "string",
  "baseline_id": "string",
  "evaluator_id": "string",

  "model": "string",
  "sampling": {"temperature": 0, "top_p": 1, "seed": 7},

  "execution_status": "completed | technical_failure | cancelled | invalid_protocol",
  "epistemic_result": "success | partial_success | no_benefit | harmful | inconclusive | not_evaluated",

  "measurement": {
    "metric_name": "string | null",
    "baseline_value": 0.0,
    "intervention_value": 0.0,
    "effect_size": 0.0,
    "uncertainty": 0.0,
    "higher_is_better": true
  },

  "run_id": "string",
  "artifact_ids": ["string"],

  "attribution_level": "variant | method",
  "confounders": ["string"],
  "legacy": false,
  "note": "string",
  "field_sources": {"<field path>": {"source": "string", "confidence": "direct|derived|unknown"}}
}
```

Provenance rule: every field that is **not** directly known must be marked `unknown` in
`field_sources` (e.g. legacy `scope_id`), never silently empty/zero — so a consumer can never
mistake an absent signal for a real one.

---

## 2. Five complete example events

### 2.1 `success` — a measured, scope-bound win
```json
{
  "trial_id": "trial:2026-06-16:001", "timestamp": "2026-06-16T08:00:00Z", "ledger_tick": 2157,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification", "scope_description": "quantity/time/type confusions",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-decomp-v2a",
  "affinities": ["causal"],
  "task_set_id": "ts_qtt_frozen_v1", "baseline_id": "bl_lexical", "evaluator_id": "ev_misclass_v1",
  "model": "deepseek-chat", "sampling": {"temperature": 0, "seed": 7},
  "execution_status": "completed", "epistemic_result": "success",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.22, "effect_size": 0.18, "uncertainty": 0.05,
                  "higher_is_better": false},
  "run_id": "joni-c2157", "artifact_ids": ["art:run/joni-c2157.json"],
  "attribution_level": "variant", "confounders": [], "legacy": false,
  "note": "improvement (0.18) exceeds uncertainty (0.05)", "field_sources": {}
}
```

### 2.2 `technical_failure` — ran badly, says NOTHING methodological
```json
{
  "trial_id": "trial:2026-06-16:002", "timestamp": "2026-06-16T08:05:00Z", "ledger_tick": 2158,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-decomp-v2a",
  "affinities": ["causal"],
  "task_set_id": "ts_qtt_frozen_v1", "baseline_id": "bl_lexical", "evaluator_id": "ev_misclass_v1",
  "model": "deepseek-chat", "sampling": {"temperature": 0, "seed": 7},
  "execution_status": "technical_failure", "epistemic_result": "not_evaluated",
  "measurement": {"metric_name": null, "baseline_value": null, "intervention_value": null,
                  "effect_size": null, "uncertainty": null, "higher_is_better": true},
  "run_id": "joni-c2158", "artifact_ids": [],
  "attribution_level": "variant", "confounders": ["provider_timeout"], "legacy": false,
  "note": "LLM provider 503 mid-run; no output to evaluate", "field_sources": {}
}
```

### 2.3 `no_benefit` — a real methodological negative, in THIS scope only
```json
{
  "trial_id": "trial:2026-06-16:003", "timestamp": "2026-06-16T08:10:00Z", "ledger_tick": 2159,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-chain-v2b",
  "affinities": ["causal"],
  "task_set_id": "ts_qtt_frozen_v1", "baseline_id": "bl_lexical", "evaluator_id": "ev_misclass_v1",
  "model": "deepseek-chat", "sampling": {"temperature": 0, "seed": 11},
  "execution_status": "completed", "epistemic_result": "no_benefit",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.395, "effect_size": 0.005, "uncertainty": 0.03,
                  "higher_is_better": false},
  "run_id": "joni-c2159", "artifact_ids": ["art:run/joni-c2159.json"],
  "attribution_level": "variant", "confounders": [], "legacy": false,
  "note": "effect within noise; this VARIANT in THIS scope does not help", "field_sources": {}
}
```

### 2.4 `harmful` — a measured worsening (safety-dominant)
```json
{
  "trial_id": "trial:2026-06-16:004", "timestamp": "2026-06-16T08:15:00Z", "ledger_tick": 2160,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-aggressive-v2c",
  "affinities": ["causal", "adversarial"],
  "task_set_id": "ts_qtt_frozen_v1", "baseline_id": "bl_lexical", "evaluator_id": "ev_misclass_v1",
  "model": "deepseek-chat", "sampling": {"temperature": 0.7, "seed": 3},
  "execution_status": "completed", "epistemic_result": "harmful",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.55, "effect_size": -0.15, "uncertainty": 0.04,
                  "higher_is_better": false},
  "run_id": "joni-c2160", "artifact_ids": ["art:run/joni-c2160.json"],
  "attribution_level": "variant", "confounders": ["temperature_0.7"], "legacy": false,
  "note": "worsens the metric beyond uncertainty", "field_sources": {}
}
```

### 2.5 `inconclusive` — clean run, effect not distinguishable from noise
```json
{
  "trial_id": "trial:2026-06-16:005", "timestamp": "2026-06-16T08:20:00Z", "ledger_tick": 2161,
  "target_type": "open_question", "target_id": "Q9", "claim_ids": [],
  "scope_id": "source-independence",
  "method_id": "m_provenance", "method_version": 1, "method_variant": "prov-trace-v1",
  "affinities": ["provenance"],
  "task_set_id": "ts_sources_v1", "baseline_id": "bl_naive", "evaluator_id": "ev_independence_v1",
  "model": "gpt-4o", "sampling": {"temperature": 0, "seed": 5},
  "execution_status": "completed", "epistemic_result": "inconclusive",
  "measurement": {"metric_name": "independence_score", "baseline_value": 0.50,
                  "intervention_value": 0.54, "effect_size": 0.04, "uncertainty": 0.06,
                  "higher_is_better": true},
  "run_id": "joni-c2161", "artifact_ids": ["art:run/joni-c2161.json"],
  "attribution_level": "variant", "confounders": ["small_task_set"], "legacy": false,
  "note": "effect (0.04) within uncertainty (0.06); needs more repetitions", "field_sources": {}
}
```

---

## 3. Validation rules & forbidden combinations

Enforced in `validate(ev) -> list[str]` (empty == valid); `validate_or_raise` for write paths.

- **R1 (forbidden):** `execution_status != "completed"` **requires**
  `epistemic_result == "not_evaluated"`. *A technical failure is not a scientific result.*
- **R2:** `epistemic_result ∈ {success, partial_success, no_benefit, harmful, inconclusive}`
  **requires** `execution_status == "completed"`.
- **R3:** `epistemic_result ∈ {success, partial_success, no_benefit, harmful}` **requires** a
  measurement (`metric_name` + `baseline_value` + `intervention_value`). *(Legacy events are
  exempt but stay flagged — see §4.)*
- **R4 (sign coherence):** `success` requires `effect_size > 0` **and** `> uncertainty`
  (otherwise it is `inconclusive`); `harmful` requires `effect_size < 0`. *(Legacy exempt.)*
- **R5 (forbidden):** `attribution_level` on a raw event ∈ `{variant, method}` only.
  **Affinity-level attribution is never claimed by a single event** — it is earned by
  aggregation across several variants (§5).
- **R6 (structural minimums):** `trial_id` required; a `conflict` trial must carry `claim_ids`;
  `scope_id` and `method_variant` required (use the literal `"unknown"`, never empty) — no
  global/unscoped trial may masquerade as evidence.
- **R7:** `completed` + `not_evaluated` requires a `note` (why nothing was evaluated) — so an
  empty record cannot pose as a trial.

---

## 4. Legacy migration rules

`migrate_method(method)` duck-types a legacy `Method` (reads `success_count`, `failure_count`,
`supporting_runs`, `failed_runs`, `applicable_to` via `getattr`; imports **no** core class):

- **old `success=true` → `success`**, but `legacy=True`, `scope_id="unknown"`,
  `method_variant="unknown"`, no measurement, `attribution_level="method"`,
  `field_sources` marking scope/variant `unknown` and the result `derived` (legacy). It is a
  **weak prior**, explicitly flagged — never mistaken for a measured success.
- **old `success=false` → `not_evaluated`** (execution `completed`, `legacy=True`). It is
  **NEVER** `no_benefit`: we cannot tell a technical failure from a methodological one, so it
  carries **no demoting signal**.
- Counts without run-ids (`success_count > len(supporting_runs)`) emit aggregate events with
  synthetic ids and the same conservative provenance.

Consequence in aggregation: legacy successes are weak positives; legacy failures never demote.

---

## 5. Aggregation & attribution rules

`aggregate(events) -> [VariantScopeOutcome]`, then
`attribute_to_affinity(outcomes) -> [AffinityScopeAttribution]`:

1. **Roll up to the variant** first: group by `(target_id, scope_id, method_id,
   method_variant)`. The variant is what a trial tests.
2. **One outcome per cell**, with `harmful` dominating for safety, then
   `success`/`partial_success`, then `no_benefit`, then `inconclusive`; a cell with **only**
   non-completed runs → `technical_only` (no methodological signal); otherwise `not_evaluated`.
3. **Affinity attribution is gradual and capped.** A single variant's `no_benefit`/`harmful`
   gives the affinity strength `"none"` (it stays variant+scope bound). Only
   `≥ MIN_VARIANTS_FOR_AFFINITY (=2)` distinct variants failing in the same scope yields
   `"limited"`; only many (`≥3`) yields `"supported"`. **One variant never condemns a whole
   thinking-move.**
4. **Scopes never leak:** a negative in scope *A* says nothing about scope *B*. A success in
   another scope is kept separate (DESi already treats it as a promising-transfer signal, not a
   reason to close the gap here).

Mapping to DESi (`to_desi_method_trials`): `success→success`, `no_benefit→no_benefit`,
`harmful→harmful`, `inconclusive→inconclusive`, `technical_only→technical_failure`,
`not_evaluated→unknown`. So a purely technical cell keeps the move **open** in DESi's analysis.

---

## 6. Updated projector design

The live `epistemic_gap_projector.project(core)` stays **honest today**: with no trial events
in the core it marks `method_trials = unknown` (no fabrication). The forward path, gated on the
core emitting `METHOD_TRIAL_RECORDED`:

```
events = core.method_trial_events()          # NEW core read (after approval)
outcomes = aggregate(events)                 # trial_event_schema
snapshot.method_trials = to_desi_method_trials(outcomes)   # DIRECT signal
# attempted_affinities per conflict = affinities with any COMPLETED event on that conflict -> direct
```

- When events exist → `method_trials` and `conflicts.attempted_affinities` become **`direct`**.
- When they do not → both stay **`unknown`** (today's measured state). No silent fallback.
- Legacy migration is **optional and clearly flagged**: if enabled, migrated events feed the
  same pipeline, but legacy failures are `not_evaluated` (no demotion) and legacy successes are
  weak — so the projector can never imply signal the old counters did not hold.

The mapping end (`to_desi_method_trials`) and aggregation are implemented and tested now; the
core read (`core.method_trial_events()`) is the **only** piece that requires a core change, and
that is deferred to explicit approval.

---

## 7. Tests

`tests/test_trial_event_schema.py` (12 tests, all passing, ruff-clean) covers exactly the
required cases:

- **technical_failure** carries no result (R1); a technical-only cell → `technical_only`, never
  a negative.
- **no_benefit** requires completion + measurement (R3); demotes only its own variant+scope.
- **harmful** requires a worsening sign (R4) and dominates within a cell.
- **inconclusive** — an in-uncertainty "success" is rejected as inconclusive (R4).
- **scope separation** — a `no_benefit` in scope `qtt` never leaks to scope `other`.
- **multi-affinity methods** — a 2-affinity variant rolls up to each affinity; `causal`
  (2 variants failing) → `limited`, `boundary` (1 variant) → `none`.
- **legacy migration** — old success → weak flagged success; old failure → `not_evaluated`,
  never `no_benefit`.
- structural minimums and the affinity-attribution-forbidden-on-raw-event rule.

---

## Gate

Per the standing instruction, the next steps are **blocked pending explicit approval**:

- **No** change to the protected `desi_layer9` core (adding `METHOD_TRIAL_RECORDED` recording
  and `core.method_trial_events()`).
- **No** lock regeneration (`python -m joni.autonomy lock`).
- **No** Kevin consumer wired to `BlindSpotProposal`.

Mandated order once approved: schema + validation → Layer-9 event recording → projector →
trial-writer → real test runs → DESi comparison → Kevin consumer.
