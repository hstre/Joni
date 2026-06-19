"""Benefit-review of Joni's adopted extensions - review the value, prune the failures.

The lifecycle Joni's own ideas follow: a coherent idea, once agreed, becomes an Auftrag and is
built in as an extension; after a while its **benefit must be reviewed**, and on failure the
extension is removed. This module is the review-and-prune step for the model-arm extensions.

"Remove" is implemented as **deactivate**, deliberately: an autonomous loop must never destructively
self-edit its own source. A failed extension is switched OFF (recorded in
``state/ext_disabled.json``, which each arm's ``enabled()`` honours) - the code stays, so a human
can fix and re-enable it, or delete it for good. This delivers "the extension is removed" (it stops
running) without Joni rewriting his own code.

Failure = an extension that has been ACTIVE for a full review window yet produced **no** measurable
contribution in that window (its activity log did not grow). A delivering extension simply gets a
fresh window. The review never touches the protected core or anything not in its small registry.
"""

from __future__ import annotations

import json
import os

from . import projection
from .config import paths

# name -> (env_flag, default_on, activity_keys in extensions, review_window_cycles). Only arms that
# write an activity log can be benefit-reviewed (no log -> no way to measure contribution).
_REGISTRY: dict[str, tuple[str, bool, tuple[str, ...], int]] = {
    "doktores": ("JONI_DOKTORES", True, ("doktores_review", "doktores_hyp_log"), 60),
    "literature_synthesis": ("JONI_LITERATURE_SYNTHESIS", False, ("synthesis_log",), 60),
}


def _flag_on(flag: str, default_on: bool) -> bool:
    return os.getenv(flag, "1" if default_on else "0") != "0"


def _disabled_path():
    return paths().root / "state" / "ext_disabled.json"


def _load_disabled() -> set:
    p = _disabled_path()
    try:
        return set(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else set()
    except Exception:  # noqa: BLE001 - a missing/garbled file just means nothing is disabled
        return set()


def active(name: str) -> bool:
    """An extension arm's ``enabled()`` calls this: True unless the benefit-review pruned it."""
    return name not in _load_disabled()


def _activity(extensions: dict, keys) -> int:
    return sum(len(extensions.get(k, []) or []) for k in keys)


def review(extensions: dict, proto, cycle: int = 0) -> dict:
    """Review each registered extension; auto-deactivate one that has been active a full window
    with no contribution. Returns the disabled set. Deterministic, bounded, never a core touch."""
    state = extensions.setdefault("ext_review", {})       # name -> {since, count}
    disabled = _load_disabled()
    proj = projection.enabled()
    changed = False
    for name, (flag, default_on, keys, window) in _REGISTRY.items():
        running = proj and _flag_on(flag, default_on) and name not in disabled
        if not running:
            state.pop(name, None)                         # not active -> no window running
            continue
        cur = _activity(extensions, keys)
        st = state.get(name)
        if not isinstance(st, dict) or "since" not in st:
            state[name] = {"since": cycle, "count": cur}  # open a fresh review window
            continue
        if cycle - int(st["since"]) >= window:
            if cur <= int(st.get("count", 0)):            # no growth in a full window = no benefit
                disabled.add(name)
                changed = True
                proto.record(cycle, "note",
                             f"extension-review: '{name}' deactivated - no measurable contribution "
                             f"in {window} cycles (auto-pruned; code kept, re-enable after a fix)")
            else:
                state[name] = {"since": cycle, "count": cur}   # it delivered -> new window
    if changed:
        p = _disabled_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(sorted(disabled)), encoding="utf-8")
    extensions["ext_disabled"] = sorted(disabled)
    extensions["ext_review_status"] = {
        name: {"active": (projection.enabled() and _flag_on(flag, default_on)
                          and name not in disabled),
               "disabled": name in disabled,
               "since": state.get(name, {}).get("since"),
               "window": window}
        for name, (flag, default_on, _keys, window) in _REGISTRY.items()}
    return {"disabled": sorted(disabled)}
