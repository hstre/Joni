"""Joni's epistemic identity, on the one authoritative core (desi_layer9).

This is the Joni-side integration of Layer 9. Joni's beliefs, goals, memories,
self-model and narration all live in the authoritative ``desi_layer9.Layer9`` core and
move only through its gate - there is no second epistemic store. The legacy ``state.py``
container is retired as an *authoritative* store: its data is imported here via the PR-3
migration and it remains only as the operative-shell demonstrator.

Two views, as before, but now both resolve to the core:

  * **Conversation View** - a first-person line built from the *approved* state
    (active/confirmed claims, the current self-model, a live goal). Language only.
  * **Epistemic View** - dissolves any utterance into the exact Layer-9 objects behind
    it: claims, evidence, goals, memories, self-model claims, the operator, the proposal,
    the decision, taint, review and the ledger event (§14).

Crucially, the three are kept apart (§6): ``OperationalState`` is measured system data,
a ``SelfModelClaim`` is a *provisional* belief Joni holds about itself, and a
``NarrativeSummary`` is language that may describe but never overwrite either.
"""

from __future__ import annotations

from desi_layer9 import (
    Layer9,
    ObjectType,
    Operator,
    ProposalType,
    Status,
    make_proposal,
    migration,
    persistence,
)
from desi_layer9.provenance import Provenance


