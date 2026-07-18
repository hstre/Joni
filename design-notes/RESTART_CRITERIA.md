# Joni — restart criteria (the gate before autonomy resumes)

Joni is **parked** (the `joni-autonomy` schedule is commented out; the loop only relaunches via
`workflow_dispatch`). It was parked deliberately to fix the state-consolidation problems the
operator review named, rather than build more layers on top of a silting store.

Autonomy resumes **only** when every criterion below is met. Some are checked mechanically by
`scripts/restart_readiness.py`; the rest are the operator's judgment. This file is the contract;
the script is the read-out.

## The criteria (operator review, point 8)

1. **The two alarm metrics measure the right thing.**
   - Weak-claim rides on *presented-strong* (status `confirmed` **or** authority ≥ `reviewed`),
     not merely `active`; its concern is the **hollow** share (no independent external source
     family), so synthetic self-support never reads as strong. *(Phase A.)*
   - Self-model repetition is measured on real `SELF_MODEL_CLAIM` objects with digits kept — a
     count-only change is no longer a false repeat. *(Phase A.)*
   - **Check:** the latest `state/collapse_series.jsonl` row carries the new fields
     (`weak_claim_ratio.hollow_ratio`, `repetition.selfmodel_count`, `conflict_depth.by_status`).

2. **No obvious token-hypotheses are still being minted.**
   - The synthesis gate now requires a real term, a non-sink topic, ≥2 independent external source
     families, a majority-compatible cluster, and (optionally) the term-judge — and the wording no
     longer claims a "single underlying factor". *(Phase B.)*
   - **Check:** over a short shadow run, `emerge` mints no new `-as-a-lens`/through-line hypothesis
     on a name, slug, function word or sink topic. (Operator watches the protocol.)

3. **The method backlog is shrinking or actually being tested — not just growing.**
   - Either the one-time reconsolidation (`scripts/reconsolidation_audit.py --apply`) has cleared
     the clear-junk pile, **or** the real method-trial path (sandbox P0 → P1–P3) has begun moving
     `trial_count` off zero. A flat "N methods, 0 trials, growing" is not acceptable.
   - **Check:** `reconsolidation_audit.audit` junk-method count is low, or `vitality.method_trials_total > 0`.

4. **The metabolism is coupling intake to consolidation.**
   - `JONI_METABOLISM=1` is set, and a shadow run shows the hunger/satiety state reacting: load
     rising with backlog, `sated` suppressing intake, `hungry` returning below the low threshold.
     Thresholds tuned from the shadow load numbers, not left at the untested defaults. *(Phase C.)*
   - **Check:** `state` transitions appear in the protocol and `metabolism_history` shows the band
     working (no per-cycle flip-flop).

5. **The two conflict numbers are explained.**
   - The panel now reports `open_conflicts` = live (`open` + `under_review`, matching
     `core.open_conflicts()`) alongside `tolerated` / `closed` / `by_status`, so the panel and the
     dashboard reconcile. *(Phase A.)*
   - **Check:** `conflict_depth.by_status` present; panel `open_conflicts` == `len(core.open_conflicts())`.

6. **A replay after reconsolidation is stable.**
   - After any `--apply` sweep, a cold load replays cleanly and within the cold-replay budget (the
     O(n²) incident's guard); no orphaned references, no hash drift.
   - **Check:** operator runs `python -m joni.autonomy verify` and a cold load; `cold_replay` level ok.

## What is explicitly NOT a restart criterion

- The metacognition supervisor staying shadow — it is interesting but not the acute therapy, and
  it holds no authority. It may remain off.
- The full sandbox trial stack (P1–P3) being complete — P0 (the safe harness) is in; P1–P3 are a
  separate, later track. Restart does not depend on them, only on criterion 3 being satisfied one
  way or the other.

## The consolidation regime before restart (point 7)

Before normal autonomy resumes, run a short **consolidation-only** phase — "digest, don't eat":
`JONI_CONSOLIDATE_ONLY=1` forces the no-intake path every cycle regardless of load (no research
ingest, no new methods/topics/syntheses), while the shedding and conflict passes keep running. This
is the explicit switch for the deliberate pre-restart digest; the metabolism only throttles when
*overloaded*, so it does not by itself guarantee a quiet consolidation window. Run these cycles with
no public activity and no new self-improvement work; when the backlog and conflicts have clearly
fallen and a replay is stable, move on to the resume procedure.

## Resume procedure (once the gate is green)

1. Run the consolidation regime above (`JONI_CONSOLIDATE_ONLY=1`) until the backlog has fallen.
2. Set `JONI_METABOLISM=1` (and thresholds tuned from the shadow load) in the workflow, and clear
   `JONI_CONSOLIDATE_ONLY`.
3. Un-comment the `schedule:` block (or trigger once via `workflow_dispatch`).
4. Watch the first few cycles: metabolism state, collapse panel, no new token-hypotheses.
