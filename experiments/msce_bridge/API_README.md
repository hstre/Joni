# DESi Claim–Evidence Entailment Auditor — Prototype

A read-only epistemic gate for the **L2 → L3 consolidation boundary**, built in response to the
MSCE team's invitation to prototype a DESi-based validation layer.

It answers exactly one question:

```
given evidence + declared assumptions   ⟹   L3 claim ?
```

It does **not** answer whether the claim is *true*, whether it is *useful*, or how *ambiguous* the
sentence is. A verdict of `compatible_not_entailed` means: *the cited evidence does not fully carry
this claim* — a statement about the derivation, not about the world.

---

## Status: prototype under evaluation

This is not a validated service, and the API says so itself. `GET /v1/capabilities` returns the
measured limits as part of the contract:

| | |
|---|---|
| **Architecture** | **v2 — model proposes, controls constrain** |
| Dev set (external, independently built) | **18/20 and 16/20** across 2 runs · **zero false passes** · 0–1 downgrades |
| Model baseline alone (no controls) | 17–18/20 across 3 runs · zero false passes |
| Superseded v1 (rules judged) | **7/20** with **3 false passes** |
| Control layer status | **inert on this data** — no control has yet caught a real model failure; the catalogue is *unvalidated* |
| Blind set (40 cases) | **sealed** — not yet run, one-shot |
| Test set (internal demo, superseded) | 9 cases — a demonstration set, *not* a validation corpus |
| Verdict variance (1 draw/statement) | 6/9 – 9/9 across 5 runs on identical input |
| Verdict variance (5 draws/statement) | 7/9 – 9/9 across 7 runs on identical input |
| Verdict variance (5 draws + proposition splitting) | **6/9 – 9/9** across 4 runs; violations 4/7 – 7/7 — splitting fixed a dangerous defect but did **not** narrow the band |
| Parser calibration | **none performed** against an inter-annotator gold standard |
| Model dependency | verdicts shift with the parser model (measured) |
| Residual disagreement | 1 of 9 is a *contested* gold item — the parser consistently (agreement 1.0) picks a defensible alternative reading of a conditional |

We report this because a caller must be able to see the state of the evidence before relying on a
verdict. Please treat the numbers above as the reason to run it on **your** data rather than as a
claim about how well it works.

---

## The architecture (v2): model proposes, controls constrain

```
model        proposes verdict + reasoning   (k draws, strict majority)
   ↓
controls     deterministic, check measured danger patterns
   ↓         (may ONLY move down the ladder)
DESi         accept · downgrade · require review
   ↓
Layer 9      persists only what was governed
```

**The load-bearing invariant.** Controls move a verdict only **down** the pass ladder
(`entailed` > `partially_entailed` > `compatible_not_entailed` > `insufficient`). They never create
a verdict, never raise one, and **never assert `contradicted`** — claiming a contradiction is a
positive statement, and rules demonstrably fail at that (our own lexical negation heuristic scored
43 % false contradictions).

