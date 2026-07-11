# Probabilistic Verifier — an escalation stage for Doktores

**Purpose.** Doktores decides from ONE `joni-hard` call whether a paper/tool could improve a
non-core module and, if so, files an *Auftrag* (auto-implemented since #227). That single binary
judgement is fine when clear, but risky when borderline. The verifier adds a probabilistic,
multi-dimensional re-assessment on the *consequential* decisions — a **signal, never a truth**.

Grounded in *LLM-as-a-Verifier* (arXiv 2607.05391): continuous scores instead of discrete judge
labels, scaled by **repetition** (variance reduction) and **criteria decomposition**.

**Boundary kept — "LLM for language, rules for logic".** The model produces continuous per-dimension
scores; the escalation trigger, weighted aggregation, safety vetoes and final action are all
**deterministic**. Scores are decision signals, not facts.

## Where it sits
`doktores.review()`, after the applicable verdict + full-text grounding (#228/#229), *before* the
`_commission(...)` is built. Nothing in the existing Doktores logic is replaced.

```
source → Doktores verdict (applicable?) → full-text grounding → [should_escalate? → verifier] → file
```

## Modes (default: shadow)
- `JONI_VERIFIER_MODE=shadow` (default): runs alongside, **logs what it would do, changes nothing**
  (`extensions["verifier_shadow"]`). Both loops run in parallel so we can evaluate which was more
  sensible before adopting — the same observe-then-adopt discipline as the router shadow.
- `enforce`: a non-`file` action (abstain / read_full_text / run_additional_pass / human_review)
  holds back the auto-file.
- `off` (or `JONI_VERIFIER=0`): disabled.

## Dimensions (continuous 0..1, Joni's translation of the clinical spec)
`module_fit`, `evidence_grounding`, `consistency`, `alternatives`, `error_safety`, `impact`,
`info_needed` (inverted), `reasoning_stability`, `hard_constraint_compliance`, `overclaim_risk`
(inverted). **Plausibility and evidence are kept separate** — an eloquent, coherent proposal on weak
evidence is not filed.

## Safety vetoes (rules; safety overrides the score)
1. high-severity red-flag → `human_review`
2. a core/degrade/security red-flag, or `hard_constraint_compliance` below floor → `human_review`
3. `evidence_grounding` below floor → `read_full_text` (if more is needed) else `abstain`
4. `module_fit` below floor → `abstain`
5. oversold (`overclaim_risk` high & evidence low) → `abstain`
6. unstable run (`reasoning_stability` variance high) or borderline aggregate → `run_additional_pass`
7. else → `file`

## Configuration (env, no hardcoding)
`JONI_VERIFIER_MODE`, `JONI_VERIFIER_REPS` (3), `JONI_VERIFIER_MARGIN` (0.15),
`JONI_VERIFIER_INSTABILITY` (0.15), `JONI_VERIFIER_EVIDENCE_FLOOR` (0.35),
`JONI_VERIFIER_FIT_FLOOR` (0.40), `JONI_VERIFIER_MAX_COST_EUR` (0.05),
`JONI_VERIFIER_DISAGREEMENT` (0.20), `JONI_VERIFIER_USE_LOGPROBS` (0).

## Cost control
Runs only on to-be-filed commissions (≤1/cycle). Bounded repetitions; the per-verification cost is
capped (`max_cost_eur`) — the loop stops before overshooting rather than guessing. Budget-gated
through the normal model-call seam; a spent budget or all-malformed replies → `None`, and the normal
Doktores decision stands.

## Limits / next iteration
- No logprob path yet (Joni's broker exposes no logits) — the numeric-JSON path is the default and
  always works; `use_logprobs` is reserved for a future refinement.
- Doktores is a single judge reviewing one source, so there is no "score margin / doctor
  disagreement" trigger; the verifier's repeated scoring surfaces instability instead. When Doktores
  gains continuous triage scores, add the margin trigger in `escalation.py`.
- **Next:** an evaluation script comparing A (plain Doktores) vs C (verifier) on the accumulated
  `verifier_shadow` log — escalation rate, abstain/red-flag rate, and (where determinable) which was
  more sensible — before flipping `enforce` on.

## Files
`src/joni/autonomy/verifier/{__init__,config,models,escalation,scorer,safety,audit}.py`,
wired in `doktores.review()`. Tests: `tests/test_verifier.py`.

## Run the tests
`cd backend-equivalent repo root && python -m pytest tests/test_verifier.py -q`
