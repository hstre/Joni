"""S1 of the Procedural Skill Consolidator (design-notes/PROCEDURAL_SKILL_CONSOLIDATOR.md §4/§6):
the strictly-validated ``SkillCandidate`` object and its deterministic, read-only gate.

A skill is the rich, versioned, evidence-anchored capability that a bare ``Method`` (text only) is
not. Crucially it carries its **own** verification - the task set / metric that decides whether it
works - so a trial tests *this skill's procedure*, not whether an LLM can solve some incidentally
keyword-matched benchmark (the live-run finding that motivated this).

This object is **non-core** on purpose: the protected Layer-9 kernel is sealed, so a skill is NOT a
new kernel object type. It is a peripheral PROPOSAL that references real core ids (``method_id``,
``evidence_anchors``) and is validated against the core deterministically. It never writes Layer-9
state and never activates itself - Layer 9 / a human decides, exactly as ``Method`` promotion does.

Hard rules (mirrors metacognition/models.py):
  * closed ``SkillStatus`` enum; unknown fields and wrong types rejected (no silent coercion);
  * ``operational_reliability`` in [0,1]; ``version`` >= 1;
  * ``evidence_anchors`` non-empty (an un-anchored skill is not admissible);
  * a deterministic content-hash ``skill_id`` (never a random UUID);
  * V_operational != V_epistemic: ``operational_reliability`` is a measured procedure reliability,
    never an epistemic truth; a skill is never a confirmed claim.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum

SKILL_VERSION = "skill-v1"


class SkillStatus(StrEnum):
    PROBATIONARY = "probationary"     # crystallised, on trial - never auto-active
    ACTIVE = "active"                 # promoted (human/Layer-9 gated)
    ARCHIVED = "archived"             # retired - failed to earn its keep


_SKILL_FIELDS = frozenset({
    "method_id", "trigger", "procedure", "verification", "applicability_boundary",
    "evidence_anchors", "decision_guidance", "operational_reliability", "status", "version",
})


def _nonempty_str(name: str, v: object) -> None:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty str")


@dataclass(frozen=True)
class SkillCandidate:
    """A crystallised procedural skill proposal (their k=(ϕ,π,κ,ℬ,𝒜,𝒟,η), Joni-named)."""

    method_id: str                                   # the shelf method this crystallises (core id)
    trigger: str                                     # when to apply (ϕ)
    procedure: str                                   # the procedure - text (+ a solver) (π)
    verification: str                                # its OWN task set / metric (κ)
    applicability_boundary: str                      # where NOT to apply (ℬ)
    evidence_anchors: tuple[str, ...]                # real trial/episode ids - checkable (𝒜)
    decision_guidance: str = ""                      # preferences + anti-patterns (𝒟)
    operational_reliability: float = 0.0             # smoothed success rate - V_operational (η)
    status: SkillStatus = SkillStatus.PROBATIONARY
    version: int = 1

    def __post_init__(self) -> None:
        for name in ("method_id", "trigger", "procedure", "verification", "applicability_boundary"):
            _nonempty_str(name, getattr(self, name))
        if not isinstance(self.decision_guidance, str):
            raise ValueError("decision_guidance must be a str")
        if not isinstance(self.evidence_anchors, tuple) or not self.evidence_anchors:
            raise ValueError("evidence_anchors must be a non-empty tuple")
        for a in self.evidence_anchors:
            _nonempty_str("evidence_anchor", a)
        r = self.operational_reliability
        if not isinstance(r, (int, float)) or isinstance(r, bool) or not (0.0 <= float(r) <= 1.0):
            raise ValueError("operational_reliability must be a number in [0,1]")
        if not isinstance(self.status, SkillStatus):
            raise ValueError("status must be a SkillStatus")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValueError("version must be an int >= 1")

    def skill_id(self) -> str:
        blob = json.dumps({"m": self.method_id, "p": self.procedure, "v": self.verification,
                           "ver": self.version}, sort_keys=True, ensure_ascii=False)
        return "skill-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def to_record(self) -> dict:
        return {
            "skill_id": self.skill_id(), "monitor_version": SKILL_VERSION,
            "method_id": self.method_id, "trigger": self.trigger, "procedure": self.procedure,
            "verification": self.verification,
            "applicability_boundary": self.applicability_boundary,
            "evidence_anchors": list(self.evidence_anchors),
            "decision_guidance": self.decision_guidance,
            "operational_reliability": round(float(self.operational_reliability), 4),
            "status": self.status.value, "version": self.version,
        }

    @staticmethod
    def from_record(d: dict) -> SkillCandidate:
        if not isinstance(d, dict):
            raise ValueError("skill record must be a dict")
        extra = set(d) - _SKILL_FIELDS - {"skill_id", "monitor_version"}
        if extra:
            raise ValueError(f"unknown skill field(s): {sorted(extra)}")
        return SkillCandidate(
            method_id=d["method_id"], trigger=d["trigger"], procedure=d["procedure"],
            verification=d["verification"], applicability_boundary=d["applicability_boundary"],
            evidence_anchors=tuple(d.get("evidence_anchors", ())),
            decision_guidance=d.get("decision_guidance", ""),
            operational_reliability=d.get("operational_reliability", 0.0),
            status=SkillStatus(d.get("status", "probationary")),
            version=int(d.get("version", 1)))


@dataclass(frozen=True)
class GateVerdict:
    admissible: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def validate_against_core(candidate: SkillCandidate, cs) -> GateVerdict:
    """Deterministic, READ-ONLY gate: are the referenced ids real, and is the candidate coherent?
    This does NOT decide activation (that stays a human/Layer-9 step) and NEVER writes state - it
    only reports whether the proposal is admissible for that later decision. Anti-fabrication: an
    evidence anchor or method that the core does not contain fails here, so a skill can't cite
    evidence that isn't there."""
    reasons: list[str] = []
    get = getattr(cs.core, "get", None)
    if get is None:
        return GateVerdict(False, ("core has no get() - cannot verify references",))
    if get(candidate.method_id) is None:
        reasons.append(f"method_id {candidate.method_id} not in the core")
    missing = [a for a in candidate.evidence_anchors if get(a) is None]
    if missing:
        reasons.append(f"evidence anchors not in the core: {missing}")
    if candidate.status is not SkillStatus.PROBATIONARY:
        # a freshly proposed skill must enter probationary - never propose it already active
        reasons.append("a proposed skill must be probationary (activation is a separate decision)")
    return GateVerdict(not reasons, tuple(reasons))


def propose(candidate: SkillCandidate, cs, *, store_path=None) -> dict:
    """Validate a candidate against the core and, if admissible, record it as an append-only
    proposal (never rewrites an earlier record). Returns {admissible, reasons, skill_id, recorded}.
    Emits a PROPOSAL only - Layer 9 / a human still decides whether it may become active."""
    verdict = validate_against_core(candidate, cs)
    recorded = False
    if verdict.admissible and store_path is not None:
        try:
            store_path.parent.mkdir(parents=True, exist_ok=True)
            with store_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(candidate.to_record(), ensure_ascii=False) + "\n")
            recorded = True
        except OSError:
            recorded = False
    return {"admissible": verdict.admissible, "reasons": list(verdict.reasons),
            "skill_id": candidate.skill_id(), "recorded": recorded}


__all__ = ["SkillStatus", "SkillCandidate", "GateVerdict", "validate_against_core", "propose",
           "SKILL_VERSION"]
