"""Bridge: a Kevin ``real_trial`` result -> a SEALED v4 METHOD_TRIAL_RECORDED, recorded through the
one authoritative Layer-9 core, then PROJECTED into a DESi solution-space-gap view.

This is the production wiring the 22 review rounds deliberately left open:

  * the **writer** (``record_real_trial``) takes Kevin's measured result, maps it to a
    ``MethodTrialRecorded`` whose VERDICT is computed by ``rule_v2`` (never asserted by Kevin),
    seals
    it to v4 (``to_journal``) and submits it through ``core.submit`` - the first production trial
    event crosses the irreversible journal boundary, so it is gated by ``JONI_TRIAL_WRITER``
    (default
    on) and idempotent per content-addressed ``trial_id`` (a deterministic measurement is
    recorded
    exactly once, ever);
  * the **consumer** (``project``) runs the read-only ``trial_event_projector`` over the recorded
    events and returns the solution-space-gap summary for the protocol/site.

Boundary kept (CLAUDE.md): LLM/Kevin for the measurement, RULES for the verdict. Kevin never
promotes and never decides the epistemic verdict; the record is authoritative, the trial verdict
inside it is not core-confirmed (``epistemic_authority='none'``).
"""

from __future__ import annotations

import dataclasses
import os
from datetime import UTC, datetime

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, make_proposal
from desi_layer9.provenance import Provenance

from . import trial_event_projector
from .trial_event_schema import (
    RULE_V2_HASH,
    Decision,
    Estimand,
    Measurement,
    MethodTrialRecorded,
    evaluate_decision,
)


def writer_enabled() -> bool:
    """The trial-event writer is live but switchable without a code change (it crosses the
    irreversible journal boundary). Default ON."""
    return os.getenv("JONI_TRIAL_WRITER", "1") != "0"


def _content_trial_id(result: dict) -> str:
    """A deterministic, content-addressed id: the SAME measured outcome is recorded once, ever
    (re-runs are idempotent at the gate), so a deterministic trial never floods the journal."""
    sha = str(result.get("task_set_sha", ""))[:12]
    return f"realtrial-{result.get('method_id', 'unknown')}-{sha}"


def event_from_real_trial(result: dict, *, ledger_tick: int,
                          trial_id: str | None = None) -> MethodTrialRecorded:
    """Map a ``kevin.real_trial`` result dict to a ``MethodTrialRecorded`` (epistemic, rule_v2).

    The measurement (baseline/intervention/effect/CI) is Kevin's; the VERDICT is computed by rule_v2
    from the measured confidence interval against the pre-registered ``minimum_effect`` - a two-pass
    construction (probe -> read the rule's ``computed`` verdict -> rebuild) keeps rule_v2 as the
    SOLE
    verdict authority, with no duplicated rule logic here."""
    metric = result["metric"]
    direction = "lower_is_better" if result.get("lower_is_better") else "higher_is_better"
    min_effect = float(result.get("min_effect") or 0.1)
    ci = tuple(result["confidence_interval"])
    estimand = Estimand(outcome_metric=metric, contrast="intervention_minus_baseline",
                        direction=direction, minimum_effect=min_effect, decision_rule_id="rule_v2")
    measurement = Measurement(metric_name=metric, baseline_value=float(result["baseline"]),
                              intervention_value=float(result["intervention"]),
                              effect_size=float(result["delta"]),
                              uncertainty=float(result.get("effect_se") or 0.0),
                              confidence_interval=ci)
    task_set = str(result.get("task_set", "unknown"))
    common = dict(
        trial_id=trial_id or _content_trial_id(result),
        timestamp=datetime.now(UTC).replace(microsecond=0).isoformat(),
        ledger_tick=int(ledger_tick),
        target_type="open_question", target_id=task_set, scope_id=task_set,
        scope_description=f"frozen transfer task set ({metric})",
        method_id=str(result.get("method_id", "unknown")),
        method_variant=str(result.get("method_id", "unknown")),
        affinities=tuple(result.get("affinities") or ()),   # the DESi axis this trial informs
        task_set_id=task_set, task_sample_id=str(result.get("task_set_sha", ""))[:12],
        baseline_id="baseline_solver", evaluator_id=f"metric:{metric}",
        model=str(result.get("processor_model", "none")), estimand=estimand,
        measurement=measurement, execution_status="completed", protocol_status="valid",
        run_id=str(result.get("evaluation_mode", "real_trial")))
    # pass 1: a rule-evaluable probe; rule_v2 returns its verdict in "computed" (verified or not).
    probe = MethodTrialRecorded(
        **common, epistemic_result="inconclusive",
        decision=Decision("rule_v2", RULE_V2_HASH, "inconclusive"))
    res = evaluate_decision(probe)
    verdict = res.get("computed")
    if verdict is None:                              # structural problem -> honest, not evaluated
        return dataclasses.replace(
            probe, epistemic_result="not_evaluated",
            decision=Decision("rule_v2", RULE_V2_HASH, "not_evaluated"),
            note=f"rule_v2 could not evaluate: {res.get('reason', res.get('status'))}")
    # pass 2: the event now carries the rule's own verdict (self-consistent -> reads as "verified").
    return dataclasses.replace(
        probe, epistemic_result=verdict,
        decision=Decision("rule_v2", RULE_V2_HASH, verdict))