class EpistemicIdentity:
    """Joni's authoritative epistemic state and its dual view."""

    def __init__(self, core: Layer9 | None = None, name: str = "Joni") -> None:
        self.core = core or Layer9()
        self.name = name

    # -- recording (all through the gate, deterministic-operator origin) ----- #
    def _submit(self, ptype, operator, payload, *, targets=(), model=False, reviewed=False):
        prov = (Provenance.from_model(external=True, model_id="local")
                if model else Provenance.from_operator())
        proposer = "model" if model else "joni"
        return self.core.submit(
            make_proposal(ptype, operator, payload=payload, proposer=proposer,
                          provenance=prov, target_objects=tuple(targets)),
            actor="joni")

    def _last(self, object_type: ObjectType):
        objs = self.core.all(object_type)
        return objs[-1] if objs else None

    def learn_claim(self, text: str, topic: str, *, activate: bool = True,
                    model: bool = False) -> str:
        self._submit(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
                     {"text": text, "topic": topic}, model=model)
        claim = self._last(ObjectType.CLAIM)
        if activate:
            self._submit(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                         {"to_status": "active"}, targets=(claim.id,))
        return claim.id

    def attach_evidence(self, claim_id: str, content: str, *, relation: str = "supports",
                        reviewed: bool = False) -> str:
        self._submit(ProposalType.CLAIM_PROPOSAL, Operator.EVIDENCE_ATTACH,
                     {"content": content, "relation": relation,
                      "review_status": "reviewed" if reviewed else "unreviewed"},
                     targets=(claim_id,))
        return self._last(ObjectType.EVIDENCE_LINK).id

    def confirm_claim(self, claim_id: str):
        return self._submit(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CONFIRM, {},
                            targets=(claim_id,))

    def open_conflict(self, claim_ids: tuple[str, ...], *, severity: str = "hard") -> str:
        self._submit(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_OPEN,
                     {"claim_ids": list(claim_ids), "severity": severity}, targets=claim_ids)
        return self._last(ObjectType.CONFLICT).id

    def adopt_goal(self, text: str, *, horizon: str = "long", priority: float = 0.5) -> str:
        self._submit(ProposalType.GOAL_PROPOSAL, Operator.GOAL_CREATE,
                     {"text": text, "horizon": horizon, "priority": priority})
        return self._last(ObjectType.GOAL).id

    def record_memory(self, summary: str, *, refs: tuple[str, ...] = ()) -> str:
        self._submit(ProposalType.STATE_REVISION_PROPOSAL, Operator.MEMORY_RECORD,
                     {"summary": summary, "refs": list(refs)})
        return self._last(ObjectType.MEMORY_EPISODE).id

    def propose_self_model(self, text: str, *, evidence: tuple[str, ...] = (),
                           counterevidence: tuple[str, ...] = ()) -> str:
        self._submit(ProposalType.SELF_MODEL_PROPOSAL, Operator.SELF_MODEL_PROPOSE,
                     {"text": text, "evidence": list(evidence),
                      "counterevidence": list(counterevidence)})
        return self._last(ObjectType.SELF_MODEL_CLAIM).id

    def snapshot_operational(self, metrics: dict) -> str:
        """Measured system data - written by the deterministic system, not a model.

        Routed THROUGH the gate (Operator.OPERATIONAL_STATE), like every other authoritative write:
        it produces a ledger event, is replay-reproducible, and passes the authority/taint checks.
        (It used to write ``core.objects[...]`` directly - a second, ungated write path that was
        invisible to replay and verify_chain.)"""
        self._submit(ProposalType.STATE_REVISION_PROPOSAL, Operator.OPERATIONAL_STATE,
                     {"metrics": dict(metrics)})
        return self._last(ObjectType.OPERATIONAL_STATE).id

    def render_narrative(self, text: str, *, basis: tuple[str, ...] = ()) -> str:
        self._submit(ProposalType.STATE_REVISION_PROPOSAL, Operator.NARRATIVE_RENDER,
                     {"text": text, "basis": list(basis)}, targets=basis)
        return self._last(ObjectType.NARRATIVE_SUMMARY).id

    # -- the dual view ------------------------------------------------------ #
    def _approved_claims(self):
        return [c for c in self.core.all(ObjectType.CLAIM)
                if c.status in (Status.ACTIVE, Status.CONFIRMED)]

    def conversation(self, prompt: str = "") -> str:
        """First-person line from the approved state. Language only - no new facts."""
        lines = []
        claims = sorted(self._approved_claims(), key=lambda c: -c.confidence_or_support)
        if claims:
            lines.append(f"I currently hold that {claims[0].text.lower()}.")
        sm = self.core.all(ObjectType.SELF_MODEL_CLAIM)
        if sm:
            lines.append(f"About myself, provisionally: {sm[-1].text.lower()}")
        goals = [g for g in self.core.all(ObjectType.GOAL) if g.status is Status.ACTIVE]
        if goals:
            lines.append(f"I'm working toward: {goals[0].text.lower()}.")
        contested = [c for c in self.core.all(ObjectType.CLAIM) if c.status is Status.CONTESTED]
        if contested:
            lines.append("On one point I hold two incompatible explanations open.")
        return " ".join(lines) or "I don't have a settled view on that yet."

    def epistemic_trace(self, utterance: str, *, refs: tuple[str, ...] = ()) -> dict:
        """Dissolve an utterance into the Layer-9 objects behind it (§14)."""
        def ids(ot):
            return [o.id for o in self.core.all(ot) if not refs or o.id in refs]

        last_decision = self.core.all(ObjectType.DECISION)
        last_dec = last_decision[-1] if last_decision else None
        taint = {}
        if refs:
            obj = self.core.get(refs[0])
            taint = obj.taint.to_dict() if obj is not None else {}
        return {
            "utterance": utterance,
            "claims": [c.id for c in self._approved_claims()],
            "evidence": ids(ObjectType.EVIDENCE),
            "goals": [g.id for g in self.core.all(ObjectType.GOAL)],
            "memories": ids(ObjectType.MEMORY_EPISODE),
            "self_model_claims": ids(ObjectType.SELF_MODEL_CLAIM),
            "operator": last_dec.operator.value if last_dec and last_dec.operator else None,
            "proposal": last_dec.proposal_id if last_dec else None,
            "decision": last_dec.id if last_dec else None,
            "taint": taint,
            "review": ids(ObjectType.REVIEW),
            "ledger_event": last_dec.ledger_event if last_dec else None,
        }

    # -- persistence + migration ------------------------------------------- #
    def save(self, path):
        return persistence.save(self.core, path)

    @classmethod
    def load(cls, path, name: str = "Joni") -> EpistemicIdentity | None:
        core = persistence.load(path)
        return cls(core=core, name=name) if core is not None else None

    @classmethod
    def from_legacy(cls, legacy_state: dict, *, kevin_jsonl: str | None = None,
                    name: str = "Joni") -> EpistemicIdentity:
        """Migrate an old Joni state (and optionally Kevin methods) onto the core."""
        core, _report = migration.migrate(joni_state=legacy_state, kevin_jsonl=kevin_jsonl)
        return cls(core=core, name=name)
