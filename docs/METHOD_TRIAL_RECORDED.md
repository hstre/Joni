# Specification — `METHOD_TRIAL_RECORDED` (immutable, scope-bound trial event)

**Status:** PROPOSAL — review round 3 (conditionally approved for controlled core integration
after these changes). **No core change, no lock regeneration, no Kevin connection has been
made.** This document plus `src/joni/autonomy/trial_event_schema.py` and its tests
`tests/test_trial_event_schema.py` are a design artifact. The protected `desi_layer9` core is
untouched.

**Schema version:** `method_trial_recorded_v3`

### What changed in v3 — the last three corrections

The review accepted v2 in substance and asked for three final changes, all of the same kind:
*metadata must not silently become evidence.*

1. **A legacy success is upgraded only against a verifiable artifact, never a run-id.** A run-id
   is an identifier, not a proof. Even `kevin-real` stays `not_evaluated` unless a
   `legacy_validation` block (protocol id + artifact hash + evaluator + confirmed provenance,
   `verification_status="verified"`) is present (§4).
2. **Affinity attribution requires a *versioned independence policy*, not `distinct models OR
   implementations`.** Two thin wrappers over the same model/data are not independent however many
   runs they produce (§5).
3. **The epistemic verdict leaves the generic validator.** The schema validator checks *structure*
   and *allowed combinations* only; a registered, versioned `decision_rule_id` + `decision_rule_hash`
   (a Rule-Evaluator) decides whether the measurement justifies the verdict. An unknown or
   non-reproducible hash blocks a trustworthy verdict (§3b).

Carried over from v1/v2: three orthogonal status axes; a technical failure carries no
methodological signal; trials bound to `method_variant × target × scope`, never to an affinity;
conservative legacy handling (old `success=false` → `not_evaluated`, never `no_benefit`).

---

## 0. Why this exists (the measured finding)

The read-only projector run against the **real** Joni Layer-9 history (2156 ledger events, 7 open
conflicts, 20 methods) found `method_trials = 0`, `attempted_affinities = unknown`. Layer 9 records
only global `Method.success_count`/`failure_count` + a `run_id` — *that* a trial happened, not what
it meant, on which conflict, in which scope, with which variant. Without that, DESi degrades to a
static conflict-kind table. This event fixes capture at the source so a local negative can never
become a global demotion, and a technical failure can never pose as a scientific negative.

### Status model (three axes + cause)

| axis | question | values |
|---|---|---|
| `execution_status` | did it **run** to completion? | `completed`, `failed`, `cancelled` |
| `protocol_status` | was the **protocol** valid? | `valid`, `invalid`, `unknown` |
| `failure_kind` | *if* it failed, why? | `none`, `technical`, `timeout`, `parser`, `model`, `dependency`, `infrastructure` |
| `epistemic_result` | what did a **completed, valid** run show? | `success`, `partial_success`, `no_benefit`, `harmful`, `inconclusive`, `not_evaluated` |

Only a `completed` + `valid` run can carry a real result. A technical failure is
`execution_status="failed"` + `failure_kind="technical"` → `not_evaluated`. The trial binds to
`(method_id, method_version, method_variant)` × `(target_id, scope_id)`; `affinities` only records
which thinking-moves the variant exercised.

---

## 1. Schema (Python + JSON)

Authoritative form: `MethodTrialRecorded` in `trial_event_schema.py`. JSON (`to_dict`), new/changed
v3 blocks marked:

