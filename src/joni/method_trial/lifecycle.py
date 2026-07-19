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


def run(cs, extensions: dict, proto, cycle: int = 0, *, budget=None, runs_per_week: int = 0,
        max_per_cycle: int = MAX_PER_CYCLE, call=None) -> dict:
    """Trial up to ``max_per_cycle`` un-tested candidate methods that match a benchmark, and record
    each measured verdict. No-op unless ``JONI_SANDBOX_LLM_TRIALS=1``. Never raises."""
    if not solver_synth.enabled():
        return {"trialed": 0, "results": []}
    done, results = 0, []
    for m in _untested_candidates(cs):
        if done >= max_per_cycle:
            break
        prob = problems.match(str(getattr(m, "name", "")), str(getattr(m, "summary", "")))
        if prob is None:
            continue                                   # no benchmark -> left honestly untested
        method_text = str(getattr(m, "summary", "") or getattr(m, "name", ""))
        out = solver_synth.trial_method(cs, method_text, prob.spec, prob.task_desc,
                                        budget=budget, cycle=cycle, runs_per_week=runs_per_week,
                                        call=call)
        if not out.get("trialed"):
            continue                                   # synthesis failed / over budget: not a trial
        verdict = out["verdict"]
        with contextlib.suppress(Exception):           # a recording must never break the cycle
            cs.record_method_trial(m.id, success=(verdict == "benefit"), run_id=f"sandbox-c{cycle}")
        done += 1
        results.append({"method": m.id, "verdict": verdict,
                        "delta": out.get("result", {}).get("delta")})
        proto.record(cycle, "trialed",
                     f"sandbox-trialed '{getattr(m, 'name', m.id)}': {verdict} "
                     f"(delta {out.get('result', {}).get('delta')}) - trial recorded")
    extensions["sandbox_trials"] = results
    return {"trialed": done, "results": results}


__all__ = ["run", "MAX_PER_CYCLE"]
