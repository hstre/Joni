# Layer-9 baseline candidate — review package

**Status:** REVIEW PACKAGE. **No `layer9_kernel_lock` is created.** The manifest may be generated
**only after** the user explicitly designates a commit as the human-reviewed baseline. The writer
stays locked until then.

## Identity

| | |
|---|---|
| **Baseline candidate (code)** | `b0c5b34` (review round 11) |
| **Superseded candidates** | `37e5206` (r10) · `41bc8a4` (r9) · `60a77c9` (r8) · `b91a80f` (r7) · `7810e25` (r6) · `e5cf6ca` (r5) · `1b1e6bf` (r4) · `dfb7d75` (r3) · `c5fdd9a` (r2) · `61118b3` (r1) — all *rejected pending fixes* by independent review |
| **Last accepted Layer-9 state (base)** | `282d541` (`Schema v3: …proposal-only`) — no kernel change up to here |
| **Branch** | `claude/kevin-creativity-architecture-ukz17g` |

Full diff to review:

```
git diff 282d541 b0c5b34 -- src/desi_layer9 \
  src/joni/autonomy/trial_event_projector.py src/joni/autonomy/trial_event_schema.py \
  src/joni/autonomy/rule_artifacts
```

Adding this governance doc changes **no** kernel/projector/test file, so the kernel+projector tree
is byte-identical at `b0c5b34` and at this doc's commit.

> **The base test suite is now self-sufficient:** it passes with the optional `desi` extra
> **blocked** (535 passed, 7 skipped, 0 failed) — the DESi mapping is an optional integration test
> (`importorskip`). Pinning the DESi extra to a commit SHA remains a `dependency_manifest` TODO.
>
> **A full repository archive is shipped this round** (`git archive b0c5b34`): `pytest -q` and
> `ruff check .` run from the extracted tree with **no** manual `PYTHONPATH` (pyproject sets
> `pythonpath = ["src"]`). The focused review subset is provided additionally.

### Review round 11 — validator, input-contract and schema/decoder are CAUSALLY bound (vs `37e5206`)

1. **Validator hash is re-derived and checked before the validator is trusted.** `_resolve_artifact`
   recomputes the validator hash from the actual (byte-pinned for archived, live for current)
   validator; `evaluate_decision` rejects a mismatch as `unverifiable` **before** running it. The
   attack *real rule bytes + copied `validator_hash` 9b4a64c1… + manipulated validator bytes
   2cc80f77… returning `[]`* now returns `unverifiable`, not `verified`.
2. **Input contract is hash-checked AND applied.** The byte-pinned canonical-JSON contract's hash is
   re-derived at use (stale/forged → `unverifiable`); `_apply_input_contract` enforces
   `require_effect` / `require_confidence_interval` / `required_measurement_fields` before
   validator+rule (unmet → `inconsistent`). The production r6 artifact carries the **real** historical
   contract `{require_effect, require_confidence_interval}`, not `{}`.
3. **`schema_version` + input decoder are operative.** `MethodTrialRecorded` carries a recorded
   `schema_version`; `evaluate_decision` refuses an artifact whose `schema_version` ≠ the event's
   (→ `unverifiable`). The input projection is a versioned, hashed decoder (`_decode_v3`, byte-pinned
   `decode_v3.pysrc`); `decoder_hash` and `canonical_input_projection_hash` are re-derived at use and
   the artifact's **own** decoder builds the blocks — `_blocks()` no longer silently applies today's
   field semantics to old events.

New byte-pinned artifacts: `decode_v3.pysrc` (`sha256:5b85b74f…`), `rule_v2_r6.contract.json`
(`sha256:92c77200…`). New tests (round 11, 11 tests): validator-bytes swap with copied hash →
`unverifiable`; live validator hash re-attested each use; contract swap with stale hash →
`unverifiable`; contract actually applied; real r6 contract requires effect+CI; a new artifact may
carry a stricter contract while the old event stays under its own; schema-version mismatch →
`unverifiable`; decoder-bytes swap with copied hash → `unverifiable`; production r6 artifact binds
decoder+contract+validator.

### Review round 10 — historical evaluation is byte-pinned (rule + validator + contract) (vs `41bc8a4`)

