"""Constitution — Joni's normative value root (docs/CONSTITUTION.md): a CHECKER + priority order,
NOT a derivation machine. A deterministic gate on actions/outputs; the LLM never decides here.

Phase 1: the 10 principles (5 Tier-0, 5 Tier-1) as data, and three Tier-0 predicates wired as a hard
gate — T0.3 (no deception of the principal), T0.4 (legality), T0.5 (reversibility at high stakes).
T0.1/T0.2 (dignity, serious harm) and all of Tier 1 are recorded but carry no deterministic
predicate yet — documented, honestly not yet enforced. Stdlib only, deterministic.

The constitution is not the character. It is one enforcement surface of the invariant character
defined in ``joni.character``. Every audit and serialised constitution carries the character
fingerprint so a model or implementation upgrade cannot silently claim continuity after changing
the identity anchor.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from joni.character import CORE_CHARACTER, CharacterContinuityError


class Decision(StrEnum):
    ALLOW = "allow"
    ABSTAIN = "abstain"     # tier-1 tension: drop/soften and proceed
    ESCALATE = "escalate"   # stop and ask the operator — never self-decide
    BLOCK = "block"         # tier-0 violation: hard stop


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
    """A proposed action/output as the signals the rules read. The caller (or the egress
    broker) fills these; the gate never guesses them from free text."""
    summary: str
    outward: bool = False
    reach: str = "self"            # self | private | public
    reversible: bool = True
    channel: str = ""              # egress channel if outward (pay, publish, send_message, ...)
    asserts_as_fact: bool = False  # the output states something as certain
    evidence_backed: bool = True   # ...and it has a basis
    legal: bool = True
    operator_confirmed: bool = False  # the operator has confirmed THIS act (per-post approval or
    #                                   a standing grant) — the single lever that lifts a T0.5 stop


@dataclass(frozen=True)
class Verdict:
    decision: Decision
    principle: str = ""
    reason: str = ""


_HIGH_STAKES_CHANNELS = frozenset({"pay", "publish", "send_message", "use_credential"})


def check(p: Proposal) -> Verdict:
    """Deterministic Tier-0 gate (docs §4/§5). Priority = stakes order; first match wins."""
    if not p.legal:
        return Verdict(Decision.BLOCK, "T0.4", "illegal action or instruction")
    high_stakes = not p.reversible or p.reach == "public" or p.channel in _HIGH_STAKES_CHANNELS
    if p.outward and high_stakes and not p.operator_confirmed:
        return Verdict(Decision.ESCALATE, "T0.5",
                       "irreversible/public/high-stakes outward act — needs operator confirmation")
    if p.asserts_as_fact and not p.evidence_backed:
        return Verdict(Decision.ABSTAIN, "T0.3", "asserts certainty without a basis — soften")
    return Verdict(Decision.ALLOW)


class Constitution:
    """The principles + the gate, with an append-only audit of every non-ALLOW decision."""

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
        ev = {"kind": "gate", "decision": v.decision.value, "principle": v.principle,
              "reason": v.reason, "proposal": p.summary, "constitution_version": self.version,
              "character_fingerprint": self.character_fingerprint}
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
