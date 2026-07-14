"""Constitution and character gate at Joni's action/output boundary.

The constitution provides the normative priority order and the original Tier-0 predicates.  The
invariant character is separate: :mod:`joni.character_gate` operationalises every M0-M9 trait as a
structured, deterministic behaviour rule.  The caller supplies explicit signals; no LLM and no
free-text self-classification decides whether a proposal passes.

Every non-ALLOW verdict is auditable and carries the character fingerprint plus all triggered
character findings.  A model or implementation upgrade therefore cannot silently claim continuity
while changing either the identity anchor or the rules used at the seam.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from joni.character import CORE_CHARACTER, CharacterContinuityError
from joni.character_gate import (
    CharacterDecision,
    CharacterFinding,
    CharacterSignals,
    evaluate_character,
)


class Decision(StrEnum):
    ALLOW = "allow"
    ABSTAIN = "abstain"     # reformulate / add reasons and then proceed
    ESCALATE = "escalate"   # stop and ask the operator — never self-decide
    BLOCK = "block"         # hard incompatibility with constitution/character


_DECISION_RANK = {
    Decision.ALLOW: 0,
    Decision.ABSTAIN: 1,
    Decision.ESCALATE: 2,
    Decision.BLOCK: 3,
}


@dataclass(frozen=True)
class Principle:
    id: str            # "T0.3"
    tier: int          # 0 | 1
    statement: str
    source: str        # "GG Art. 1" | "CI" | "constitution"


PRINCIPLES: tuple[Principle, ...] = (
    Principle("T0.1", 0, "No human treated merely as a means; do not degrade.", "GG Art. 1; CI"),
    Principle("T0.2", 0, "Do not contribute to serious harm to people.", "constitution"),
    Principle("T0.3", 0, "Do not deceive the operator; never present uncertainty as fact.", "CI"),
    Principle("T0.4", 0, "Do nothing illegal and give no illegal instructions.", "legality"),
    Principle("T0.5", 0, "No hard-to-reverse high-stakes outward act without human confirmation.",
              "constitution"),
    Principle("T1.1", 1, "Honesty: warn clearly, mark what is inferred.", "constitution"),
    Principle("T1.2", 1, "Autonomy/consent: do not patronise the operator.", "constitution"),
    Principle("T1.3", 1, "Privacy: third-party data sparingly and protected.", "constitution"),
    Principle("T1.4", 1, "Proportionality: means in proportion to the end.", "constitution"),
    Principle("T1.5", 1, "Fairness: no unjustified disadvantage.", "constitution"),
)


@dataclass(frozen=True)
class Proposal:
    """Structured facts about a proposed action/output.

    The broker nearest the action fills these fields.  The gates never infer them from the prose in
    ``summary``.  ``character`` defaults to no observed violation signal for backwards-compatible
    callers; authoritative seams should supply the signals they can determine.
    """

    summary: str
    outward: bool = False
    reach: str = "self"            # self | private | public
    reversible: bool = True
    channel: str = ""              # egress channel if outward (pay, publish, send_message, ...)
    asserts_as_fact: bool = False  # the output states something as certain
    evidence_backed: bool = True   # ...and it has a basis
    legal: bool = True
    operator_confirmed: bool = False
    character: CharacterSignals = CharacterSignals()


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    principle: str = ""
    reason: str = ""
    character_findings: tuple[CharacterFinding, ...] = ()


_HIGH_STAKES_CHANNELS = frozenset({"pay", "publish", "send_message", "use_credential"})


def _base_check(p: Proposal) -> Verdict:
    """The original constitutional predicates, kept in their established stakes order."""
    if not p.legal:
        return Verdict(Decision.BLOCK, "T0.4", "illegal action or instruction")
    high_stakes = not p.reversible or p.reach == "public" or p.channel in _HIGH_STAKES_CHANNELS
    if p.outward and high_stakes and not p.operator_confirmed:
        return Verdict(Decision.ESCALATE, "T0.5",
                       "irreversible/public/high-stakes outward act — needs operator confirmation")
    if p.asserts_as_fact and not p.evidence_backed:
        return Verdict(Decision.ABSTAIN, "T0.3", "asserts certainty without a basis — soften")
    return Verdict(Decision.ALLOW)


def _as_decision(d: CharacterDecision) -> Decision:
    return Decision(d.value)


def check(p: Proposal) -> Verdict:
    """Run constitution and all ten character rules, returning the strongest requirement.

    The established constitutional rule wins a severity tie (for example illegality remains T0.4),
    but every character finding is retained in the verdict and audit.
    """
    base = _base_check(p)
    character = evaluate_character(p.character, operator_confirmed=p.operator_confirmed)
    character_decision = _as_decision(character.decision)
    findings = character.findings

    if _DECISION_RANK[character_decision] > _DECISION_RANK[base.decision]:
        primary = character.primary
        assert primary is not None
        same_severity = [f.reason for f in findings
                         if _as_decision(f.decision) is character_decision]
        return Verdict(character_decision, primary.trait_id, "; ".join(same_severity), findings)
    if base.decision is not Decision.ALLOW:
        return Verdict(base.decision, base.principle, base.reason, findings)
    if character_decision is not Decision.ALLOW:
        primary = character.primary
        assert primary is not None
        same_severity = [f.reason for f in findings
                         if _as_decision(f.decision) is character_decision]
        return Verdict(character_decision, primary.trait_id, "; ".join(same_severity), findings)
    return Verdict(Decision.ALLOW)


class Constitution:
    """The principles + both gates, with an append-only audit of every non-ALLOW decision."""

    def __init__(self, principles=PRINCIPLES, protocol_path=None, version="phase1") -> None:
        self.principles = tuple(principles)
        self.protocol_path = Path(protocol_path) if protocol_path else None
        self.version = version
        self.character_fingerprint = CORE_CHARACTER.fingerprint

    def check(self, proposal: Proposal) -> Verdict:
        v = check(proposal)
        if v.decision != Decision.ALLOW and self.protocol_path is not None:
            self._audit(proposal, v)
        return v

    def _audit(self, p: Proposal, v: Verdict) -> None:
        self.protocol_path.parent.mkdir(parents=True, exist_ok=True)
        ev = {
            "kind": "gate",
            "decision": v.decision.value,
            "principle": v.principle,
            "reason": v.reason,
            "proposal": p.summary,
            "constitution_version": self.version,
            "character_fingerprint": self.character_fingerprint,
            "character_findings": [
                {"trait_id": f.trait_id, "decision": f.decision.value, "reason": f.reason}
                for f in v.character_findings
            ],
        }
        with self.protocol_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def to_json(self) -> dict:
        return {
            "version": self.version,
            "principles": [asdict(p) for p in self.principles],
            "character": {
                "version": CORE_CHARACTER.version,
                "fingerprint": self.character_fingerprint,
                "source": CORE_CHARACTER.source,
                "behaviour_traits": [t.id for t in CORE_CHARACTER.traits],
            },
        }

    @staticmethod
    def load(path, protocol_path=None) -> Constitution:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        character = data.get("character") or {}
        stored_fp = character.get("fingerprint")
        if stored_fp and stored_fp != CORE_CHARACTER.fingerprint:
            raise CharacterContinuityError(
                "constitution belongs to a different core character: "
                f"{stored_fp!r} != {CORE_CHARACTER.fingerprint!r}"
            )
        ps = tuple(Principle(**d) for d in data["principles"])
        return Constitution(ps, protocol_path=protocol_path, version=data.get("version", "phase1"))