1. **Real immutable rule artifact** — the archived `rule_v2@r6` is the **verbatim source bytes**
   from prior release `7810e25`, stored under `src/joni/autonomy/rule_artifacts/rule_v2_r6.pysrc`.
   Its `implementation_hash` is the sha256 of those exact bytes —
   `sha256:2438455fd5dde3db1bb401efaccd7f13bf5fa4dd6cf6cb052b2dce2e390e05a4`, the **real published
   hash**, never recomputed from a re-typed copy. `make_archived_artifact` enforces a pinned
   `expected_rule_hash` and re-derives the hash from the bytes at every use.
2. **Versioned `EvaluationArtifact` binds validator + input contract** — `rule_id`,
   `schema_version`, `implementation_hash`, `validator_hash`, `input_contract_hash`. Historical
   evaluation runs the artifact's **own** (byte-pinned) validator + input contract, not the current
   one; the r6 rule ships with the byte-pinned validator snapshot it was decided under
   (`cross_block_v1.pysrc`, `sha256:9b4a64c1…`). An old event is never re-interpreted under a
   tightened current validator or a newer rule.
3. **Append-only, immutable catalog** — `build_rule_registry` keys on
   `(rule_id, implementation_hash)`, refuses to overwrite a key, returns a `MappingProxyType`; a
   changed rule/validator is **added** as a new artifact.

New tests: archived r6 hash equals the literal prior-release hash and is derived from the stored
bytes; a copy with a mismatched `expected_rule_hash` is rejected; the full mandated flow (fix real
hash → event under that hash → verify under new software → append a new version → old event still
verifiable); the historical artifact binds its **own** validator (an old event stays verified under
the lenient archived validator while the same event under the tightened current version is
`inconsistent`); historical artifacts are byte-identical and append-only.

### Review round 9 — DESi-independent suite + operational classes + real rule catalog (vs `60a77c9`)

1. **Base suite is DESi-independent** — the one DESi-mapping test `importorskip`s the extra; the
   suite is green with `desi` blocked.
2. **Operational classification** — `_operational_class`: `failed → technical_failure`,
   `cancelled → cancelled`, `invalid protocol → protocol_invalid`,
   `completed+valid+not_evaluated → unevaluated`, else `unknown_operational`; none feed attribution.
3. **Real append-only catalog** — `DEFAULT_RULE_REGISTRY` keeps an archived frozen version
   (`_rule_v2_archived_r6`) alongside the current rule; an old event verifies under its archived
   version via the production registry and is never re-interpreted under the current one.
4. **Docs corrected** — `METHOD_TRIAL_RECORDED.md` now documents
   `verify_events → VerifiedTrialEvidence → aggregate` and the separate `operational_observations`.

### Review round 8 — evidence re-attestation + inconclusive + historical rules + operational (vs `b91a80f`)

1. **Evidence is re-attested, not token-trusted** — `VerifiedTrialEvidence` carries an `attestation`
   binding the verdict to the canonical event; `aggregate` requires `verdict ==
   event.epistemic_result`, the attestation to re-bind to the current event, **and** the event to
   re-verify under the rule, so a `dataclasses.replace` substitution raises `ValueError`.
2. **`inconclusive` is rule-verifiable** — new `RULE_EVALUABLE_RESULTS` (incl. `inconclusive`,
   excl. `not_evaluated`); it verifies, aggregates, maps to DESi `inconclusive`, but yields no
   affinity demotion/promotion.
3. **Historical rule versions preserved** — `build_rule_registry` is append-only/immutable, keyed by
   `(rule_id, implementation_hash)`; an old event verifies under its archived implementation and is
   never re-interpreted under a newer one.
4. **Operational channel** — `OperationalTrialObservation` / `operational_observations` carry
   technical-failure / `not_evaluated` facts for DESi (mapped to `technical_failure`) **without**
   producing attribution.

### Review round 7 — no aggregation bypass + rule input contract + equivalence (vs `7810e25`)

1. **Typed verification boundary** — raw events become aggregable evidence only via `verify_events`
   (re-runs the rule, verified-only) which emits a token-guarded `VerifiedTrialEvidence`; `aggregate`
   accepts only that (raw events raise `TypeError`), so `attribute_to_affinity`/`to_desi_method_trials`
   cannot translate an unverified claim into epistemic weight.