```json
{
  "schema_version": "method_trial_recorded_v3",
  "event_type": "METHOD_TRIAL_RECORDED",
  "trial_id": "...", "timestamp": "ISO-8601 UTC", "ledger_tick": 0,

  "target_type": "conflict | open_question | evidence_gap",
  "target_id": "...", "claim_ids": ["..."],
  "scope_id": "... ('unknown' explicitly)", "scope_description": "...",

  "method_id": "...", "method_version": 1, "method_variant": "...",
  "implementation_id": "...",                          // (v2) implementation lineage
  "affinities": ["causal"],

  "task_set_id": "...", "task_sample_id": "...",        // (v3) sample/split, for independence
  "baseline_id": "...", "evaluator_id": "...",
  "estimand": {"outcome_metric": "...", "contrast": "intervention_minus_baseline",
               "direction": "higher_is_better | lower_is_better",
               "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},

  "model": "...", "model_family": "...",                // (v3) coarser, for independence
  "sampling": {"temperature": 0, "seed": 7},

  "execution_status": "completed | failed | cancelled",
  "protocol_status": "valid | invalid | unknown",
  "failure_kind": "none | technical | timeout | parser | model | dependency | infrastructure",
  "epistemic_result": "success | partial_success | no_benefit | harmful | inconclusive | not_evaluated",

  "measurement": {"metric_name": "... | null", "baseline_value": 0.0, "intervention_value": 0.0,
                  "effect_size": 0.0, "uncertainty": 0.0},   // effect_size ORIENTED positive==better

  "decision": {                                          // (v3) the applied, reproducible verdict
    "decision_rule_id": "rule_v2", "decision_rule_hash": "sha256:...",
    "verdict": "no_benefit", "effect_size": 0.045,
    "confidence_interval": [0.01, 0.08], "minimum_effect": 0.10
  },

  "run_id": "...", "artifact_ids": ["..."],
  "attribution_level": "variant | method", "attribution_strength": "none", "confounders": ["..."],

  "legacy": false, "legacy_reported_success": false,
  "legacy_validation": null,                             // (v3) or a VERIFIED artifact block (§4)
  "note": "...", "field_sources": {"<path>": {"source": "...", "confidence": "direct|derived|unknown"}}
}
```

The `decision` block holds the inputs and the verdict the rule produced; `estimand` holds the
*pre-registered* design. The validator checks they are consistent in **structure**; the
Rule-Evaluator checks the verdict is justified.

---

## 2. Example events

Five complete events (success, failed/technical, no_benefit, harmful, completed-but-invalid) are
exercised verbatim in the tests, each with its `estimand` and `decision` block. Representative
`no_benefit` body (decision-rule verdict, minimum effect not met):

```json
{
  "target_type": "conflict", "target_id": "X17", "claim_ids": ["C-7"], "scope_id": "qtt",
  "method_id": "m_causal", "method_variant": "causal-chain-v2b", "implementation_id": "impl-B",
  "task_sample_id": "ts1", "evaluator_id": "ev1", "model": "deepseek-chat", "model_family": "deepseek",
  "affinities": ["causal"],
  "estimand": {"outcome_metric": "misclass_rate", "direction": "lower_is_better",
               "minimum_effect": 0.10, "decision_rule_id": "rule_v2"},
  "execution_status": "completed", "protocol_status": "valid", "failure_kind": "none",
  "epistemic_result": "no_benefit",
  "measurement": {"metric_name": "misclass_rate", "baseline_value": 0.40, "intervention_value": 0.355,
                  "effect_size": 0.045, "uncertainty": 0.02},
  "decision": {"decision_rule_id": "rule_v2", "decision_rule_hash": "sha256:...",
               "verdict": "no_benefit", "effect_size": 0.045, "confidence_interval": [0.01, 0.08],
               "minimum_effect": 0.10},
  "attribution_level": "variant", "attribution_strength": "none", "legacy": false
}
```

---

## 3. Validation rules (STRUCTURE + allowed combinations only)

`validate(ev) -> list[str]`:

- **R1:** `execution_status != "completed"` ⇒ `epistemic_result == "not_evaluated"`.
- **R1b:** `failed` ⇔ a `failure_kind != "none"`.
- **R2:** `protocol_status == "invalid"` ⇒ `not_evaluated`; `unknown` ⇒ no real result.
- **R3:** a real result ⇒ `completed` + `valid` (legacy exempt — see §4).
- **R4:** a real result ⇒ a measurement (`metric_name` + baseline + intervention) (legacy exempt).
- **R5 (decision STRUCTURE):** a real result ⇒ a `decision` with a non-empty `decision_rule_id`
  **and** `decision_rule_hash`, `decision.verdict == epistemic_result`, and
  `decision.decision_rule_id == estimand.decision_rule_id`. **No statistics formula here.**
- **R6:** raw events carry `attribution_level ∈ {variant, method}` and `attribution_strength ==
  "none"` (affinity strength is earned only by aggregation).
- **R7 (legacy):** a `legacy` event may carry only `success` or `not_evaluated`; a legacy
  `success` requires a **verified** `legacy_validation` (§4).
