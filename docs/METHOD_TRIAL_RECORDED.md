# Specification — `METHOD_TRIAL_RECORDED` (immutable, scope-bound trial event)

**Status:** PROPOSAL — review round 2. **No core change, no lock regeneration, no Kevin
connection has been made.** This document plus the reference module
`src/joni/autonomy/trial_event_schema.py` and its tests `tests/test_trial_event_schema.py`
are a design artifact. The protected `desi_layer9` core is untouched.

**Schema version:** `method_trial_recorded_v2`

### What changed in v2 (the four review points)

1. **Legacy `success=true` is no longer trusted as epistemic success** (verified against the
   old writers — see §4).
2. **Three orthogonal status axes** (`execution_status` × `protocol_status` ×
   `epistemic_result`) plus a `failure_kind` cause, instead of one overloaded status list (§1, §3).
3. **Affinity attribution requires *independent* variants**, not a flat two-variant count (§5).
4. **Every event carries an `estimand` + decision rule**, so `no_benefit` is the pre-registered
   rule's verdict, never a post-hoc small number (§1, §3).

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
source** so that a **local** negative result can never become a **global** demotion, and a
**technical** failure can never masquerade as a **scientific** negative result.

### The status model (three axes + cause)

| axis | question | values |
|---|---|---|
| `execution_status` | did the trial **run** to completion? | `completed`, `failed`, `cancelled` |
| `protocol_status` | was the **protocol** valid? | `valid`, `invalid`, `unknown` |
| `failure_kind` | *if* it failed, why? | `none`, `technical`, `timeout`, `parser`, `model`, `dependency`, `infrastructure` |
| `epistemic_result` | what did a **completed, valid** run show? | `success`, `partial_success`, `no_benefit`, `harmful`, `inconclusive`, `not_evaluated` |

Only a `completed` + `valid` run can carry a real `epistemic_result`. A technical failure is
`execution_status="failed"` + `failure_kind="technical"` → `epistemic_result="not_evaluated"`,
so it demotes nothing. An `invalid` protocol carries no result even if the run completed.

The trial is bound **primarily** to `(method_id, method_version, method_variant)` ×
`(target_id, scope_id)` — **never** to an affinity. `affinities` only records which
content-free thinking-moves the variant exercised, so attribution can roll **up** to an
affinity, slowly and with limits — never the other way round.

---

## 1. Schema (Python + JSON)

Authoritative Python form: `MethodTrialRecorded` in `trial_event_schema.py`. JSON projection
(`to_dict`):

```json
{
  "schema_version": "method_trial_recorded_v2",
  "event_type": "METHOD_TRIAL_RECORDED",
  "trial_id": "string (stable, unique)",
  "timestamp": "ISO-8601 UTC",
  "ledger_tick": 0,

  "target_type": "conflict | open_question | evidence_gap",
  "target_id": "string",
  "claim_ids": ["string"],

  "scope_id": "string ('unknown' explicitly, never empty)",
  "scope_description": "string (optional)",

  "method_id": "string",
  "method_version": 1,
  "method_variant": "string (the variant under test; 'unknown' explicitly)",
  "implementation_id": "string (implementation lineage, for independence checks)",
  "affinities": ["string"],

  "task_set_id": "string",
  "baseline_id": "string",
  "evaluator_id": "string",
  "estimand": {
    "outcome_metric": "conflict_resolution_score",
    "contrast": "intervention_minus_baseline",
    "direction": "higher_is_better | lower_is_better",
    "minimum_effect": 0.05,
    "decision_rule_id": "rule_v2"
  },

  "model": "string",
  "sampling": {"temperature": 0, "top_p": 1, "seed": 7},

  "execution_status": "completed | failed | cancelled",
  "protocol_status": "valid | invalid | unknown",
  "failure_kind": "none | technical | timeout | parser | model | dependency | infrastructure",
  "epistemic_result": "success | partial_success | no_benefit | harmful | inconclusive | not_evaluated",

  "measurement": {
    "metric_name": "string | null",
    "baseline_value": 0.0,
    "intervention_value": 0.0,
    "effect_size": 0.0,   "_comment": "ORIENTED so positive == better, per estimand.direction",
    "uncertainty": 0.0
  },

  "run_id": "string",
  "artifact_ids": ["string"],

  "attribution_level": "variant | method",
  "attribution_strength": "none",
  "confounders": ["string"],
  "legacy": false,
  "legacy_reported_success": false,
  "note": "string",
  "field_sources": {"<field path>": {"source": "string", "confidence": "direct|derived|unknown"}}
}
```

Provenance rule: any field **not** directly known is marked `unknown` in `field_sources`
(e.g. legacy `scope_id`), never silently empty/zero.

---

## 2. Five complete example events

