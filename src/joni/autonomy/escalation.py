"""The audited escalation from Granite to DeepSeek - logic by rules, not by an LLM.

The architecture is **not** "two models give opinions and we average". It is a strict pipeline:

    input -> Granite (joni-semantic) proposes structured candidates
          -> Layer 9 checks schema / provenance / status / conflicts
          -> ONLY when a named, deterministic escalation rule fires:
             DeepSeek (joni-hard) is invoked as the escalation analyst
          -> Layer 9 decides authoritatively (both models only ever produce proposals)

DeepSeek is therefore never a silent fallback and never a parallel vote. It is reached only
through one of these explicit, auditable reasons (priority order = stakes order):

  * ``risky_status_transition`` - a self-model change or a method promotion (highest stakes)
  * ``high_conflict_load``      - more open conflicts than the threshold
  * ``contested``               - a claim sits in CONTESTED, or an open conflict is hard
  * ``low_evidence_coverage``   - too few active claims carry any evidence
  * ``underspecified``          - a proposal is too thin to judge structurally
  * ``unclear_scope``           - a proposal has no real topic/scope

The chosen reason is persisted in the call capture (``escalation_reason``), so every DeepSeek
invocation is attributable. Thresholds are env-dialled; the whole layer is opt-in behind the
same ``JONI_SEMANTIC_PROPOSALS`` switch and capped at one escalation per cycle (budget is the
hard ceiling).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import desi_layer9 as l9
from desi_layer9 import Status

from . import model_call, model_profile, projection
from .config import paths

# Reasons, in descending stakes. The first that fires wins (a single, named escalation).
RISKY_STATUS_TRANSITION = "risky_status_transition"
HIGH_CONFLICT_LOAD = "high_conflict_load"
CONTESTED = "contested"
LOW_EVIDENCE_COVERAGE = "low_evidence_coverage"
UNDERSPECIFIED = "underspecified"
UNCLEAR_SCOPE = "unclear_scope"

_ORDER = (RISKY_STATUS_TRANSITION, HIGH_CONFLICT_LOAD, CONTESTED,
          LOW_EVIDENCE_COVERAGE, UNDERSPECIFIED, UNCLEAR_SCOPE)

_SYS = (
    "You are an escalation analyst for an epistemic reasoning agent. You are given a DIFFICULT "
    "open problem (a contradiction, an underspecified or low-coverage area) that the primary "
    "structured model could not settle. Reason about it and output ONLY a JSON array of objects "
    "{\"text\": <one atomic, checkable statement that sharpens or resolves the problem>, "
    "\"topic\": <short topic>}. No opinions, no meta-commentary, no questions. At most 4 items. "
    "Your output is a PROPOSAL, never a decision.")


def enabled() -> bool:
    """Escalation rides the same master switch as the proposal layer, with its own opt-out."""
    return projection.enabled() and os.getenv("JONI_ESCALATION", "1") != "0"


def _thr_conflict_load() -> int:
    return int(os.getenv("JONI_ESCALATE_CONFLICT_LOAD", "3"))


def _thr_min_coverage() -> float:
    return float(os.getenv("JONI_ESCALATE_MIN_COVERAGE", "0.34"))


def _min_claims_for_coverage() -> int:
    # Below this, there are too few claims to judge coverage - do not escalate on it.
    return int(os.getenv("JONI_ESCALATE_COVERAGE_MIN_CLAIMS", "5"))


@dataclass(frozen=True)
class Signals:
    """The deterministic inputs to the escalation decision - gathered from Layer 9, never an LLM."""

    conflict_load: int = 0
    hard_conflict: bool = False
    contested_claims: int = 0
    evidence_coverage: float = 1.0       # fraction of active claims carrying >=1 evidence link
    coverage_measured: bool = False      # False when too few claims to judge coverage
    risky_transition: bool = False
    underspecified: bool = False
    unclear_scope: bool = False


def reason(sig: Signals) -> str | None:
    """The single named escalation reason, or ``None``. Pure and ordered by stakes - this is the
    whole routing decision, deterministic (no model is consulted to decide to escalate)."""
    if sig.risky_transition:
        return RISKY_STATUS_TRANSITION
    if sig.conflict_load >= _thr_conflict_load():
        return HIGH_CONFLICT_LOAD
    if sig.contested_claims > 0 or sig.hard_conflict:
        return CONTESTED
    if sig.coverage_measured and sig.evidence_coverage < _thr_min_coverage():
        return LOW_EVIDENCE_COVERAGE
    if sig.underspecified:
        return UNDERSPECIFIED
    if sig.unclear_scope:
        return UNCLEAR_SCOPE
    return None


def gather_signals(cs, *, risky_transition: bool = False,
                   underspecified: bool = False, unclear_scope: bool = False) -> Signals:
    """Read the escalation signals off the current Layer-9 state."""
    open_conflicts = cs.core.open_conflicts()
    hard = any(getattr(c, "severity", "soft") == "hard" for c in open_conflicts)
    contested = sum(1 for c in cs.core.all(l9.ObjectType.CLAIM) if c.status is Status.CONTESTED)
    active = cs.active_claims()
    measured = len(active) >= _min_claims_for_coverage()
    coverage = 1.0
    if measured:
        with_ev = {el.claim_id for el in cs.core.all(l9.ObjectType.EVIDENCE_LINK)}
        coverage = sum(1 for c in active if c.id in with_ev) / max(1, len(active))
    return Signals(
        conflict_load=len(open_conflicts), hard_conflict=hard, contested_claims=contested,
        evidence_coverage=coverage, coverage_measured=measured,
        risky_transition=risky_transition, underspecified=underspecified,
        unclear_scope=unclear_scope)


def _focus(cs) -> tuple[str, str]:
    """The hardest open contradiction, as (focus_text, topic) for the escalation prompt.
    Prefers a hard-severity conflict; falls back to any open one, else a generic state focus."""
    open_conflicts = sorted(cs.core.open_conflicts(),
                            key=lambda c: (0 if getattr(c, "severity", "soft") == "hard" else 1,
                                           c.id))
    texts = {c.id: (c.text, c.topic) for c in cs.core.all(l9.ObjectType.CLAIM)}
    for conf in open_conflicts:
        ids = [i for i in conf.claim_ids[:2] if i in texts]
        if len(ids) == 2:
            (ta, topa), (tb, _) = texts[ids[0]], texts[ids[1]]
            return (f"Contradiction:\n- A: {ta}\n- B: {tb}", topa or "unsorted")
    topics = cs.topics()
    return ("Low-coverage / underspecified area in the current state.",
            topics[0] if topics else "unsorted")


def escalate_if_needed(cs, extensions: dict, proto, cycle: int, *,
                       risky_transition: bool = False) -> dict:
    """Run at most one DeepSeek escalation when a named rule fires. The escalation's output, like
    Granite's, enters Layer 9 as ``candidate`` SOURCE proposals (never authoritative). No-op when
    disabled or when no rule fires - DeepSeek is never reached without a recorded reason."""
    out = {"escalated": 0, "reason": None, "claims": 0}
    if not enabled():
        return out
    sig = gather_signals(cs, risky_transition=risky_transition)
    why = reason(sig)
    if why is None:
        return out
    focus, topic = _focus(cs)
    prof = model_profile.profile("joni-hard")
    context = projection.state_slice(cs, focus, k=prof.state_k)
    ctx = "\n".join(f"- {t}" for t in context) or "(none yet)"
    user = (f"ESCALATION REASON: {why}\n\nPROBLEM:\n{focus}\n\n"
            f"RELEVANT EXISTING STATE (state_k={prof.state_k}):\n{ctx}")
    store_dir = paths().model_calls
    output, cap = model_call.call(prof, _SYS, user, run_id=f"joni-c{cycle}",
                                  store_dir=store_dir, escalation_reason=why)
    if output is None or cap is None:
        return out
    props = projection._parse(output, topic)
    for p in props:
        cs.learn(p["text"], p["topic"], source_id=f"deepseek:{cap.call_id}")
        out["claims"] += 1
    out["escalated"] = 1
    out["reason"] = why
    log = extensions.setdefault("escalations", [])
    log.append({"call_id": cap.call_id, "served_model": cap.served_model, "reason": why,
                "state_k": cap.state_k, "replayed": cap.replayed, "claims": len(props)})
    extensions["escalations"] = log[-200:]
    proto.record(cycle, "escalated",
                 f"DeepSeek escalation [{why}] proposed {len(props)} claim(s) "
                 f"[{cap.served_model}, replayed={cap.replayed}] - candidates via the gate, "
                 "not authoritative; Layer 9 decides")
    return out