- **R8 (structural):** `trial_id`; `conflict` ⇒ `claim_ids`; `scope_id` and `method_variant`
  non-empty; `completed`+`valid`+`not_evaluated` ⇒ a `note`.

## 3b. Rule-Evaluator (the verdict lives here, not in the validator)

The canonical entry is **`evaluate_envelope(envelope, payload, registry=DEFAULT_RULE_REGISTRY)`**.
Routing comes from a **stable evaluation envelope** — *never* the schema-dependent payload field
paths — so a future schema may relocate its routing fields without breaking selection.
`evaluate_payload`/`evaluate_decision` build the v3 envelope via `envelope_for_payload` (the only
place that reads v3 payload paths).

The envelope (`evaluation_envelope_v1`) carries `envelope_version`, `schema_version`, `rule_id`,
`rule_hash`, `claimed_verdict`, `payload_hash` (and optionally `capsule_hash`):

- **unknown `envelope_version` → `"unverifiable"`** (fail-closed routing);
- `payload_hash` must equal the hash of the supplied payload — a payload swapped under the same
  routing → `"unverifiable"`;
- the artifact is selected by `(rule_id, rule_hash)` **from the envelope**; unknown → `"unverifiable"`;
- the envelope's `schema_version` must equal the artifact's — mismatch → `"unverifiable"`;
- **every** component hash (rule, validator, contract interpreter, decoder, projection, **input
  adapter**, **exec-env**, **composite capsule**) is **re-derived from the actual artifact and
  checked** before that component is trusted — any mismatch → `"unverifiable"`;
- then the artifact's **own** byte-pinned decoder (on the payload) → **own** contract interpreter →
  **own** self-contained validator → **own** byte-pinned input adapter → **own** rule; `"verified"`
  only if all pass and the computed verdict equals the envelope's `claimed_verdict`, else
  `"inconsistent"`;
- `"not_applicable"` when there is no real verdict to check.

### The evaluation capsule (envelope + decoder + contract + validator + adapter + rule + loader)

An event is never re-interpreted by *today's* code, and the historical components carry **no live
runtime dependency** — not even the compiler semantics. Each registry entry is an
`EvaluationArtifact` that binds the **whole** evaluation under one version. **Every** hash is
re-derived from the actual (byte-pinned for archived, live for current) component at use:

| field | meaning |
|---|---|
| `rule_id` | logical rule name (`"rule_v2"`) |
| `schema_version` | the schema this artifact decodes; must equal the envelope's `schema_version` |
| `implementation_hash` | sha256 of the **rule** that decides the verdict — the registry key |
| `validator_hash` | sha256 of the **self-contained** cross-block validator, re-derived at use |
| `input_contract_hash` | sha256 of the **executable** contract interpreter, re-derived at use |
| `decoder_hash` | sha256 of the input decoder (**payload** → block dicts), re-derived at use |
| `canonical_input_projection_hash` | sha256 of the **key-schema** the decoder emits, re-checked from the actual decode |
| `input_adapter_hash` | sha256 of the **byte-pinned input adapter** (decoder blocks → rule view) |
| `exec_env_hash` | sha256 of the pinned **execution environment** (future flags, optimize, loader version + hash) |
| `capsule_hash` | composite sha256 over **all** of the above + `schema_version` + `envelope_version` — uniquely addresses the whole capsule |

**Loader / execution environment (a byte-pinned trust root).** The byte-pinned sources are only
meaningful together with the compiler semantics they were validated under. The loader is itself a
**byte-pinned artifact** (`loader_v1.pysrc`): `_resolve_artifact` **bootstraps it from its bytes**
(never the module global) and re-derives `loader_hash` against the artifact before executing any
component, so swapping the live `_exec_callable` cannot change what runs. It compiles with
**explicit numeric future-flag bits** and **`dont_inherit=True`** (the r6 rule's un-imported
annotation loads *only* because the `annotations` flag — value `16777216` — is supplied explicitly).
The artifact records `execution_environment = {language, python_semantics, future_flags (numeric),
future_flag_bits, optimize, loader_version, loader_hash}`; the **runtime Python major.minor is
enforced** to equal `python_semantics`, and the whole numeric environment is folded into
`exec_env_hash` and `capsule_hash`. A swapped loader, tampered loader bytes, a changed numeric flag,
or a wrong Python version → `"unverifiable"`.

