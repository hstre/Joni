# Governance audit — core-lock scope vs. the real Layer-9 kernel

**Status:** REVIEW report. **No lock extension or regeneration has been done** (that is itself a
governance change, and a human action). This documents a scope finding and proposes a protected
set for review.

```yaml
governance_lock:
  status: passed
  protects_desi_layer9: false
  implication: a green lock does NOT attest Layer-9 core integrity
```

## The finding

The minimal trial-event step changed real epistemic-kernel files
(`desi_layer9/core.py`, `objects.py`, `enums.py`, `transitions.py`, `ids.py`, `__init__.py`, and a
new `trial_event_validation.py`). Throughout, `joni.autonomy.governance.verify_core(".")` reports
**`(True, [])`** — "core OK".

That is **not** a success of the lock; it is proof the lock **cannot see** these changes. A green
core-lock currently says nothing about whether the Layer-9 decision machine was modified.

## What the lock protects today

`PROTECTED_CORE` (in `joni/autonomy/governance.py`) is resolved relative to `src/joni/` and frozen
in `joni_core.lock` (13 modules):

```
models.py  state.py  operators.py  conflict.py  router.py  memory.py
persistence.py  loops.py  renderer.py  identity.py  model_client.py  seed.py
autonomy/governance.py
```

These are the **operative-identity / persona-runtime** layer (how Joni *appears* and routes), plus
the guard guarding itself. Legitimate to protect — but it is not the epistemic kernel.

## What actually controls epistemic state — and is OUTSIDE the manifest

Every file below lives in `src/desi_layer9/` and is **not** in the lock:

| file | controls | integrity criticality |
|---|---|---|
| `core.py` | the gate (`submit`), all operator handlers, state transitions, `_HANDLERS` | **critical** |
| `enums.py` | the closed sets of `Operator`, `ObjectType`, `Authority`, `Status` | **critical** |
| `objects.py` | the object schema (incl. method counters, the new record) | **critical** |
| `transitions.py` | allowed status transitions per object class | **critical** |
| `policy.py` | `may_request`, control/authoritative operator sets, governance gating | **critical** |
| `hashing.py` | `snapshot_hash`, the ledger chain, `verify_chain` — the integrity instrument itself | **critical** |
| `ledger.py` | the ledger event + chain fields | **critical** |
| `persistence.py` | `replay` / `save` / `load` — replay determinism | **critical** |
| `rules.py` | confirmation rules (e.g. `can_confirm_claim`) | **critical** |
| `provenance.py` | origin/provenance → taint & authority inputs | high |
| `taint.py` | taint propagation | high |
| `base.py` | `EpistemicObject` governance metadata | high |
| `ids.py` | deterministic id minting (replay identity) | high |
| `trial_event_validation.py` | the new gate-side structural validation | high |
| `migration.py` | legacy migration | medium |

The irony worth stating plainly: `hashing.py` — the file that *implements* tamper-evidence — is
itself unprotected by the manifest that claims to guarantee core integrity.

## Why this matters

- **`core-lock green` ≠ `Layer-9 core unchanged`.** Any change to transitions, authority, policy,
  replay or hashing passes the lock silently. An attacker or a careless refactor could weaken the
  gate while the governance instrument reports "core OK".
- The persona layer is pinned; the *decision* layer is not. That inverts the intended priority.

## Proposed protected scope (for review — NOT applied)

1. Add the **critical** and **high** `desi_layer9` modules above to the protected manifest, as a
   distinct section (e.g. `PROTECTED_LAYER9`) so the two concerns stay legible:
   `core.py, enums.py, objects.py, transitions.py, policy.py, hashing.py, ledger.py,
   persistence.py, rules.py, provenance.py, taint.py, base.py, ids.py, trial_event_validation.py`.
2. Resolve these paths explicitly (the current `_package_dir()` points at `src/joni`; the kernel is
   `src/desi_layer9`), so a future `verify_core` hashes both trees.
3. Decide the policy for the **vendored** nature of `desi_layer9`: if it mirrors an upstream
   package, pin the upstream commit/hash too, so "matches the lock" also means "matches the audited
   upstream".
4. Sequence: land this audit → freeze the new, wider scope via the **human** `lock` action (never
   by Joni) → only then is a green lock a real attestation of Layer-9 integrity.

## Until the scope is fixed

Every status report must state, verbatim:

> **lock passed, but `desi_layer9` is outside the protected manifest** (a green lock does not attest
> Layer-9 core integrity).

## Order of work (unchanged)

Replay/migration → **governance-lock-scope decision (this report)** → projector → writer → real
trials → DESi comparison → Kevin. No projector hookup before the replay/legacy-coexistence layer is
fully reviewed and this scope question is decided.
