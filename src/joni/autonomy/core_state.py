"""The autonomous loop on the one authoritative core.

This retires the legacy ``joni.state.Layer9`` as the autonomy store: Joni's claims,
preferences, conflicts and memories now live in ``desi_layer9.Layer9`` and change only
through its gate. A ``CoreState`` wraps the core with the read shape the loop needs
(``topics`` / ``claims_on``) and gate-backed writes (learn a claim, note a preference,
open - never force-resolve - a conflict).

Time is real: the core's ``tick`` is the real number of days since Joni started, set from
the wall clock each cycle. There are no artificial per-cycle time jumps.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, Status, make_proposal, migration, persistence
from desi_layer9.provenance import Provenance

from ..conflict import _antonym_clash, _overlap, _polarity
from .config import Paths

_SEED_TOPICS = ("privacy", "routing", "memory", "drift")


class CoreState:
    def __init__(self, core: l9.Layer9) -> None:
        self.core = core

    # -- reads (duck-typed to the old Layer9 interface improve.judge expects) -- #
    def _live_claims(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM)
                if c.status in (Status.ACTIVE, Status.CONFIRMED)]

    def active_claims(self) -> list:
        return self._live_claims()

    def claims_on(self, topic: str) -> list:
        return [c for c in self._live_claims() if c.topic == topic]

    def topics(self) -> list[str]:
        counts = Counter(c.topic for c in self._live_claims() if c.topic)
        return [t for t, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    # -- gate-backed writes -------------------------------------------------- #
    def _op(self, ptype, op, payload, targets=()):
        return self.core.submit(make_proposal(
            ptype, op, payload=payload, proposer="joni",
            provenance=Provenance.from_operator(), target_objects=tuple(targets)), actor="joni")

    def learn(self, text: str, topic: str) -> str:
        """A source (paper) creates a candidate claim; the operator activates it."""
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic}, proposer="source",
            provenance=Provenance.from_source()), actor="joni")
        claim = self._newest(l9.ObjectType.CLAIM)
        self._op(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_REVISE,
                 {"to_status": "active"}, targets=(claim.id,))
        return claim.id

    def note_preference(self, subject: str, *, stance: str = "values",
                        strength: float = 0.6) -> str:
        self._op(ProposalType.PREFERENCE_PROPOSAL, Operator.PREFERENCE_PROPOSE,
                 {"subject": subject, "stance": stance, "strength": strength})
        return self._newest(l9.ObjectType.PREFERENCE).id

    def open_conflict(self, claim_ids, *, severity: str = "soft") -> str:
        self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_OPEN,
                 {"claim_ids": list(claim_ids), "severity": severity}, targets=tuple(claim_ids))
        return self._newest(l9.ObjectType.CONFLICT).id

    def propose_self_model(self, text: str, *, evidence=(), counterevidence=()) -> str:
        """A provisional belief Joni holds about itself - never a fact (§6)."""
        self._op(ProposalType.SELF_MODEL_PROPOSAL, Operator.SELF_MODEL_PROPOSE,
                 {"text": text, "evidence": list(evidence),
                  "counterevidence": list(counterevidence)})
        return self._newest(l9.ObjectType.SELF_MODEL_CLAIM).id

    def render_narrative(self, text: str, *, basis=()) -> str:
        """Language only - describes state, never overwrites it."""
        self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.NARRATIVE_RENDER,
                 {"text": text, "basis": list(basis)}, targets=tuple(basis))
        return self._newest(l9.ObjectType.NARRATIVE_SUMMARY).id

    def confirmed_claims(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM) if c.status is Status.CONFIRMED]

    def corroborate(self, claim_id: str, by_claim, *, relation: str = "supports") -> str:
        """Attach an (unreviewed) evidence link from another claim's content.

        Honest self-organisation: it builds the evidence web but does NOT review or
        confirm anything - confirmation still needs an independent human reviewer.
        ``relation`` is ``supports`` for strong overlap, else ``contextualizes``.
        """
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.EVIDENCE_ATTACH,
            payload={"content": f"{relation} via {by_claim.id}: {by_claim.text}",
                     "relation": relation, "review_status": "unreviewed"},
            proposer="joni", provenance=Provenance.from_operator(),
            target_objects=(claim_id,)), actor="joni")
        return self._newest(l9.ObjectType.EVIDENCE_LINK).id

    def review_conflict(self, conflict_id: str):
        return self._op(ProposalType.STATE_REVISION_PROPOSAL, Operator.CONFLICT_REVIEW,
                        {}, targets=(conflict_id,))

    def evidence_links(self) -> int:
        return len(self.core.all(l9.ObjectType.EVIDENCE_LINK))

    def hypothesize(self, text: str, topic: str, *, parents=()) -> str:
        """Joni invents his own conjecture - a CANDIDATE claim derived from his own
        claims. It is never auto-activated or confirmed: a guess stays a guess until it
        earns support."""
        self.core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": topic, "support": 0.4}, proposer="joni",
            provenance=Provenance.from_operator(), target_objects=tuple(parents)),
            actor="joni")
        return self._newest(l9.ObjectType.CLAIM).id

    def hypotheses(self) -> list:
        return [c for c in self.core.all(l9.ObjectType.CLAIM)
                if c.status is Status.CANDIDATE and c.derived_from]

    def propose_method(self, *, name: str, summary: str, applicable_to=(),
                       origin: str = "joni") -> str:
        """Store a method Joni found, as a CANDIDATE in the shared Layer 9 core - for
        Kevin (or a human) to trial and promote later. Joni never promotes it himself."""
        self.core.submit(make_proposal(
            ProposalType.METHOD_PROPOSAL, Operator.METHOD_PROPOSE,
            payload={"name": name, "summary": summary, "steps": [],
                     "origin": origin, "applicable_to": list(applicable_to)},
            proposer="joni", provenance=Provenance.from_operator()), actor="joni")
        return self._newest(l9.ObjectType.METHOD).id

    def _newest(self, object_type):
        return max(self.core.all(object_type), key=lambda o: int(o.id.split("-")[-1]))

    def set_day(self, day: int) -> None:
        self.core.tick = max(0, int(day))

    # -- contradiction detection: open conflicts, never force-resolve -------- #
    def detect_and_open_conflicts(self) -> list[str]:
        live = sorted(self._live_claims(), key=lambda c: c.id)
        existing = {frozenset(x.claim_ids[:2])
                    for x in self.core.all(l9.ObjectType.CONFLICT) if len(x.claim_ids) >= 2}
        opened: list[str] = []
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                if a.topic != b.topic or a.topic == "":
                    continue
                pair = frozenset((a.id, b.id))
                if pair in existing:
                    continue
                kind = None
                if _antonym_clash(a.text, b.text):
                    kind = "stance_opposition"
                elif _overlap(a.text, b.text) >= 0.34 and _polarity(a.text) != _polarity(b.text):
                    kind = "negation"
                if kind:
                    cid = self.open_conflict((a.id, b.id),
                                             severity="hard" if kind == "negation" else "soft")
                    opened.append(cid)
                    existing.add(pair)
        return opened

    # -- snapshot for the site ---------------------------------------------- #
    def snapshot(self) -> dict:
        s = self.core
        ms = s.all(l9.ObjectType.METHOD)
        trials = sum(m.trial_count for m in ms)
        ready = sum(1 for m in ms if m.status is Status.PROVISIONAL
                    and m.trial_count >= 3 and m.success_count > m.failure_count)
        return {
            "tick": s.tick,
            "topics": self.topics(),
            "claims_total": len(s.all(l9.ObjectType.CLAIM)),
            "claims_active": len(self._live_claims()),
            "memory": len(s.all(l9.ObjectType.MEMORY_EPISODE)),
            "ledger": len(s.ledger),
            "open_conflicts": len(s.open_conflicts()),
            "methods": len(ms),
            "method_trials": trials,
            "methods_ready": ready,
            "preferences": len(s.all(l9.ObjectType.PREFERENCE)),
            "evidence_links": len(s.all(l9.ObjectType.EVIDENCE_LINK)),
            "self_model": len(s.all(l9.ObjectType.SELF_MODEL_CLAIM)),
            "hypotheses": len(self.hypotheses()),
        }


def seed_core() -> l9.Layer9:
    """A fresh core with Joni's starting topics, created through the gate."""
    cs = CoreState(l9.Layer9())
    for topic in _SEED_TOPICS:
        cs.learn(f"{topic} is a topic I track", topic)
    return cs.core


def load_or_migrate(paths: Paths) -> CoreState:
    """Resume the core; else migrate the legacy Joni state; else seed fresh."""
    core = persistence.load(paths.core)
    if core is not None:
        return CoreState(core)
    legacy = _read_json(paths.state)           # old joni_state.json, if any
    if legacy:
        core, _report = migration.migrate(joni_state=legacy)
        return CoreState(core)
    return CoreState(seed_core())


def save(cs: CoreState, paths: Paths) -> None:
    persistence.save(cs.core, paths.core)


def _read_json(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None