**Stored evaluation envelope (replay uses it, not a live bridge).** `MethodTrialRecorded.to_journal()`
embeds the stable envelope alongside the payload as the canonical **stored** form; replay
(`evaluate_payload`) reads the **embedded** envelope and never the live `envelope_for_payload`
(which is writer-side only). `payload_hash` binds the payload, so a post-write tamper →
`"unverifiable"`. Evidence comes straight from the stored `(envelope, payload)` pair via
`verify_payloads` → `aggregate`; no current dataclass reconstruction is a precondition for
aggregation (dataclasses stay display-only).

**Input adapter.** The transform from the decoder's block dicts to the read-only object view the rule
consumes (`build_view`) is its own **byte-pinned** artifact (`view_adapter_v1.pysrc`), hashed into
the capsule — no un-attested live transform sits between decoder and rule.

The historical components are **self-contained**, so no live helper can silently change a historical
result:

- the **validator** snapshot carries its own `_finite`/`_ci_errors`/`_EPS` and imports — `_exec_callable`
  injects **no** epistemically-relevant globals, so `validator_hash` covers the whole executable
  closure;
- the **contract** is an executable `check_contract(meas, dec, est)` interpreter (its *meaning* is
  hashed, not just its data), applied before the validator/rule;
- the **decoder** maps the **raw payload** to the canonical blocks and is the only input path — the
  rule and validator see the decoder's output, never the live event object;
- the **rule** decides from a read-only view built **only** from the decoder output.

`DEFAULT_RULE_REGISTRY` is an **append-only, immutable** (`MappingProxyType`) catalog. A changed
rule (or a tightened validator/contract/decoder) is **added** as a new artifact; an existing key is
never overwritten (`build_rule_registry` raises on a duplicate key). Two artifact flavours:

- **live** (`make_live_artifact`) — bound to the current in-process functions; hashes track source.
- **archived** (`make_archived_artifact`) — the rule, validator, contract **and** decoder are all
  **byte-pinned, self-contained verbatim source** (under `joni/autonomy/rule_artifacts/`). The
  `implementation_hash` is the sha256 of the exact stored rule bytes — the **real prior-release
  hash**, *not* one recomputed from a re-typed copy. A pinned `expected_rule_hash` is enforced at
  construction, and every component hash is re-derived from its bytes at every use, so a forged
  artifact (claimed hash, different code/contract/decoder/validator) is rejected before its code is
  trusted. The production catalog ships the archived r6 capsule (rule `sha256:2438455f…` +
  byte-pinned self-contained validator, contract and decoder snapshots) alongside the current live
  `rule_v2`; an event recorded under the r6 hash is forever evaluated by the r6 rule **and** its r6
  validator/contract/decoder, and is never re-scored by the current components.

The reference rule `rule_v2` (hashed by `RULE_V2_HASH`) is one registered implementation: oriented
`effect_size` with a confidence interval — `harmful` if `eff ≤ −minimum_effect`; `success` if
`eff ≥ minimum_effect` and the CI lower bound is positive; `no_benefit` if the CI excludes 0 but
`|eff| < minimum_effect`; else `inconclusive`. A clearly-resolved **negative** effect under
`higher_is_better` is `harmful`, **not** `no_benefit` — and the evaluator flags an event that
claims otherwise. Different metrics/uncertainty conventions are handled by registering different
rules, never by changing the generic schema.

---

## 4. Legacy migration — a verified artifact, never a run-id

`migrate_method(method, *, resolve_legacy_validation=None)`:

Verified against the old writers: the dominant writer (kevin `trial_runner.trial_methods`) sets
`success` from a synthetic structural-overlap heuristic it tags *"a simulation, not an effectiveness
measurement"*; only `real_trial.run_real_trial` has measured semantics, and its full result lives in
a separate artifact. So:

- **old `success=true` → `not_evaluated`** + `legacy_reported_success=true`, **by default**.
- It becomes a **weak `success`** only if `resolve_legacy_validation(run_id)` returns a
  `LegacyValidation` with `verification_status="verified"` **and** `artifact_hash` **and**
  `protocol_id` **and** `evaluator_id`. The verified block is attached to the event. A run-id
  string — including `kevin-real` — never suffices on its own; `validate` rejects a legacy
  `success` without a verified block.
- **old `success=false` → `not_evaluated`** (never `no_benefit`).

---

## 5. Aggregation & attribution (versioned independence policy)

