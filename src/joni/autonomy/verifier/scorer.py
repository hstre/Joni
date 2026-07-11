"""The probabilistic scorer - repeated, multi-dimensional, continuous 0..1 assessment.

One joni-hard call per repetition; the mean and the SPREAD across repetitions are both kept, so a
noisy, unstable judgement cannot hide behind a tidy average (paper 2607.05391: repeated evaluation
reduces variance, criteria decomposition reduces complexity). No dependency on token logprobs - the
model returns structured numeric scores; the logit-expectation path is an optional refinement,
the numeric path is the default and always works. Best-effort: fewer than one valid repetition (all
malformed / budget spent) returns None, and the normal Doktores decision stands.
"""

from __future__ import annotations

import json
import statistics

from .. import model_call, model_profile
from .models import DIMENSIONS, VerificationDimension, VerificationRedFlag

_SYS = (
    "You are a strict VERIFIER for Joni, an autonomous agent. Joni's Doktores arm proposed a "
    "self-improvement (a non-core code change derived from a source). Your job is NOT to propose "
    "anything new and NOT to decide - only to SCORE the proposal on independent dimensions so a "
    "deterministic rule can decide. Rules: judge each dimension on its own; never raise a score "
    "just because the text is longer or more eloquent; keep PLAUSIBILITY (it sounds right) apart "
    "from EVIDENCE (the source actually supports it); distinguish MISSING evidence from NEGATIVE "
    "evidence; name safety red-flags explicitly. Output ONLY JSON:\n"
    "{\"scores\": {<dimension>: <0.0-1.0>, ...}, \"red_flags\": [{\"type\": <str>, \"severity\": "
    "\"low|medium|high\", \"explanation\": <str>}], \"rationale\": <short str>}\n"
    "Dimensions (all 0..1): module_fit (the method really maps onto the named non-core module), "
    "evidence_grounding (grounded in the source's actual method, not just plausibility), "
    "consistency (internally coherent), alternatives (a simpler/existing route considered, or it "
    "may not apply), error_safety (change stays non-core and cannot degrade Joni), impact "
    "(measurable benefit), info_needed (HIGH = more evidence/full text needed), "
    "reasoning_stability (justification is stable), hard_constraint_compliance (non-core only, "
    "never the protected "
    "core), overclaim_risk (HIGH = convincing but unsupported). No prose outside the JSON."
)


def _user(item, verdict: dict, grounded, full_text=None) -> str:
    body = (full_text or "").strip()
    if body:
        evidence = f"FULL PAPER TEXT (method/body, truncated):\n{body[:8000]}"
    else:
        evidence = ("ONLY the abstract is available (the full paper could not be fetched - a gated "
                    f"source):\n{(getattr(item, 'summary', '') or '')[:1500]}")
    return (
        f"SOURCE: {getattr(item, 'title', '')}\nURL: {getattr(item, 'url', '')}\n"
        f"{evidence}\n\n"
        f"Doktores' proposed self-improvement:\n"
        f"- target module: {verdict.get('component_key', '?')}\n"
        f"- change: {verdict.get('desired', '')}\n"
        f"- acceptance criterion: {verdict.get('acceptance', '')}\n\n"
        "Score every dimension 0..1 and list red-flags. JSON only."
    )


def _parse(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        s, e = text.find("{"), text.rfind("}")
        if s == -1 or e <= s:
            return None
        try:
            return json.loads(text[s:e + 1])
        except json.JSONDecodeError:
            return None


def _clamp(v) -> float | None:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


def _default_ask(cfg, *, cycle, budget, runs_per_week, store_dir):
    prof = model_profile.profile("joni-hard")

    def ask(system: str, user: str):
        text, _cap = model_call.call(
            prof, system, user, run_id=f"joni-c{cycle}-verifier",
            store_dir=store_dir, escalation_reason="doktores-verifier",
            budget=budget, runs_per_week=runs_per_week)
        return text
    return ask


def score(item, verdict: dict, grounded, cfg, *, full_text=None, budget=None, cycle=0,
          runs_per_week=0, store_dir=None, ask=None):
    """Run cfg.reps verifications; return (dimensions, red_flags, valid_reps, cost) or None.

    ``cost`` is the estimated spend charged to ``budget`` (bounded by cfg.max_cost_eur - the loop
    stops before exceeding it rather than guessing)."""
    prof = model_profile.profile("joni-hard")
    ask = ask or _default_ask(cfg, cycle=cycle, budget=budget, runs_per_week=runs_per_week,
                              store_dir=store_dir)
    per_dim: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    red_flags: list[VerificationRedFlag] = []
    rationale = ""
    try:
        per_call = float(model_call.est_call_cost(prof))
    except Exception:  # noqa: BLE001 - cost estimate is advisory; budget.call charges the real seam
        per_call = 0.0
    cost = 0.0
    user = _user(item, verdict, grounded, full_text)
    for _ in range(cfg.reps):
        if per_call and cost + per_call > cfg.max_cost_eur:
            break                                          # defined budget stop, never overshoot
        out = _parse(ask(_SYS, user))
        cost += per_call
        if not out:
            continue                                       # malformed rep -> skip (retry via next)
        scores = out.get("scores") or {}
        got = False
        for d in DIMENSIONS:
            v = _clamp(scores.get(d))
            if v is not None:
                per_dim[d].append(v)
                got = True
        if not got:
            continue
        rationale = rationale or str(out.get("rationale", ""))[:300]
        for rf in (out.get("red_flags") or [])[:6]:
            if isinstance(rf, dict) and rf.get("type"):
                red_flags.append(VerificationRedFlag(
                    type=str(rf.get("type"))[:60], severity=str(rf.get("severity", "medium")),
                    explanation=str(rf.get("explanation", ""))[:200]))
    valid = max(len(v) for v in per_dim.values()) if per_dim else 0
    if valid == 0:
        return None                                        # nothing usable -> normal decision holds
    dims: dict[str, VerificationDimension] = {}
    for d in DIMENSIONS:
        vals = per_dim[d]
        if not vals:
            continue
        var = statistics.pvariance(vals) if len(vals) > 1 else 0.0
        dims[d] = VerificationDimension(name=d, score=statistics.fmean(vals), variance=var,
                                        rationale=rationale)
    return dims, _dedup(red_flags), valid, round(cost, 6)


def _dedup(flags):
    seen, out = set(), []
    for f in flags:
        if f.type not in seen:
            seen.add(f.type)
            out.append(f)
    return out
