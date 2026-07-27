"""Schlafmodus, Phase S0: the state machine, its triggers, and intake suppression.

The sleep mode exists for one reason: when intake outruns digestion, the shelf grows faster than
anything on it ever ripens. Sleeping is the deliberate counter-move - stop eating, keep processing.

This module is only the **skeleton**: the four-state machine (AWAKE / SLEEP_LIGHT / SLEEP_DEEP /
WAKE_TRANSITION), its deterministic + time triggers, the intake suppression, and the honest
before/after measurement. It introduces **no new thinking pass**. The passes that run while Joni
sleeps are the ones that already exist (trials, re-trials, Hindsight review, disputes, breakdown) -
later phases wire refragmentation, the DESi structural audit and the wake queue on top of this.

Two triggers, both deterministic, no model:

  * **pressure** - digestion has stalled for ``JONI_SLEEP_STALL`` cycles (read from the intake<->
    digestion marker: no test, no worked Streitfrage, no Hindsight review in that time);
  * **time**    - Joni has been awake ``JONI_SLEEP_AWAKE_CYCLES`` cycles.

Hysteresis on both sides (a minimum awake span before re-sleeping, a minimum sleep span before
waking) plus a hard cap on total sleep, so the machine can neither flap nor get stuck asleep.

**Shadow by default.** The state machine runs and is persisted every cycle, but it only *gates*
intake when ``JONI_SLEEP=1``. Off, it is pure observation: how often would Joni sleep, and did those
windows actually mature anything? That is measured before the gate is ever handed the authority -
the same measure-before-adopting rule every other arm here follows.

The measurement is deliberately about **ripening, not activity**: the wake report compares four
monotone maturation counters (valid tests, crystallised skills, resolved episodes, Hindsight
reviews) before sleep and after waking. "Refragmented 400 entries" is not progress; a verdict that
closed, a skill that matured, an episode that resolved is. ``matured`` is false when nothing moved,
and that is the point - a sleep window that changed nothing must read as a failure, not as work.

Read-only wrt Layer 9. Writes exactly one artefact (``state/sleep_state.json``). Fail-open.
"""
from __future__ import annotations

import contextlib
import json
import os

AWAKE = "AWAKE"
SLEEP_LIGHT = "SLEEP_LIGHT"
SLEEP_DEEP = "SLEEP_DEEP"
WAKE_TRANSITION = "WAKE_TRANSITION"

#: the states in which intake is suppressed (the wake transition is still a handover cycle)
ASLEEP: tuple[str, ...] = (SLEEP_LIGHT, SLEEP_DEEP, WAKE_TRANSITION)

STALL_CYCLES = 2        # digestion stalled this long -> pressure
AWAKE_CYCLES = 24       # awake this long -> sleep is due (time trigger)
DEEP_AFTER = 3          # cycles in SLEEP_LIGHT with pressure still on -> SLEEP_DEEP
MIN_SLEEP = 2           # hysteresis: never wake before this many cycles asleep
MIN_AWAKE = 6           # hysteresis: never re-sleep before this many cycles awake
MAX_SLEEP = 8           # hard cap: a sleep that never ends is a failure, not a state


def enabled() -> bool:
    """Whether sleep may actually SUPPRESS intake. Off = the machine runs as pure observation."""
    return os.getenv("JONI_SLEEP") == "1"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _read(path) -> dict:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def pressure(cycle: int, *, digestion_path) -> tuple[bool, str]:
    """Deterministic pressure signal: has digestion stalled? Reads the intake<->digestion marker.
    No history yet (a cold start) is never pressure - he does not fall asleep on an empty ledger."""
    st = _read(digestion_path)
    last = st.get("last_digested_cycle")
    if last is None:
        return False, ""
    stalled = cycle - int(last)
    if stalled >= _int("JONI_SLEEP_STALL", STALL_CYCLES):
        return True, f"Verdauung steht seit {stalled} Zyklen"
    return False, ""


def decide(st: dict, cycle: int, *, pressure: bool) -> tuple[str, str]:
    """The pure transition function: current state + this cycle's pressure -> (next state, reason).
    Deterministic, no IO, no model - the whole point is that it can be read and tested in one go."""
    state = st.get("state", AWAKE)
    age = cycle - int(st.get("since", cycle))                  # cycles in the CURRENT state
    asleep_since = st.get("asleep_since")
    slept = cycle - int(asleep_since) if asleep_since is not None else 0

    if state == AWAKE:
        if age < _int("JONI_SLEEP_MIN_AWAKE", MIN_AWAKE):
            return AWAKE, ""                                   # hysteresis: no immediate re-sleep
        if pressure:
            return SLEEP_LIGHT, "Druck: Aufnahme überholt Verarbeitung"
        if age >= _int("JONI_SLEEP_AWAKE_CYCLES", AWAKE_CYCLES):
            return SLEEP_LIGHT, f"Zeit-Trigger: {age} Zyklen wach"
        return AWAKE, ""

    if state in (SLEEP_LIGHT, SLEEP_DEEP):
        if slept >= _int("JONI_SLEEP_MAX", MAX_SLEEP):
            return WAKE_TRANSITION, f"Schlaf-Obergrenze ({slept} Zyklen) erreicht"
        if not pressure and slept >= _int("JONI_SLEEP_MIN", MIN_SLEEP):
            return WAKE_TRANSITION, "Druck weg - Verdauung läuft wieder"
        if state == SLEEP_LIGHT and pressure and age >= _int("JONI_SLEEP_DEEP_AFTER", DEEP_AFTER):
            return SLEEP_DEEP, "Druck hält an - Tiefschlaf"
        return state, ""

    return AWAKE, "Übergabe abgeschlossen"                     # WAKE_TRANSITION lasts one cycle