**This reverses the error direction.** In v1 a parser slip could produce a *false pass* — a dropped
conjunct became `entailed`. In v2 the parser only feeds the controls, so a slip either misses a
control (the model's verdict stands) or fires one wrongly (a downgrade). **Both are the safe side.**

**Why one control is switched off.** `evidence_padding` is registered but inactive. We inherited the
control catalogue from v1's defect list without checking whether v2 inherits those defects — it does
not. The model is immune to the padding attack (identical verdict, agreement 1.0 with and without
padding), while the control produced three false blocks on the dev set and caught zero attacks.

> A control catalogue must be derived from the **measured failures of the system it guards**, not
> from its predecessor's.

Re-enabling it is a registry change, not a code change.

### What the model is used for

Judging the derivation — and, separately, normalising each statement into a fixed structure that
the controls read.

```
relation    : causes | prevents | correlates_with | is_a | part_of | has_property
              | requires | enables | contradicts | supports | measured_as | recommends
modality    : negated | hypothetical | possible | probable | asserted
quantifier  : singular | existential | generic | universal
scope_level : instance | subclass | class
conditions  : qualifiers the statement depends on
```

Every verdict is then computed by **deterministic rules** over those structures. A quantifier jump
is an ordinal comparison, not a keyword match. No model decides anything.

Each response carries both layers separately, so you can audit where each part came from:

```json
"determinism": {
  "model_derived": ["structures"],
  "rule_derived":  ["verdict", "violations", "justification"],
  "parser_model":  "deepseek-v4-flash",
  "draws_per_statement": 5
}
```

**Compound statements are decomposed, never truncated.** A statement asserting several things is
split into atomic propositions (majority vote on the count) and each is audited separately. The
overall verdict is the **weakest part**: one contradicted conjunct makes the whole claim
contradicted, and `entailed` requires *every* part to hold. If the split itself has no majority,
the verdict is `insufficient` rather than a judgement on a partial parse.

This closes a defect we found by direction-testing: before decomposition, a claim was normalised to
its **first conjunct only**, so a claim explicitly denying X could be reported `entailed` by
evidence asserting X. A false `entailed` is the most dangerous verdict this system can produce, and
your own L3 output contains exactly this shape ("… are candidates only; they do not have decision
authority"). The response now carries `propositions` and `per_proposition` so you can see how a
statement was split and which part failed.

**Irrelevant evidence cannot help.** Relevance requires entity overlap, not merely a matching
relation. Without that, padding a claim with unrelated universally-quantified statements ("Every
container image has a base layer") raised the aggregate and flipped the verdict to `entailed` —
more evidence was monotonically better, and a generator that picks its own evidence ids could
exploit it. **What the auditor still cannot see: relevant evidence that was *not* cited.** It
judges the derivation from what you give it.

**Normalisation is sampled, not asked.** Each field is drawn *k* times and decided by strict
majority. A field without a majority is *undetermined*, and the verdict becomes `insufficient` —
never a guessed judgement. (Asking a model for its own confidence returns a one-hot vector; asking
it repeatedly and counting is what produces a distribution.)

---

## Endpoints

```
POST /v1/audit          one claim
POST /v1/audit/batch    up to 50 claims
GET  /v1/capabilities   what it does, and its measured limits
GET  /v1/health
```

OpenAPI schema at `/openapi.json`, interactive docs at `/docs`.

### Request

```json
{
  "claim_id": "world_1/inference/3",
  "claim": "Binary wheels are incompatible with musl systems.",
  "evidence": [
    {"source_id": "tr_3", "text": "Alpine uses musl."},
    {"source_id": "tr_4", "text": "A binary wheel failed to load in one Alpine container."}
  ],
  "declared_assumptions": [],
  "context": "MSCE L3 candidate"
}
```

### Response

```json
{
  "verdict": "compatible_not_entailed",
  "model_verdict": "compatible_not_entailed",
  "model_agreement": 1.0,
  "downgraded": false,
  "vetoes": [],
  "violations": ["unsupported_generalization", "scope_expansion"],
  "justification": ["Modellurteil 'compatible_not_entailed' (Zustimmung 1.0)"],
  "determinism": {
    "verdict_proposed_by": "model",
    "verdict_constrained_by": "deterministic controls",
    "controls_can_upgrade": false,
    "active_controls": ["conjunction_coverage", "epistemic_hedge", "modality_escalation",
                        "quantifier_escalation", "scope_escalation"]
  }
}
```

`model_verdict` is what the model proposed; `verdict` is what survived the controls. When they
differ, `vetoes` says which control fired and why. **`verdict` is never stronger than
`model_verdict`** — that is an invariant, and it is tested.

### Verdicts

| | |
|---|---|
| `entailed` | relation, modality, quantifier and scope are all covered |
| `partially_entailed` | the core holds; a qualifier from the evidence was dropped |
| `compatible_not_entailed` | not contradicted, but the evidence does not carry it |
| `contradicted` | an item of evidence asserts the same proposition, denied |
| `insufficient` | no evidence, or the normalisation was not determinate |

### Violations

`missing_premise` · `causal_upgrade` · `modal_strengthening` · `scope_expansion` ·
`unsupported_generalization` · `entity_shift` · `condition_dropped`

---

## Running it

```bash
pip install fastapi uvicorn
export DEEPSEEK_API_KEY=...          # your key; the service holds no credentials
export ENTAIL_K=5                    # draws per statement (default 5)
export ENTAIL_PARSER=beta            # which parser model
uvicorn api:app --host 0.0.0.0 --port 8080
```

Nothing is stored, nothing is written back, no state is kept between requests. Run it yourself — we
would rather you did not send data anywhere.

**Cost:** `k` model calls to split each statement, plus `k` per resulting proposition. A simple
claim with one evidence item costs about `4k`; a two-conjunct claim roughly `6k`. An L3 row with
*n* entries and *m* evidence items scales as `k · (n + m) · (1 + average conjuncts)`.

If that is too expensive at volume, the cheap mitigation is a pre-filter that sends only compound
or otherwise suspicious statements through the full path — we have not built it.

---

## What would make this worth adopting

The honest next step is not more features. It is **one measurement**:

> Of the L3 entries this gate flags as not entailed — how many were actually wrong?

That number is useful in both directions. If most flagged entries were fine, the gate is too strict
and we learn where. If most were genuinely unsupported, you have a working filter at a boundary
that currently only checks structure.

We would also need a **parser suitability test**: a set of hand-annotated statements each candidate
parser must pass before use, with its result sealed alongside the model id — because a silent model
swap changes verdicts (we measured this). Note that such a gold standard contains genuinely
contested items, so inter-annotator agreement is the ceiling for any parser, not 100 %.