def record_real_trial(cs, result: dict, *, run_id: str = "kevin-real") -> dict:
    """WRITER: seal Kevin's measured trial to v4 and submit it through the one authoritative core.

    Idempotent (content-addressed ``trial_id``), gated by ``JONI_TRIAL_WRITER``. Returns a small
    summary; never raises into the cycle (a failure is reported, not fatal)."""
    out = {"recorded": False, "trial_id": _content_trial_id(result)}
    if not writer_enabled():
        out["reason"] = "writer disabled (JONI_TRIAL_WRITER=0)"
        return out
    try:
        event = event_from_real_trial(result, ledger_tick=cs.core.tick)
        sealed = event.to_journal()
        decision = cs.core.submit(make_proposal(
            ProposalType.METHOD_PROPOSAL, Operator.METHOD_TRIAL_RECORDED, payload=sealed,
            proposer="kevin", provenance=Provenance.from_model(external=False, model_id="kevin")),
            actor="kevin")
    except Exception as exc:  # noqa: BLE001 - never let recording break the cycle
        out["reason"] = f"record failed: {exc}"
        return out
    out["recorded"] = bool(decision.accepted)
    out["verdict"] = event.epistemic_result
    out["reason"] = decision.reason
    return out


def project(cs) -> dict:
    """CONSUMER: project the recorded trial events into the DESi solution-space-gap view.
    Clean empty result if the projector / desi extra is unavailable."""
    if not trial_event_projector.available():
        return {"available": False}
    try:
        proj = trial_event_projector.project_trial_events(cs.core)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "reason": str(exc)}
    proj["available"] = True
    return proj


def blind_spots(cs, *, top_k: int = 4) -> list[dict]:
    """CONSUMER (the steering signal): project the core into the DESi EpistemicGapSnapshot and run
    ``analyze_gaps`` to get the highest-value SOLUTION-SPACE GAPS - the 'probability islands' where
    missing thinking-move (affinity) on a real target most likely unlocks progress. Each item is
    resolved to something Kevin can act on: the target id, the missing affinity, the priority, and
    the target's claim ids. Empty list if DESi is unavailable. Read-only; never writes the core."""
    from . import epistemic_gap_projector as egp
    if not egp.available():
        return []
    try:
        from desi.solution_space_gap import analyze_gaps
        snap = egp.project(cs.core, core_commit="live")
        props = sorted(analyze_gaps(snap), key=lambda p: -p.priority)
    except Exception:  # noqa: BLE001 - never let the steering signal break the cycle
        return []
    out: list[dict] = []
    for p in props[:top_k]:
        kind, _, tid = str(p.target).partition(":")     # e.g. "conflict:X-1" / "claim:C-7"
        obj = cs.core.objects.get(tid)
        claim_ids = list(getattr(obj, "claim_ids", ())) if obj is not None else (
            [tid] if kind == "claim" else [])
        out.append({"target": p.target, "target_kind": kind, "target_id": tid,
                    "missing_affinity": p.missing_affinity, "priority": round(p.priority, 4),
                    "expected_information_gain": p.expected_information_gain,
                    "claim_ids": claim_ids})
    return out


def trial_event_count(cs) -> int:
    return len(cs.core.method_trial_events())


def all_trial_events(cs) -> list:
    return [o for o in cs.core.all(l9.ObjectType.METHOD_TRIAL_EVENT)]
