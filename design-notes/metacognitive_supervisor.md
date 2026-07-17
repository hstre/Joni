# Metacognitive supervisor — functional, externalized, shadow-only

*Status: incremental build. This push lands the tested **foundation** (schema + append-only
audit + honest metrics); the real adapters, the shadow hook, and the offline benchmark follow
in subsequent commits. Nothing here holds decision authority.*

## 1. Conceptual delimitation
This is **functional externalized metacognition** — *system-level metacognitive monitoring
and control*. It is emphatically **not** an LLM prompted to "reflect" on its own prose, and it
makes **no** claim of consciousness, sentience, or phenomenal introspection. Only **structured
signals from the responsible subsystem** enter the record; a model's free text is never
classified as self-knowledge.

## 2. Why this is externalized metacognition
Metacognition = monitoring one's own cognition and regulating it. Here that is realized
*externally and structurally*: per decision we record which monitoring signals existed, what
the system predicted about its own success, which control it chose, what it cost, and what
belastbare outcome was later observed — then we score how well that self-monitoring tracked
reality. The "self-model" is a measured, auditable object, not an assertion.

## 3. What Joni already had
Layer 9 as the authoritative epistemic state; claims/evidence/provenance/conflicts; the router
and budget control; Doktores + the probabilistic verifier; character + constitution gates;
deterministic actions (ALLOW/ABSTAIN/ESCALATE/BLOCK); an append-only audit and replay-stable
transitions.

## 4. What the supervisor adds
The missing layer is **systematic measurement**: signal-availability → predicted success/error
→ chosen control → route & cost → later observed outcome → **calibration & utility**, per
decision seam and task family. It answers: *when do Joni's own check-signals bear, when are they
dark, and which regulation was actually better under those conditions?*

## 5. Monitoring signals (structured only)
Verifier scores + dispersion; evidence coverage; open conflicts; provenance class; guard
liveness; budget status; presence/absence of a checker; route + tool result; Layer-9 status
transitions; human decisions; test/CI results. Numeric signals are validated to lie in [0,1];
categorical context is a closed enumeration or an id. **No** raw prompts/answers/secrets.

## 6. Control actions (closed enum)
`proceed · retrieve · verify · ask_human · abstain · defer · escalate`. A `plain_control` may
be recorded when a parallel non-supervised path exists (for intervention-utility comparison).

## 7. Outcome sources (a result is otherwise `unknown`)
`success/failure/mixed` require at least one belastbare source: a deterministic checker, a gold
label, an existing test, a CI result, a later Layer-9 status, an explicit human decision, a
reproducible tool success, or a documented PR outcome. **`unknown` is never silently
reinterpreted** as success/failure or any negative class. A merged PR with green CI means
`implementation_accepted_and_tests_passed` — mapped to `success` only when the episode
predicted exactly that target.

## 8. Limits of the measurement
Outcome coverage is partial; many episodes stay `unknown`. Calibration is refused below a
documented minimum (`insufficient_evidence`, never `well_calibrated`). No global score is
offered that would hide domain differences — metrics are grouped by task family / decision seam
/ signal source / model family / full-text vs abstract. `meta-d'`/M-ratio are out of scope here
(they need a controlled type-1/type-2 benchmark, not open production tasks).

## 9. Shadow mode
The supervisor **blocks nothing, changes no decision, moves no threshold, flips no enforce
mode, and triggers no extra paid model call** unless separately and explicitly configured. It
does not touch the router, gate, or persona. It is off by default and, when on, is a read-only
post-cycle observer (the `_maybe_router_shadow` pattern).

## 10. Metrics
Brier; ECE with fixed, documented bins (10 equal-width over [0,1]); AUROC **only** when both
classes are present; risk/accuracy-coverage; proceed-vs-abstain/defer/escalate behaviour; added
cost/calls; intervention utility vs a parallel plain path. Computed only over belastbare binary
outcomes, per group, with an explicit refusal when data is thin.

## 11. Benchmark (staged)
A small deterministic offline suite that **separates task performance from metacognitive
performance**: fixtures where the system is right and knows it, wrong but knows it, wrongly
confident, needlessly abstaining, stale, conflicted, provenance-missing, tool-required,
budget-exhausted, fluent-but-unsupported, guard-dark, correct-proceed, correct-abstain,
wrong-proceed, needless-abstain. The suite must show that accuracy and metacognitive
sensitivity are distinct.

## 12. Adoption gate (a later, separate, human-approved PR)
This work ends **before** enforce. A later PR may only propose enforce after: enough belastbare
outcomes across several task families; comparison vs a plain baseline **and** a naive-confidence
baseline; no safety or liveness regression; bounded extra cost; no degradation on
unknown/unverifiable cases; domain-specific thresholds; human sign-off; and — if any core change
is required — a deliberate core reseal. **No enforce is switched on in this work.**

