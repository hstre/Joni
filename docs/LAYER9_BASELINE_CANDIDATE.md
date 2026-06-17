# Layer-9 baseline candidate — review package

**Status:** REVIEW PACKAGE. **No `layer9_kernel_lock` is created.** The manifest may be generated
**only after** the user explicitly designates a commit as the human-reviewed baseline. The writer
stays locked until then.

## Identity

| | |
|---|---|
| **Baseline candidate (code)** | `8412040` (review round 20) |
| **Superseded candidates** | `5e385a8` (r19) · `6fe3020` (r18) · `d11515a` (r17) · `2d327c3` (r16) · `571cc7b` (r15) · `72a5d5f` (r14) · `c1e0d8e` (r13) · `dddac93` (r12) · `b0c5b34` (r11) · `37e5206` (r10) · `41bc8a4` (r9) · `60a77c9` (r8) · `b91a80f` (r7) · `7810e25` (r6) · `e5cf6ca` (r5) · `1b1e6bf` (r4) · `dfb7d75` (r3) · `c5fdd9a` (r2) · `61118b3` (r1) — all *rejected pending fixes* by independent review |
| **Last accepted Layer-9 state (base)** | `282d541` (`Schema v3: …proposal-only`) — no kernel change up to here |
| **Branch** | `claude/kevin-creativity-architecture-ukz17g` |

Full diff to review:

```
git diff 282d541 8412040 -- src/desi_layer9 \
  src/joni/autonomy/trial_event_projector.py src/joni/autonomy/trial_event_schema.py \
  src/joni/autonomy/rule_artifacts
```

> **The base test suite is now self-sufficient:** it passes with the optional `desi` extra
> **blocked** (604 passed, 7 skipped, 0 failed) — the DESi mapping is an optional integration test
> (`importorskip`). Pinning the DESi extra to a commit SHA remains a `dependency_manifest` TODO.
>
> **A full repository archive is shipped** (`git archive 8412040`): `pytest -q` and `ruff check .`
> run from the extracted tree with **no** manual `PYTHONPATH` (pyproject sets `pythonpath = ["src"]`).
> The focused review subset is provided additionally.

### Review round 20 — the WHOLE public state surface is immutable + an AUTHENTICATED migration trust source (vs `5e385a8`)

Round 19 was rejected on two grounds that proved *"submit is still not the only write path"* and
*"the migration attestation is still a self-declared claim"*. Both fully closed; the r6 rule hash is
unchanged (`sha256:2438455f…`).

1. **`core.objects` no longer exposes internal instances.** It was a `MappingProxyType` over the live
   store — it froze the keys but handed back the **real** objects, so `core.objects[id].status = …`
   or `core.objects[id].payload[…] = …` mutated authoritative state and the snapshot hash. The
   `objects` property now returns a read-only mapping of **deep copies**; integrity hashing reads the
   internal `_objects` directly (no copy).
2. **The ledger is fully encapsulated.** It was a public mutable list (`core.ledger.clear()` wiped the
   audit trail; events were editable). The store is now the internal `_ledger`; the public `ledger`
   property is an **immutable tuple of deep-copied events**; `verify_chain` works on `_ledger`. A
   returned event cannot reach the chain; storage-level corruption is still detected.
3. **The clock and the minter are no longer public write surfaces.** `tick` is a **read-only**
   property over `_tick`; the only clock input is the **monotonic** `set_clock()` (it advances, never
   moves backward — replay determinism), used by the orchestrator's `set_day`. The id minter is
   private `_minter` and `_seq` stays private: no public handle mints ids or shifts the sequence
   outside `submit()`.
4. **The migration trust source is a PINNED, authenticated catalog — not a self-declared field and
   not a caller-supplied function.** The old per-entry `historical_decision` (whose `decision_hash`
   was never checked) and the `historical_verifier=lambda: True` escape hatch are **gone**. A document
   carries a `historical_attestation` whose `verifier_id` SELECTS an entry in the internal
   `_TRUSTED_HISTORICAL_ATTESTATIONS`; migration then checks, fail-closed: the `attestation_hash`
   recomputes **and equals the pinned anchor** (a forged attestation for a different body has a hash
   the caller cannot forge), `source_snapshot_hash` **binds** the document's `snapshot_hash`, and each
   migrated body's canonical hash is in the attested `accepted_entry_hashes` (acceptance is **checked,
   never self-declared**). The migration log records the full attestation chain. A deployment
   populates the catalog with signed historical attestations; the shipped demo anchor is inert (base
   `282d541` has no v3 trial events).

