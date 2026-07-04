"""Guard — the shared enforcement seam: run the constitution gate AND the personal use-policy at the
one point where Joni is about to output or act (docs/CONSTITUTION.md §4,
docs/PERSONAL_STATE.md §7). Deterministic; the LLM never decides here.

Shadow mode (default): compute + audit the verdict but never block — safe on the live output
path with ZERO behavioural change; the audit shows what enforce mode WOULD do. Enforce mode:
BLOCK / ESCALATE stop the output/action; ABSTAIN softens but proceeds.
"""
from __future__ import annotations

from dataclasses import dataclass

from joni.constitution.gate import Constitution, Decision, Proposal, Verdict
from joni.personal.store import PersonalClaim, Use, use_policy

_OUTWARD_USE = (Use.ASSERT, Use.SOFT)   # what may inform the outward voice; INTERNAL/NONE excluded


def usable_personal(claims) -> tuple[PersonalClaim, ...]:
    """The personal claims the use-policy permits to inform Joni's outward voice: confirmed/
    observed/inferred self-claims (ASSERT/SOFT). Sensitive, third-party (``other:``), rejected and
    outdated claims are dropped (INTERNAL/NONE). Single source of truth for the consumption filter —
    both ``guard()`` and the self-review consumption path call it."""
    return tuple(c for c in claims if use_policy(c) in _OUTWARD_USE)


@dataclass(frozen=True)
class GuardDecision:
    verdict: Verdict                              # the constitution decision (already audited)
    allowed: bool                                 # may the output/action proceed?
    usable_personal: tuple[PersonalClaim, ...]    # personal claims permitted to inform the voice
    mode: str                                     # "shadow" | "enforce"


def guard(proposal: Proposal, personal_claims=(), *, constitution: Constitution,
          mode: str = "shadow") -> GuardDecision:
    """Evaluate a proposed output/action against both gates. ``constitution.check`` audits every
    non-ALLOW verdict. In shadow mode ``allowed`` is always True (never blocks); in enforce mode a
    BLOCK or ESCALATE sets it False. The personal claims are filtered to those the use-policy lets
    inform the outward voice (confirmed/observed/inferred self-claims; sensitive / third-party /
    rejected / outdated are dropped)."""
    verdict = constitution.check(proposal)
    usable = usable_personal(personal_claims)
    stop = verdict.decision in (Decision.BLOCK, Decision.ESCALATE)
    allowed = True if mode == "shadow" else not stop
    return GuardDecision(verdict, allowed, usable, mode)
