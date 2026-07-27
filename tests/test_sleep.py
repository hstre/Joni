"""Schlafmodus S0: the state machine, its two deterministic triggers, the hysteresis on both sides,
the hard cap, intake suppression (shadow by default) and the honest maturation measurement."""
from __future__ import annotations

import json
from types import SimpleNamespace

from joni.autonomy import sleep


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _paths(tmp_path):
    return SimpleNamespace(
        sleep_state=tmp_path / "sleep_state.json",
        digestion=tmp_path / "digestion.json",
        scoreboard_series=tmp_path / "consolidator_series.jsonl")


def _awake(since=0):
    return {"state": sleep.AWAKE, "since": since, "asleep_since": None}


# --- the transition function -------------------------------------------------------------------

def test_hysteresis_blocks_an_immediate_re_sleep():
    # pressure right after waking must NOT put him straight back to sleep
    state, _ = sleep.decide(_awake(since=10), 12, pressure=True)
    assert state == sleep.AWAKE


def test_pressure_trigger_puts_him_to_sleep():
    state, reason = sleep.decide(_awake(since=0), 6, pressure=True)
    assert state == sleep.SLEEP_LIGHT and "Aufnahme überholt" in reason


def test_time_trigger_puts_him_to_sleep_without_any_pressure():
    state, reason = sleep.decide(_awake(since=0), sleep.AWAKE_CYCLES, pressure=False)
    assert state == sleep.SLEEP_LIGHT and "Zeit-Trigger" in reason


def test_light_deepens_only_while_the_pressure_holds():
    st = {"state": sleep.SLEEP_LIGHT, "since": 10, "asleep_since": 10}
    assert sleep.decide(st, 10 + sleep.DEEP_AFTER, pressure=True)[0] == sleep.SLEEP_DEEP
    assert sleep.decide(st, 10 + sleep.DEEP_AFTER - 1, pressure=True)[0] == sleep.SLEEP_LIGHT


def test_a_released_pressure_wakes_him_but_not_before_the_minimum():
    st = {"state": sleep.SLEEP_DEEP, "since": 10, "asleep_since": 10}
    assert sleep.decide(st, 11, pressure=False)[0] == sleep.SLEEP_DEEP       # min sleep = 2
    assert sleep.decide(st, 10 + sleep.MIN_SLEEP, pressure=False)[0] == sleep.WAKE_TRANSITION


def test_the_hard_cap_ends_even_a_sleep_whose_pressure_never_releases():
    # a sleep that never ends would be a failure state, not a mode - the cap counts from FALLING
    # asleep, so deepening cannot silently extend it
    st = {"state": sleep.SLEEP_DEEP, "since": 13, "asleep_since": 10}
    state, reason = sleep.decide(st, 10 + sleep.MAX_SLEEP, pressure=True)
    assert state == sleep.WAKE_TRANSITION and "Obergrenze" in reason


def test_the_wake_transition_lasts_exactly_one_cycle():
    st = {"state": sleep.WAKE_TRANSITION, "since": 20, "asleep_since": 10}
    assert sleep.decide(st, 21, pressure=True)[0] == sleep.AWAKE     # even under pressure


# --- the pressure signal -----------------------------------------------------------------------

def test_pressure_reads_the_digestion_marker(tmp_path):
    p = _paths(tmp_path)
    assert sleep.pressure(50, digestion_path=p.digestion) == (False, "")   # no history: never
    p.digestion.write_text(json.dumps({"last_digested_cycle": 48}))
    assert sleep.pressure(49, digestion_path=p.digestion)[0] is False
    under, why = sleep.pressure(50, digestion_path=p.digestion)
    assert under is True and "2 Zyklen" in why


# --- suppression: shadow by default ------------------------------------------------------------

