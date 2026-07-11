"""Auditability - every escalation is reproducible and benchmark-evaluable.

Records why it escalated, what was scored, the per-dimension mean and spread, the red-flags, the
final action and the veto rule that produced it, plus reps and estimated cost. No user data is
written unfiltered; only the source id/title and the structured verdict/scores go in.
"""

from __future__ import annotations


def record(item, verdict, grounded, esc, dims, red_flags, decision, reps, cost, cfg,
           full_text=None) -> dict:
    return {
        "source": getattr(item, "key", getattr(item, "id", "")),
        "title": (getattr(item, "title", "") or "")[:160],
        "target_module": verdict.get("component_key", ""),
        # what the VERIFIER actually judged on (the whole paper when fetchable, else the abstract)
        "verifier_evidence": "full-text" if (full_text or "").strip() else "abstract",
        "grounded_in": "full-text" if isinstance(grounded, dict) else "abstract",
        "escalation_reasons": list(esc.reasons),
        "mode": cfg.mode,
        "reps": reps,
        "dimensions": {name: {"score": round(d.score, 4), "variance": round(d.variance, 4)}
                       for name, d in dims.items()},
        "red_flags": [{"type": f.type, "severity": f.severity, "explanation": f.explanation}
                      for f in red_flags],
        "aggregate_score": decision.aggregate,
        "confidence": decision.confidence,
        "action": decision.action,
        "veto": decision.veto,
        "cost_eur": cost,
        "prompt_version": "v1",
    }