**The verification boundary is mandatory.** Raw events are NOT aggregated directly — the only path
is `verify_events(events) -> [VerifiedTrialEvidence]` (re-runs the registered rule; verified-only),
then `aggregate(evidence) -> [VariantScopeOutcome]`, then `attribute_to_affinity(outcomes, *,
policy)`. `aggregate` rejects raw events (`TypeError`) and **re-attests** each evidence object
(verdict ↔ event, attestation re-bind, and re-verify), so a substituted event is rejected. There is
**no** `aggregate(events)` shortcut.

1. Roll up per `(target, scope, method, variant)` over VERIFIED evidence; `harmful` dominates, then
   `success`, `no_benefit`, `inconclusive`; success + harmful in one cell → `conflicting`.
2. **Affinity attribution requires an `IndependencePolicy` to be satisfied** — not a count, not an
   `OR`. `independence_policy_v1` (all requirements ON) demands: ≥2 distinct variants; distinct
   implementations; distinct model **families**; independent task samples; independent evaluator;
   and **no shared confounder** (fail-closed on unknowns). Two thin wrappers over the same
   model/data/judge → `strength="none"`. Any success in the evidence → `"none"` (inconsistent).
3. Strengths: policy-satisfied with ≥3 variants → `supported`; with 2 → `limited`; else `none`.
4. Scopes never leak; a success elsewhere is a separate promising-transfer signal.

Mapping to DESi (`to_desi_method_trials`): `conflicting → inconclusive`, others pass through.
**Technical failures never reach this path**: `verify_events` admits only rule-evaluable verdicts,
so a `technical_only` cell can no longer arise here. Technical / `not_evaluated` runs travel a
**separate** non-epistemic channel — `operational_observations(events)` — classified
(`technical_failure` / `unevaluated` / `cancelled` / `protocol_invalid`) and **never** producing
attribution.

---

## 6. Updated projector design

The live projector stays honest today (`method_trials = unknown`, no fabrication). Forward path,
gated on the core emitting events:

```
events    = core.method_trial_events()        # NEW core read (after approval)
evidence  = verify_events(events)             # rule-verified ONLY (the mandatory boundary)
outcomes  = aggregate(evidence)               # raw events are refused
snapshot.method_trials       = to_desi_method_trials(outcomes)        # DIRECT signal
snapshot.operational_signals = operational_observations(events)       # non-epistemic, separate
# attempted_affinities = affinities with any verified event -> direct
```

Events present → `direct`; absent → `unknown`. Legacy migration is optional and flagged; with no
verified artifacts it contributes only `not_evaluated`. `verify_events`/`aggregate`/
`to_desi_method_trials`/`evaluate_decision`/`attribute_to_affinity`/`operational_observations` are
implemented and tested now; only `core.method_trial_events()` needs a core change, deferred to
explicit approval. (`to_desi_method_trials` imports DESi lazily and is exercised only in the
optional integration test — the base suite passes without the `desi` extra installed.)

---

## 7. Tests

`tests/test_trial_event_schema.py` (20 tests, all passing, ruff-clean; full Joni suite green)
covers, beyond the v2 set, the five new review cases:

- **`kevin-real` without an artifact stays `not_evaluated`**; an **unverified** legacy `success`
  is rejected by `validate`.
- a **verified** artifact allows only a *weak* legacy `success`.
- **two insufficiently-independent variants** (same family/impl/sample/judge or shared confounder)
  → **no** affinity attribution; two independent variants → `limited`; the policy is **configurable
  and versioned** (a relaxed policy is shown changing the outcome).
- a **clearly-resolved negative effect** under `higher_is_better` is judged **`harmful`, not
  `no_benefit`**, by the rule evaluator (and an event claiming `no_benefit` is flagged inconsistent).
- an **unknown decision-rule hash** yields `"unverifiable"` — structurally valid, but no
  trustworthy verdict.

---

## Gate

Conditionally approved for **controlled core integration after** the v3 changes above — which are
now implemented. Still **blocked pending explicit go-ahead**:

- **No** change to the protected `desi_layer9` core.
- **No** lock regeneration.
- **No** Kevin consumer wired to `BlindSpotProposal`.

Mandated order once approved: **append-only event recording → replay/migration test → projector →
writer → real trials → DESi comparison → Kevin consumer.**