### 2.1 `success` — measured, clears the pre-registered threshold
```json
{
  "trial_id": "trial:001", "timestamp": "2026-06-16T08:00:00Z", "ledger_tick": 2157,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-decomp-v2a",
  "implementation_id": "impl-A", "affinities": ["causal"],
  "task_set_id": "ts_qtt_frozen_v1", "baseline_id": "bl_lexical", "evaluator_id": "ev_misclass_v1",
  "estimand": {"outcome_metric": "misclassification_rate", "contrast": "intervention_minus_baseline",
               "direction": "lower_is_better", "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},
  "model": "deepseek-chat", "sampling": {"temperature": 0, "seed": 7},
  "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
  "epistemic_result": "success",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.22, "effect_size": 0.18, "uncertainty": 0.05},
  "run_id": "joni-c2157", "artifact_ids": ["art:run/joni-c2157.json"],
  "attribution_level": "variant", "attribution_strength": "none", "confounders": [],
  "legacy": false, "legacy_reported_success": false,
  "note": "effect 0.18 >= minimum_effect 0.10 and beyond uncertainty 0.05", "field_sources": {}
}
```

### 2.2 `failed` / `technical` — ran badly, says NOTHING methodological
```json
{
  "trial_id": "trial:002", "timestamp": "2026-06-16T08:05:00Z", "ledger_tick": 2158,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-decomp-v2a",
  "implementation_id": "impl-A", "affinities": ["causal"],
  "estimand": {"outcome_metric": "misclassification_rate", "direction": "lower_is_better",
               "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},
  "model": "deepseek-chat",
  "execution_status": "failed", "protocol_status": "unknown", "failure_kind": "timeout",
  "epistemic_result": "not_evaluated",
  "measurement": {"metric_name": null, "baseline_value": null, "intervention_value": null,
                  "effect_size": null, "uncertainty": null},
  "run_id": "joni-c2158", "artifact_ids": [],
  "attribution_level": "variant", "attribution_strength": "none", "confounders": ["provider_timeout"],
  "legacy": false, "legacy_reported_success": false,
  "note": "LLM provider timeout mid-run; no output to evaluate", "field_sources": {}
}
```

### 2.3 `no_benefit` — the decision rule's verdict (minimum effect NOT met), scope-bound
```json
{
  "trial_id": "trial:003", "timestamp": "2026-06-16T08:10:00Z", "ledger_tick": 2159,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-chain-v2b",
  "implementation_id": "impl-B", "affinities": ["causal"],
  "estimand": {"outcome_metric": "misclassification_rate", "direction": "lower_is_better",
               "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},
  "model": "deepseek-chat", "sampling": {"temperature": 0, "seed": 11},
  "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
  "epistemic_result": "no_benefit",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.355, "effect_size": 0.045, "uncertainty": 0.02},
  "run_id": "joni-c2159", "artifact_ids": ["art:run/joni-c2159.json"],
  "attribution_level": "variant", "attribution_strength": "none", "confounders": [],
  "legacy": false, "legacy_reported_success": false,
  "note": "effect 0.045 resolved (> uncertainty 0.02) but BELOW minimum_effect 0.10 -> rule_v2 = no_benefit",
  "field_sources": {}
}
```

### 2.4 `harmful` — measured worsening beyond the threshold (safety-dominant)
```json
{
  "trial_id": "trial:004", "timestamp": "2026-06-16T08:15:00Z", "ledger_tick": 2160,
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7", "C-12"],
  "scope_id": "qtt-misclassification",
  "method_id": "m_causal", "method_version": 2, "method_variant": "causal-aggressive-v2c",
  "implementation_id": "impl-C", "affinities": ["causal", "adversarial"],
  "estimand": {"outcome_metric": "misclassification_rate", "direction": "lower_is_better",
               "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},
  "model": "deepseek-chat", "sampling": {"temperature": 0.7, "seed": 3},
  "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
  "epistemic_result": "harmful",
  "measurement": {"metric_name": "misclassification_rate", "baseline_value": 0.40,
                  "intervention_value": 0.55, "effect_size": -0.15, "uncertainty": 0.04},
  "run_id": "joni-c2160", "artifact_ids": ["art:run/joni-c2160.json"],
  "attribution_level": "variant", "attribution_strength": "none", "confounders": ["temperature_0.7"],
  "legacy": false, "legacy_reported_success": false,
  "note": "effect -0.15 <= -minimum_effect 0.10", "field_sources": {}
}
```

