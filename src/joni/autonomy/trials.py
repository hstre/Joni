"""Let Kevin trial the methods Joni parked on the shared shelf.

Joni harvests methods onto the shared Layer-9 core as *candidates* (``methods.py``); he
fills the shelf but never tries anything. Kevin is the one that puts a method to work.
Each cycle, if Kevin is installed, we hand it the same in-memory core and let it run its
deterministic transfer trials on the candidate/provisional methods, recording outcomes
through the gate.

This keeps ONE authoritative core: Kevin trials Joni's live shelf in-process, no second
store, no cross-repo copy. The governance boundary is Kevin's, not ours - it records
trials and flags *activation-ready* provisional methods, but it never promotes. A trial is
recorded at most once per ``run_id``, so a method only reaches activation over Joni's real,
repeated runs - no time jumps.

Soft dependency: without ``kevin`` (or with the core unavailable) this is a clean no-op.
"""

from __future__ import annotations


def run_trials(cs, proto, cycle: int = 0, *, run_id: str | None = None) -> dict:
    empty = {"trialed": 0, "succeeded": 0, "failed": 0, "activation_ready": 0}
    try:
        from kevin import trial_runner
    except Exception:  # noqa: BLE001  - Kevin not installed: skip silently.
        return empty

    rid = run_id or f"joni-c{cycle}"
    try:
        rep = trial_runner.trial_methods(cs.core, run_id=rid)
    except Exception as exc:  # noqa: BLE001  - never let a trial break the cycle.
        proto.record(cycle, "note", f"method trials skipped: {exc}")
        return empty

    ready = len(rep.get("activation_ready", []))
    if rep["trialed"]:
        proto.record(
            cycle, "trialed",
            f"Kevin trialed {rep['trialed']} method(s): {rep['succeeded']} passed, "
            f"{rep['failed']} failed"
            + (f" · {ready} activation-ready (awaiting a human)" if ready else ""))
    return {"trialed": rep["trialed"], "succeeded": rep["succeeded"],
            "failed": rep["failed"], "activation_ready": ready}
