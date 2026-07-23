"""P3 of the method-sandbox (design-notes/METHOD_SANDBOX_AUFTRAG.md §6): wire trials into the loop.

This closes the loop the shelf has been missing. Each cycle (when enabled), for a few un-tested
candidate methods that MATCH a hand-curated benchmark (``problems``), it synthesises a solver from
the method's text (P2), runs it in the sandbox (P0) and judges it by the metric (P1) - then records
the measured verdict as a per-method trial through the gate (``cs.record_method_trial``). That moves
``trial_count`` / ``success_count`` / ``failure_count``, so the existing lifecycle takes over:

  * a run of ``no_benefit`` / ``harmful`` verdicts drives a method toward ``retire_unproductive`` -
    the 268-method backlog finally **drains** on measured evidence, not just age;
  * a ``benefit`` makes it eligible for activation-**ready** (human/Kevin-gated), never auto-active.

Honest bounds: only methods with a matching benchmark are trialed; the rest stay untested (no false
signal). Recording is a measured trial, not a promotion - Joni still never promotes his own methods.
OFF by default (``JONI_SANDBOX_LLM_TRIALS``); capped per cycle; budget-metered; fail-open.
"""
from __future__ import annotations

import contextlib

import desi_layer9 as l9

from . import problems, solver_synth

MAX_PER_CYCLE = 2


def _untested_candidates(cs) -> list:
    return [m for m in cs.core.all(l9.ObjectType.METHOD)
            if getattr(getattr(m, "status", None), "value", "") in ("candidate", "provisional")
            and int(getattr(m, "trial_count", 0)) == 0]


def _skill_store():
    """The append-only SkillCandidate store, or None when config is unavailable (standalone tests).
    Resolving paths() must never break a trial - a crystallisation without a store still validates
    the candidate and reports it, it just isn't persisted."""
    try:
        from ..autonomy.config import paths
        return paths().skill_candidates
    except Exception:  # noqa: BLE001
        return None


def _crystallize_and_propose(cs, m, prob, out, proto, cycle) -> dict | None:
    """On a measured benefit, crystallise the method into a probationary SkillCandidate that carries
    its OWN verification (the benchmark) and propose it through the read-only gate (append-only).
    Fail-open: a crystallisation fault never breaks the trial loop. Returns the propose() dict (with
    ``admissible`` / ``skill_id``) or None if nothing crystallised."""
    try:
        from . import skill
        affinity = prob.spec.affinities[0] if getattr(prob.spec, "affinities", ()) else ""
        cand = skill.crystallize(
            m, verification=getattr(prob.spec, "task_set", ""), task_desc=prob.task_desc,
            affinity=affinity, trial_result=out.get("result", {}), evidence_anchors=(m.id,))
        if cand is None:
            return None
        res = skill.propose(cand, cs, store_path=_skill_store())
        if res.get("admissible"):
            proto.record(cycle, "skill_proposed",
                         f"crystallised skill from '{getattr(m, 'name', m.id)}' "
                         f"({res['skill_id']}, reliability {cand.operational_reliability}) - "
                         f"probationary, awaiting a Layer-9/human decision")
        return res
    except Exception:  # noqa: BLE001 - crystallisation must never break the trial loop
        return None


def run(cs, extensions: dict, proto, cycle: int = 0, *, budget=None, runs_per_week: int = 0,
        max_per_cycle: int = MAX_PER_CYCLE, call=None) -> dict:
    """Trial up to ``max_per_cycle`` un-tested candidate methods that match a benchmark, and record
    each measured verdict. No-op unless ``JONI_SANDBOX_LLM_TRIALS=1``. Never raises."""
    if not solver_synth.enabled():
        return {"trialed": 0, "results": []}
    done, results, skills = 0, [], []
    considered = matched = discarded = 0            # the trial funnel (scoreboard, priority 1)
    for m in _untested_candidates(cs):
        if done >= max_per_cycle:
            break
        considered += 1
        prob = problems.match(str(getattr(m, "name", "")), str(getattr(m, "summary", "")))
        if prob is None:
            continue                                   # no benchmark -> left honestly untested
        matched += 1
        method_text = str(getattr(m, "summary", "") or getattr(m, "name", ""))
        out = solver_synth.trial_method(cs, method_text, prob.spec, prob.task_desc,
                                        budget=budget, cycle=cycle, runs_per_week=runs_per_week,
                                        call=call)
        if not out.get("trialed"):
            discarded += 1                             # a mapping that produced NO valid test
            continue                                   # synthesis failed / over budget: not a trial
        verdict = out["verdict"]
        with contextlib.suppress(Exception):           # a recording must never break the cycle
            cs.record_method_trial(m.id, success=(verdict == "benefit"), run_id=f"sandbox-c{cycle}")
        done += 1
        results.append({"method": m.id, "name": str(getattr(m, "name", m.id)),
                        "task_set": getattr(prob.spec, "task_set", ""), "verdict": verdict,
                        "delta": out.get("result", {}).get("delta")})
        proto.record(cycle, "trialed",
                     f"sandbox-trialed '{getattr(m, 'name', m.id)}': {verdict} "
                     f"(delta {out.get('result', {}).get('delta')}) - trial recorded")
        if verdict == "benefit":                       # crystallise a measured success into a skill
            proposed = _crystallize_and_propose(cs, m, prob, out, proto, cycle)
            if proposed is not None:
                skills.append(proposed)
    extensions["sandbox_trials"] = results
    extensions["skills_proposed"] = skills
    # the funnel priority 1 scores on: valid tests (trialed) vs discarded mappings (no valid test)
    extensions["trial_funnel"] = {"considered": considered, "matched": matched,
                                  "trialed": done, "discarded": discarded}
    return {"trialed": done, "results": results, "skills_proposed": len(skills),
            "funnel": extensions["trial_funnel"]}


__all__ = ["run", "MAX_PER_CYCLE"]
