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

- **Enabled in production** via `JONI_ROUTER_SHADOW=1` in the autonomy workflow. With the flag unset
  the hook is completely inert, so it can be turned off without a code change.
- **Persistent, capped log.** When enabled it runs `hook.run_after_cycle`, which computes the
  per-commit ledger shadow over the just-written snapshot and appends one record (with `cycle` + `ts`)
  to **`state/router_shadow.jsonl`** — a *tracked* file under `state/`, which the loop commits each
  cycle (`git add state`), so the log persists across jobs. It is capped to the last 500 records, so
  it can never bloat the repo. It never writes Joni's Layer-9 state.
- **Decoupled.** The router is imported from `DESI_REPO`, else the workflow's `DESI_ROOT` (the `_desi`
  checkout), else a local default. A missing router is a clean no-op.
- **Never breaks a cycle.** Any error is swallowed — `try/except` guards both the call site in
  `run.py` and the body of `run_after_cycle`.

So in production the log now accumulates one router-shadow record per cycle, committed with the
cycle's state — the per-cycle gate selectivity is observable over time without any effect on the loop.

## Slice-quality shadow (`slice_quality_shadow.py`) — the plausible-wrong-slice checks on real data

Runs the five DESi plausible-wrong-slice vectors (missing-opposition / same-scope-newer /
thin-provenance / scope-mismatch / k-unstable) over Joni's real v2 graph and aggregates the per-vector
fire-rate. This is what turns fixtures-passing checks into an evidence-based adoption.

**Latest reading — per-claim, 2 486 live claims (`active`+`contested`), v2 graph:**

| vector | fire-rate | verdict |
|---|---|---|
| missing_opposition (#3) | 6.4 % (158) | selective — adopt |
| same_scope_newer (#5) | **7.2 %** (180) | **now selective** (was 64.8 % with topic-scope) |
| thin_provenance (#4) | 2.3 % (58) | selective — adopt |
| scope_mismatch (#6) | 0 % | structurally dead (no scope tags in the model) |
| k_unstable (#2) | 0.2 % (5) | marginal |

The headline is #5: held back at **64.8 %** on 1 366 claims with a *topic* scope, it dropped to **7.2 %**
once claims carried the deterministic subject key — the bet that "same subject" (not topic) is the
right granularity, paid in by real data. Would-gate-update on 370/2 486; modes `state_slice` 2 328 /
`guarded` 158.

```bash
DESI_REPO=/home/user/DESi python shadow/slice_quality_shadow.py --granularity claim
```

## Ontology-coverage shadow (`ontology_coverage_shadow.py`) — does the ontology probe have purchase?

Same evidence-first discipline, applied **before** wiring DESi's new Ontology Probe into anything. The
probe's promise is to soften the `same_scope` over-fire above: when a subject token is ambiguous across
kinds (`operator` = math object vs. person) the probe marks the scope uncertain and a supersession flag
is withheld (separate-only — it can never assert sameness). Whether that is real depends entirely on
**coverage**, so this measures it on Joni's terms first:

- **addressable pool** — same-subject-key collision groups (the #5 over-fire pool) + claims in them.
- **coverage** — of the salient subject tokens, how many the ontology actually knows. With no corpus
  installed this is **0**, reported honestly (the probe then stays a silent no-op).
- **addressable groups** — collision groups carrying an across-kind-ambiguous token: what the
  separate-only rule could legitimately soften.

```bash
DESI_REPO=/home/user/DESi python shadow/ontology_coverage_shadow.py            # real WordNet (fail-open)
DESI_REPO=/home/user/DESi python shadow/ontology_coverage_shadow.py --seed-demo # labelled demo ontology
```

The default WordNet adapter is fail-open (0 coverage when the corpus is absent); `--seed-demo` makes the
mechanism visible via a small, explicitly-labelled in-memory ontology. Adoption stays gated on a
non-zero coverage reading — not on the fixtures.

**Latest reading — 2 486 live claims, 2 030 subject keys, 2 271 distinct tokens:** addressable pool =
**283** same-subject collision groups (739 claims). WordNet coverage **0** (no corpus → silent no-op).
Demo seed: 4 covered ambiguous tokens (`agent`/`kernel`/`memory`/`model`), but **0 of 283** collision
groups carry one — the 7 ambiguous-token keys are all singletons. **Conclusion: not adopted on this
data** — Joni's collisions are genuine same-subject repeats, not homonymy, so the separate-only rule
has no target here. The channel stays built + unit-correct, gated on a real corpus *and* evidence that
homonymy collisions actually occur.

## Not yet (next increments)

- A **time-series** view over the accumulated `state/router_shadow.jsonl`: watch the gate rate move
  as Joni's state evolves over the run.
- Only after the shadow log shows stable, sensible gating over many cycles: consider switching one
  low-risk gate live (e.g. `claim_reject` confirmation), never a blanket enable.
