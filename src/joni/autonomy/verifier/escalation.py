"""Escalation trigger - decide whether a Doktores decision needs the probabilistic verifier.

More compute ONLY where the decision is actually uncertain or consequential. In Joni's domain the
verifier is invoked at the one moment that matters: a commission about to be FILED (and, since the
auto-trigger is armed, auto-implemented). That is already selective - only ~4% of reviewed sources
reach filing. On top of that, specific signals raise the escalation reason set:

  * abstract-only evidence (the full text was not read) - the method may be oversold;
  * a structural red-flag hint on the verdict itself.

The clinical "score margin / doctor disagreement" triggers have no direct analogue while Doktores is
a single binary judge; the verifier's own repeated multi-dimensional scoring surfaces that
instability instead. When Doktores gains continuous triage scores, add the margin trigger here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EscalationDecision:
    escalate: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)


def should_escalate(verdict: dict, grounded, cfg) -> EscalationDecision:
    """A to-be-filed commission is always escalated (it is consequential and auto-implementable);
    the reasons capture WHY, for the audit and the shadow evaluation."""
    if not cfg.enabled or not verdict or verdict.get("applicable") is not True:
        return EscalationDecision(False)
    reasons = ["commission_to_file"]
    if grounded is None:                      # #228 grounding got no full text -> abstract only
        reasons.append("abstract_only_evidence")
    # cheap structural hint: an acceptance criterion with no number/percentage is weak/unfalsifiable
    acc = str(verdict.get("acceptance", "")).lower()
    if acc and not any(c.isdigit() for c in acc) and "%" not in acc:
        reasons.append("acceptance_maybe_unfalsifiable")
    return EscalationDecision(True, tuple(reasons))
