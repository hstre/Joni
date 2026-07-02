"""(b) The operator cycle: propose a deep operator, apply it, grade by RESOLUTION, record the trial.

This is the seam that turns the pipeline from a proposer into a learner. One cycle:
  1. propose deep operators for the core's open gaps (Baustein B via ``from_core``);
  2. take the top proposal and APPLY it — via an INJECTED ``apply_fn(core, proposal)``. The creative
     'use method M to resolve gap G' step is the loop's / an LLM's job; this module never invents it and
     never mutates the protected core itself. Tests inject a stub;
  3. GRADE deterministically by whether the target conflict is resolved in the core AFTER the attempt —
     an observed fact, not an LLM judge: gone -> success, still open -> no_benefit, apply errored ->
     technical_failure;
  4. RECORD a ``DeepMethodTrial`` to the store, which feeds Baustein C.

Deterministic given ``apply_fn``. Fail-open: if proposing fails (no DESi), the cycle records nothing.
"""

from __future__ import annotations

from .operators import DeepMethodTrial, from_core
from .trial_store import record_trial


def open_conflict_ids(core) -> set[str]:
    try:
        return {c.id for c in core.open_conflicts()}
    except Exception:  # noqa: BLE001
        return set()


def grade_by_resolution(target: str, before: set[str], after: set[str], *,
                        errored: bool = False) -> str:
    """The deterministic grade from OBSERVED core state (no judge). ``target`` is the gap id."""
    if errored:
        return "technical_failure"
    if target not in before:
        return "unknown"                       # we can't attribute a gap that wasn't open to begin with
    return "success" if target not in after else "no_benefit"


def _default_propose(core):
    return from_core(core, top_k_per_gap=1)


def run_operator_cycle(core, store_path: str, apply_fn, *, propose=None, scope: str = "live"):
    """Run ONE cycle and return the recorded ``DeepMethodTrial`` (or ``None`` if there was nothing to
    do). ``apply_fn(core, proposal)`` is the injected creative step; ``propose(core)`` defaults to
    ``from_core``. The target conflict's resolution in the core decides the grade."""
    propose = propose or _default_propose
    proposals = list(propose(core) or [])
    if not proposals:
        return None
    p = proposals[0]
    target = p.target.split(":", 1)[-1]        # "conflict:X17" -> "X17"

    before = open_conflict_ids(core)
    errored = False
    try:
        apply_fn(core, p)
    except Exception:  # noqa: BLE001 -> a technical failure carries NO methodological signal
        errored = True
    after = open_conflict_ids(core)

    result = grade_by_resolution(target, before, after, errored=errored)
    trial = DeepMethodTrial(method_id=p.method_id, target=target, result=result, scope=scope,
                            gap_kind=p.gap_kind or "unknown")
    record_trial(store_path, trial)
    return trial