## 13. Safety & privacy boundaries
No writes to the protected core (`src/desi_layer9/`, `joni_core.lock`, character/constitution
gates, authoritative Layer-9 transitions). The trace stores ids, structured categories, bounded
hashes, short pre-cleaned reasons, existing refs, and numeric signals — never full
prompts/papers/answers/secrets. Projections and dashboards are bounded; the full append-only
history stays on disk.

---

## Build status (this push)
- `metacognition/models.py` — versioned `Episode` + append-only `OutcomeEvent`; closed enums;
  strict validation (unknown fields, wrong types, out-of-[0,1] rejected); deterministic
  `episode_id`; `unknown` stays `unknown`.
- `metacognition/audit.py` — append-only JSONL; a later outcome is a new event referencing
  `episode_id`, never a rewrite; bounded read projection.
- `metacognition/metrics.py` — Brier/ECE(fixed bins)/AUROC(both-classes-only)/coverage;
  refuses below the minimum.
- `tests/test_metacognition.py` — schema/validation, append-only outcome, honest-refusal.

## Build status (adapter slice)
- `metacognition/method_gate.py` — the FIRST real adapter (a second-path gate per the taxonomy):
  a pure view over an emergent method → an episode (deterministic signal blend, derived
  knowledge boundary) and, later, a belastbares outcome from the method's Layer-9 status
  (rejected/retired→failure, active/confirmed→success, provisional-with-net-pass→success,
  candidate/maturing→None, still unknown). No desi_layer9 import → fully unit-tested.
- `metacognition/supervisor.py` — `observe()`: logs one episode per newly-minted method, then
  resolves pending episodes whose method reached a terminal status. Read-only over the core;
  append-only to the log; the desi_layer9 read is isolated and injectable for tests.
- `run.py::_maybe_metacognition_shadow` — the post-cycle hook, **off by default**
  (`JONI_METACOG_SHADOW=1` to enable), fail-safe, observation-only (the `_maybe_router_shadow`
  pattern). Off ⇒ a normal run is completely unaffected.
- `tests/test_metacognition_adapter.py` — pure adapter + the log-once-then-resolve flow, incl.
  "a still-pending method is never coerced".

## Build status (benchmark slice)
- `metacognition/benchmark.py` — the 15-fixture deterministic offline suite (known-and-knows,
  unknown-and-knows, unknown-but-overconfident, known-needless-holdback, stale, conflicting,
  missing-provenance, tool-required, budget-exhausted, fluent-unsupported, guard-disabled,
  correct-proceed, correct-abstain, wrong-proceed, needless-abstain). Each fixture has a gold
  label; `evaluate()` reports **task accuracy vs metacognitive accuracy** and the fixtures where
  the two diverge (good task / bad metacog, and bad task / good metacog). Pure, no model, no core.
- `tests/test_metacognition_benchmark.py` — the 15 scenarios are present, every fixture builds a
  valid episode, the two accuracies diverge, withheld outcomes stay `unknown` (never coerced), and
  calibration runs over the gold-labelled binary outcomes.

## Capability table (honest, evolving)
"Now measurable" = the supervisor records the structured signal and can score it once enough
belastbare outcomes exist; it does not claim the capability is *good*, only that it is *measured*.

| Capability | Already present | Now measurable | Still open |
|---|---|---|---|
| Knowledge boundaries | ACTIVE/CANDIDATE + provenance in Layer 9 | `knowledge_boundary` enum per episode (incl. `monitor_dark`) | validated boundary labels across many task families |
| Uncertainty | verifier scores, support values | `predicted_success` + calibration (Brier/ECE) once resolved | uncertainty on open production tasks (thin outcomes) |
| Conflict detection | conflict engine + open conflicts | signals recorded; conflict-path outcome resolution | a wired conflict adapter with reopen/supersede outcomes |
| Evidence appraisal | evidence coverage, provenance class | signals per episode | calibration of appraisal vs later truth |
| Strategy / control choice | ALLOW/ABSTAIN/ESCALATE/BLOCK | `selected_control` + a plain-path comparison field | measured control-utility vs a real plain baseline |
| Tool choice | router + tool results | `route` / `model_or_tool` recorded | tool-choice outcome scoring |
| Cost control | budget + `calls.jsonl` | `expected_cost`/`actual_cost` per episode | added-cost vs added-value at enforce |
| Later error detection | Layer-9 transitions, tests, CI | append-only outcome events (method gate live; Doktores staged) | broad outcome coverage; low unknown-rate |
| Calibration | ECE report existed (predictive layer) | grouped Brier/ECE/AUROC, refused when thin | enough per-domain data to trust it |
| Cross-domain generalisation | — | per task_family / seam grouping (no hidden global score) | multiple task families with enough outcomes |
| Introspection on model activations | — | — | out of scope (no activation access) |
| Consciousness | — | — | **Not the subject and not claimed.** |

