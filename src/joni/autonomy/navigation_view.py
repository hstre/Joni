"""Joni's navigation capability — run the solution-space navigation on the live Layer-9 core.

READ-ONLY: it projects the core into a prioritised exploration agenda (which unreached island / which
bridge to work next, with which deep-method operator and why) and returns it as a plain dict. It NEVER
mutates the core, never runs a model in the loop path, and lazy-imports ``solution_space`` so it adds
nothing to loop startup. Fail-open: if the package or the data is unavailable, it returns an empty,
clearly-marked result rather than raising.

This is the confirmed value of the solution-space work (navigation + discovery), wired as a capability
the autonomy loop can call — deliberately NOT the method-as-prompt lever that nine measurements found
null. The *acting* on the agenda (the creative exploration step) stays out of here; this only SURFACES
where the room is.
"""

from __future__ import annotations


def run_navigation(core, *, top: int = 8, allow_model: bool = False, **kw) -> dict:
    """Project ``core`` into a navigation agenda. ``allow_model`` defaults to False (deterministic
    lexical embeddings — no network in the loop). Returns ``{"available": bool, ...report}``."""
    try:
        from joni.solution_space import navigate_core
    except Exception:  # noqa: BLE001 -> package/optional dep missing: stay silent, never crash a cycle
        return {"available": False, "reason": "solution_space unavailable", "agenda": []}
    try:
        report = navigate_core(core, top=top, allow_model=allow_model, **kw)
    except Exception:  # noqa: BLE001 -> read-only projection must never break the loop
        return {"available": False, "reason": "navigation failed", "agenda": []}
    return {"available": True, **report.to_dict()}


def top_agenda_line(core, **kw) -> str:
    """A one-line human summary of the highest-priority next step (for a loop log). Empty if none."""
    rep = run_navigation(core, **kw)
    agenda = rep.get("agenda") or []
    if not agenda:
        return ""
    a = agenda[0]
    return (f"navigation: {a['kind']} {a['target']} (prio {a['priority']}) "
            f"-> try {a['method_id']} — {a['reason']}")
