# Router shadow-observer (step 4: shadow before live)

A **pure observer**. It does not touch Joni's loop, state, or Layer-9 core — it only *reads* the
committed `state/layer9.snapshot.json` and asks the real, deployed DESi router *"what would you have
done?"*, per topic. No writes to Joni state, no added latency, no shared state. Switching the router
on for real is a separate, later decision; this measures first.

## Why shadow, not live

The external DESi router has been benchmarked (policy correctness, replay against the ablation,
live closed-loop, a state-integrity layer, a two-tier commit gate). Before it gates anything in Joni,
we run it alongside and check: how often *would* it have been guarded / ask_user / retrieval, and how
often would it have gated a state update — and is any of that obviously unnecessary (over-blocking)?

## Run

```bash
python shadow/router_shadow.py            # all topics
python shadow/router_shadow.py --limit 50 # cap topics
DESI_REPO=/path/to/DESi python shadow/router_shadow.py
```

It imports the **real** router from the DESi repo (default `/home/user/DESi`, override `DESI_REPO`).
If it cannot import it, it exits loudly — it never substitutes a fake. Each run appends one summary
record to `shadow/shadow_log.jsonl` (git-ignored).

## Mapping (Layer-9 → router DesiReport)

| Layer-9 | router input |
|---|---|
| claim `status=active` | the usable state slice |
| claim `status=rejected`/`contested` | invalidated/superseded |
| `conflict` objects (open) touching the topic | open conflicts |
| `status=candidate` claims dominating the active ones | thin footing → low confidence (caution) |

## Latest reading (snapshot `7d561beb`, 301 topics, read-only)

| posture | topics | share |
|---|---|---|
| `state_slice` (light) | 281 | 93% |
| `retrieval` (no usable state) | 14 | 5% |
| `guarded` | 6 | 2% |

- Would gate a state update on **20 / 301 topics (7%)** — selective, not paranoid (an `always_guarded`
  baseline would gate 100%).
- Clean topics: **281**, of which gated (over-block): **0** → the router is not paranoid on Joni's
  clean state.
- Hotspots (most rejected/contested or conflicted) — e.g. `forum` (192 rejected/contested), `memory`
  (11) — are exactly where it would be guarded.

## Per-commit ledger shadow (`ledger_shadow.py`) — the sharp metric

Finer than topic posture: it walks Joni's Layer-9 **ledger** and, for every canonical state-mutating
commit (`claim_create` / `claim_revise` / `claim_reject` / `conflict_open` / `conflict_review`), asks
the real router whether it would have **gated** that update. Layer-9 ticks only span 0..3 while the
ledger holds 15k events, so the unit is the commit, not the tick.

```bash
python shadow/ledger_shadow.py
```

Latest reading (snapshot `7d561beb`, **3314 canonical commits**, read-only):

| | result |
|---|---|
| would gate a state update | **648 / 3314 (20%)** |
| risky commits (touch rejected/contested or an open conflict) | 648 — **gated 648/648 (100%)** |
| clean commits | 2666 — **gated 0 (no over-block)** |

By operator: `claim_reject` 142/142 and `conflict_open`/`conflict_review` 78/78 (100% — inherently
risky); `claim_create` 232/1622 (14%) and `claim_revise` 118/1394 (8%) — only the commits whose target
is rejected/contested or in an open conflict. **The router gates every risky commit and waves through
every clean one: 100% recall on risky, 0% over-block on clean.** That is the selectivity claim,
measured on Joni's real ledger — not a baseline that blocks everything.

## Post-cycle hook (`hook.py`) — automatic per-cycle logging

`run.py` calls `_maybe_router_shadow(p, cycle)` at the end of each cycle. It is **opt-in and
fail-safe**:

- **Off by default.** It does nothing unless `JONI_ROUTER_SHADOW=1` is set, so a normal production
  run is completely unaffected.
- **Observation-only.** When enabled it runs `hook.run_after_cycle`, which computes the per-commit
  ledger shadow over the just-written snapshot and appends one record (with `cycle` + `ts`) to
  `shadow/shadow_log.jsonl`. It never writes Joni state.
- **Never breaks a cycle.** Any error, or a missing DESi router (the production default, where
  `DESI_REPO` is absent), is a clean no-op — guarded by `try/except` at two levels.

To run Joni in shadow mode: set `JONI_ROUTER_SHADOW=1` and `DESI_REPO=/path/to/DESi`; the log then
accumulates one per-cycle record automatically. With the flag unset, the hook is inert.

## Not yet (next increments)

- A **time-series** view: re-run per snapshot over successive cycles to watch the gate rate move as
  Joni's state evolves (needs the loop to advance the Layer-9 tick).
- Only after the shadow log shows stable, sensible gating over many cycles: consider switching one
  low-risk gate live (e.g. `claim_reject` confirmation), never a blanket enable.
