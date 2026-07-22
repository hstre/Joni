"""S4 of the Procedural Skill Consolidator (design note §6): the skill lifecycle.

A crystallised skill (S3) enters ``probationary``. Maturation is not a claim - it is **earned** by
repeated sandbox passes against the skill's **own** verification (the benchmark that first
crystallised it). Each cycle this module:

  * re-trials a few *undecided* probationary skills against their stored ``verification`` benchmark,
    recording each measured pass/fail through the gate (``cs.record_method_trial``) so the smoothed
    ``operational_reliability`` reflects real, repeated evidence - not one lucky run;
  * assesses every known skill deterministically (``skill.assess_lifecycle``) and surfaces a
    **recommendation**: promote (enough repeated passes at a high success rate), archive (a measured
    failure below the floor), or hold (still maturing).

Hard invariants (§7). It **never writes a skill status** - promotion and archival are
recommendations written to an append-only log and a human "decide these" sheet; **activation is
gated**. Recording a re-trial is measurement, not promotion. V_operational never becomes
V_epistemic. OFF for re-trials unless ``JONI_SANDBOX_LLM_TRIALS=1``; the assessment always runs
(it only reads counts). Capped per cycle, budget-metered, fail-open.
"""
from __future__ import annotations

import contextlib
import json

from . import problems, skill, solver_synth

MAX_RETRIALS_PER_CYCLE = 2


def load_candidates(store_path) -> list[skill.SkillCandidate]:
    """Latest record per ``skill_id`` from the append-only proposal store (last line wins, so a
    later human-appended status change supersedes the crystallisation). Malformed lines are skipped,
    never fatal. Returns ``[]`` when the store is missing or unreadable."""
    if store_path is None:
        return []
    try:
        text = store_path.read_text(encoding="utf-8")
    except OSError:
        return []
    latest: dict[str, skill.SkillCandidate] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            cand = skill.SkillCandidate.from_record(json.loads(line))
        except (ValueError, json.JSONDecodeError):
            continue
        latest[cand.skill_id()] = cand
    return list(latest.values())


def _eligible_for_retrial(cand: skill.SkillCandidate, cs, t: skill.LifecycleThresholds) -> bool:
    """A probationary skill that is not yet decidable: still short of the passes needed for a
    promotion recommendation, and not already a measured failure. Terminal skills are not re-trialed
    (no wasted budget)."""
    if cand.status is not skill.SkillStatus.PROBATIONARY:
        return False
    get = getattr(getattr(cs, "core", None), "get", None)
    method = get(cand.method_id) if get is not None else None
    if method is None:
        return False
    sc = int(getattr(method, "success_count", 0) or 0)
    tc = int(getattr(method, "trial_count", 0) or 0)
    rel = sc / tc if tc > 0 else 0.0
    if sc >= t.min_passes:                                              # enough passes to judge
        return False
    # not yet a measured failure either -> still worth re-proving
    return not (tc >= t.min_trials_to_judge and rel <= t.archive_reliability)


def retrial(cs, cand: skill.SkillCandidate, *, budget=None, cycle: int = 0, runs_per_week: int = 0,
            call=None) -> dict | None:
    """Re-prove a skill against its **own** stored verification: synthesise a solver from the
    skill's procedure text, run it over that benchmark in the sandbox, and record the measured
    pass/fail through the gate. Returns the verdict dict, or None if there is no benchmark for the
    verification or the trial did not run. Fail-open."""
    prob = problems.by_task_set(cand.verification)
    if prob is None:
        return None                                    # no gold set for this verification: skip
    out = solver_synth.trial_method(cs, cand.procedure, prob.spec, prob.task_desc,
                                    budget=budget, cycle=cycle, runs_per_week=runs_per_week,
                                    call=call)
    if not out.get("trialed"):
        return None
    verdict = out["verdict"]
    with contextlib.suppress(Exception):               # a recording must never break the cycle
        cs.record_method_trial(cand.method_id, success=(verdict == "benefit"),
                               run_id=f"skill-retrial-c{cycle}")
    return {"skill_id": cand.skill_id(), "method": cand.method_id,
            "task_set": cand.verification, "name": cand.method_id, "verdict": verdict,
            "delta": out.get("result", {}).get("delta")}


