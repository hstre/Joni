# Technical debt — tracked, not yet actioned

## TD-1 — variable 3-/4-tuple handler return contract

**Where:** `desi_layer9/core.py` — operator handlers and `Layer9.submit`.

**What:** handlers return `(output_ids, status, message)` or, to tag a distinct ledger decision
(e.g. an idempotent retry), `(output_ids, status, message, decision)`. `submit` branches on
`len(result)`.

**Why it is debt:** a variable-length tuple is a small convenience that tends to accrete semantic
variants over time (a 5th element, a differently-meant 4th, position confusion). The existing tests
show every current handler still works, but the contract is implicit.

**Proposed cleanup (later, not now):** a typed result object, e.g.

```python
@dataclass(frozen=True)
class HandlerResult:
    output_ids: list[str]
    status: str
    message: str
    decision: str = "accepted"          # ledger decision tag
```

`submit` would accept `HandlerResult` (and, during a transition window, still tolerate the legacy
tuple). This makes the ledger-decision channel explicit and stops new variants sneaking in via tuple
length. **No behavioural change intended** — purely a contract hardening.

**Status:** documented; deferred. Not blocking the current append-only step.

---

## TD-2 — `trial_id` uniqueness is not a store-level atomic constraint

**Where:** `desi_layer9/core.py` — `_h_method_trial_recorded` (lookup-then-mint).

**What:** uniqueness/idempotency on `trial_id` is enforced by a lookup over existing events before
minting. This is correct **only because `submit` is synchronous, serial and non-reentrant** (no
`async`/threads/locks in `core.py` or `persistence.py`; the journal model is single-writer). The
`test_BOUNDARY_forced_reentrancy_would_break_uniqueness` test documents that an artificial interleave
between the lookup and the mint would double-mint.

**Proposed mitigation (only if a multi-writer / concurrent store is ever introduced):** enforce
`trial_id` uniqueness atomically at the storage layer (a unique index / compare-and-append), not by
a pre-mint lookup. Until then, the serial submit model is the guarantee and must not be broken
(e.g. do not make handlers re-enter `submit`).

**Status:** documented; no change needed under the current single-writer model.
