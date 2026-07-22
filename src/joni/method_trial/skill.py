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


def crystallize(method, *, verification, task_desc, affinity, trial_result, evidence_anchors,
                decision_guidance: str = "") -> SkillCandidate | None:
    """The crystallisation bridge (design note §6, stage S3): turn a shelf ``Method`` that
    *measurably* beat its baseline in the sandbox into a probationary ``SkillCandidate``.

    A bare method is text only; a skill is the rich, evidence-anchored capability that carries its
    **own** verification - the exact benchmark that decided it works - plus the trial's measured
    effect and the reliability observed so far. This is the ONLY place a trial result becomes a
    skill proposal, and it does so honestly:

      * only a genuine metric pass crystallises (``trial_result['passed']``); a ``no_benefit`` or
        ``harmful`` trial returns ``None`` - no skill is minted from a non-result;
      * V_operational != V_epistemic: ``operational_reliability`` is the measured success rate,
        never an epistemic truth, and the candidate is always ``probationary`` - never auto-active;
      * it builds a *proposal* only. Layer 9 / a human still decides (via ``propose`` -> the gate).

    ``method`` is duck-typed (``id`` / ``name`` / ``summary`` / optional ``success_count`` /
    ``trial_count``) so this module never imports the method library. Returns ``None`` (never
    raises) if the trial did not pass or the pieces do not form a valid candidate - crystallisation
    must never break the trial loop.
    """
    if not isinstance(trial_result, dict) or not trial_result.get("passed"):
        return None
    procedure = str(getattr(method, "summary", "") or getattr(method, "name", "")).strip()
    method_id = str(getattr(method, "id", "")).strip()
    verification = str(verification or "").strip()
    if not (procedure and method_id and verification):
        return None
    aff = (str(affinity or "").strip() or "general")
    desc = (task_desc or "").strip()
    first = desc.splitlines()[0].strip() if desc else aff
    delta = trial_result.get("delta")
    sc = int(getattr(method, "success_count", 0) or 0)
    tc = int(getattr(method, "trial_count", 0) or 0)
    reliability = min(1.0, max(0.0, round(sc / tc, 4))) if tc > 0 else 1.0
    guidance = decision_guidance or (
        f"measured benefit Δ={delta} over the baseline on '{verification}'; the negative "
        f"control did not reproduce it. Probationary - activation is a separate Layer-9/human "
        f"decision.")
    try:
        return SkillCandidate(
            method_id=method_id,
            trigger=f"{aff}: {first}",
            procedure=procedure,
            verification=verification,
            applicability_boundary=(
                f"only for {aff} inputs of the '{verification}' kind; not for free text, other "
                f"formats, or inputs the benchmark did not cover"),
            evidence_anchors=tuple(str(a) for a in evidence_anchors if str(a).strip()),
            decision_guidance=guidance,
            operational_reliability=reliability,
            status=SkillStatus.PROBATIONARY,
        )
    except ValueError:
        return None


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


class LifecycleAction(StrEnum):
    """What S4 *recommends* for a skill - never what it does. Activation stays human/Layer-9 gated,
    so even ``PROMOTE`` is a recommendation surfaced for a human, not a state write."""

    PROMOTE = "promote"     # earned repeated passes -> recommend active (a human still decides)
    ARCHIVE = "archive"     # failed to earn its keep -> recommend retiring the proposal
    HOLD = "hold"           # still maturing / already terminal - no change recommended


@dataclass(frozen=True)
class LifecycleThresholds:
    """The bar a probationary skill must clear to be *recommended* for activation, and the floor
    below which it is *recommended* for archival. Deterministic - no model in the loop."""

    min_passes: int = 3                 # repeated benefit trials before promotion is considered
    promote_reliability: float = 0.75   # smoothed success rate to recommend active
    archive_reliability: float = 0.34   # at/below this (after enough trials) -> recommend archive
    min_trials_to_judge: int = 3        # never judge a skill on too little evidence


@dataclass(frozen=True)
class LifecycleAssessment:
    """A single, append-only lifecycle recommendation. It records the measured evidence it rests on
    (passes / trials / reliability) so the human deciding can see *why* - the consolidator asserts
    nothing it cannot show from real trial counts."""

    skill_id: str
    method_id: str
    action: LifecycleAction
    target_status: SkillStatus
    reliability: float
    passes: int
    trials: int
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_record(self) -> dict:
        return {"skill_id": self.skill_id, "method_id": self.method_id,
                "action": self.action.value, "target_status": self.target_status.value,
                "reliability": round(float(self.reliability), 4), "passes": self.passes,
                "trials": self.trials, "reasons": list(self.reasons)}


def assess_lifecycle(candidate: SkillCandidate, cs, *,
                     thresholds: LifecycleThresholds | None = None) -> LifecycleAssessment:
    """Deterministically decide what to *recommend* for a skill from its method's real, accumulated
    trial counts (S4). This is READ-ONLY and human-gated: it never writes a status, never activates,
    and never turns operational success into an epistemic claim - it only surfaces a recommendation
    a human/Layer 9 then acts on. ``PROMOTE`` needs repeated passes AND a high smoothed success
    rate; ``ARCHIVE`` needs a measured failure below the floor after enough trials; else HOLDs.
    """
    t = thresholds or LifecycleThresholds()
    get = getattr(getattr(cs, "core", None), "get", None)
    method = get(candidate.method_id) if get is not None else None
    sc = int(getattr(method, "success_count", 0) or 0)
    tc = int(getattr(method, "trial_count", 0) or 0)
    reliability = round(sc / tc, 4) if tc > 0 else 0.0

    def _mk(action, target, reasons):
        return LifecycleAssessment(candidate.skill_id(), candidate.method_id, action, target,
                                   reliability, sc, tc, tuple(reasons))

    if candidate.status is SkillStatus.ARCHIVED:
        return _mk(LifecycleAction.HOLD, SkillStatus.ARCHIVED, ("already archived",))
    if method is None:
        return _mk(LifecycleAction.HOLD, candidate.status,
                   ("method not in the core - cannot judge fresh evidence",))
    # a measured failure archives regardless of current status (a promoted skill that later fails)
    if tc >= t.min_trials_to_judge and reliability <= t.archive_reliability:
        return _mk(LifecycleAction.ARCHIVE, SkillStatus.ARCHIVED,
                   (f"reliability {reliability} <= floor {t.archive_reliability} after {tc} trials "
                    "- failed to earn its keep",))
    if candidate.status is SkillStatus.PROBATIONARY:
        if sc >= t.min_passes and reliability >= t.promote_reliability:
            return _mk(LifecycleAction.PROMOTE, SkillStatus.ACTIVE,
                       (f"{sc} repeated passes, reliability {reliability} >= "
                        f"{t.promote_reliability} - recommend active (human-gated)",))
        return _mk(LifecycleAction.HOLD, SkillStatus.PROBATIONARY,
                   (f"maturing - {sc} passes / {tc} trials, reliability {reliability} "
                    f"(need {t.min_passes} passes at >= {t.promote_reliability})",))
    return _mk(LifecycleAction.HOLD, SkillStatus.ACTIVE,
               (f"active and holding - reliability {reliability} over {tc} trials",))


__all__ = ["SkillStatus", "SkillCandidate", "GateVerdict", "validate_against_core", "crystallize",
           "propose", "LifecycleAction", "LifecycleThresholds", "LifecycleAssessment",
           "assess_lifecycle", "SKILL_VERSION"]
