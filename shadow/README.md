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

## Not yet (next increments)

- **Per-cycle** shadow: walk the ledger per tick and ask whether each cycle's *commit* (a decision
  accepting a proposal whose target is contested/rejected) would have been gated — the direct
  "would the router have blocked this state update?" metric.
- Wire it as a post-cycle hook (still observation-only) so the log accumulates automatically.