New artifact: none (kernel state-surface encapsulation + a joni-level authenticated trust root).
Round-20 tests (13): mutating an `objects` value / injecting a key does not change state; the ledger
cannot be cleared/mutated externally (chain intact) but storage tampering is still caught; the clock
is read-only + monotonic; there is no public minter; a missing / forged / snapshot-unbound /
tampered / unknown-verifier / self-declared attestation is fail-closed; `load_migrated` takes no
caller-supplied verifier; the pinned attestation migrates and the log documents the attestation
chain; the migration output does not alias its input.

### Review round 19 — TRUE state immutability + a trusted migration source (vs `6fe3020`)

Round 18 was rejected on two grounds: *"a deep copy is not immutability"* — the authoritative state
was still rewritable, because `submit()` stored the caller's **own** Proposal instance (so a
post-submit `proposal.payload[...] = 999` changed the snapshot with no operator/ledger/audit) and the
journal was list-mutable with in-place-rewritable entries — and the migrator *trusted itself*:
`load_migrated()` silently ignored a present `snapshot_hash` (a `sha256:DEADBEEF` document still
migrated) and could not tell a historically-accepted v3 command from a rejected one. Both closed; the
r6 rule hash is unchanged (`sha256:2438455f…`).

1. **`submit()` is now the only writer, and it severs the WHOLE proposal.** The first thing `submit()`
   does is `copy.deepcopy(proposal)`, so Layer 9 never stores the instance the caller still holds; a
   later mutation of the caller's proposal (or its nested payload) cannot change authoritative state.
2. **The journal is structurally immutable.** `JournalEntry` is a **frozen** dataclass that stores
   canonical-JSON **bytes** (`payload_canonical`) and reconstructs the payload on read, so a
   `entry.payload[...] = 777` mutates only a throw-away parsed view and rebinding a field raises. The
   public `journal` is a read-only **tuple** (no `append`/`pop`/`clear`) and `objects` is a read-only
   `MappingProxyType`; `get()`/`all()` return independent deep copies. The trial record itself stores
   its payload as an immutable canonical string.
3. **Migration is bound to a trusted historical source (fail-closed).** `load_migrated(doc)` no longer
   ignores a present `snapshot_hash`: if the document carries one, a passing
   `historical_verifier(doc)` is **mandatory**, otherwise the load is refused (the `DEADBEEF`
   document is rejected). `migrate_journal_entries` requires a per-entry `historical_decision`
   attestation (`accepted` + `gate_policy_version`): an **unattested** v3 command fails closed, a
   command attested as historically **rejected** is **dropped** (never resealed as accepted v4), and an
   unknown capsule still fails closed. The migration log documents the trusted source
   (`gate_policy_version`) and the capsule it bound to.
4. **Migration output no longer aliases its input** (the secondary r18 blocker): the input payload is
   deep-copied before sealing and the sealed body is re-copied, so mutating the input after migration
   cannot reach into the migrated output (or vice versa).

New artifact: none (kernel journal/immutability + the joni-level migration loader). Round-19 tests
(11): the six mandatory immutability vectors — original-proposal mutation, `get()`-result mutation,
`all()`-result mutation, in-place journal-payload mutation, journal-list mutation, and that snapshot +
ledger chain + a fresh replay stay identical after every vector — plus: a present `snapshot_hash` is
refused without a passing verifier; a historically-rejected v3 command is not resealed as accepted v4;
an unattested v3 command fails closed; the migration log documents source/policy/capsule; the
migration output does not alias its input.

### Review round 18 — journal immutability (no aliasing) + honest, versioned v3→v4 migration (vs `d11515a`)

Two fundamentals remained: the authoritative journal was rewritable through reference aliasing, and
the documented backward-readability of accepted v3 trial journals was no longer true. Both fixed; the
r6 rule hash is unchanged (`sha256:2438455f…`).

