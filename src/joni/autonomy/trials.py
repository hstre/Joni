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

import os


def run_trials(cs, proto, cycle: int = 0, *, run_id: str | None = None) -> dict:
    empty = {"trialed": 0, "succeeded": 0, "failed": 0, "activation_ready": 0}
    # The synthetic keyword-shape simulator carries NO epistemic weight (it is honestly labelled as
    # a mock). Now that the REAL trial protocol exists, running it every cycle is just activity +
    # protocol noise, so it is OFF by default in production (JONI_SYNTHETIC_TRIALS=0). Kept
    # available as a deterministic control arm (set =1) and for tests.
    if os.getenv("JONI_SYNTHETIC_TRIALS", "1") == "0":
        return empty
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


def run_real_method_trial(cs, extensions: dict, proto, cycle: int = 0) -> dict:
    """Run the REAL method-trial protocol (``kevin.real_trial`` · real_trial_protocol_v1) - a
    measured trial (frozen task set, baseline vs intervention, predefined metric, repetitions,
    negative control, full provenance + a real confidence interval), NOT the synthetic keyword
    simulator. The decision rests on the metric alone. Clean no-op without ``kevin``.

    The measured result is now also RECORDED through the one authoritative Layer-9 core as a sealed
    v4 ``METHOD_TRIAL_RECORDED`` event (the writer, gated by ``JONI_TRIAL_WRITER``; the verdict is
    rule_v2's, not Kevin's) and PROJECTED into the DESi solution-space-gap view (the consumer). The
    latest result is stored for the site; a protocol note is written when the verdict changes."""
    out = {"ran": False}
    try:
        from kevin import real_trial
    except Exception:  # noqa: BLE001 - kevin not installed: clean no-op
        return out
    try:
        result = real_trial.run_joni_conflict_trial().to_dict()
    except Exception as exc:  # noqa: BLE001 - never let a trial break the cycle
        proto.record(cycle, "note", f"real method-trial skipped: {exc}")
        return out
    prev = extensions.get("real_trial", {})
    extensions["real_trial"] = result

    # WRITER + CONSUMER: record the measured trial as an immutable sealed v4 event, then project the
    # accumulated events into the DESi solution-space-gap view. Clean no-ops if unavailable.
    from . import kevin_trial_bridge as bridge
    rec = bridge.record_real_trial(cs, result, run_id=f"joni-c{cycle}")
    proj = bridge.project(cs)
    extensions["trial_events"] = {"count": bridge.trial_event_count(cs),
                                  "last": rec, "writer_enabled": bridge.writer_enabled()}
    if proj.get("available"):
        suff = proj.get("dataset_sufficiency", {})
        extensions["trial_event_projection"] = {
            "sufficiency": suff.get("verdict"),
            "registered_events": suff.get("registered_events", 0),
            "rule_verified_events": suff.get("rule_verified_events", 0),
            "ready_conflict_scopes": suff.get("analysis_ready_conflict_scopes", []),
            "verified_outcomes": len(proj.get("verified_scope_bound_outcomes", [])),
            "operational_observations": len(proj.get("operational_observations", []))}
    if rec.get("recorded"):
        sfc = extensions.get("trial_event_projection", {}).get("sufficiency", "n/a")
        proto.record(cycle, "trialed",
                     f"recorded sealed trial event {rec['trial_id']} "
                     f"(verdict {rec.get('verdict')}, "
                     f"rule_v2) · {extensions['trial_events']['count']} event(s) in the core · "
                     f"DESi sufficiency: {sfc}")

    if (prev.get("task_set_sha") != result.get("task_set_sha")
            or prev.get("passed") != result.get("passed")):
        proto.record(
            cycle, "trialed",
            f"REAL method-trial [{result['method_id']}] on {result['task_set']} "
            f"(sha {result['task_set_sha'][:8]}): {result['metric']} baseline "
            f"{result['baseline']} -> intervention {result['intervention']} (Δ{result['delta']}, "
            f"CI {result.get('confidence_interval')}, control {result['negative_control']}, reps "
            f"{result['repetitions']}) -> {'PASS' if result['passed'] else 'no pass'} · "
            f"{result['uncertainty']} uncertainty · epistemic_weight={result['epistemic_weight']} "
            "(measured, not the synthetic mock)")
    return {"ran": True, "passed": result["passed"], "direction": result["direction"],
            "recorded": rec.get("recorded", False)}