2. **Gate input contract** — `RULE_INPUT_CONTRACTS`: a real verdict under `rule_v2` requires
   `measurement.effect_size` **and** `confidence_interval`; the journal never holds a
   `success`/`harmful`/`no_benefit` with no statistical basis.
3. **`no_benefit` is equivalence** — CI entirely within `(−min, +min)` (zero may be included); a
   precise null is `no_benefit`, not weaker than a small positive effect.
4. **`uncertainty` is uninterpreted** — `rule_v2` ignores it; the gate no longer cross-checks it
   against the CI (no scientifically-undefined inequality).

### Review round 6 — implementation-bound verification + statistical contract (vs `e5cf6ca`)

1. **The rule hash binds to the executed function** — `evaluate_decision` re-derives
   `sha256(source of entry.fn)` on every use and requires re-derived == claimed
   `implementation_hash` == event `decision_rule_hash`; a forged registry function that merely
   copies the correct hash is `unverifiable`. `make_rule_entry` computes the hash from the function;
   `DEFAULT_RULE_REGISTRY` is immutable (`MappingProxyType`).
2. **`success`/`harmful` require the minimum effect to be statistically supported** —
   `ci_low ≥ min` / `ci_high ≤ −min`. A positive interval spanning below the threshold (e.g.
   `[0.001, 0.219]`, `min 0.10`) is `inconclusive`, not a verified success.
3. **`uncertainty` / `partial_success` contracts fixed** — `rule_v2` uses only the CI (documented);
   the gate rejects an `uncertainty` exceeding the CI width; `partial_success` is documented as not
   producible by `rule_v2`.

### Review round 5 — `verified` bound to the observation (vs `1b1e6bf`)

The decision could no longer invent its effect, but could still bring its own interval, and a bare
point estimate could verify as success. Now the verdict is computed **entirely from the
measurement**:

1. **Resolution required** — `_rule_v2` reads effect, uncertainty **and** the confidence interval
   from the measurement; `success`/`harmful` need the interval to resolve the direction beyond zero
   (a `0.20 ± 100` point estimate with no interval is `inconclusive`).
2. **The interval belongs to the measurement** — `confidence_interval` moved to `Measurement`; a
   decision-supplied or diverging interval is rejected/`inconsistent`; the decision is reduced to
   `{rule_id, rule_hash, verdict}`.
3. **Measurement internal consistency** — the effect must be derivable from baseline/intervention
   under the estimand contrast/direction (or carry an `effect_derivation` id+hash) and lie within
   its own interval.
4. **Rule hash binds to the implementation** — `RULE_V2_HASH = sha256(source of _rule_v2)`; a
   `RuleEntry` carries spec+impl hashes; an implementation-hash mismatch is `unverifiable`, so a
   code change rotates the hash and old events stay bound to their version.

### Review round 4 — verification source fixed (vs `dfb7d75`)

`verified` previously meant the decision block agreed with *itself*. Now it means the **stored
measurement** (against the **pre-registered estimand**) justifies the verdict:

1. **Decision may not contradict the measurement** — `_rule_v2` computes from
   `measurement.effect_size`; `cross_block_consistency` requires `decision.effect_size ==
   measurement.effect_size` and `measurement.metric_name == estimand.outcome_metric`; a
   contradiction is `inconsistent`, never `verified`.
2. **Decision may not override the pre-registered threshold** — the rule uses only
   `estimand.minimum_effect`; `decision.minimum_effect` must equal it.
3. **Numeric/interval invariants** — `confidence_interval` lower ≤ upper, no NaN/Infinity,
   `uncertainty ≥ 0`, `minimum_effect > 0` for real verdicts.

The one canonical `cross_block_consistency` lives in `desi_layer9.trial_event_validation` and is
reused by the gate **and** the rule evaluator (side-finding addressed — no divergent copies).

### Review round 3 — three more blockers fixed (vs `c5fdd9a`)

1. **Unknown ≠ independence (fail-closed)** — every independence dimension must be *known* for all
   compared variants; an unknown/missing implementation/model-family/task-sample/evaluator makes
   the dimension non-distinct (`independence metadata incomplete`). The v3 gate additionally
   requires these provenance fields for evaluable real verdicts.