1. **The replay journal is DEEP-FROZEN on entry.** `submit()` severs the proposal payload from the
   caller (`copy.deepcopy`), and `JournalEntry.__post_init__` deep-copies its payload + provenance, so
   the journal shares **no** nested references with the caller's dict or any earlier export.
   `JournalEntry.to_dict()` returns independent deep copies and `from_dict()` does not alias its input.
   Mutating the caller's payload, an exported `to_dict()`, or a `from_dict()` input after the fact
   **cannot** rewrite the journal — `state = f(seed, journal)` is immune to aliasing (replay + snapshot
   stay identical).
2. **Honest, versioned v3→v4 migration.** The deterministic v4-only boundary means an accepted v3
   trial event is **not** raw-replayable; the docs now say so (`backward_readable: true` only for
   claim/conflict/legacy journals; `trial_events_v3_backward_readable: false`). Backward compatibility
   for trial events is an explicit, **versioned** migration: `load_migrated(doc)` re-seals each v3
   trial body verbatim to a sealed v4 entry under its **known** capsule (fail-closed on an unknown
   historical rule) **before** replay — introducing **no** submit privilege. The reconstructed state
   is the upgraded (v4) state; the trial *data* is preserved.
3. **Gate-versioning boundary documented** (secondary): the journal stores the command, not the
   original gate decision/policy version; a rejection is reproducible only under the same gate
   software (pinned by the planned kernel lock for the baseline). Binding the journal/policy version
   is a documented requirement for any post-lock kernel revision.

New artifact: none (kernel journal + a joni-level migration loader). Round-18 tests (9): mutating the
caller payload / an exported `to_dict` / a `from_dict` input cannot rewrite the journal; replay is
immune to external mutation; a historical v3 journal migrates to v4 and the trial reappears (body
verbatim); migration is fail-closed on an unknown rule; migration introduces no submit privilege; a
raw v3 journal is not directly replayable without migration.

### Review round 17 — deterministic write boundary + body-bound operational class (vs `2d327c3`)

The deepest issue was now in the state machine itself: the replay privilege was a public bypass, a
rejected v3 was journaled then re-accepted on replay (breaking `state = f(seed, journal)`), and the
operational class was writer-chosen. All fixed; the r6 rule hash is unchanged (`sha256:2438455f…`).

1. **The write boundary is DETERMINISTIC — no replay privilege.** `submit()` no longer takes a
   `replaying` parameter and `Layer9` carries no `_replaying` state. A v3 `METHOD_TRIAL_RECORDED` is
   **never** accepted (only sealed v4 is writable); the rule depends only on the proposal, so a v3
   attempt reproduces the **same** rejection on replay. A rejected v3 leaves only an audited rejected
   `Proposal` (no trial event), so replaying the journal yields an **identical snapshot** — the
   `f(seed, journal)` invariant holds with no public or privileged bypass.
2. **Pre-v4 v3 data migrates by RE-SEALING to v4** (`seal_payload`), never by a raw replay; the
   projector still **reads** v3 payloads as `legacy_unsealed`. This is the explicit, tested migration
   contract.
3. **The operational class is DERIVED from the body.** The gate (`derive_operational_class`) computes
   the class from execution/protocol status and requires `operational_envelope.operational_class` to
   equal it — a writer can no longer mislabel a technical failure as merely unevaluated (or vice
   versa).

New artifact: none (kernel state-machine + gate logic). Round-17 tests (6): v3 is never writable
under any public API (`submit` exposes no replay param); a rejected v3 attempt replays to an
identical snapshot; v3 migrates by re-sealing; `operational_class` must be body-derived; each class
is pinned to its execution state; `submit` carries no mutable replay state.

### Review round 16 — frozen live capsule, v4-only write boundary, operational seal mode (vs `571cc7b`)

The sealed journal was enforced, but the **current** production capsule still bound a dynamic
validator wrapper, the gate still accepted new unsealed v3, and operational events could not be
sealed. All fixed; the r6 rule hash is unchanged (`sha256:2438455f…`).

1. **The current production capsule is byte-pinned.** `_live_cross_block` (which dynamically
   imported `cross_block_consistency`, so its source hash did not bind the actual validator) is gone
   from production. Both production capsules are now **archived, byte-pinned, self-contained**: the
   current rule is `rule_v2_v2.pysrc` (byte-identical to the live `_rule_v2`; its bytes hash ==
   `RULE_V2_HASH`) with the byte-pinned validator/contract/decoder/adapter. Monkeypatching the live
   `cross_block_consistency` after sealing no longer changes a sealed event's evaluation.