### 2.5 `completed` + `invalid` protocol → `inconclusive` is impossible, `not_evaluated`
```json
{
  "trial_id": "trial:005", "timestamp": "2026-06-16T08:20:00Z", "ledger_tick": 2161,
  "target_type": "open_question", "target_id": "Q9", "claim_ids": [],
  "scope_id": "source-independence",
  "method_id": "m_provenance", "method_version": 1, "method_variant": "prov-trace-v1",
  "implementation_id": "impl-P", "affinities": ["provenance"],
  "estimand": {"outcome_metric": "independence_score", "direction": "higher_is_better",
               "minimum_effect": 0.08, "decision_rule_id": "rule_v2"},
  "model": "gpt-4o", "sampling": {"temperature": 0, "seed": 5},
  "execution_status": "completed", "protocol_status": "invalid", "failure_kind": "none",
  "epistemic_result": "not_evaluated",
  "measurement": {"metric_name": "independence_score", "baseline_value": 0.50,
                  "intervention_value": 0.62, "effect_size": 0.12, "uncertainty": 0.03},
  "run_id": "joni-c2161", "artifact_ids": ["art:run/joni-c2161.json"],
  "attribution_level": "variant", "attribution_strength": "none", "confounders": ["baseline_leaked_into_intervention"],
  "legacy": false, "legacy_reported_success": false,
  "note": "the baseline leaked into the intervention split -> protocol invalid; the apparent +0.12 cannot be trusted",
  "field_sources": {}
}
```

*(A clean `inconclusive` — completed, valid, but `|effect| <= uncertainty` — is also valid; it
is exercised in the tests.)*

---

## 3. Validation rules & forbidden combinations

Enforced in `validate(ev) -> list[str]`:

- **R1:** `execution_status != "completed"` ⇒ `epistemic_result == "not_evaluated"`.
- **R1b:** `failed` ⇔ a `failure_kind != "none"` (and a `completed`/`cancelled` run has none).
- **R2:** `protocol_status == "invalid"` ⇒ `epistemic_result == "not_evaluated"`;
  `protocol_status == "unknown"` ⇒ no *real* result (`success`/`partial_success`/`no_benefit`/
  `harmful`).
- **R3:** a real result ⇒ `execution_status == "completed"` **and** `protocol_status == "valid"`.
- **R4 (measurement + estimand):** a real result ⇒ a measurement (`metric_name` + baseline +
  intervention) **and** an estimand with `decision_rule_id` and `minimum_effect > 0`.
- **R5 (decision-rule consistency):** the label must be the rule's output —
  `success` ⇒ `effect_size >= minimum_effect` **and** `> uncertainty`;
  `harmful` ⇒ `effect_size <= -minimum_effect`;
  `no_benefit` ⇒ `|effect_size| < minimum_effect` **and** `> uncertainty` (resolved but under the
  bar — *minimum effect not met*); `inconclusive` ⇒ `|effect_size| <= uncertainty`.
- **R6 (attribution):** raw events may carry `attribution_level ∈ {variant, method}` only, and
  `attribution_strength == "none"` — affinity-level strength is earned only by independent
  aggregation (§5).
- **R7 (structural):** `trial_id` required; a `conflict` trial needs `claim_ids`; `scope_id` and
  `method_variant` required (literal `"unknown"`, never empty); `completed`+`valid`+
  `not_evaluated` needs a `note`.
- **Legacy exemption:** events with `legacy=True` are exempt from R3/R4/R5 and the unknown-protocol
  arm of R2 (they predate the regime and carry `protocol_status="unknown"` honestly), but **never**
  from R1 or the invalid-protocol rule. They stay clearly weak via `legacy=True` and no measurement.

---

## 4. Legacy migration rules — verified against the old writers

`migrate_method(method, *, proven_success_runs=None)` duck-types a legacy `Method`
(`success_count`, `failure_count`, `supporting_runs`, `failed_runs`, `applicable_to`).

**Why `success=true` is not trusted.** The core handler `_h_method_trial_record` stores only
`success` + `run_id` into global counters. Tracing the writers:

- The **dominant** writer, kevin `trial_runner.trial_methods` (runs every cycle), sets
  `success = improvement >= MIN` with `improvement = fit * HELP`, where `fit` is a **synthetic
  structural-overlap heuristic** on a deterministically-picked foreign task. The writer tags its
  own report `evaluation_mode` / `epistemic_weight` with the note *"a simulation, not an
  effectiveness measurement."* ⇒ **not** measured epistemic benefit.
- Only `real_trial.run_real_trial` (run_id `kevin-real`) decides `passed` by a predefined metric +
  threshold + clean negative control — measured semantics — and even there the full result lives in
  a **separate artifact**, not in the `Method` counters.

Therefore:

- **old `success=true` → `not_evaluated`** + `legacy_reported_success=true`,
  `attribution_strength="none"`, `protocol_status="unknown"`, no measurement — **by default**.
- Only run classes **proven** to carry measured success (passed via `proven_success_runs`, e.g.
  `("kevin-real",)`) become a **weak `success`** (still `legacy=True`, no scope/variant/effect).
