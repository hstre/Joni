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
| Test set | **9 cases** — a demonstration set, *not* a validation corpus |
| Verdict variance (1 draw/statement) | 6/9 – 9/9 across 5 runs on identical input |
| Verdict variance (5 draws/statement) | **7/9 – 9/9** across 7 runs on identical input |
| Parser calibration | **none performed** against an inter-annotator gold standard |
| Model dependency | verdicts shift with the parser model (measured) |
| Residual disagreement | 1 of 9 is a *contested* gold item — the parser consistently (agreement 1.0) picks a defensible alternative reading of a conditional |

We report this because a caller must be able to see the state of the evidence before relying on a
verdict. Please treat the numbers above as the reason to run it on **your** data rather than as a
claim about how well it works.

---

## The architectural split

A language model is used for **exactly one thing**: normalising each statement into a fixed
structure drawn from closed vocabularies.

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
  "violations": ["unsupported_generalization", "scope_expansion"],
  "justification": [
    "Claim quantifiziert 'generic', Evidenz nur 'existential'",
    "Claim spricht auf Ebene 'class', Evidenz nur 'instance'"
  ],
  "structures": { "claim": {...}, "evidence": [...] },
  "determinism": {...}
}
```

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

**Cost:** `k` model calls per statement. An L3 row with *n* entries citing *m* distinct evidence
items costs roughly `k · (n + m)` calls.

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