## Build status (second adapter — conflict seam)
- `metacognition/conflict_gate.py` — a second real, distinct decision seam (`conflict.resolution`):
  a pure view over a Layer-9 conflict (severity, breadth, kind) → an episode with a deterministic
  resolvability estimate; and `resolve()` maps the conflict's later status to a belastbares outcome
  with **both classes** — resolved→success, open-past-a-stale-window→failure, recently-open→None
  (unknown, never coerced).
- `supervisor.observe_conflicts()` + the run.py hook now calls it too (still off by default). Two
  real adapters (method gate + conflict seam) now log and resolve, neither changing behaviour.
- `tests/test_metacognition_conflict.py` — pure adapter (both outcome classes) + the log-once /
  resolve-on-status / resolve-on-staleness / never-coerce-recent flow.

## Build status (shadow-evaluation report)
- `metacognition/report.py` + `scripts/metacognition_report.py` — a bounded, pure projection:
  overall coverage + unknown/monitor_dark rates, per-task-family and per-seam calibration (refused
  when thin), control mix, cost, and an explicit `plain_vs_shadow = not_available` (no plain path
  yet). `python scripts/metacognition_report.py` runs it self-contained over the benchmark; pass
  `--source state/metacognition.jsonl` for a real log. Demo over the benchmark shows the thesis:
  task_accuracy 0.375 vs metacognitive_accuracy 0.533 — the two genuinely diverge.

## Build status (Adapter A — Doktores coherence verifier)
- `metacognition/doktores_gate.py` — Joni's Doktores is a probabilistic verifier over its OWN
  ideas: a structured `coherent` yes/no verdict per hypothesis (recorded in
  `extensions['doktores_hyp_log']`). That verdict is the signal; the belastbares outcome is the
  hypothesis-claim's LATER Layer-9 status (active/confirmed→success, rejected/superseded→failure,
  candidate→unknown). Deterministic, in-state - **no PR/CI reader needed** for this seam.
- `supervisor.observe_doktores()` + the run.py hook (still off by default) — three real adapters
  now log and resolve (method gate, conflict seam, Doktores coherence), none changing behaviour.
- `tests/test_metacognition_doktores.py` — pure adapter (both classes) + log-from-extensions,
  resolve-from-claim-status, never-coerce-candidate.

Honest scope note: the richer multi-dimensional verifier the brief sketches (per-dimension means,
dispersion, red flags, veto) is not present in Joni's Doktores today - it lives in the DESi
Semantic Layer. The literature-review Doktores → commission → PR path, whose outcome IS PR/CI
state, needs a separate GitHub-state reader and remains a documented future adapter.

## Build status (literature-Doktores + PR/CI outcome reader)
- `metacognition/doktores_literature_gate.py` — the literature arm of Doktores: an episode per
  applicable self-improvement review commission, carrying the structured signals (`applicable`,
  `component_key`, the model tier that judged it, full-text vs abstract). Control = `ask_human`
  (it files an Auftrag for a human-gated PR).
- `metacognition/pr_outcomes.py` — belastbare PR/CI outcomes from observable sources, all PURE and
  tested: `index_from_commissions_done` (an implemented commission = success, this source has no
  failures) and `index_from_issues` (GitHub joni-auftrag PRs: merged→success, closed-unmerged→
  failure, open→skip). This module performs **no egress** — the shadow observer opens no socket in
  the loop (docs/EGRESS_GATE.md). The live GitHub read is an operator-run convenience in
  `scripts/metacognition_report.py --github OWNER/REPO` (the `scripts/` tree is gate-exempt): it
  fetches the closed joni-auftrag issues and feeds the JSON into the pure `index_from_issues`.
- `supervisor.observe_doktores_literature()` + the run.py hook build the index from
  `commissions_done.json` only (local, cheap, zero network), then resolve. Unmatched commissions
  stay `unknown` — the commission→PR link is best-effort (by component key), so this is expected
  and honest.
- `tests/test_metacognition_doktores_literature.py` — the adapter, both PR-index parsers, and the
  observer's log-then-resolve / never-coerce-unmatched flow.

Four real adapters now log and resolve (method gate, conflict seam, Doktores coherence, Doktores
literature), none changing behaviour; all off by default.

## Remaining
Only an operator decision: whether to open a PR for this branch, and - much later, separately, with
human approval - the enforce PR gated by the pre-registered adoption conditions (section 12).
Enforce stays out of scope here by design.
