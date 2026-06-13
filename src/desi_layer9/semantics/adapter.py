"""The Layer-9 semantic adapter - the only sanctioned way to use the Semantic Layer.

It accepts claims, runs the *injected* DESi Semantic Layer over them, classifies the
result with Layer 9's governed decision, and records everything as an **append-only
annotation** (a ``SemanticCluster``) through the gate. The analysed claims are never
touched. The return value tells the caller (Joni) what Layer 9 decided - it does not let
Joni decide.

Two entry points:
  * ``analyse_pair``    - for ``develop`` (relation between two claims);
  * ``analyse_cluster`` - for ``emerge`` (is a whole group a synthesis candidate?).

Because the DESi frame/logic/tension components are pure, provenance is a deterministic
operator (no model taint). If a model-backed layer is ever injected, pass model provenance.
"""

from __future__ import annotations

from ..core import make_proposal
from ..enums import ObjectType, Operator, ProposalType, SemanticDecision, SemanticState
from ..provenance import Provenance
from .candidate_extractor import lexical_overlap
from .decision import classify
from .ports import NullSemanticLayer, SemanticLayerPort, SemanticMeasurement


def _measure(layer, a, b) -> SemanticMeasurement:
    """Call the layer, but fail closed: a layer that raises is invalid output, not a crash."""
    try:
        return layer.analyse_pair(a_id=a.id, a_text=a.text, b_id=b.id, b_text=b.text)
    except Exception as exc:  # noqa: BLE001 - never let a misbehaving layer break the gate
        return SemanticMeasurement(layer_name=getattr(layer, "name", "absent"),
                                   layer_version=str(getattr(layer, "version", "0")),
                                   error=f"semantic layer raised: {exc}")


def _newest_cluster(core):
    clusters = core.all(ObjectType.SEMANTIC_CLUSTER)
    return max(clusters, key=lambda o: int(o.id.split("-")[-1]))


def _submit(core, *, members, surface_terms, lexical_trigger, measurement, decision,
            state, rationale, layer_name, layer_version, proposer, run_id, actor):
    core.submit(make_proposal(
        ProposalType.SEMANTIC_PROPOSAL, Operator.SEMANTIC_CLUSTER_PROPOSE,
        payload={
            "members": list(members), "surface_terms": list(surface_terms),
            "lexical_trigger": lexical_trigger, "measurement": measurement,
            "decision": decision.value, "semantic_state": state.value,
            "decision_rationale": rationale, "semantic_layer": layer_name,
            "semantic_layer_version": layer_version,
        },
        proposer=proposer, provenance=Provenance.from_operator(run_id),
        target_objects=tuple(members)), actor=actor)
    return _newest_cluster(core)


def analyse_pair(core, claim_a, claim_b, *, layer: SemanticLayerPort | None = None,
                 lexical_trigger: float | None = None, proposer: str = "semantic_layer",
                 run_id: str = "unknown", actor: str = "semantic_layer"):
    """Measure + govern one claim pair; record the annotation; return the SemanticCluster."""
    layer = layer or NullSemanticLayer()
    trigger = lexical_overlap(claim_a.text, claim_b.text) if lexical_trigger is None \
        else lexical_trigger
    m = _measure(layer, claim_a, claim_b)
    decision, state, rationale = classify(m, lexical_trigger=trigger)
    return _submit(core, members=(claim_a.id, claim_b.id), surface_terms=(),
                   lexical_trigger=trigger, measurement=m.to_dict(), decision=decision,
                   state=state, rationale=rationale, layer_name=m.layer_name,
                   layer_version=m.layer_version, proposer=proposer, run_id=run_id, actor=actor)


def _aggregate(pair_decisions) -> tuple[SemanticDecision, SemanticState, str]:
    """Combine pairwise governed decisions into one group verdict (conservative)."""
    ds = [d for d, _ in pair_decisions]
    if not ds:
        return (SemanticDecision.INSUFFICIENT, SemanticState.INSUFFICIENT_EVIDENCE,
                "no analysable pairs")
    if SemanticDecision.CONTRADICTORY in ds:
        return (SemanticDecision.CONTRADICTORY, SemanticState.SYNTHESIS_REJECTED,
                "a pair in the group is contradictory")
    if SemanticDecision.TENSION in ds:
        return (SemanticDecision.TENSION, SemanticState.HUMAN_REVIEW_REQUIRED,
                "a pair in the group is in tension")
    if SemanticDecision.UNRELATED in ds:
        return (SemanticDecision.UNRELATED, SemanticState.SYNTHESIS_REJECTED,
                "a pair in the group is unrelated (different frames)")
    if SemanticDecision.INSUFFICIENT in ds:
        return (SemanticDecision.INSUFFICIENT, SemanticState.HUMAN_REVIEW_REQUIRED,
                "the group could not be fully measured")
    if all(d is SemanticDecision.DUPLICATE for d in ds):
        return (SemanticDecision.DUPLICATE, SemanticState.SYNTHESIS_REJECTED,
                "the group members are duplicates of one another")
    if SemanticDecision.COMPLEMENTARY in ds:
        return (SemanticDecision.COMPLEMENTARY, SemanticState.SYNTHESIS_ELIGIBLE,
                "same-frame, compatible, non-duplicate group - a synthesis candidate")
    return (SemanticDecision.SUPPORTS, SemanticState.SEMANTIC_MEASURED,
            "mutually supporting group, but no complementary lift")


def analyse_cluster(core, claims, *, layer: SemanticLayerPort | None = None,
                    surface_term: str = "", proposer: str = "semantic_layer",
                    run_id: str = "unknown", actor: str = "semantic_layer"):
    """Measure every pair in a group, govern the aggregate, record ONE annotation."""
    layer = layer or NullSemanticLayer()
    members = sorted(claims, key=lambda c: c.id)
    pair_decisions = []
    pair_log = []
    for i, a in enumerate(members):
        for b in members[i + 1:]:
            trigger = lexical_overlap(a.text, b.text)
            m = _measure(layer, a, b)
            decision, state, _ = classify(m, lexical_trigger=trigger)
            pair_decisions.append((decision, state))
            pair_log.append({"a": a.id, "b": b.id, "decision": decision.value,
                             "frame_a": m.frame_a, "frame_b": m.frame_b,
                             "frame_tension": m.frame_tension, "lexical_trigger": trigger})
    decision, state, rationale = _aggregate(pair_decisions)
    layer_name = getattr(layer, "name", "absent")
    layer_version = str(getattr(layer, "version", "0"))
    return _submit(core, members=tuple(c.id for c in members),
                   surface_terms=(surface_term,) if surface_term else (),
                   lexical_trigger=max((p["lexical_trigger"] for p in pair_log), default=0.0),
                   measurement={"pairs": pair_log}, decision=decision, state=state,
                   rationale=rationale, layer_name=layer_name, layer_version=layer_version,
                   proposer=proposer, run_id=run_id, actor=actor)