2. **A v4-only write boundary.** `core.submit` gained a `replaying` flag (set by
   `persistence.replay`); the recording handler refuses a NEW submission whose `schema_version` ≠ v4.
   Existing v3 journals stay readable for display (visible as `legacy_unsealed`); a writer can no
   longer add a fresh unsealed event. (r17 made this deterministic; r18 documents that an accepted
   v3 trial event is migration-loaded, not raw-replayed — see the compatibility note below.)
3. **A sealed operational v4 mode.** A v4 object carries EXACTLY ONE of an epistemic
   `evaluation_envelope` (capsule_hash mandatory) or an `operational_envelope` (`operational_class` +
   body hash, no capsule). `to_journal` seals `not_evaluated` events operationally, so it never emits
   a capsule_hash=null epistemic seal the gate would reject; operational events evaluate to
   `operational`, never become evidence, and carry their classified `operational_class`.
4. **Capsule-manifest decision (explicit).** The write-gate validates structure + binding but does
   **not** require the capsule to be in the catalog (the kernel must not depend on the joni registry);
   a well-formed seal whose capsule is unknown downstream is marked `sealed_unknown_capsule` and is
   never verified or aggregated (a missing `capsule_hash` stays `unverifiable`).

New artifact: `rule_v2_v2.pysrc` (`91f2d789`). Round-16 tests (11): live-validator monkeypatch does
not change the frozen capsule; production current capsule is archived/byte-pinned; new v3 refused but
v3 replays; new v4 accepted; operational event seals + the kernel accepts it; completed+valid+
not_evaluated → unevaluated; `to_journal` never emits a gate-rejected v4; both-seals refused; unknown
capsule is `sealed_unknown_capsule`, never evidence.

### Review round 15 — the SEALED v4 journal is enforced at the kernel gate (vs `72a5d5f`)

The capsule was closed but **unused at the real entry point**: Layer 9 stored plain v3 payloads
without the sealed envelope, so replay fell back to the live bridge; the envelope addressed only the
rule; and unsealed events could still become verified evidence. All fixed; the r6 rule hash is
unchanged (`sha256:2438455f…`). This round changes the **kernel gate** (`desi_layer9`, which is
outside the protected manifest) — it hardens the gate; it does **not** enable a writer.

1. **Sealed v4 journal format, enforced at the gate.** `method_trial_recorded_v4` stores the body
   PLUS an embedded `evaluation_envelope` (with `capsule_hash` + `evaluation_body_hash`).
   `to_journal()`/`seal_payload()` produce it; the Layer-9 gate (`validate_evaluation_envelope`,
   called from `_h_method_trial_recorded`) **requires** it for v4 and rejects a v4 event with no
   envelope or whose `evaluation_body_hash` does not bind the body. Replay reads the **embedded**
   envelope; changing the live `envelope_for_payload` cannot re-route a stored event. v3 events are
   `legacy_unsealed`.
2. **`capsule_hash` is the mandatory routing key.** The registry is keyed by the composite
   `capsule_hash`, so two capsules with the **same** rule_hash but a different
   validator/contract/decoder/loader coexist (no hash tricks). The envelope stores `capsule_hash`;
   `evaluate_envelope` selects by it (missing/unknown → `unverifiable`) and cross-checks
   rule_id/rule_hash for transparency.
3. **No verified evidence from a live-reconstructed envelope.** `evaluate_payload` returns
   `legacy_unsealed` for an envelope-less object; `verify_payloads` **skips** unsealed objects — they
   are visible but never produce evidence, sufficiency or DESi weight.
4. **Distinct hash names.** The envelope's body binding is `evaluation_body_hash` (body only) — a
   different scope from the kernel's `payload_hash` (whole stored object); gate and evaluator share
   one canonicalisation.

New artifact: none (v4 schema + gate logic). Round-15 tests (7): kernel stores the sealed envelope
and replay ignores the live bridge; gate rejects a v4 event without an envelope; gate rejects a
non-binding body hash; two same-rule capsules coexist; `capsule_hash` is the mandatory routing key;
`legacy_unsealed` events never become evidence; `evaluation_body_hash` is a distinct scope.

### Review round 14 — loader trust-root, exec-env closure, python pinning, stored envelope (vs `c1e0d8e`)

