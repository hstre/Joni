"""P2 of the method-sandbox (design-notes/METHOD_SANDBOX_AUFTRAG.md §6): method text -> solver.

A shelf method is only *text* (name + summary + steps). To trial it for real, that text has to
become an executable ``solve(payload) -> dict``. Here a captured ``joni-hard`` call synthesises
that solver from the method's description; it then runs as the **intervention** in the P0 sandbox
and is judged by the P1 metric against a **hand-curated, frozen** task set.

Two invariants make this honest rather than circular:

  * **LLM for language, rules for logic.** The model only *writes* the solver. Whether the method
    helped is decided by the metric alone (P1) - `benefit` / `no_benefit` / `harmful`, recorded
    honestly (a failed synthesis is a result, not hidden).
  * **Anti-circularity (Auftrag §5).** The task set, its gold labels, the baseline and the negative
    control are hand-curated and independent. The model that writes the solver **never** labels its
    own test cases.

Safety: the synthesised code is untrusted and runs **only** through ``sandbox.run_solver`` - the P0
harness (import allowlist, audit hook, resource limits, process-group kill) contains a pathological
or malicious generation as a clean failure, which the metric then scores as no benefit.

OFF by default (``JONI_SANDBOX_LLM_TRIALS=1``); budget-metered and captured via ``model_call``.
"""
from __future__ import annotations

import os
import re
from dataclasses import replace

from . import sandbox_trial

_SYS = (
    "You write ONE pure-Python function and nothing else. Define exactly:\n"
    "    def solve(payload: dict) -> dict\n"
    "Return {\"label\": <one allowed label>}. It is PURE COMPUTE: no I/O, no network, no files, "
    "no os/sys/subprocess/open. You may import ONLY from: math, re, json, statistics, itertools, "
    "functools, collections, string, decimal, fractions. Output ONLY the function source - no "
    "explanation, no markdown fences."
)


def enabled() -> bool:
    return os.getenv("JONI_SANDBOX_LLM_TRIALS") == "1"


def _user_prompt(method_text: str, task_desc: str) -> str:
    return (f"Method (implement its idea as the solver):\n{method_text.strip()}\n\n"
            f"Task the solver must perform:\n{task_desc.strip()}\n\n"
            "Write solve(payload) accordingly.")


def _extract_code(text: str) -> str | None:
    """Pull the function source out of the model output - tolerant of a ```python fence or prose
    around it. Returns None if there is no ``def solve``."""
    if not text:
        return None
    fence = re.search(r"```(?:python)?\s*(.+?)```", text, re.DOTALL)
    body = fence.group(1) if fence else text
    if "def solve" not in body:
        return None
    # trim anything before the first top-level def solve
    idx = body.find("def solve")
    return body[idx:].strip() or None


def _default_call(system: str, user: str, *, run_id: str, budget, runs_per_week: int):
    from ..autonomy import model_call, model_profile
    from ..autonomy.config import paths
    out, _cap = model_call.call(model_profile.joni_hard(), system, user, run_id=run_id,
                                store_dir=paths().model_calls, budget=budget,
                                runs_per_week=runs_per_week)
    return out


def synthesize_solver(method_text: str, task_desc: str, *, budget=None, cycle: int = 0,
                      runs_per_week: int = 0, call=None) -> str | None:
    """Synthesise a solver source from the method's text (captured ``joni-hard`` call, or an
    injected ``call`` for tests). Returns the source, or None (empty input / over budget / model
    unavailable / no usable code) - the caller then simply does not trial this method."""
    text = (method_text or "").strip()
    if not text:
        return None
    caller = call or _default_call
    out = caller(_SYS, _user_prompt(text, task_desc), run_id=f"solversynth-c{cycle}",
                 budget=budget, runs_per_week=runs_per_week)
    return _extract_code(out or "")


def _verdict(result: dict) -> str:
    """Metric-only verdict. ``benefit`` = a real, controlled improvement; ``harmful`` = the method
    made it worse than the baseline; ``no_benefit`` = no measurable gain (or a noise-level one)."""
    if result.get("passed"):
        return "benefit"
    if float(result.get("delta", 0.0)) < 0:
        return "harmful"
    return "no_benefit"


def trial_method(cs, method_text: str, problem: sandbox_trial.TrialSpec, task_desc: str, *,
                 budget=None, cycle: int = 0, runs_per_week: int = 0, call=None) -> dict:
    """Synthesise a solver from ``method_text``, run it as the intervention over the hand-curated
    ``problem`` in the sandbox, and record an honest metric-only verdict. ``problem``'s
    intervention_src is ignored - the synthesised solver replaces it. The method is never labelled
    by the same model that solves it. Fail-open: never raises for a synthesis or trial fault."""
    src = synthesize_solver(method_text, task_desc, budget=budget, cycle=cycle,
                            runs_per_week=runs_per_week, call=call)
    if not src:
        return {"trialed": False, "verdict": "no_solver"}
    spec = replace(problem, intervention_src=src)
    result = sandbox_trial.run(spec)
    verdict = _verdict(result)
    sealed = sandbox_trial.record(cs, spec, run_id=f"llmtrial-c{cycle}") if cs is not None else {}
    return {"trialed": True, "verdict": verdict, "result": result,
            "sealed": bool(sealed.get("sealed"))}


__all__ = ["enabled", "synthesize_solver", "trial_method"]