2. **Crash-proof projector** — the gate type-checks every field the projector casts
   (`method_version`, `ledger_tick`, `confidence_interval`, numeric measurement/decision fields,
   `affinities`); `_project_event` wraps reconstruction so a malformed payload becomes
   `projection_status=invalid_payload` (weight none), never an uncaught crash, and one bad event
   cannot stop the others.
3. **Mixed success+harmful** — a cell with both is `conflicting` (success + harmful preserved); any
   success in the evidence blocks a negative affinity demotion; pure-harmful stays demotable.

### Review round 2 — three blockers fixed (vs `61118b3`)

1. **Scope-bound sufficiency** — `_dataset_sufficiency` groups by `(target_id, scope_id)`; two
   variants in different scopes of one conflict no longer jointly satisfy; ready
   `(conflict, scope)` pairs are listed in `analysis_ready_conflict_scopes`.
2. **Real independence** — `_profile` flags any implementation / model-family / task-sample /
   evaluator / confounder shared by ≥2 variants (overlap detection), replacing the
   `len(union) ≥ n` false positive.
3. **Full v3 gate** — `validate_trial_payload` validates the complete v3 structure (scope, method/
   variant, estimand, measurement, decision block, model/evaluator/baseline provenance, types,
   forbidden combinations) so `schema_version=v3` guarantees v3 structure before the irreversible
   journal; still no statistics/verdict in the core; unknown extra fields consciously allowed.

Tests added: same-conflict-two-scopes → insufficient; same-scope-two-independent → sufficient +
ready pair exposed; partial-overlap & fully-shared deps → not independent; disjoint → independent;
minimal v3 rejected; full v3 accepted; unknown extra field allowed+preserved; real verdict without
`decision_rule_hash` rejected; `not_evaluated` stored without measurement values.

## Changed kernel files (vs `282d541`) — 7 files, +189 / −4

| file | change | why |
|---|---|---|
| `enums.py` | `Operator.METHOD_TRIAL_RECORDED`, `ObjectType.METHOD_TRIAL_EVENT` | a new operator + immutable record type, additive; legacy operator untouched |
| `ids.py` | `MTE` id prefix | deterministic ids for the new record |
| `objects.py` | `MethodTrialEvent` dataclass | immutable record: canonical-JSON payload, `record_authority` vs `epistemic_authority` |
| `transitions.py` | `METHOD_TRIAL_EVENT → _IMMUTABLE_RECORD` | registered transitionless (append-only) |
| `trial_event_validation.py` (new) | structural gate validator + `canonical_payload` | one supported schema version; unknown → reject; canonicalisation |
| `core.py` | `_h_method_trial_recorded`, `method_trial_events()`, `trial_event_hashes()`, optional 4-tuple handler return | append-only handler (idempotent on `trial_id`, mutates **no** counter), read-only envelope, named hashes, auditable idempotent-retry decision tag |
| `__init__.py` | export `MethodTrialEvent` | package surface |

**Unchanged on purpose:** `_h_method_trial_record` and the legacy counters, `_h_method_promote`,
`policy.py`, `hashing.py`, `ledger.py`, `persistence.py`. The new path is **inert**: nothing in
promotion/discard reads it.

## Projector / schema (outside the kernel)

| file | role |
|---|---|
| `src/joni/autonomy/trial_event_projector.py` (new, 259 ln) | read-only projection of `method_trial_events()`; three separated axes; versioned sufficiency; `measured_candidate` semantics |
| `src/joni/autonomy/trial_event_schema.py` | the v3 schema, decision rule-evaluator, independence policy (already accepted) |

## Tests and the contract each secures

**`tests/test_method_trial_event_recording.py`** (append-only recording)
- append / read deep-copy isolation (nested + original ref) → *the record is immutable & verbatim*;
- idempotent retry / divergent-id conflict → *no duplicate evidence from retries; retry is audited
  as `idempotent_existing`*;
- unknown schema / structural reject → *fail-closed at the gate*;
- inertness vs counters & promotion; legacy coexistence → *no second decision-making truth*;
- replay-identical; tamper detectable; transitionless;
- `payload_hash` vs `record_object_hash`; one shared `object_canonical` serializer (identity +
  patch) → *no drift-prone parallel field list*.

**`tests/test_trial_event_replay_coexistence.py`** (replay / coexistence / uniqueness)
- legacy-only / new-only / mixed journals replay to identical snapshot hashes → *the two worlds
  never touch*;