def retire_unproductive(cs, proto, cycle: int = 0, *, max_retire: int = 5,
                        extensions: dict | None = None) -> int:
    """Joni's *Auftrag* (joni-auftrag · method-trialing): give the trial a clear pass/fail
    criterion so the shelf does not grow without ever maturing.

    Pass = activation-ready (Kevin's criterion: a measurable positive difference, success > failure
    after >=3 trials). **Fail = discarded**: a method that has had at least
    ``JONI_METHOD_MAX_TRIALS`` trials and *still* shows no net gain (success <= failure) is
    rejected through the gate
    (``METHOD_REJECT``) - a negative result is a result. This bounds the method count and never
    auto-confirms anything; a maturing method (success > failure) is never touched here.

    **State ledger (Auftrag #145, after LedgerAgent)**: retirement used only the in-the-moment
    counts, which can discard a method that *just* passed (a premature / inconsistent retirement). A
    persisted ``method_ledger`` records observed facts per method - its success count over time and
    the cycle it last gained a pass - and the retirement consults it: a method with a pass within
    ``JONI_METHOD_LEDGER_WINDOW`` cycles is HELD, not discarded. Nothing is auto-confirmed.
    """

    import desi_layer9 as l9
    max_trials = int(os.getenv("JONI_METHOD_MAX_TRIALS", "8"))
    window = max(1, int(os.getenv("JONI_METHOD_LEDGER_WINDOW", "6")))
    ledger = extensions.setdefault("method_ledger", {}) if isinstance(extensions, dict) else {}

    live = [m for m in cs.core.all(l9.ObjectType.METHOD)
            if m.status in (l9.Status.CANDIDATE, l9.Status.PROVISIONAL)]
    live_ids = {m.id for m in live}
    # 1. Update the ledger: record each live method's observed facts (success count, and the cycle
    #    it last gained a pass). This persisted state is what the retirement consults.
    for m in live:
        rec = ledger.get(m.id) or {"success": 0, "last_pass_cycle": -(10**9)}
        if m.success_count > rec.get("success", 0):
            rec["last_pass_cycle"] = cycle           # observed: this method passed since last seen
        rec["success"] = m.success_count
        rec["last_seen_cycle"] = cycle
        ledger[m.id] = rec
    for mid in [k for k in ledger if k not in live_ids]:
        ledger.pop(mid, None)                         # drop methods no longer on the shelf

    retired = 0
    for m in sorted(live, key=lambda x: (x.success_count - x.failure_count, x.id)):
        if retired >= max_retire:
            break
        if m.trial_count >= max_trials and m.success_count <= m.failure_count:
            # 2. Check the ledger BEFORE discarding: a recent pass means retiring now would be
            #    premature / inconsistent - hold the method another window instead.
            last_pass = ledger.get(m.id, {}).get("last_pass_cycle", -(10**9))
            if cycle - last_pass < window:
                proto.record(cycle, "trialed",
                             f"holding method {m.id} '{getattr(m, 'name', m.id)}' - the ledger "
                             f"shows a pass within {window} cycle(s); retiring now would be "
                             "premature")
                continue
            cs.reject_method(m.id)
            retired += 1
            proto.record(cycle, "trialed",
                         f"retired method {m.id} '{getattr(m, 'name', m.id)}' after "
                         f"{m.trial_count} trial(s) with no measurable gain "
                         f"(success {m.success_count} <= failure {m.failure_count}) - discarded so "
                         "the shelf does not grow unbounded; a negative result is a result")

    if isinstance(extensions, dict):
        extensions["method_ledger"] = ledger
    return retired