def _maturation(paths) -> dict:
    """The four monotone maturation counters, read from the latest Consolidator scoreboard row.

    These are the honest before/after quantities: things that RIPENED (a measured test, a
    crystallised skill, a resolved episode, a completed review), never things that merely happened.
    """
    p = getattr(paths, "scoreboard_series", None)
    rec: dict = {}
    if p is not None:
        with contextlib.suppress(OSError, json.JSONDecodeError):
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                rec = json.loads(lines[-1])
    return {
        "valid_tests": int((rec.get("window") or {}).get("valid_tests", 0)),
        "skills": int((rec.get("skills") or {}).get("total", 0)),
        "episodes_resolved": int((rec.get("episodes") or {}).get("resolved", 0)),
        "hindsight_reviews": int((rec.get("hindsight") or {}).get("reviews", 0)),
    }


def wake_report(st: dict, cycle: int, paths) -> dict:
    """Did this sleep window ripen anything? Delta of the maturation counters, entry vs wake.
    ``matured`` false = the window produced activity but no maturation. That is a failed sleep."""
    before = st.get("entry") or {}
    after = _maturation(paths)
    delta = {k: v - int(before.get(k, 0)) for k, v in after.items()}
    asleep_since = st.get("asleep_since")
    return {"cycle": cycle,
            "slept_cycles": cycle - int(asleep_since) if asleep_since is not None else 0,
            "delta": delta, "matured": any(v > 0 for v in delta.values())}


def is_asleep(st: dict) -> bool:
    """Whether the sleep PASSES should run this cycle. Independent of the gate on purpose: in
    observation mode Joni does the sleep work without the sleep fast, so the question 'does sleep
    work ripen anything?' can be answered before intake is ever actually stopped."""
    return bool(st) and st.get("state") in (SLEEP_LIGHT, SLEEP_DEEP)


def woke_this_cycle(st: dict, prev_state: str) -> bool:
    """True on exactly the cycle the machine returned to AWAKE - when S4 writes the handover."""
    return bool(st) and prev_state == WAKE_TRANSITION and st.get("state") == AWAKE


def intake_suppressed(st: dict) -> bool:
    """Whether THIS cycle's intake is actually held back. Only ever true with the gate switched on -
    in observation mode the machine may report SLEEP_DEEP and still let every intake through."""
    return bool(st) and enabled() and st.get("state") in ASLEEP


def step(extensions: dict, proto, cycle: int, *, paths) -> dict:
    """Advance the machine one cycle, persist it, expose it as ``extensions['sleep']``.
    Fail-open by construction: any error yields ``{}``, i.e. AWAKE and nothing suppressed."""
    try:
        path = getattr(paths, "sleep_state", None)
        st = _read(path) or {"state": AWAKE, "since": cycle, "asleep_since": None}
        under, why = pressure(cycle, digestion_path=getattr(paths, "digestion", None))
        new, reason = decide(st, cycle, pressure=under)
        prev = st.get("state", AWAKE)
        if new != prev:
            st["state"] = new
            st["since"] = cycle
            st["reason"] = reason or why
            if new == SLEEP_LIGHT and prev == AWAKE:
                st["asleep_since"] = cycle
                st["entry"] = _maturation(paths)               # the honest 'before'
            if new == AWAKE and prev == WAKE_TRANSITION:
                st["last_wake"] = wake_report(st, cycle, paths)
                st["asleep_since"] = None
                st.pop("entry", None)
            shadow = "" if enabled() else " [Beobachtung - Aufnahme wird nicht gedrosselt]"
            proto.record(cycle, "sleep", f"{prev} -> {new}: {st['reason']}{shadow}")
        st["cycle"] = cycle
        st["prev"] = prev                                      # S4 reads this to spot the wake
        st["pressure"] = under
        st["gate"] = enabled()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        extensions["sleep"] = st
        return st
    except Exception:  # noqa: BLE001 - the sleep machine must never break a cycle
        return {}


__all__ = ["AWAKE", "SLEEP_LIGHT", "SLEEP_DEEP", "WAKE_TRANSITION", "ASLEEP", "enabled",
           "pressure", "decide", "wake_report", "intake_suppressed", "is_asleep",
           "woke_this_cycle", "step"]