The components were pinned, but the loader that *executes* them was swappable, the loader's closure
and the Python version were not bound, and the routing envelope was a live derivative. All closed;
the r6 rule hash is unchanged (`sha256:2438455f…`).

1. **The loader is a byte-pinned trust root.** `loader_v1.pysrc` (`02f22f0e…`) is bootstrapped FROM
   ITS BYTES in `_resolve_artifact` (never the module global), its hash re-derived and checked
   against the artifact's `execution_environment` before any artifact byte runs. The reproduced
   attack — replacing `schema._exec_callable` after the registry is built — now has **no effect**;
   tampering the loader bytes with a copied hash → `unverifiable`.
2. **The exec-env binds the loader's full numeric closure.** Future flags are carried as **numeric
   values** (`{"annotations": 16777216}` + `future_flag_bits`) and passed to the loader as arguments
   (no mutable global table); `exec_env_hash` covers the numeric flags, optimize, loader id+hash and
   `python_semantics`. Changing the numeric flag value → `unverifiable`.
3. **`python_semantics` is enforced.** `_trusted_loader` requires runtime major.minor ==
   `execution_environment.python_semantics` (else `unverifiable`) and folds it into `exec_env_hash`
   and `capsule_hash`.
4. **The evaluation envelope is stored and replayed.** `to_journal()` embeds the envelope alongside
   the payload; `evaluate_payload` reads the **embedded** envelope (replay never uses the live
   `envelope_for_payload` bridge), and `payload_hash` binds the payload (tamper → `unverifiable`).
   Monkeypatching `envelope_for_payload` after journaling cannot re-route a stored event.
5. **Aggregation runs from the stored (envelope, payload) pair.** `verify_payloads(stored)` verifies
   each stored pair via `evaluate_envelope` and emits payload-based evidence; `aggregate` reads
   grouping fields from the payload and re-verifies the pair — **no** dataclass reconstruction is a
   precondition. The projector feeds raw stored payloads to `verify_payloads`; dataclasses are
   display-only.

New artifact: `loader_v1.pysrc` (`02f22f0e…`). Round-14 tests (9): live-loader swap has no effect;
tampered loader bytes → `unverifiable`; numeric flag value bound; `python_semantics` enforced;
stored-envelope replay ignores a changed live bridge; journal payload tamper detected; aggregation
from stored objects; production capsule binds loader + python semantics.

### Review round 13 — routing envelope, byte-pinned adapter, pinned loader, capsule hash (vs `dddac93`)

The historical components were pinned, but were still assembled by current glue. All four
connection layers are now part of the capsule; the r6 rule hash is unchanged (`sha256:2438455f…`).

1. **Byte-pinned input adapter.** The decoder→rule view transform (`build_view`) is its own
   self-contained artifact (`view_adapter_v1.pysrc`, `ff53fa45…`); `input_adapter_hash` is bound and
   re-derived, and the rule consumes `artifact.adapter_fn(meas, dec, est)`. Sabotaging the live
   `build_view` leaves a historical verdict unchanged; tampering the adapter bytes → `unverifiable`.
   (The r6 rule still takes a view object, so its `2438455f` bytes/hash are untouched — but the view
   is built *only* from decoder output by a pinned adapter.)
2. **Stable routing envelope.** `evaluate_envelope(envelope, payload, registry)` selects the artifact
   from `evaluation_envelope_v1` (`envelope_version`, `schema_version`, `rule_id`, `rule_hash`,
   `claimed_verdict`, `payload_hash`), independent of the payload's field layout; `payload_hash`
   binds the payload. A relocated decision block still routes; an unknown envelope version or a
   payload tampered under the same envelope → `unverifiable`.
3. **Pinned loader + execution environment.** `_exec_callable` compiles with explicit future flags
   and `dont_inherit=True`; the r6 rule's un-imported annotation loads *only* under the explicit
   `annotations` flag (without it → `NameError`). The artifact binds `execution_environment`
   (future_flags, optimize, loader_version, loader_hash) + `exec_env_hash`; a wrong flag spec →
   `unverifiable`.
4. **Composite `capsule_hash`** over rule + validator + contract + decoder + projection + adapter +
   exec-env + schema_version + envelope_version uniquely addresses the whole capsule, re-derived and
   checked at use; an envelope may additionally pin `capsule_hash`.

