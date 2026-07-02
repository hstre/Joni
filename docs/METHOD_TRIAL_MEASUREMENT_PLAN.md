# Plan: do stored thinking-methods actually transfer? — measuring method value honestly

**Status:** plan / gated core-ask. Nothing here is built yet. This is the falsification-first,
budget-disciplined path to replace the *synthetic* method-trial mock with a **measured** signal that
retirement (and the condition guard, `trials.retire_unproductive`) can honestly rest on.

## Why this exists

Kevin's `trial_methods` is deliberately labelled a **synthetic mock** (`epistemic_weight="none"`): its
pass/fail is keyword-shape overlap, not evidence. The measured protocol (`real_trial_protocol_v1`)
exists but is **hardwired to one method** (`contradiction-first-review`) on one frozen conflict task
set — it does not generalise to an arbitrary shelf method, because a real measurement needs a task set
**and** solvers that actually *apply* that method. So today the whole trial→retire subsystem is
epistemically dormant in production (`JONI_SYNTHETIC_TRIALS=0`): nothing trials on real signal, nothing
retires on it, and the condition guard has no live effect. Consuming Kevin's condition (done: Joni
`83a1ac7`, Kevin `feecc15`) wired the plumbing; it did **not** create real signal.

**The load-bearing question is not "how do we measure cheaply" — it is "do stored thinking-methods
transfer at all, measurably, above a scrambled control?"** If the answer is *no*, the honest outcome is
to retire the *idea of trialing methods by effect*, not to perfect a measurement of nothing. The plan
is therefore as much about validating the **premise** as building the apparatus, and the cheapest
falsification comes first.

## The precise claim we are testing

> Disciplining a problem-solving attempt with stored method **M** produces a measurable improvement
> over an undisciplined baseline, on tasks **outside M's origin domain**, larger than the improvement
> from a **scrambled/irrelevant** method — reliably enough (effect size + CI) to decide retain vs
> retire.

Five things must be pinned before any spend: **(1)** the outcome metric, **(2)** the task battery,
**(3)** baseline / intervention / **negative control**, **(4)** the estimator + decision rule
(effect δ, repetitions, CI, power), **(5)** the honesty guards (no self-grading, no leakage,
determinism, provenance). `real_trial.TrialResult` already carries the shape for 1/3/4 (baseline vs
intervention vs negative_control, metric, repetitions, CI, `task_set_sha`) — reuse it.

## Stages — each with a go/no-go gate, cheapest falsification first

### Stage 0 · Frame & instrument — **no LLM, cost 0**
- Write the falsifiable claim (above) + the decision it feeds (retire iff measured effect < threshold
  with sufficient power), and **pre-register** δ, repetitions, CI width, and "negative control must be
  ≈ baseline". Pre-registration is what stops post-hoc rationalisation.
- Inventory reusable assets: `real_trial.run_real_trial(method_id, task_set, metric, …)`,
  `example_task_set`, `frozen_joni_conflict_cases_v1`, the solver seam
  (baseline / method / negative_control). Catalogue what a *new* method needs.
- Deliverable: this spec + a measurement-harness contract (interfaces). **Gate:** the metric is
  machine-checkable and the decision rule is written down before any data is seen.

### Stage 1 · A tiny GOLD battery with checkable answers — **no LLM, cost = authoring time**
- Hand-author 10–20 foreign tasks per a few domains whose answers are **objectively checkable**
  (exact / numeric-tolerance / regex): spot-the-contradiction, find-the-bug-in-this-snippet,
  estimate-with-bounds, rule-out-the-catastrophic. Checkable answers mean **no LLM judge** — the
  biggest source of self-delusion is removed by construction.
- Deliverable: `task_sets/gold_v1/` + a deterministic checker per task. **Gate:** every task's answer
  is verifiable without a model, and no task lies inside any candidate method's origin domain.
- *Honest bottleneck:* authoring genuinely method-discriminating tasks is the hard, human part. If we
  cannot write tasks where a method plausibly helps, that itself is a finding.