def test_the_machine_suppresses_nothing_until_the_gate_is_switched_on(monkeypatch):
    st = {"state": sleep.SLEEP_DEEP}
    monkeypatch.delenv("JONI_SLEEP", raising=False)
    assert sleep.intake_suppressed(st) is False           # observation - nothing auto-activates
    monkeypatch.setenv("JONI_SLEEP", "1")
    assert sleep.intake_suppressed(st) is True
    assert sleep.intake_suppressed({"state": sleep.AWAKE}) is False
    assert sleep.intake_suppressed({}) is False           # a failed step never suppresses


# --- the step: persistence + the honest before/after -------------------------------------------

def test_step_persists_the_state_and_records_the_transition(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_SLEEP", raising=False)
    p = _paths(tmp_path)
    p.digestion.write_text(json.dumps({"last_digested_cycle": 0}))
    ext, proto = {}, _Proto()
    sleep.step(ext, proto, 0, paths=p)                    # opens the awake window at cycle 0
    st = sleep.step(ext, proto, 6, paths=p)               # 6 awake + stalled digestion -> sleep
    assert st["state"] == sleep.SLEEP_LIGHT and st["asleep_since"] == 6
    assert st["gate"] is False and ext["sleep"] is st
    assert json.loads(p.sleep_state.read_text())["state"] == sleep.SLEEP_LIGHT
    assert any("Beobachtung" in s for k, s in proto.events if k == "sleep")


def test_the_wake_report_measures_ripening_not_activity(tmp_path):
    p = _paths(tmp_path)
    # entry snapshot: 1 valid test, 2 skills; on waking the scoreboard shows the SAME counters,
    # i.e. the window was busy but nothing matured - that must read as a failure, not as work.
    st = {"state": sleep.WAKE_TRANSITION, "asleep_since": 10,
          "entry": {"valid_tests": 1, "skills": 2, "episodes_resolved": 0, "hindsight_reviews": 0}}
    p.scoreboard_series.write_text(json.dumps(
        {"window": {"valid_tests": 1}, "skills": {"total": 2},
         "episodes": {"resolved": 0}, "hindsight": {"reviews": 0}}) + "\n")
    rep = sleep.wake_report(st, 15, p)
    assert rep["slept_cycles"] == 5 and rep["matured"] is False
    assert rep["delta"] == {"valid_tests": 0, "skills": 0, "episodes_resolved": 0,
                            "hindsight_reviews": 0}
    # one measured test more -> ripening
    p.scoreboard_series.write_text(json.dumps(
        {"window": {"valid_tests": 2}, "skills": {"total": 2},
         "episodes": {"resolved": 0}, "hindsight": {"reviews": 0}}) + "\n")
    rep2 = sleep.wake_report(st, 15, p)
    assert rep2["matured"] is True and rep2["delta"]["valid_tests"] == 1


def test_a_full_sleep_cycle_leaves_a_wake_report_behind(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_SLEEP", raising=False)
    p = _paths(tmp_path)
    ext, proto = {}, _Proto()
    p.digestion.write_text(json.dumps({"last_digested_cycle": 0}))
    sleep.step(ext, proto, 0, paths=p)
    sleep.step(ext, proto, 6, paths=p)                            # -> SLEEP_LIGHT
    p.digestion.write_text(json.dumps({"last_digested_cycle": 8}))   # digestion resumes
    assert sleep.step(ext, proto, 8, paths=p)["state"] == sleep.WAKE_TRANSITION
    st = sleep.step(ext, proto, 9, paths=p)
    assert st["state"] == sleep.AWAKE and st["asleep_since"] is None
    # nothing on the scoreboard moved while he slept -> the window is reported as unproductive
    assert st["last_wake"]["slept_cycles"] == 3 and st["last_wake"]["matured"] is False
    assert "entry" not in st


def test_step_is_fail_open(tmp_path, monkeypatch):
    # a paths object without the sleep artefacts must not raise, and must suppress nothing
    monkeypatch.setenv("JONI_SLEEP", "1")
    st = sleep.step({}, _Proto(), 1, paths=SimpleNamespace())
    assert st["state"] == sleep.AWAKE and sleep.intake_suppressed(st) is False
