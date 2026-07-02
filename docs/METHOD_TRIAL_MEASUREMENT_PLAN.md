# Plan: do stored thinking-methods actually transfer? — measuring method value honestly

**Status:** plan / gated core-ask. Nothing here is built yet. This is the falsification-first,
budget-quarantined path to replace the *synthetic* method-trial mock with a **measured** signal that
retirement (and the condition guard, `trials.retire_unproductive`) can honestly rest on.

**v2 (2026-07-02):** hardened after operator + external review, before any spend. The review's point
stands — as a *measurement plan* it was solid; as *load-bearing evidence* it needed more controls,
cleaner data-point independence, a proxy holdout, and no strong claim from a tiny battery. All folded in
below.

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
transfer at all, measurably, above a battery of controls?"** If the answer is *no*, the honest outcome
is to retire the *idea of trialing methods by effect*, not to perfect a measurement of nothing. The plan
is therefore as much about validating the **premise** as building the apparatus, and the cheapest
falsification comes first.

## The precise claim we are testing

> Disciplining a problem-solving attempt with stored method **M** produces a measurable improvement
> over an undisciplined baseline, on tasks **outside M's origin domain**, larger than the improvement
> from **each** of a battery of controls (neutral preamble, scrambled method, irrelevant plausible
> method) — reliably enough (effect size + CI, on independent data points) to decide retain vs retire.

The governing asymmetry: **a false promotion (keeping/activating a worthless method) is worse than a
false retirement.** So every threshold is set to protect against false positives first; the
false-positive rate is the safety-critical number throughout.

## Stages — each with a go/no-go gate, cheapest falsification first

### Stage 0 · Frame & PRE-REGISTER — **no LLM, cost 0**
Write the falsifiable claim and lock the analysis **before any data is seen** — this is what stops
post-hoc rationalisation. Pre-register, in the repo, all of:
- **primary metric** (a machine-checkable scalar; higher = better, with a `lower_is_better` flag);
- **minimum effect δ** worth acting on, and the **CI method**;
- **independence unit** — the thing one data point *is*: a task, a task-variant, a prompt-template, or a
  model-family. (See Stage 2/3: repetitions of a deterministic run are **not** independent data.)
- **success threshold vs EACH control**, not only vs the plain baseline;
- **false-positive policy**: false promotion ≫ false retirement; thresholds protect against FP first;
- **proxy acceptability threshold** (max tolerated false-positive rate for any cheap in-loop proxy),
  fixed *before* Stage 4 results exist;
- **method-plausibility definition** (see below) — declared before any method meets a task.
- **Gate:** metric is machine-checkable and the whole decision rule is written down before data.

**Non-circular method plausibility.** "A genuinely-good method" must be defined *without* looking at any
trial result — otherwise the battery is unconsciously built to flatter it. A method counts as
*a-priori plausible* only via a pre-registered rationale (an independent operator/human judgement, or a
cited external result), recorded before Stage 1, never from the trial outcome. The pilot then tests
whether the a-priori-plausible methods actually win; agreement is the finding, not the assumption.

### Stage 1 · Gold **Micro** Battery — **no LLM, cost = authoring time**
A *pilot-only* battery: 10–20 foreign tasks per a few domains with **objectively checkable** answers
(exact / numeric-tolerance / regex) — checkable answers mean **no LLM judge**, removing the biggest
source of self-delusion by construction. This size is explicitly a pilot, **not** an authority for
retain/retire (see the power note in Stage 3).

Each task must **declare** (in the fixture):
- **target skill** it exercises;
- **expected helpful method class** (which kind of method *should* help — pre-registered, not tuned);
- **forbidden origin domain** (no method may be trialed on a task inside its own origin);
- **deterministic checker** (the verifier, no model);
- **plausible failure modes** (how a wrong attempt looks);
- **why it is not solvable by superficial verbosity alone** — the task must resist "more words = better".

- Deliverable: `task_sets/gold_micro_v1/` + a checker per task. **Gate:** every answer verifiable
  without a model; every task carries all six declarations; no task inside a candidate's origin domain.
- **Mandated follow-on:** a larger **held-out battery** (authored to the same contract, never seen
  during pilot/proxy work) is required *before* any retain/retire decision. The micro battery falsifies;
  the holdout battery is what a real decision rests on.

### Stage 2 · The pilot — does the premise hold against a CONTROL BATTERY? — **small, budgeted LLM spend, offline, NOT the loop**
Intervention = solve the task with M's steps prepended as an explicit discipline. It must beat **each**
of four conditions, not just the bare baseline:

| condition | what it isolates |
|---|---|
| **plain baseline** | the naked solver, no preamble |
| **length-matched neutral preamble** | token / attention effect ("more prompt = more care") |
| **scrambled method** (same length, structure destroyed) | loss of *structure*, tone kept |
| **irrelevant plausible method** (a real but off-target method) | "methodical tone" without relevance |

