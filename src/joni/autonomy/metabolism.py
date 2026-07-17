"""Homeostatic metabolism - the missing regulator that couples INTAKE to CONSOLIDATION.

Joni already *sheds* (``homeostasis.regulate`` + the ``retire_*`` passes) and *measures*
(``homeostasis.vitality``), but the two run open-loop: ingest and emergence can keep minting
claims, topics, syntheses and methods regardless of how large the un-consolidated backlog has
grown. The health metrics observe the state; they never throttle it. So "newly produced" is
structurally favoured over "cleanly integrated", and every improvement to intake capacity just
lets Joni overfeed faster.

This module is the setpoint controller. Each cycle it reads Joni's own state (the deterministic
``vitality`` record + the live conflict count), computes a **load** in [0,1] from the pressures
that matter - un-supported hypothesis backlog, un-tested method pile, conflict growth outpacing
resolution, stagnation - and holds a two-state metabolism with **hysteresis**:

  * **hungry**  - intake and new synthesis are allowed;
  * **sated**   - stop expanding; spend the following cycles only on consolidation.

Hysteresis (enter ``sated`` at ``high``, only return to ``hungry`` below ``low``) stops it
oscillating between eating and pausing every cycle. The central rule, in one line:

    if epistemic liabilities grow faster than they are consolidated, stop expansion and
    consolidate until the backlog has clearly fallen.

This is not another intelligence layer - it is a basic metabolism. It is deterministic, holds no
epistemic authority, writes no Layer-9 object (its state lives in the peripheral ``extensions``
dict and the protocol), and only *gates* the existing intake steps; the shedding/consolidation
passes always run. It is measured every cycle but only enforces when ``JONI_METABOLISM=1`` - so
the operator can read real load numbers from a shadow run before tuning the thresholds and
switching it on.
"""
from __future__ import annotations

import desi_layer9 as l9

# Hysteresis band on the load score. Deliberately conservative defaults; tune from a shadow run
# (the per-cycle load is recorded) before enabling enforcement.
DEFAULT_HIGH = 0.70          # hungry -> sated at/above this load
DEFAULT_LOW = 0.40           # sated -> hungry only below this load

# Denominators that turn a raw count into a [0,1] pressure. Anchored to the existing caps so the
# metabolism and the shedding passes speak the same scale (regulate caps live hypotheses at 30;
# JONI_METHOD_MAX_AGE defaults to 40).
_BACKLOG_CAP = 30            # un-supported hypotheses
_UNTESTED_METHOD_CAP = 40    # candidate/provisional methods with zero trials
_CONFLICT_GROWTH_CAP = 20    # net new live conflicts since last cycle
_STAGNATION_CAP = 12         # cycles of no epistemic development

_HUNGRY, _SATED = "hungry", "sated"


def pressures(vitality: dict, *, open_conflicts: int, prev_open_conflicts: int,
              untested_methods: int) -> dict:
    """The individual [0,1] pressures. Each is a liability that a healthy metabolism keeps low."""
    backlog = min(1.0, vitality.get("unsupported_hypotheses", 0) / _BACKLOG_CAP)
    methods = min(1.0, untested_methods / _UNTESTED_METHOD_CAP)
    growth = max(0, open_conflicts - prev_open_conflicts)
    conflict = min(1.0, growth / _CONFLICT_GROWTH_CAP)
    stagnation = min(1.0, vitality.get("stagnation_cycles", 0) / _STAGNATION_CAP)
    return {"backlog": round(backlog, 3), "untested_methods": round(methods, 3),
            "conflict_growth": round(conflict, 3), "stagnation": round(stagnation, 3)}


def load(p: dict) -> float:
    """The binding constraint - the WORST pressure. A governor stops on any single overload, not
    on the average (an average lets one runaway dimension hide behind three calm ones)."""
    return round(max(p.values()), 3) if p else 0.0


def next_state(prev_state: str, load_value: float, *,
               high: float = DEFAULT_HIGH, low: float = DEFAULT_LOW) -> str:
    """The hysteresis state machine. From hungry, cross ``high`` to satiate; from sated, only fall
    below ``low`` to feed again; in between, hold - so it never flip-flops each cycle."""
    if prev_state == _SATED:
        return _HUNGRY if load_value <= low else _SATED
    return _SATED if load_value >= high else _HUNGRY


def intake_allowed(state) -> bool:
    """Intake / new synthesis is allowed unless the metabolism is sated. Accepts a state string or
    a full metabolism record."""
    s = state.get("state") if isinstance(state, dict) else state
    return s != _SATED


def _untested_methods(cs) -> int:
    return sum(1 for m in cs.core.all(l9.ObjectType.METHOD)
               if getattr(m, "trial_count", 0) == 0
               and getattr(getattr(m, "status", None), "value", "") in ("candidate", "provisional"))


def observe(cs, extensions: dict, proto, cycle: int = 0, *,
            high: float = DEFAULT_HIGH, low: float = DEFAULT_LOW) -> dict:
    """Compute and persist this cycle's metabolism from Joni's own state. Read-only w.r.t. Layer 9;
    records a protocol note only on a state change. Returns the record (with ``state``/``load``)."""
    vit = extensions.get("vitality", {})
    prev = extensions.get("metabolism", {})
    open_now = len(cs.core.open_conflicts())
    prev_open = int(prev.get("open_conflicts", open_now))
    untested = _untested_methods(cs)
    p = pressures(vit, open_conflicts=open_now, prev_open_conflicts=prev_open,
                  untested_methods=untested)
    lv = load(p)
    state = next_state(prev.get("state", _HUNGRY), lv, high=high, low=low)
    record = {"state": state, "load": lv, "pressures": p, "open_conflicts": open_now,
              "untested_methods": untested, "cycle": cycle}
    extensions["metabolism"] = record
    hist = extensions.setdefault("metabolism_history", [])
    hist.append({"cycle": cycle, "state": state, "load": lv})
    extensions["metabolism_history"] = hist[-500:]
    if prev.get("state", _HUNGRY) != state:
        proto.record(cycle, "note",
                     f"metabolism: {prev.get('state', _HUNGRY)} -> {state} "
                     f"(load {lv:.2f}; pressures {p})")
    return record


__all__ = ["pressures", "load", "next_state", "intake_allowed", "observe",
           "DEFAULT_HIGH", "DEFAULT_LOW"]