New artifact: `view_adapter_v1.pysrc` (`ff53fa45…`). Round-13 tests (10): adapter byte-pinning +
tamper; envelope routing with relocated payload; unknown envelope version; payload tamper under same
envelope; loader compiles historical bytes under explicit semantics (and fails without the flag);
wrong exec-env flags → `unverifiable`; capsule_hash binds every component; production r6 capsule
binds adapter+loader+capsule_hash.

### Review round 12 — the evaluation capsule is causally CLOSED (vs `b0c5b34`)

The historical bytes were stored, but were still assembled by current runtime glue. All four gaps
are closed; the r6 rule hash is unchanged (`sha256:2438455f…`).

1. **Self-contained historical validator** — `cross_block_v1.pysrc` now carries its own
   `_is_num`/`_finite`/`_ci_errors`/`_EPS` + imports; `_resolve_artifact` execs it with **no**
   injected globals, so `validator_hash` covers the whole executable closure. Monkeypatching the
   live `_finite`/`_EPS` leaves a historical verdict unchanged.
2. **Rule decides from the decoder output, not the event** — `evaluate_payload` runs `rule_fn` on a
   view built **only** from the decoder's `(measurement, decision, estimand)`; `rule_fn(ev)` is gone.
   A decoder override flips the verdict, proving the rule/validator input is the decoder's.
3. **Historical decoder runs first, on the raw payload** — `evaluate_payload(payload, registry)` is
   the canonical entry: it reads `schema_version` from the raw payload, selects the artifact, and
   applies the artifact's byte-pinned decoder (`decode_v3.pysrc`, now payload-driven) **before** any
   live dataclass reconstruction. The projector evaluates the raw payload.
4. **Contract interpreter is versioned and hashed** — the contract is now an executable
   `check_contract(meas, dec, est)` (`contract_v2_r6.pysrc`, replacing the JSON + live
   `_apply_input_contract`); `input_contract_hash` covers the interpreter bytes. A change to the live
   interpreter cannot re-interpret a historical contract.

New artifacts: self-contained `cross_block_v1.pysrc` (`ddc83e52…`), payload-driven `decode_v3.pysrc`
(`f526051b…`), executable `contract_v2_r6.pysrc` (`f796d38b…`); `rule_v2_r6.pysrc` unchanged
(`2438455f…`). Round-12 tests: validator self-containment under live-helper sabotage; validator-bytes
tamper → `unverifiable`; rule-input-from-decoder; live contract-interpreter change does not affect the
archived artifact; `evaluate_payload` on the raw stored payload.

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

## Changed kernel files (vs `282d541`) — 10 files, +705 / −65

| file | change | why |
|---|---|---|
| `enums.py` | `Operator.METHOD_TRIAL_RECORDED`, `ObjectType.METHOD_TRIAL_EVENT` | a new operator + immutable record type, additive; legacy operator untouched |
| `ids.py` | `MTE` id prefix | deterministic ids for the new record |
| `objects.py` | `MethodTrialEvent` dataclass | immutable record: canonical-JSON payload, `record_authority` vs `epistemic_authority` |
| `transitions.py` | `METHOD_TRIAL_EVENT → _IMMUTABLE_RECORD` | registered transitionless (append-only) |
| `trial_event_validation.py` (new) | structural gate + `canonical_payload`; **r15-17:** `method_trial_recorded_v4`, `validate_v4_seal` (epistemic **or** operational), `evaluation_body_hash`, `derive_operational_class` | v4 SEALED; EXACTLY ONE seal, body-bound; **operational_class derived from the body**; unknown → reject |
| `core.py` (r15-20) | `_h_method_trial_recorded` enforces `validate_v4_seal`; a **DETERMINISTIC v4-only write boundary** (no `replaying`/`_replaying`); **`submit()` deep-copies the whole incoming proposal**; a **frozen** `JournalEntry`; **ALL mutable state private** (`_tick`/`_objects`/`_minter`/`_ledger`/`_journal`/`_seq`); `objects`/`ledger` are read-only **deep-copied** views, `journal` an immutable tuple, `tick` read-only with a monotonic `set_clock()`, no public minter | a v4 event without a bound seal is refused; **v3 is never a writable trial event**; **`submit()` is the ONLY write path** — no public handle (object store, ledger, clock, minter) can rewrite authoritative state; v3 data migrates (`load_migrated`) to v4 under a pinned attestation |
| `hashing.py` (r20) | `snapshot_hash`/`verify_chain` read the internal `_objects`/`_ledger` directly | integrity hashing covers the real objects/ledger (the public views are deep copies) |
| `core.py` | `_h_method_trial_recorded`, `method_trial_events()`, `trial_event_hashes()`, optional 4-tuple handler return | append-only handler (idempotent on `trial_id`, mutates **no** counter), read-only envelope, named hashes, auditable idempotent-retry decision tag |
| `__init__.py` | export `MethodTrialEvent` | package surface |

