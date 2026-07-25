"""Priority 2 (operator measure 1): couple intake to digestion.

New claims and methods may only be fully admitted when digestion is actually happening - at least
one of: a method **test**, a **Streitfrage** worked, or a **Hindsight review** - in the current or
the immediately preceding cycle. Otherwise the shelf grows faster than it is processed and the
backlog only widens.

This is deterministic backpressure, not a freeze: it engages ONLY when *all* digestion stalls for
longer than the grace window, and releases the moment any digestion resumes. Because tests run on
the existing shelf and reviews run on the existing provisional store, digestion can always restart
without new intake, so the gate can never deadlock. Read-only wrt Layer 9; OFF unless
``JONI_INTAKE_COUPLING=1``.
"""
from __future__ import annotations

import contextlib
import json
import os

GRACE = 1                      # digestion in cycle N-1 permits intake in cycle N


def enabled() -> bool:
    return os.getenv("JONI_INTAKE_COUPLING") == "1"


def digested_this_cycle(extensions: dict) -> bool:
    """Did real digestion happen this cycle: a method trial/re-trial recorded, or a Hindsight review
    reactivated-and-resolved? (Mere condensation each cycle is not 'work'; a resolved review is.)"""
    if extensions.get("sandbox_trials") or extensions.get("skill_retrials"):
        return True
    hs = extensions.get("hindsight") or {}
    return int(hs.get("reviews_triggered", 0)) > 0


def _read(path) -> dict:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def intake_permitted(cycle: int, *, path, grace: int = GRACE) -> bool:
    """Permit intake iff digestion happened within the last ``grace`` cycles. No history yet (a
    fresh window) permits - the gate never freezes a cold start; it engages only after a stall."""
    st = _read(path)
    last = st.get("last_digested_cycle")
    if last is None:
        return True
    return (cycle - int(last)) <= grace


def note(cycle: int, extensions: dict, *, path) -> dict:
    """Record this cycle's digestion (call at END of cycle, after the trial + Hindsight arms).
    Updates the marker the next intake gate reads. Fail-open; sets ``extensions['digestion']``."""
    st = _read(path)
    d = digested_this_cycle(extensions)
    if d:
        st["last_digested_cycle"] = cycle
    st["total_cycles"] = int(st.get("total_cycles", 0)) + 1
    st["total_digested"] = int(st.get("total_digested", 0)) + (1 if d else 0)
    st["digested_this_cycle"] = d
    st["cycle"] = cycle
    if path is not None:
        with contextlib.suppress(OSError):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
    extensions["digestion"] = st
    return st


__all__ = ["enabled", "digested_this_cycle", "intake_permitted", "note", "GRACE"]
