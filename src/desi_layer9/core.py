"""The authoritative Layer-9 core: store + state-update gate + operators.

This is the single deterministic write path. **No code outside the operators here may
mutate authoritative state.** Everything enters as a ``Proposal`` through ``submit``,
which runs the gate:

    proposal -> schema check -> proposer/authority check -> control check ->
    strip controlled fields -> operator execution (transition + taint + provenance) ->
    ledger event -> state mutation -> Decision

A model's output is only ever a proposal. Status and authority in a proposal payload are
*never* adopted - they are stripped and audited as ``rejected_fields``. Conflicts are
opened, not force-resolved. Methods become active only after trials + promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import policy
from .enums import (
    Authority,
    ConflictKind,
    ConflictStatus,
    MemoryKind,
    ObjectType,
    Operator,
    ProposalType,
    RelationType,
    SemanticDecision,
    SemanticState,
    Status,
)
from .hashing import chain_event
from .ids import IdMinter
from .ledger import LedgerEvent
from .objects import (
    Claim,
    Conflict,
    Decision,
    Evidence,
    EvidenceLink,
    Goal,
    MemoryEpisode,
    Method,
    NarrativeSummary,
    OperationalState,
    Preference,
    Project,
    Proposal,
    SelfModelClaim,
    SemanticCluster,
)
from .provenance import Provenance
from .rules import can_confirm_claim
from .taint import Taint, merge_all
from .transitions import assert_conflict_transition, assert_transition

_CONTROLLED_FIELDS = ("status", "authority")        # never adopted from a payload
_METHOD_TRIALS_FOR_ACTIVE = 3


@dataclass
class JournalEntry:
    """One recorded operation - the replayable unit. State = f(seed, journal).

    ``tick`` is the core's tick at the moment the operation ran, so replay can restore the
    exact historical tick before re-applying it (objects record ``created_tick`` /
    ``last_changed_tick``). Without it, a journal spanning a tick change (e.g. a midnight
    day rollover) would not reproduce its own snapshot hash.
    """

    operator: Operator
    proposal_type: ProposalType
    payload: dict
    proposer: str
    provenance: dict                 # Provenance.to_dict()
    target_objects: tuple[str, ...]
    actor: str
    governance_approved: bool
    reason: str = ""
    tick: int = 0

    def to_dict(self) -> dict:
        return {
            "operator": self.operator.value, "proposal_type": self.proposal_type.value,
            "payload": self.payload, "proposer": self.proposer, "provenance": self.provenance,
            "target_objects": list(self.target_objects), "actor": self.actor,
            "governance_approved": self.governance_approved, "reason": self.reason,
            "tick": self.tick,
        }

    @classmethod
    def from_dict(cls, d: dict) -> JournalEntry:
        return cls(
            operator=Operator(d["operator"]), proposal_type=ProposalType(d["proposal_type"]),
            payload=dict(d.get("payload", {})), proposer=d.get("proposer", "unknown"),
            provenance=dict(d.get("provenance", {})),
            target_objects=tuple(d.get("target_objects", ())),
            actor=d.get("actor", "system"), governance_approved=bool(d.get("governance_approved")),
            reason=d.get("reason", ""), tick=int(d.get("tick", 0)),
        )


def _clamp(x: float) -> float:
    return round(min(1.0, max(0.0, float(x))), 6)


@dataclass
class Layer9:
    """The authoritative epistemic state and its only write path."""

    tick: int = 0
    objects: dict[str, object] = field(default_factory=dict)
    minter: IdMinter = field(default_factory=IdMinter)
    ledger: list[LedgerEvent] = field(default_factory=list)
    journal: list[JournalEntry] = field(default_factory=list)
    _seq: int = 0

    # -- reads -------------------------------------------------------------- #
    def get(self, oid: str):
        return self.objects.get(oid)

    def all(self, object_type: ObjectType) -> list:
        return [o for o in self.objects.values() if o.object_type is object_type]

    def open_conflicts(self) -> list[Conflict]:
        return [c for c in self.all(ObjectType.CONFLICT)
                if c.conflict_status in (ConflictStatus.OPEN, ConflictStatus.UNDER_REVIEW)]

    # -- ledger (internal) -------------------------------------------------- #
    def _emit(self, operator: Operator, actor: str, *, decision: str, reason: str,
              input_refs: tuple = (), output_refs: tuple = (), reviewed_by: str = "",
              cost: float = 0.0, sampling: dict | None = None) -> LedgerEvent:
        self._seq += 1
        ev = LedgerEvent(
            id=self.minter.next(ObjectType.LEDGER_EVENT), sequence=self._seq, tick=self.tick,
            operator=operator, actor=actor, decision=decision, reason=reason,
            input_refs=tuple(input_refs), output_refs=tuple(output_refs),
            reviewed_by=reviewed_by, cost=cost, sampling_provenance=sampling or {},
        )
        previous = self.ledger[-1] if self.ledger else None
        self.ledger.append(ev)
        chain_event(ev, previous, self)
        return ev

    # -- the ONLY public write path ----------------------------------------- #
    def submit(self, proposal: Proposal, *, actor: str = "system",
               governance_approved: bool = False) -> Decision:
        # 0. journal the operation - the replayable unit (state = f(seed, journal)).
        self.journal.append(JournalEntry(
            operator=proposal.requested_operator, proposal_type=proposal.proposal_type,
            payload=dict(proposal.payload), proposer=proposal.proposer,
            provenance=proposal.provenance.to_dict(),
            target_objects=tuple(proposal.target_objects), actor=actor,
            governance_approved=governance_approved, reason=proposal.reason, tick=self.tick,
        ))

        # 1. record the proposal (its taint reflects who proposed it).
        proposal.id = self.minter.next(ObjectType.PROPOSAL)
        proposal.created_tick = proposal.last_changed_tick = self.tick
        proposal.status, proposal.authority = Status.CANDIDATE, Authority.CANDIDATE
        proposal.taint = self._proposer_taint(proposal)
        self.objects[proposal.id] = proposal
        ev0 = self._emit(Operator.PROPOSAL_SUBMIT, actor, decision="submitted",
                         reason=proposal.reason, output_refs=(proposal.id,))
        proposal.ledger_event = ev0.id

        op = proposal.requested_operator
        origin = proposal.provenance.origin_type
        rejected_fields = tuple(f for f in _CONTROLLED_FIELDS if f in proposal.payload)

        # 2. gate checks (order matters: proposer/governance before implementation).
        reasons: list[str] = []
        if op is None:
            reasons.append("no operator requested")
        elif not policy.may_request(origin, op):
            reasons.append(f"a {origin.value} proposer may not request {op.value}")
        elif op in policy.CONTROL_OPERATORS and not governance_approved:
            reasons.append("control-plane change requires governance approval")
        elif op not in _HANDLERS:
            reasons.append(f"operator not implemented: {op.value}")
        if reasons:
            return self._reject(proposal, op, reasons, rejected_fields, actor)

        # 3. execute the operator (transition/rule failures reject + audit).
        try:
            changed, new_status, reason = _HANDLERS[op](self, proposal, actor, governance_approved)
        except Exception as exc:  # noqa: BLE001 - any operator failure is an audited reject
            return self._reject(proposal, op, [str(exc)], rejected_fields, actor)

        ev = self._emit(op, actor, decision="accepted", reason=reason,
                        input_refs=proposal.target_objects, output_refs=tuple(changed))
        for cid in changed:
            self.objects[cid].ledger_event = ev.id
        proposal.status = Status.ACTIVE
        return self._decide(proposal, op, True, new_status, reason, rejected_fields, ev.id)

    # -- gate helpers ------------------------------------------------------- #
    def _proposer_taint(self, proposal: Proposal) -> Taint:
        base = merge_all([self.objects[t].taint for t in proposal.target_objects
                          if t in self.objects] or [Taint()])
        if proposal.provenance.is_model_output:
            base = base.derive(unverified_model_output=True)
        return base

    def _reject(self, proposal, op, reasons, rejected_fields, actor) -> Decision:
        proposal.status = Status.REJECTED
        reason = "; ".join(reasons)
        self._emit(op or Operator.PROPOSAL_REJECT, actor, decision="rejected", reason=reason,
                   input_refs=(proposal.id,))
        return self._decide(proposal, op, False, None, reason, rejected_fields, None)

    def _decide(self, proposal, op, accepted, new_status, reason, rejected_fields,
                ev_id) -> Decision:
        d = Decision(
            id=self.minter.next(ObjectType.DECISION), proposal_id=proposal.id, operator=op,
            accepted=accepted, new_status=new_status, reason=reason,
            rejected_fields=tuple(rejected_fields), ledger_event=ev_id,
            created_tick=self.tick, last_changed_tick=self.tick, created_by="gate",
            status=Status.ACTIVE, authority=Authority.AUTHORITATIVE,
        )
        self.objects[d.id] = d
        return d

    def _mint(self, cls, object_type: ObjectType, proposal: Proposal, actor: str, **fields):
        obj = cls(
            id=self.minter.next(object_type),
            created_tick=self.tick, last_changed_tick=self.tick,
            provenance=proposal.provenance, taint=proposal.taint,
            derived_from=proposal.target_objects, created_by=actor,
            **fields,
        )
        self.objects[obj.id] = obj
        return obj

    # ---- operator handlers (the ONLY mutators) ---------------------------- #
    def _h_claim_create(self, p, actor, gov):
        c = self._mint(Claim, ObjectType.CLAIM, p, actor,
                       text=p.payload.get("text", ""), topic=p.payload.get("topic", ""),
                       status=Status.CANDIDATE, authority=Authority.CANDIDATE,
                       confidence_or_support=_clamp(p.payload.get("support", 0.5)))
        return [c.id], c.status.value, f"created claim {c.id}"

    def _h_claim_revise(self, p, actor, gov):
        c = self.objects[p.target_objects[0]]
        to = Status(p.payload["to_status"])
        assert_transition(ObjectType.CLAIM, c.status, to)
        c.status, c.last_changed_tick = to, self.tick
        return [c.id], to.value, f"{c.id} -> {to.value}"

    def _h_claim_confirm(self, p, actor, gov):
        c = self.objects[p.target_objects[0]]
        links = [el for el in self.all(ObjectType.EVIDENCE_LINK) if el.claim_id == c.id]
        hard = any(x.severity == "hard" for x in self.open_conflicts() if c.id in x.claim_ids)
        ok, why = can_confirm_claim(c, links, unresolved_hard_contradiction=hard)
        if not ok:
            raise ValueError("cannot confirm: " + "; ".join(why))
        assert_transition(ObjectType.CLAIM, c.status, Status.CONFIRMED)
        c.status, c.authority = Status.CONFIRMED, Authority.AUTHORITATIVE
        c.reviewed_by, c.last_changed_tick = actor, self.tick
        return [c.id], "confirmed", f"{c.id} confirmed"

    def _h_claim_contest(self, p, actor, gov):
        c = self.objects[p.target_objects[0]]
        assert_transition(ObjectType.CLAIM, c.status, Status.CONTESTED)
        c.status, c.last_changed_tick = Status.CONTESTED, self.tick
        return [c.id], "contested", f"{c.id} contested"

    def _h_claim_reject(self, p, actor, gov):
        c = self.objects[p.target_objects[0]]
        assert_transition(ObjectType.CLAIM, c.status, Status.REJECTED)
        c.status, c.last_changed_tick = Status.REJECTED, self.tick
        return [c.id], "rejected", f"{c.id} rejected"

    def _h_evidence_attach(self, p, actor, gov):
        ev = self._mint(Evidence, ObjectType.EVIDENCE, p, actor,
                        content=p.payload.get("content", ""),
                        kind=p.payload.get("kind", "statement"), status=Status.CANDIDATE)
        link = self._mint(
            EvidenceLink, ObjectType.EVIDENCE_LINK, p, actor,
            claim_id=p.target_objects[0], evidence_id=ev.id,
            relation=RelationType(p.payload.get("relation", "supports")),
            strength=_clamp(p.payload.get("strength", 0.5)),
            review_status=p.payload.get("review_status", "unreviewed"), status=Status.CANDIDATE)
        return [ev.id, link.id], "attached", f"evidence {ev.id} -> {p.target_objects[0]}"

    def _h_conflict_open(self, p, actor, gov):
        x = self._mint(Conflict, ObjectType.CONFLICT, p, actor,
                       conflict_status=ConflictStatus.OPEN,
                       kind=p.payload.get("kind", "contradiction"),
                       conflict_kind=ConflictKind(p.payload.get("conflict_kind", "unqualified")),
                       severity=p.payload.get("severity", "soft"),
                       claim_ids=tuple(p.payload.get("claim_ids", p.target_objects)),
                       status=Status.ACTIVE, authority=Authority.AUTHORITATIVE)
        changed = [x.id]
        contestable = (Status.ACTIVE, Status.CONFIRMED, Status.PROVISIONAL)
        for cid in x.claim_ids:                       # the conflict marks claims contested
            c = self.objects.get(cid)
            if c is not None and c.status in contestable:
                assert_transition(ObjectType.CLAIM, c.status, Status.CONTESTED)
                c.status, c.last_changed_tick = Status.CONTESTED, self.tick
                changed.append(cid)
        return changed, "open", f"opened conflict {x.id}"

    def _h_conflict_review(self, p, actor, gov):
        x = self.objects[p.target_objects[0]]
        assert_conflict_transition(x.conflict_status, ConflictStatus.UNDER_REVIEW)
        x.conflict_status, x.last_changed_tick = ConflictStatus.UNDER_REVIEW, self.tick
        return [x.id], "under_review", f"{x.id} under review"

    def _h_conflict_resolve(self, p, actor, gov):
        # Resolution is explicit and reasoned - never forced for narrative tidiness.
        x = self.objects[p.target_objects[0]]
        to = ConflictStatus(p.payload.get("to", "resolved"))     # resolved | tolerated
        assert_conflict_transition(x.conflict_status, to)
        x.conflict_status = to
        x.resolution = p.payload.get("resolution")
        x.resolution_reason = p.payload.get("reason")
        x.last_changed_tick = self.tick
        return [x.id], to.value, f"{x.id} -> {to.value}"

    def _h_goal_create(self, p, actor, gov):
        g = self._mint(Goal, ObjectType.GOAL, p, actor, text=p.payload.get("text", ""),
                       horizon=p.payload.get("horizon", "long"),
                       priority=_clamp(p.payload.get("priority", 0.5)),
                       status=Status.ACTIVE, authority=Authority.AUTHORITATIVE)
        return [g.id], "active", f"created goal {g.id}"

    def _h_goal_update(self, p, actor, gov):
        g = self.objects[p.target_objects[0]]
        if "progress" in p.payload:
            g.progress = _clamp(p.payload["progress"])
        g.last_changed_tick = self.tick
        return [g.id], g.status.value, f"updated goal {g.id}"

    def _h_goal_abandon(self, p, actor, gov):
        g = self.objects[p.target_objects[0]]
        assert_transition(ObjectType.GOAL, g.status, Status.REJECTED)
        g.status, g.last_changed_tick = Status.REJECTED, self.tick
        return [g.id], "rejected", f"abandoned goal {g.id}"

    def _h_project_create(self, p, actor, gov):
        pr = self._mint(Project, ObjectType.PROJECT, p, actor,
                        title=p.payload.get("title", ""), topic=p.payload.get("topic", ""),
                        status=Status.ACTIVE, authority=Authority.AUTHORITATIVE)
        return [pr.id], "active", f"created project {pr.id}"

    def _h_project_abandon(self, p, actor, gov):
        pr = self.objects[p.target_objects[0]]
        assert_transition(ObjectType.PROJECT, pr.status, Status.REJECTED)
        pr.status, pr.last_changed_tick = Status.REJECTED, self.tick
        return [pr.id], "rejected", f"abandoned project {pr.id}"

    def _h_preference_propose(self, p, actor, gov):
        pref = self._mint(Preference, ObjectType.PREFERENCE, p, actor,
                          subject=p.payload.get("subject", ""),
                          stance=p.payload.get("stance", "prefers"),
                          strength=_clamp(p.payload.get("strength", 0.5)),
                          formed_from=tuple(p.payload.get("formed_from", ())),
                          status=Status.CANDIDATE)
        return [pref.id], "candidate", f"preference {pref.id}"

    def _h_memory_record(self, p, actor, gov):
        m = self._mint(MemoryEpisode, ObjectType.MEMORY_EPISODE, p, actor,
                       kind=MemoryKind(p.payload.get("kind", "episodic")),
                       summary=p.payload.get("summary", ""),
                       refs=tuple(p.payload.get("refs", ())),
                       source_event=p.payload.get("source_event"),
                       importance=_clamp(p.payload.get("importance", 0.5)),
                       retrieval_weight=_clamp(p.payload.get("retrieval_weight", 0.5)),
                       status=Status.ACTIVE)
        return [m.id], "active", f"recorded memory {m.id}"

    def _h_memory_recall(self, p, actor, gov):
        # Recall bumps salience but NEVER epistemic status (a memory does not become
        # truer by being recalled).
        m = self.objects[p.target_objects[0]]
        before = m.status
        m.recall_count += 1
        m.last_recalled_tick = self.tick
        m.retrieval_weight = _clamp(m.retrieval_weight + 0.05)
        assert m.status == before, "recall must not change status"
        return [m.id], m.status.value, f"recalled {m.id}"

    def _h_method_propose(self, p, actor, gov):
        m = self._mint(Method, ObjectType.METHOD, p, actor,
                       name=p.payload.get("name", ""), summary=p.payload.get("summary", ""),
                       steps=tuple(p.payload.get("steps", ())),
                       origin=p.payload.get("origin", "unknown"),
                       applicable_to=tuple(p.payload.get("applicable_to", ())),
                       parent_methods=tuple(p.payload.get("parent_methods", ())),
                       version=int(p.payload.get("version", 1)), status=Status.CANDIDATE)
        return [m.id], "candidate", f"proposed method {m.id}"

    def _h_method_trial_record(self, p, actor, gov):
        m = self.objects[p.target_objects[0]]
        success = bool(p.payload.get("success", False))
        m.trial_count += 1
        if success:
            m.success_count += 1
            m.supporting_runs = (*m.supporting_runs, p.payload.get("run_id", "unknown"))
        else:
            m.failure_count += 1
            m.failed_runs = (*m.failed_runs, p.payload.get("run_id", "unknown"))
        m.last_changed_tick = self.tick
        return [m.id], m.status.value, f"trial on {m.id} (success={success})"

    def _h_method_promote(self, p, actor, gov):
        m = self.objects[p.target_objects[0]]
        if m.status is Status.CANDIDATE:
            assert_transition(ObjectType.METHOD, m.status, Status.PROVISIONAL)
            m.status = Status.PROVISIONAL                # a single gate goes no further
            m.last_changed_tick = self.tick
            return [m.id], "provisional", f"{m.id} -> provisional"
        if m.status is Status.PROVISIONAL:
            if m.trial_count < _METHOD_TRIALS_FOR_ACTIVE or m.success_count <= m.failure_count:
                raise ValueError(f"{m.id} needs >= {_METHOD_TRIALS_FOR_ACTIVE} trials with "
                                 "more successes than failures before activation")
            _assert_taint_cleared(m)                      # contaminated -> needs HUMAN_VALIDATE
            assert_transition(ObjectType.METHOD, m.status, Status.ACTIVE)
            m.status, m.authority = Status.ACTIVE, Authority.AUTHORITATIVE
            m.last_changed_tick = self.tick
            return [m.id], "active", f"{m.id} -> active"
        raise ValueError(f"{m.id} cannot be promoted from {m.status.value}")

    def _h_method_reject(self, p, actor, gov):
        m = self.objects[p.target_objects[0]]
        assert_transition(ObjectType.METHOD, m.status, Status.REJECTED)
        m.status, m.last_changed_tick = Status.REJECTED, self.tick
        return [m.id], "rejected", f"rejected {m.id}"

    def _h_self_model_propose(self, p, actor, gov):
        sm = self._mint(SelfModelClaim, ObjectType.SELF_MODEL_CLAIM, p, actor,
                        text=p.payload.get("text", ""),
                        evidence=tuple(p.payload.get("evidence", ())),
                        counterevidence=tuple(p.payload.get("counterevidence", ())),
                        status=Status.CANDIDATE)
        return [sm.id], "candidate", f"self-model claim {sm.id}"

    def _h_operational_state(self, p, actor, gov):
        os_ = self._mint(OperationalState, ObjectType.OPERATIONAL_STATE, p, actor,
                         metrics=dict(p.payload.get("metrics", {})),
                         status=Status.ACTIVE, authority=Authority.AUTHORITATIVE)
        return [os_.id], "active", f"operational snapshot {os_.id}"

    def _h_human_validate(self, p, actor, gov):
        # A human/operator signs off on a contaminated object DESPITE its taint, so it may be
        # promoted. The contamination flags stay on record; only `human_validated` is set. The
        # policy gate already restricts this operator to a human / deterministic operator.
        obj = self.objects[p.target_objects[0]]
        t = getattr(obj, "taint", None)
        if t is None:
            raise ValueError(f"{obj.id} carries no taint to validate")
        obj.taint = t.with_human_validation()
        return [obj.id], "human_validated", f"{obj.id} human-validated despite taint"

    def _h_semantic_cluster_propose(self, p, actor, gov):
        # An append-only annotation of a Semantic-Layer analysis. It records what was
        # measured and what Layer 9 decided; it NEVER edits the analysed claims and is
        # never authoritative. Provenance/version are kept for audit and replay.
        sc = self._mint(
            SemanticCluster, ObjectType.SEMANTIC_CLUSTER, p, actor,
            members=tuple(p.payload.get("members", p.target_objects)),
            surface_terms=tuple(p.payload.get("surface_terms", ())),
            lexical_trigger=_clamp(p.payload.get("lexical_trigger", 0.0)),
            measurement=dict(p.payload.get("measurement", {})),
            decision=SemanticDecision(p.payload.get("decision", "insufficient-semantic-evidence")),
            semantic_state=SemanticState(p.payload.get("semantic_state", "lexical-candidate")),
            decision_rationale=p.payload.get("decision_rationale", ""),
            semantic_layer=p.payload.get("semantic_layer", "absent"),
            semantic_layer_version=str(p.payload.get("semantic_layer_version", "0")),
            status=Status.CANDIDATE, authority=Authority.UNTRUSTED)
        return [sc.id], sc.semantic_state.value, f"semantic analysis {sc.id}: {sc.decision.value}"

    def _h_narrative_render(self, p, actor, gov):
        # A narrative is language only: it summarises, it never writes operational state
        # or facts. It is untrusted by construction.
        ns = self._mint(NarrativeSummary, ObjectType.NARRATIVE_SUMMARY, p, actor,
                        text=p.payload.get("text", ""),
                        basis=tuple(p.payload.get("basis", ())),
                        status=Status.ACTIVE, authority=Authority.UNTRUSTED)
        return [ns.id], "active", f"narrative {ns.id}"


_HANDLERS = {
    Operator.CLAIM_CREATE: Layer9._h_claim_create,
    Operator.CLAIM_REVISE: Layer9._h_claim_revise,
    Operator.CLAIM_CONFIRM: Layer9._h_claim_confirm,
    Operator.CLAIM_CONTEST: Layer9._h_claim_contest,
    Operator.CLAIM_REJECT: Layer9._h_claim_reject,
    Operator.EVIDENCE_ATTACH: Layer9._h_evidence_attach,
    Operator.CONFLICT_OPEN: Layer9._h_conflict_open,
    Operator.CONFLICT_REVIEW: Layer9._h_conflict_review,
    Operator.CONFLICT_RESOLVE: Layer9._h_conflict_resolve,
    Operator.GOAL_CREATE: Layer9._h_goal_create,
    Operator.GOAL_UPDATE: Layer9._h_goal_update,
    Operator.GOAL_ABANDON: Layer9._h_goal_abandon,
    Operator.PROJECT_CREATE: Layer9._h_project_create,
    Operator.PROJECT_ABANDON: Layer9._h_project_abandon,
    Operator.PREFERENCE_PROPOSE: Layer9._h_preference_propose,
    Operator.MEMORY_RECORD: Layer9._h_memory_record,
    Operator.MEMORY_RECALL: Layer9._h_memory_recall,
    Operator.METHOD_PROPOSE: Layer9._h_method_propose,
    Operator.METHOD_TRIAL_RECORD: Layer9._h_method_trial_record,
    Operator.METHOD_PROMOTE: Layer9._h_method_promote,
    Operator.METHOD_REJECT: Layer9._h_method_reject,
    Operator.SELF_MODEL_PROPOSE: Layer9._h_self_model_propose,
    Operator.NARRATIVE_RENDER: Layer9._h_narrative_render,
    Operator.SEMANTIC_CLUSTER_PROPOSE: Layer9._h_semantic_cluster_propose,
    Operator.OPERATIONAL_STATE: Layer9._h_operational_state,   # gated path (was a bypass)
    Operator.HUMAN_VALIDATE: Layer9._h_human_validate,
}


def _assert_taint_cleared(obj) -> None:
    """A contaminated object may not be promoted to authoritative unless a human has explicitly
    validated it (Operator.HUMAN_VALIDATE). Taint that is computed but never enforced is decorative;
    this is where it actually blocks promotion."""
    t = getattr(obj, "taint", None)
    if t is not None and t.is_contaminated and not t.human_validated:
        raise ValueError(
            f"{obj.id} is contaminated and not human-validated - promotion to authoritative is "
            "blocked (a human must issue HUMAN_VALIDATE first)")


def make_proposal(
    proposal_type, requested_operator: Operator, *, payload: dict,
    proposer: str, provenance: Provenance, reason: str = "",
    target_objects: tuple[str, ...] = (),
) -> Proposal:
    """Convenience constructor for a well-formed proposal (the only ingress)."""
    return Proposal(
        proposal_type=proposal_type, requested_operator=requested_operator,
        payload=dict(payload), proposer=proposer, provenance=provenance, reason=reason,
        target_objects=tuple(target_objects),
    )