**Unchanged on purpose:** `_h_method_trial_record` and the legacy counters, `_h_method_promote`,
`policy.py`, `ledger.py`. (`hashing.py`/`persistence.py`/`migration.py` saw only the round-20
encapsulation follow-through — `_objects`/`_ledger` reads and the `_tick` constructor — no behaviour
change.) The new path is **inert**: nothing in promotion/discard reads it.

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
- new software replays old (claim/conflict/legacy) journals; unknown operator fails closed at load;
  an accepted v3 trial event is loaded via `load_migrated` (re-sealed to v4), not raw-replayed;
  known-but-unhandled
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

Full suite at `8412040`: **611 passed / 2 skipped with the `desi` extra; 604 passed / 7 skipped
with `desi` BLOCKED (0 failed); ruff clean.**

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
  backward_readable: true                         # new code, old journal (claims/conflicts/legacy)
  trial_events_v3_backward_readable: false        # an accepted v3 trial event is NOT raw-replayable
  trial_events_v3_migration: required             # load via load_migrated() -> re-sealed to v4
  trial_events_v3_migration_trust_source: pinned_internal_attestation_catalog  # NOT caller-supplied
  trial_events_v3_migration_attestation: verifier_id_resolved_against_pinned_catalog
  trial_events_v3_migration_failure_mode: fail_closed   # missing/forged/unbound/unknown attestation
  trial_events_v3_migration_snapshot_hash: bound_by_attestation_source_snapshot_hash
  forward_readable: false                         # old code, new journal
  failure_mode: fail_closed_at_load
  downgrade_after_first_new_event: blocked        # IRREVERSIBLE
```

> **Honest v3 trial-event compatibility (r18):** the deterministic v4-only write boundary means a
> historical *accepted v3 trial event* is **not** raw-replayable — `persistence.replay` rejects it
> and reconstructs no trial event. Backward compatibility for trial events is an **explicit,
> versioned migration**: `load_migrated(doc)` re-seals each v3 trial body verbatim to a sealed v4
> entry under its *known* capsule (fail-closed on an unknown historical rule) **before** replay,
> introducing no submit privilege. **(r19)** migration is additionally bound to a **trusted historical
> source**: each v3 entry must carry a `historical_decision` attestation (`accepted` +
> `gate_policy_version`) — an unattested entry fails closed, a historically-rejected one is dropped
> (never resealed as accepted), and a document carrying a `snapshot_hash` is refused unless a
> `historical_verifier` confirms it. The reconstructed state is the upgraded (v4) state — the trial
> *data* is preserved, not the byte-identical v3 snapshot. (The base `282d541` contains no trial
> events, so no production v3 trial-event journal exists.) General journals
> (claims/conflicts/legacy `METHOD_TRIAL_RECORD`) remain directly backward-readable.

> **Gate-versioning boundary (r18, for a later kernel):** the replay journal stores the *command*,
> not the original gate decision / policy version. A rejection is reproducible **only under the same
> gate software** (which the planned kernel lock pins for the baseline); a future gate change could
> decide a journaled command differently. Binding the journal/policy version (or the accepted
> transition) into each entry is a documented requirement for any post-lock kernel revision.

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

1. Review the diff `282d541..8412040` and this package.
2. Explicitly designate a commit as the **human-reviewed Layer-9 baseline**.
3. Only then: implement `layer9_kernel_lock` resolution over `src/desi_layer9` and run the **human**
   `lock` to freeze that commit (per `PROTECTION_ZONES.md`).
4. Only after the lock exists: enable the writer (this crosses the irreversible journal boundary).

Until step 2, **no kernel lock is created and the writer stays locked.**