def _append_log(log_path, actionable: list) -> None:
    """Append the actionable recommendations (promote/archive) as permanent, append-only events. The
    steady-state HOLDs are the current view (the sheet), not a per-cycle log entry."""
    if log_path is None or not actionable:
        return
    with contextlib.suppress(OSError):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            for a in actionable:
                f.write(json.dumps(a.to_record(), ensure_ascii=False) + "\n")


def _write_sheet(sheet_path, assessments: list) -> None:
    """Overwrite the human "decide these" sheet with the current recommendations. Overwritten each
    cycle (a current view, like ``to_resolve.md``) - the permanent record is the append-only log."""
    if sheet_path is None:
        return
    promote = [a for a in assessments if a.action is skill.LifecycleAction.PROMOTE]
    archive = [a for a in assessments if a.action is skill.LifecycleAction.ARCHIVE]
    hold = [a for a in assessments if a.action is skill.LifecycleAction.HOLD]
    lines = ["# Skill-Lifecycle — Entscheidungen für den Operator", "",
             "S4 empfiehlt nur. **Aktivierung bleibt human/Layer-9-gated**; Recording ≠ Promotion; "
             "operationaler Erfolg wird nie ein bestätigter Claim.", ""]

    def _block(title: str, items: list) -> None:
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append("_keine_")
        for a in items:
            lines.append(f"- `{a.skill_id}` (Methode `{a.method_id}`) — {a.passes}/{a.trials} "
                         f"Pässe, Reliability {a.reliability}: {'; '.join(a.reasons)}")
        lines.append("")

    _block("Empfohlen zur Aktivierung", promote)
    _block("Empfohlen zur Archivierung", archive)
    _block("In Bewährung (hold)", hold)
    with contextlib.suppress(OSError):
        sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(cs, extensions: dict, proto, cycle: int = 0, *, budget=None, runs_per_week: int = 0,
        thresholds: skill.LifecycleThresholds | None = None, store_path=None, log_path=None,
        sheet_path=None, call=None, max_retrials: int = MAX_RETRIALS_PER_CYCLE) -> dict:
    """Re-trial undecided probationary skills, then assess every known skill and surface
    promote/archive recommendations. Never writes a skill status. Never raises."""
    t = thresholds or skill.LifecycleThresholds()
    cands = load_candidates(store_path)
    if not cands:
        return {"assessed": 0, "retrials": 0, "promote": 0, "archive": 0}
    retrials = []
    if solver_synth.enabled():
        for cand in cands:
            if len(retrials) >= max_retrials:
                break
            if _eligible_for_retrial(cand, cs, t):
                r = retrial(cs, cand, budget=budget, cycle=cycle, runs_per_week=runs_per_week,
                            call=call)
                if r is not None:
                    retrials.append(r)
    assessments = [skill.assess_lifecycle(c, cs, thresholds=t) for c in cands]
    promote = [a for a in assessments if a.action is skill.LifecycleAction.PROMOTE]
    archive = [a for a in assessments if a.action is skill.LifecycleAction.ARCHIVE]
    _append_log(log_path, promote + archive)
    _write_sheet(sheet_path, assessments)
    for a in promote:
        proto.record(cycle, "skill_promote_ready",
                     f"skill {a.skill_id} earned promotion ({a.passes} passes, reliability "
                     f"{a.reliability}) - awaiting a human/Layer-9 decision")
    for a in archive:
        proto.record(cycle, "skill_archive_ready",
                     f"skill {a.skill_id} recommended for archival (reliability {a.reliability} "
                     f"after {a.trials} trials)")
    extensions["skill_lifecycle"] = [a.to_record() for a in assessments]
    extensions["skill_retrials"] = retrials       # S0 forms procedural episodes from these
    return {"assessed": len(assessments), "retrials": len(retrials),
            "promote": len(promote), "archive": len(archive)}


__all__ = ["load_candidates", "retrial", "run", "MAX_RETRIALS_PER_CYCLE"]