- **old `success=false` → `not_evaluated`** (`legacy_reported_success=false`). **Never**
  `no_benefit`: technical vs methodological is unknown, so it carries **no demoting signal**.

Consequence in aggregation: nothing in the legacy import promotes or demotes unless a run class is
explicitly proven; old false precision is not imported.

---

## 5. Aggregation & attribution rules

`aggregate(events) -> [VariantScopeOutcome]`, then
`attribute_to_affinity(outcomes) -> [AffinityScopeAttribution]`:

1. **Roll up to the variant** first: group by `(target_id, scope_id, method_id,
   method_variant)`. A cell's outcome uses only `completed`+`valid` runs; `harmful` dominates
   (safety), then `success`/`partial_success`, then `no_benefit`, then `inconclusive`; a cell with
   **only** unusable runs (failed/cancelled/invalid) → `technical_only` (no signal); else
   `not_evaluated`.
2. **Affinity attribution requires *independence*, not a count.** `_independent(neg)` admits a
   limited affinity statement only when the failing variant-cells have: ≥ 2 distinct variants;
   **all** protocol-valid; **distinct models OR implementations** (not all sharing one);
   and **no confounder common to all** (no dominant shared *Störquelle*). Two highly-correlated
   variants (same model, same shared confounder) → `strength="none"`. A `success` for the same
   affinity-scope makes the picture inconsistent → `strength="none"`.
3. Strengths: independent ≥ 3 variants → `supported`; independent 2 → `limited`; otherwise
   `none`. A single variant's `no_benefit` always stays variant+scope bound (`none`).
4. **Scopes never leak**, and a success in another scope is kept separate (DESi treats it as a
   promising-transfer signal, not a reason to close the gap here).

Mapping to DESi (`to_desi_method_trials`): `success→success`, `no_benefit→no_benefit`,
`harmful→harmful`, `inconclusive→inconclusive`, `technical_only→technical_failure`,
`not_evaluated→unknown`. So a purely technical/invalid cell keeps the move **open** in DESi.

---

## 6. Updated projector design

The live `epistemic_gap_projector.project(core)` stays **honest today**: with no trial events in
the core it marks `method_trials = unknown` (no fabrication). Forward path, gated on the core
emitting `METHOD_TRIAL_RECORDED`:

```
events   = core.method_trial_events()            # NEW core read (after approval)
outcomes = aggregate(events)                     # trial_event_schema
snapshot.method_trials = to_desi_method_trials(outcomes)        # DIRECT signal
# attempted_affinities per conflict = affinities with any completed+valid event -> direct
```

- Events present → `method_trials` and `conflicts.attempted_affinities` become **`direct`**.
- Absent → both stay **`unknown`** (today's measured state). No silent fallback.
- Legacy migration is **optional and clearly flagged**; with `proven_success_runs` unset, legacy
  contributes only `not_evaluated` events — the projector can never imply signal the old counters
  did not hold.

`aggregate` / `to_desi_method_trials` are implemented and tested now; only the core read
(`core.method_trial_events()`) needs a core change, deferred to explicit approval.

---

## 7. Tests

`tests/test_trial_event_schema.py` (20 tests, all passing, ruff-clean) covers the required cases:

- **failed execution** — carries no result (R1); needs a `failure_kind` (R1b); a technical/failed
  cell → `technical_only`, never a negative.
- **invalid protocol** — completed-but-invalid carries no result (R2); unknown protocol cannot
  carry a real result.
- **minimum effect not met** — `no_benefit` is valid only when the effect is resolved but below
  `minimum_effect`; an effect that *meets* the threshold may not be labelled `no_benefit`;
  `success` must clear the threshold *and* beat noise; `harmful` must worsen beyond it.
- **legacy migration** — by default no legacy success and no `no_benefit`; success upgrades only
  for a **proven** run class; the old boolean survives only as `legacy_reported_success`.
- **scope separation** — a `no_benefit` in scope `qtt` never leaks to scope `other`.
- **two highly-correlated variants** — same model + shared confounder → `strength="none"`; two
  independent variants → `limited`; a success in the mix → `none` (inconsistent).
- **multi-affinity methods** — independent failures roll up per affinity; a move touched by only
  one variant is never condemned.

---

## Gate

Per the standing instruction, the next steps are **blocked pending explicit approval**:

- **No** change to the protected `desi_layer9` core (adding `METHOD_TRIAL_RECORDED` recording and
  `core.method_trial_events()`).
- **No** lock regeneration (`python -m joni.autonomy lock`).
- **No** Kevin consumer wired to `BlindSpotProposal`.

Mandated order once approved: schema + validation → Layer-9 event recording → projector →
trial-writer → real test runs → DESi comparison → Kevin consumer.