- new software replays old journals; unknown operator fails closed at load; known-but-unhandled
  rejected in gate → *forward/back compatibility is explicit*;
- idempotency / divergent-id survive save/load;
- serial-model uniqueness + a BOUNDARY test that forced reentrancy double-mints → *uniqueness is
  per-instance, depends on serial submit*.

**`tests/test_trial_event_projector.py`** (projection)
- unknown rule hash → registered / usable / unverifiable / weight none, visible (mandatory);
- single verified success stays INSUFFICIENT; other-scope events don't satisfy the target;
- verified = `measured_candidate`, `epistemic_authority none`;
- ≥2 independent verified variants → `SUFFICIENT_FOR_GAP_ANALYSIS`;
- **sufficiency from independent `no_benefit` + `harmful`** (not only successes), scope-bound
  attribution, no global demotion, no epistemic confirmation;
- unsupported schema visible; adding a 2nd independent trial flips sufficiency traceably;
  determinism.

**`tests/test_trial_event_schema.py`** (already accepted) — v3 schema validation, rule evaluator,
independence policy.

Full suite at `b0c5b34`: **542 passed / 2 skipped with the `desi` extra; 535 passed / 7 skipped with
`desi` BLOCKED (0 failed); ruff clean.**

## Known technical debt

- **TD-1** — variable 3-/4-tuple handler return contract in `submit`; proposed typed
  `HandlerResult` later. No behavioural change intended. (`docs/TECH_DEBT.md`)
- **TD-2** — `trial_id` uniqueness is enforced by a pre-mint lookup, correct **only** under the
  serial single-writer model; a multi-writer store would need a storage-level atomic unique
  constraint.

## Operating invariants (must hold before the writer starts)

```yaml
concurrency_model:
  writer_mode: single_process_single_writer
  trial_id_uniqueness_scope: layer9_instance     # NOT global
  multi_writer_safe: false
journal_compatibility:
  backward_readable: true                         # new code, old journal
  forward_readable: false                         # old code, new journal
  failure_mode: fail_closed_at_load
  downgrade_after_first_new_event: blocked        # IRREVERSIBLE
```

The first production `METHOD_TRIAL_RECORDED` event crosses the irreversible downgrade boundary —
which is exactly why the writer must wait until this baseline is designated and locked.

## Protection-zone status at this candidate

```yaml
runtime_lock:        { status: passed,  scope: joni_runtime }      # src/joni/* unchanged here
layer9_kernel_lock:  { status: absent,  scope: epistemic_kernel }  # NOT yet created (this package)
dependency_manifest: { status: absent }                            # spec only (PROTECTION_ZONES.md)
```

> **lock passed, but `desi_layer9` is outside the protected manifest** — the green runtime lock does
> not attest the kernel changes in this candidate. That is the whole reason this package exists.

## proves / does_not_prove for this baseline candidate

```yaml
proves:
  - METHOD_TRIAL_RECORDED events are recorded append-only, immutable, canonical, idempotent
  - the new path is inert: legacy counters and method promotion are untouched
  - replay is deterministic and hash-identical; tampering is detectable
  - the projector separates event-usability, rule-verification and dataset-sufficiency
  - registered-but-unverifiable / unsupported-schema evidence stays visible
  - sufficiency requires real conflict+scope coverage and comparative depth (not event count,
    not only successes)
does_not_prove:
  - that desi_layer9 is protected by any lock (it is not, yet)
  - that any trial verdict is epistemically authoritative (verified = measured_candidate only)
  - that DESi adds value over the static baseline (not yet measured)
  - multi-writer safety (single-writer invariant only)
  - that a production writer is safe to enable (downgrade boundary not yet crossed by design)
```

## Designation procedure (human)

1. Review the diff `282d541..b0c5b34` and this package.
2. Explicitly designate a commit as the **human-reviewed Layer-9 baseline**.
3. Only then: implement `layer9_kernel_lock` resolution over `src/desi_layer9` and run the **human**
   `lock` to freeze that commit (per `PROTECTION_ZONES.md`).
4. Only after the lock exists: enable the writer (this crosses the irreversible journal boundary).

Until step 2, **no kernel lock is created and the writer stays locked.**
