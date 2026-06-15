# Backup: Joni's memory before the LLM-version A/B run

Snapshot taken **2026-06-15** at the end of the deterministic era, immediately before
restarting Joni from zero with the semantic-model proposal layer enabled.

## Why
The deterministic run (state-machine + language renderer) accumulated this memory. We now
restart the **LLM-augmented version from zero** (Granite 4.1 8B structured proposals +
DeepSeek v4-pro escalation, both as non-authoritative proposals through the Layer-9 gate) and
let it run for **2 days**, then compare. This makes the prior run the control baseline rather
than wasted work.

## What is here (the deterministic-era baseline)
- `state/` — full Layer-9 core (`layer9.json`), legacy `joni_state.json`, budget, window,
  extensions, forum state, asks/commissions at snapshot time.
- `protocol/protocol.jsonl` — the full deterministic-era protocol.
- `docs/data.json` — the site snapshot at the moment of the cut.

## Baseline metrics (from `docs/data.json` snapshot, tick = 2 days)
| metric | value |
|---|---|
| claims total | 608 |
| claims active | 427 |
| open conflicts | 25 |
| methods | 80 |
| hypotheses | 41 |
| evidence links | 107 |
| self-model claims | 8 |

## The experiment (LLM version, from zero)
- Live state was reset to 0 (no `layer9.json`, no legacy `joni_state.json`) so the next run
  seeds fresh via `seed_core` (the four starting topics only).
- `JONI_SEMANTIC_PROPOSALS=1` (Granite proposals + audited DeepSeek escalation) — the LLM version.
- `JONI_RUNTIME_DAYS=2` — a 2-day window to match the baseline's ~2-day tick.
- Same deterministic Layer-9 governance core; same budget cap.

## How to compare after 2 days
Diff the new `docs/data.json` snapshot (and `state/layer9.json` via
`epistemic_export`) against this baseline on the same axes above, plus the **new** signals the
LLM version produces:
- `state/model_calls/calls.jsonl` — every Granite/DeepSeek call (served_model, state_k,
  escalation_reason, replayed) — proof the models actually fired and at what cost.
- `extensions.semantic_calls` / `extensions.escalations` — projected claims and escalations.
- Quality, not just quantity: are the LLM-proposed claims more checkable / better-scoped, do
  conflicts get sharpened, is evidence coverage higher per claim — vs the deterministic baseline.