### Stage 2 · The pilot — does the premise even hold? — **small, budgeted LLM spend (offline, NOT the loop)**
- Mechanism: baseline = solve the task plain; intervention = solve it with M's steps prepended as an
  explicit discipline; **negative control = solve it with a *scrambled* method** (same length, no
  relevant structure). Metric = correctness on the checkable answer. Temperature 0, fixed prompts,
  provenance recorded.
- Run 1–2 methods × 1 battery, enough repetitions for a CI. **This is the linchpin gate:** if the
  intervention does **not** beat the scrambled control (only beats bare baseline), the effect is
  "any preamble helps / verbosity", **not** method value → stop, and report that stored-method
  trialing measures nothing. Cheapest possible falsification, run before any scale.
- Deliverable: pilot result (effect δ, CI, negative-control delta) on ≤2 methods. **Gate:**
  intervention − control CI excludes 0 for at least one genuinely-good method, OR we have falsified
  the premise and stop here (a valid, documented outcome).

### Stage 3 · Validity & confounds — **the adversarial pass on the pilot**
- Negative control ≈ baseline (else the metric measures length/verbosity — fix or abandon).
- No leakage: methods trialed only outside origin domain (Kevin already enforces `_pick_task`); verify.
- No self-grading: the solver call and any judging call are never the same model turn; prefer the
  checkable answers from Stage 1 so no judge is needed at all.
- Determinism + power: same (method, task_set, seed) → same result; compute how many tasks × reps are
  needed to detect δ at the chosen CI, and the **€ cost per method-trial** that implies. If that cost
  exceeds what the loop can ever afford, that is a finding that forces Stage 4.
- Deliverable: a validity checklist result + a cost/power table. **Gate:** all four confounds cleared.

### Stage 4 · Calibrate a CHEAP in-loop proxy against the measured truth — **the affordability bridge**
- The measured trial is too expensive to run per-method per-cycle in a €20/week loop. So: run the
  measured trial **offline** on a labelled panel of methods (some plausibly-good thinking moves, some
  deliberate junk) → ground-truth pass/fail per method.
- Then test whether a **cheap deterministic feature** (Kevin's keyword-shape, or a better one) predicts
  the measured truth: report `correlation(cheap_signal, measured_outcome)` and a confusion matrix. If
  it correlates acceptably, the loop uses the cheap proxy for gating while the measured trial
  re-validates it periodically. **If it correlates ≈ 0, the current synthetic mock is not a valid
  retirement basis** — a major, honest finding that says: gate on the (rare, offline) measured trial
  only, or not at all.
- Deliverable: correlation + decision (adopt proxy / require offline-measured / do not gate on effect).

### Stage 5 · Wire the validated signal into retirement — **only if 2–4 pass**
- Feed the validated per-method, per-condition pass/fail (measured offline + calibrated proxy in-loop)
  into `method_ledger`; the condition guard from `83a1ac7` now fires on real signal. Operator-gated,
  fully logged, reversible. Replace the synthetic verdict's role in retirement, don't stack on it.
- Deliverable: retirement runs on measured/validated signal; `JONI_SYNTHETIC_TRIALS` can retire.

## Cross-cutting rules
- **Falsification first:** the Stage-2 negative-control gate is the whole game — spend nothing at scale
  until a scrambled method has been shown *not* to win.
- **Budget quarantine:** measured trials run offline / in controlled experiments, never per-cycle in
  the live loop, until Stage 4 proves a cheap in-loop proxy (or we accept rare offline gating).
- **Determinism + provenance:** temperature 0, fixed seeds, `task_set_sha`, recorded solvers — a trial
  must replay to the same verdict.
- **No self-grading, no leakage:** checkable answers over LLM judges; trial only outside origin domain.
- **Maturity honesty:** every stage is Stufe 1/2/3 with explicit evidence; a null result at any gate is
  a valid, recorded outcome. We may well conclude that *method trialing by effect* is not worth its
  cost — and if so, we say it and retire the subsystem, rather than dress up a synthetic number.

## First concrete step (when we pick this up)
Stage 0 + Stage 1 authoring — zero budget, no model — produce the pre-registered spec and a first gold
battery with checkable answers. Only then does Stage 2 spend a small, bounded amount to run the single
most important experiment: **does a real method beat a scrambled one?** Everything downstream is gated
on that answer.
