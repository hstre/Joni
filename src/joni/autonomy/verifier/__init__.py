"""Probabilistic verifier - an ESCALATION stage for Doktores, not a replacement.

Doktores decides from ONE joni-hard call whether a paper/tool could improve a non-core module and,
if so, files an Auftrag. That single binary judgement is fine when the case is clear - but when it
is borderline, unstable, or safety-relevant, more scrutiny is warranted. This package adds exactly
that: a probabilistic, multi-dimensional re-assessment (repeated sampling, continuous 0..1 scores,
deterministic veto rules) that runs ONLY on escalated cases and produces a SIGNAL - never a truth.

Boundaries (Joni's rule, kept): LLM for language, rules for logic. The model produces continuous
per-dimension scores; the escalation triggers, the weighted aggregation, the safety vetoes and the
final action are all DETERMINISTIC. Scores are decision signals, not facts (paper 2607.05391,
LLM-as-a-Verifier: continuous scores via the scoring-token distribution, scaled by granularity /
repetition / criteria decomposition).

Default MODE is ``shadow``: it runs alongside the normal Doktores decision, logs what it WOULD have
done, and changes nothing - so both loops run in parallel and we evaluate which was more sensible
before ever letting it decide (``JONI_VERIFIER_MODE=enforce`` flips it on). This is the same
observe-then-adopt discipline as the router shadow.
"""

from __future__ import annotations

from . import audit, config, escalation, safety, scorer
from .models import VerificationDimension, VerificationRedFlag, VerificationResult


def verify(item, verdict: dict, grounded, *, full_text=None, budget=None, cycle: int = 0,
           runs_per_week: int = 0, store_dir=None, ask=None) -> VerificationResult | None:
    """Verify ONE proposed Doktores commission before it is filed. Returns a VerificationResult, or
    None when the verifier is off / not escalated / could not run (then the normal decision stands).

    ``verdict``    - the applicable verdict dict Doktores produced.
    ``grounded``   - the full-text grounding result (dict | False | None); None means abstract-only.
    ``full_text``  - the paper body (fetched once by Doktores), so the verifier judges on the WHOLE
                     paper, not the abstract; None for gated/unfetchable sources (then abstract).
    ``ask`` is injectable for tests; defaults to the real joni-hard model call inside ``scorer``.
    """
    cfg = config.load()
    if not cfg.enabled:
        return None
    esc = escalation.should_escalate(verdict, grounded, cfg)
    if not esc.escalate:
        return None
    scored = scorer.score(item, verdict, grounded, cfg, full_text=full_text,
                          budget=budget, cycle=cycle, runs_per_week=runs_per_week,
                          store_dir=store_dir, ask=ask)
    if scored is None:                       # budget/parse failure -> normal decision stands
        return None
    dims, red_flags, reps, cost = scored
    decision = safety.decide(dims, red_flags, cfg)
    rec = audit.record(item, verdict, grounded, esc, dims, red_flags, decision, reps, cost, cfg,
                       full_text=full_text)
    return VerificationResult(
        escalated=True, escalation_reasons=list(esc.reasons), dimensions=dims,
        aggregate_score=decision.aggregate, confidence=decision.confidence,
        red_flags=red_flags, action=decision.action, veto=decision.veto, reps=reps, audit=rec)


__all__ = ["verify", "VerificationResult", "VerificationDimension", "VerificationRedFlag", "config"]