Only if M beats **all four** (its CI vs each excludes 0 in the helpful direction) is there a genuine
method signal. If it beats baseline but not the neutral preamble or the irrelevant method, the effect is
verbosity / tone, **not** method value → stop, and report that stored-method trialing measures nothing.
This is the linchpin gate, run at pilot scale before any spend at scale.

- Deliverable: pilot result (effect δ + CI vs each control) on ≤2 a-priori-plausible methods.
- **Gate:** at least one plausible method beats all four controls, OR the premise is falsified and we
  stop here (a valid, documented outcome).

### Stage 3 · Validity, independence & power — **the adversarial pass on the pilot**
- **Independence unit is the crux.** With temperature 0 the setup is deterministic, so *repeating the
  same run yields no new information* — naive "repetitions" would inflate the CI into claiming more
  evidence than exists. A data point must vary along the pre-registered unit: **distinct tasks,
  task-variants, fixed prompt-templates, and/or model families**; fixed seeds count as reps *only* where
  genuine stochasticity exists (temperature > 0). Compute power on that real N.
- **Controls behave:** neutral preamble ≈ baseline, scrambled ≈ baseline, irrelevant ≈ baseline. If any
  control wins, the metric measures length/tone, not method — fix or abandon.
- **No leakage:** methods trialed only outside origin domain (Kevin's `_pick_task` enforces it); verify.
- **No self-grading:** the solving call and any judging call are never the same model turn; prefer the
  Stage-1 checkable answers so no judge is needed at all.
- **Power / cost:** how many independent units to detect δ at the chosen CI, and the **€ per method
  trial** it implies. If that exceeds what the loop can ever afford, that is a finding forcing Stage 4.
- Deliverable: validity checklist + a power/cost table on the correct independence unit. **Gate:** all
  confounds cleared and N is real, not inflated.

### Stage 4 · Calibrate a cheap in-loop proxy — with a HOLDOUT — **the affordability bridge**
The measured trial is too expensive to run per-method per-cycle in a €20/week loop. So run it **offline**
on a labelled panel of methods (a-priori-plausible ones + deliberate junk) → ground-truth per method.
Then test whether a **cheap deterministic feature** (Kevin's keyword-shape, or a better one) predicts the
truth — **but split methods AND task sets into train/calibration vs holdout.** A proxy tuned and scored
on the same panel overfits and lies.
- Report, on the **holdout**, the confusion matrix with **false-positive and false-negative rates
  separately**. The **false-positive rate is the safety-critical number** (a proxy that wrongly keeps
  junk is the dangerous failure). Compare it to the Stage-0 pre-registered acceptability threshold.
- If the holdout FP rate clears the threshold → the loop may use the proxy for gating, re-validated
  periodically by the offline measured trial. If it does not (or correlation ≈ 0) → **the synthetic mock
  is not a valid retirement basis**; gate only on the (rare, offline) measured trial, or not at all.
- Deliverable: holdout confusion matrix (FP/FN separate) + decision (adopt proxy / offline-only / do not
  gate on effect).

### Stage 5 · Wire the validated signal into retirement — **only if 2–4 pass**
Feed the validated per-method, per-condition pass/fail (measured offline + calibrated proxy in-loop) into
`method_ledger`; the condition guard from `83a1ac7` now fires on real signal. Operator-gated, fully
logged, reversible. Replace the synthetic verdict's role in retirement, don't stack on it. Retain/retire
decisions use the **held-out** battery, never the micro battery.

## Cross-cutting rules
- **Falsification first:** the Stage-2 control-battery gate is the whole game — spend nothing at scale
  until M has beaten a neutral preamble, a scrambled method, **and** an irrelevant plausible method.
- **FP over FN:** a false promotion is worse than a false retirement; every threshold protects against
  false positives first; the FP rate is the number that governs adoption.
- **Real independence:** data points vary along the pre-registered unit; deterministic reps are not data.
- **Budget quarantine:** measured trials run offline, never per-cycle in the live loop, until Stage 4's
  holdout proves a cheap proxy (or we accept rare offline gating).
- **Holdout everywhere it matters:** a larger held-out battery for decisions; held-out methods *and*
  tasks for proxy calibration.
- **Determinism + provenance:** fixed templates/seeds, `task_set_sha`, recorded solvers — replay to the
  same verdict.
- **No self-grading, no leakage:** checkable answers over LLM judges; trial only outside origin domain.
- **Maturity honesty:** every stage is Stufe 1/2/3 with explicit evidence; a null result at any gate is a
  valid, recorded outcome. We may conclude that *method trialing by effect* is not worth its cost — and
  if so, we say it and retire the subsystem rather than dress up a synthetic number.

## First concrete step (when we pick this up)
Stage 0 + Stage 1 — zero budget, no model — produce the pre-registered spec (with the method-plausibility
definition and the four-control comparison locked) and the gold **micro** battery with per-task
declarations and deterministic checkers. Only then does Stage 2 spend a small, bounded amount on the one
experiment that matters: **does a real method beat a neutral preamble, a scrambled method, and an
irrelevant plausible method — all three?** Everything downstream is gated on that answer.
