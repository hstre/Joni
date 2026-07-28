"""DESi Claim–Evidence Entailment Auditor — read-only HTTP interface.

A prototype of the validation layer the MSCE team proposed for the L2→L3 consolidation boundary:
submit a candidate L3 claim together with the evidence it cites, receive a verdict plus the
specific violations that produced it, with an auditable justification.

    POST /v1/audit         one claim
    POST /v1/audit/batch   a whole L3 row (many claims, shared evidence pool)
    GET  /v1/capabilities  what this service does — and its MEASURED limits
    GET  /v1/health

**Read-only by construction.** Nothing is stored, nothing is written back, no state is kept between
requests. The service returns a judgement about a derivation; it never modifies the caller's data.

**The split that matters.** A language model is used for exactly one thing — normalising each
statement into a fixed structure (relation, modality, quantifier, scope, conditions) drawn from
closed vocabularies. Every verdict is then computed by deterministic rules over those structures.
No model decides anything. The response carries both layers separately (``structures`` vs
``verdict``/``violations``) so the caller can audit where each part came from.

**Limits are served, not hidden.** ``GET /v1/capabilities`` returns the measured properties of this
prototype — parser model, sample count, observed run-to-run variance, test-set size. They are part
of the contract, not a footnote: a caller must be able to see that this is a prototype under
evaluation and not a validated instrument.

Run it::

    export DEEPSEEK_API_KEY=...          # or OPENROUTER_API_KEY, see ENTAIL_PARSER
    uvicorn api:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import spl_builder as sb  # noqa: E402

SERVICE_VERSION = "0.1.0-prototype"

app = FastAPI(
    title="DESi Claim–Evidence Entailment Auditor",
    version=SERVICE_VERSION,
    description=("Read-only epistemic gate for the L2→L3 boundary. Answers one question: does the "
                 "cited evidence entail the claim? A prototype under evaluation — see "
                 "/v1/capabilities for measured limits."),
)


# ── Schemas ─────────────────────────────────────────────────────────────────────────────────────

class Evidence(BaseModel):
    text: str = Field(..., description="The evidence statement, verbatim.")
    source_id: str = Field("", description="Caller's id for this evidence (trace/policy id).")


class AuditRequest(BaseModel):
    claim: str = Field(..., description="The candidate L3 claim to audit.")
    evidence: list[Evidence] = Field(default_factory=list,
                                     description="The evidence the claim cites. May be empty — "
                                                 "an empty list yields 'insufficient'.")
    declared_assumptions: list[str] = Field(
        default_factory=list,
        description="Premises the caller declares as licensed. A condition covered here is not "
                    "reported as condition_dropped.")
    context: str = Field("", description="Free-form context, echoed back. Not used in the verdict.")
    claim_id: str = Field("", description="Caller's id, echoed back.")


class BatchRequest(BaseModel):
    claims: list[AuditRequest]


class Violation(BaseModel):
    code: str
    explanation: str


class AuditResponse(BaseModel):
    claim_id: str
    claim: str
    verdict: str = Field(..., description="entailed | partially_entailed | "
                                          "compatible_not_entailed | contradicted | insufficient")
    violations: list[str]
    justification: list[str] = Field(..., description="Why the rules produced this verdict.")
    structures: dict = Field(..., description="The LLM-normalised structures the rules read. "
                                              "Includes per-field agreement across draws.")
    determinism: dict = Field(..., description="Which parts are model-derived vs rule-derived.")


# ── Endpoints ───────────────────────────────────────────────────────────────────────────────────

@app.get("/v1/health")
def health() -> dict:
    parser = ent.PARSER
    _, key_var = sb._route(sb.BUILDERS[parser])
    return {"status": "ok" if os.getenv(key_var) else "degraded",
            "service_version": SERVICE_VERSION,
            "parser_key_present": bool(os.getenv(key_var))}


@app.get("/v1/capabilities")
def capabilities() -> dict:
    """What this service does — and what it has been measured to do. Limits are part of the API."""
    return {
        "service_version": SERVICE_VERSION,
        "status": "prototype_under_evaluation",
        "question_answered": "Does the cited evidence entail the claim?",
        "not_answered": [
            "Is the claim true?",
            "Is the claim useful?",
            "How ambiguous is the sentence?  (that is the SPL's question, not this one)",
        ],
        "verdicts": list(ent.VERDICTS),
        "violations": list(ent.VIOLATIONS),
        "vocabularies": {
            "relation": list(sb.RELATIONS),
            "modality": list(ent.MODALITY),
            "quantifier": list(ent.QUANTIFIER),
            "scope_level": list(ent.SCOPE),
        },
        "architecture": {
            "model_used_for": "normalising each statement into the closed vocabularies above",
            "model_used_for_nothing_else": True,
            "verdict_computed_by": "deterministic rules over the normalised structures",
        },
        "parser": {
            "model": sb.BUILDERS[ent.PARSER],
            "draws_per_statement": ent.K_DRAWS,
            "aggregation": "strict majority per field; no majority -> field undetermined",
            "undetermined_field_policy": "verdict is 'insufficient' — never a guessed judgement",
            "compound_statements": (
                "split into atomic propositions (majority vote on the count), each audited "
                "separately; the overall verdict is the weakest part — one contradicted "
                "conjunct makes the whole claim contradicted, and 'entailed' requires every "
                "part to hold. If the split itself has no majority, the verdict is "
                "'insufficient' rather than a judgement on a partial parse."),
        },
        # These numbers are measured, not aspirational. A caller must be able to see the state of
        # the evidence before relying on a verdict.
        "measured_limits": {
            "test_set_size": 9,
            "test_set_note": "a demonstration set, NOT a validation corpus",
            "verdict_variance_k1": "6/9 to 9/9 across 5 runs on identical input",
            "verdict_variance_k5": "8/9 to 9/9 across 4 runs on identical input",
            "verdict_variance_k5_with_split": (
                "6/9 to 9/9 across 4 runs; violations 4/7 to 7/7. Splitting fixed a dangerous "
                "defect but did NOT narrow the band — the split step adds its own variance."),
            "fixed_defect_evidence_padding": (
                "irrelevant evidence with a universal quantifier used to raise the aggregate "
                "and flip a claim to 'entailed' — more evidence was monotonically better. "
                "Relevance now requires entity overlap, not just a matching relation. Since a "
                "generator picks its own evidence ids, this was exploitable."),
            "known_gap_missing_evidence": (
                "the auditor checks whether the CITED evidence carries the claim; it cannot see "
                "relevant evidence that was NOT cited"),
            "fixed_defect_false_entailed": (
                "before proposition splitting, a compound claim was normalised to its FIRST "
                "conjunct only — a claim explicitly denying X could be reported 'entailed' by "
                "evidence asserting X. Found by direction-testing, fixed by decomposition."),
            "residual_disagreement": ("1 of 9 cases is a contested gold-standard item: the parser "
                                      "consistently (agreement 1.0) chooses a defensible "
                                      "alternative reading of a conditional"),
            "parser_is_model_dependent": ("verdicts shift with the parser model; a different model "
                                          "measured an inverted entropy profile on a related task"),
            "known_gap": ("no calibration of the parser against an inter-annotator gold standard "
                          "has been performed"),
            "cost_note": (f"{ent.K_DRAWS} model calls per statement; an L3 row with n entries and "
                          "m evidence costs roughly k*(n+m) calls"),
        },
        "read_only": True,
        "stores_nothing": True,
    }


def _to_response(req: AuditRequest, res: dict) -> AuditResponse:
    return AuditResponse(
        claim_id=req.claim_id,
        claim=res["claim"],
        verdict=res["verdict"],
        violations=res["violations"],
        justification=res["notes"],
        structures={"claim": res["claim_structure"], "evidence": res["evidence_structures"]},
        determinism={
            "model_derived": ["structures"],
            "rule_derived": ["verdict", "violations", "justification"],
            "parser_model": sb.BUILDERS[ent.PARSER],
            "draws_per_statement": ent.K_DRAWS,
        },
    )


@app.post("/v1/audit", response_model=AuditResponse)
def audit(req: AuditRequest) -> AuditResponse:
    if not req.claim.strip():
        raise HTTPException(status_code=422, detail="claim must not be empty")
    try:
        res = ent.audit(req.claim,
                        [{"text": e.text, "source_id": e.source_id} for e in req.evidence],
                        declared_assumptions=tuple(req.declared_assumptions),
                        context=req.context)
    except SystemExit as exc:            # fehlender API-Key im Parser
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _to_response(req, res)


@app.post("/v1/audit/batch", response_model=list[AuditResponse])
def audit_batch(req: BatchRequest) -> list[AuditResponse]:
    if len(req.claims) > 50:
        raise HTTPException(status_code=413, detail="at most 50 claims per batch")
    return [audit(c) for c in req.claims]
