# Governance protection zones — specification (review)

**Status:** SPECIFICATION for review. **No lock file is changed or created.** Locking/regenerating
is a human action. This proposes three *separately-named* protection zones so a green check attests
exactly what it covers — and no more.

Today there is one `joni_core.lock` named "core lock" that actually protects only the Joni runtime
(see `GOVERNANCE_LOCK_SCOPE_AUDIT.md`). One lock over everything would blur what a pass means; three
zones keep the statements legible.

```yaml
runtime_lock:        { passed: true, scope: joni_runtime }
layer9_kernel_lock:  { passed: true, scope: epistemic_kernel }
dependency_manifest: { verified: true, desi_commit: <sha>, kevin_commit: <sha> }
```

A pass in one zone says nothing about the others. The status line must always name the zone.

### What a green status in each zone proves — and does NOT prove

```yaml
runtime_lock:
  proves:
    - the listed Joni runtime files match their approved hashes
  does_not_prove:
    - Layer-9 kernel integrity
    - dependency provenance
layer9_kernel_lock:
  proves:
    - the epistemic transition / authority / policy / hashing / persistence / replay code
      matches its approved hashes
  does_not_prove:
    - external DESi or Kevin source integrity
    - correctness of the runtime configuration
dependency_manifest:
  proves:
    - the configured dependencies resolve to the approved immutable commits
  does_not_prove:
    - that those commits are scientifically valid
    - that the loaded runtime code actually matches them, unless verified at startup (see below)
```

This explicit "does_not_prove" column is the point of splitting the zones: it stops a green check in
one zone from being read as a broader attestation.

---

## Zone 1 — `runtime_lock` (rename of today's lock)

**Scope:** `src/joni/*` — orchestration, persona, autonomy/runtime. Exactly the current
`PROTECTED_CORE` set (`models.py, state.py, operators.py, conflict.py, router.py, memory.py,
persistence.py, loops.py, renderer.py, identity.py, model_client.py, seed.py,
autonomy/governance.py`).

**Change:** rename only — "core lock" → "runtime lock". `passed` attests the runtime/persona layer
is unchanged. It does **not** attest the epistemic kernel.

## Zone 2 — `layer9_kernel_lock` (new) — the epistemic kernel

**Scope:** `src/desi_layer9/*` — the machine that decides epistemic state. Each file, with why it
must be pinned (changing it silently would change what the system may conclude or how integrity is
proven):

| file | role | why protected |
|---|---|---|
| `core.py` | the gate (`submit`), all handlers, `_HANDLERS`, state mutation | the only write path; any change alters what operators do |
| `enums.py` | closed sets: `Operator`, `ObjectType`, `Authority`, `Status` | adding/altering an operator or authority value changes the rules of the game |
| `objects.py` | object schema (incl. method counters, the trial record) | the shape of authoritative state |
| `transitions.py` | allowed status transitions | a loosened transition lets state move where it must not |
| `policy.py` | `may_request`, control/authoritative operator sets, gating | who may request what; the authority boundary |
| `rules.py` | confirmation rules (e.g. `can_confirm_claim`) | when a claim may become authoritative |
| `hashing.py` | `snapshot_hash`, chain, `verify_chain` | the integrity instrument itself — must be tamper-pinned |
| `ledger.py` | ledger event + chain fields | the audit/tamper-evidence record |
| `persistence.py` | `replay` / `save` / `load` | replay determinism = the definition of "true state" |
| `ids.py` | deterministic id minting | replay identity (ids must reproduce) |
| `provenance.py` | origin/provenance → taint & authority inputs | feeds authority/taint decisions |
| `taint.py` | taint propagation | contamination tracking |
| `base.py` | `EpistemicObject` governance metadata | the common authority/status fields |
| `trial_event_validation.py` | structural gate validation for trial events | what the gate will accept/store |
| `migration.py` | legacy migration / seed logic | how historic data enters the kernel |

`passed` attests the kernel above is byte-for-byte the audited version.

**Resolution detail:** the current `_package_dir()` returns `src/joni`; the kernel lives in
`src/desi_layer9`. The kernel lock must resolve its own tree explicitly (a second base dir), so the
two zones never accidentally share or miss files.

## Zone 3 — `dependency_manifest` (new) — external components

**Scope:** immutable commit SHAs of components pulled from outside this repo:

```yaml
dependency_manifest:
  desi_commit:  <sha>      # DESi governance/analysis (desi-governance @ ...)
  kevin_commit: <sha>      # Kevin creative companion (already SHA-pinned in autonomy.yml)
  # + any further external analysis/model component
```

`verified` attests the build used exactly those commits. (Kevin is already pinned to an immutable
SHA in `.github/workflows/autonomy.yml`; this zone makes the pin a first-class governance check
rather than a CI detail.)

### Startup attestation (a configured SHA is not enough)

A commit SHA in a config file pins **intent**, not the code that is actually loaded. The
`dependency_manifest` zone is only meaningful if, **at startup**, the chain is verified end-to-end
and the result is surfaced in the runtime status:

```
configured SHA
  -> installed package metadata / source SHA   (what got installed)
  -> actually loaded module path + its SHA      (what the process imported)
  -> result recorded in runtime_status
```

```yaml
startup_attestation:
  desi:
    configured_sha:   <sha>
    installed_sha:    <sha>          # from package metadata
    loaded_module:    /path/to/desi/__init__.py
    loaded_sha:       <sha>          # hash of what was actually imported
    match: true
  kevin: { ... same shape ... }
```

Without this, the manifest protects the *intended* dependency, not the *loaded reality* (a stale
install, a shadowing path, or an editable checkout could diverge from the pinned SHA undetected).
`verify` must fail (or loudly warn) if `configured_sha != installed_sha != loaded_sha`.

---

## Expected status output (after the zones exist)

```yaml
governance:
  runtime_lock:        { passed: true,  scope: joni_runtime }
  layer9_kernel_lock:  { passed: false, scope: epistemic_kernel, changed: [core.py, enums.py] }
  dependency_manifest: { verified: true, desi_commit: ..., kevin_commit: ... }
```

So a kernel edit (like this very trial-event step) would show `layer9_kernel_lock.passed: false`
listing the changed files — instead of today's misleading global green.

## Migration plan (no lock change yet)

1. Land this spec + the audit (`GOVERNANCE_LOCK_SCOPE_AUDIT.md`) for review.
2. Rename `runtime_lock`; keep its current hashes.
3. Implement `layer9_kernel_lock` resolution over `src/desi_layer9`; **human** runs `lock` to
   freeze the kernel at a reviewed commit (never Joni).
4. Add `dependency_manifest` recording DESi/Kevin SHAs; wire `verify` to check all three zones and
   print per-zone status with the proves/does-not-prove framing.
5. Add **startup attestation** for the dependency zone (configured → installed → loaded SHA), so a
   green dependency status reflects loaded reality, not just configured intent.
6. Until then, every status report states: **lock passed, but `desi_layer9` is outside the
   protected manifest.**

See `TRIAL_EVENT_REPLAY_NOTES.md` for the operating invariants that bound the new event path
(`trial_id` uniqueness is per-instance; the journal compatibility boundary is irreversible after the
first new event).

## Until the zones exist

> **lock passed, but `desi_layer9` is outside the protected manifest** (a green runtime lock does
> not attest Layer-9 kernel integrity).
