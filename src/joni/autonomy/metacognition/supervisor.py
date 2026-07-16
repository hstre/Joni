"""Shadow observer: log an episode per newly-minted method, resolve pending ones later.

Read-only over the Layer-9 core; append-only to state/metacognition.jsonl; holds NO decision
authority. The one desi_layer9-touching step (`_method_objects`) is isolated so the rest is
unit-testable, and `observe(..., objects=...)` lets a test inject method views directly.
"""
from __future__ import annotations

import hashlib
import os

from . import (
    conflict_gate,
    doktores_gate,
    doktores_literature_gate,
    method_gate,
    models,
)
from .audit import AuditLog
from .models import OutcomeEvent

_SEEN_CAP = 4000            # bound the per-subject cursor kept in extensions


def config_hash(seam: str) -> str:
    payload = f"{models.MONITOR_VERSION}|{seam}|shadow"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _method_objects(cs) -> list:
    import desi_layer9 as l9  # isolated core read
    return list(cs.core.all(l9.ObjectType.METHOD))


def _view(m) -> method_gate.MethodView:
    status = getattr(m, "status", "")
    return method_gate.MethodView(
        id=str(m.id), name=str(getattr(m, "name", m.id)),
        status=str(getattr(status, "value", status)),
        trial_count=int(getattr(m, "trial_count", 0)),
        success_count=int(getattr(m, "success_count", 0)),
        failure_count=int(getattr(m, "failure_count", 0)),
        n_topics=len(getattr(m, "applicable_to", ()) or ()),
        origin=str(getattr(m, "origin", "")))


def observe(cs, extensions: dict, cycle: int, tick: int, log: AuditLog, *, objects=None) -> dict:
    """Log an episode for each newly-seen method, then resolve any pending episode whose method
    has reached a belastbarer terminal status. Returns a small summary. Pure observation."""
    views = [_view(m) for m in (objects if objects is not None else _method_objects(cs))]
    cfg = config_hash("method_gate")
    ext = extensions.setdefault("metacognition", {})
    seen: dict = ext.setdefault("episode_by_method", {})     # method_id -> episode_id

    logged = 0
    for v in views:
        if v.id in seen:
            continue
        seen[v.id] = log.append_episode(
            method_gate.build_episode(v, cycle=cycle, tick=tick, config_hash=cfg))
        logged += 1

    pending = log.pending_episode_ids()
    by_id = {v.id: v for v in views}
    resolved = 0
    for mid, eid in list(seen.items()):
        if eid not in pending:
            continue
        v = by_id.get(mid)
        if v is None:
            continue                                         # method gone -> stays unknown
        out = method_gate.resolve(v)
        if out is not None:
            log.append_outcome(OutcomeEvent(
                episode_id=eid, outcome=out, outcome_source="later_layer9_status",
                outcome_cycle=cycle, resolved_tick=tick, outcome_refs=(f"method:{mid}",)))
            resolved += 1

    if len(seen) > _SEEN_CAP:                                # bound the cursor (oldest first)
        for k in list(seen)[: len(seen) - _SEEN_CAP]:
            seen.pop(k, None)
    ext["episode_by_method"] = seen
    extensions["metacognition"] = ext
    return {"logged": logged, "resolved": resolved, "methods_seen": len(views)}


def _conflict_objects(cs) -> list:
    import desi_layer9 as l9  # isolated core read
    return list(cs.core.all(l9.ObjectType.CONFLICT))


def _conflict_view(c) -> conflict_gate.ConflictView:
    cstatus = getattr(c, "conflict_status", "open")
    ckind = getattr(c, "conflict_kind", "")
    return conflict_gate.ConflictView(
        id=str(c.id), conflict_status=str(getattr(cstatus, "value", cstatus)),
        severity=str(getattr(c, "severity", "soft")),
        conflict_kind=str(getattr(ckind, "value", ckind)),
        n_claims=len(getattr(c, "claim_ids", ()) or ()))


def observe_conflicts(cs, extensions: dict, cycle: int, tick: int, log: AuditLog, *,
                      objects=None, stale_cycles: int | None = None) -> dict:
    """Log an episode per newly-seen conflict, then resolve pending ones from the conflict's later
    status (resolved -> success; open past STALE cycles -> failure; recent -> stays unknown).
    Read-only over the core; append-only to the log. Pure observation."""
    stale = stale_cycles if stale_cycles is not None \
        else max(1, int(os.getenv("JONI_METACOG_CONFLICT_STALE", "20")))
    views = [_conflict_view(c) for c in (objects if objects is not None else _conflict_objects(cs))]
    cfg = config_hash("conflict_gate")
    ext = extensions.setdefault("metacognition", {})
    seen: dict = ext.setdefault("episode_by_conflict", {})   # cid -> {episode_id, cycle}

    logged = 0
    for v in views:
        if v.id in seen:
            continue
        eid = log.append_episode(
            conflict_gate.build_episode(v, cycle=cycle, tick=tick, config_hash=cfg))
        seen[v.id] = {"episode_id": eid, "cycle": cycle}
        logged += 1

    pending = log.pending_episode_ids()
    by_id = {v.id: v for v in views}
    resolved = 0
    for cid, rec in list(seen.items()):
        eid = rec["episode_id"]
        if eid not in pending:
            continue
        v = by_id.get(cid)
        if v is None:
            continue
        out = conflict_gate.resolve(v, age=cycle - int(rec.get("cycle", cycle)), stale_cycles=stale)
        if out is not None:
            log.append_outcome(OutcomeEvent(
                episode_id=eid, outcome=out, outcome_source="later_layer9_status",
                outcome_cycle=cycle, resolved_tick=tick, outcome_refs=(f"conflict:{cid}",)))
            resolved += 1

    if len(seen) > _SEEN_CAP:
        for k in list(seen)[: len(seen) - _SEEN_CAP]:
            seen.pop(k, None)
    ext["episode_by_conflict"] = seen
    extensions["metacognition"] = ext
    return {"logged": logged, "resolved": resolved, "conflicts_seen": len(views)}


def _claim_objects(cs) -> list:
    import desi_layer9 as l9  # isolated core read
    return list(cs.core.all(l9.ObjectType.CLAIM))


def _claim_view(c) -> doktores_gate.ClaimView:
    st = getattr(c, "status", "")
    return doktores_gate.ClaimView(id=str(c.id), status=str(getattr(st, "value", st)))


def observe_doktores(cs, extensions: dict, cycle: int, tick: int, log: AuditLog, *,
                     log_entries=None, claim_objects=None) -> dict:
    """Log an episode per Doktores coherence verdict (from extensions['doktores_hyp_log']), then
    resolve pending ones from the hypothesis-claim's later Layer-9 status. Read-only, append-only,
    observation-only. The verdict is a structured signal, not free prose."""
    entries = log_entries if log_entries is not None else extensions.get("doktores_hyp_log", [])
    cfg = config_hash("doktores_coherence")
    ext = extensions.setdefault("metacognition", {})
    seen: dict = ext.setdefault("episode_by_doktores", {})   # hypothesis_id -> {episode_id, cycle}

    logged = 0
    for e in entries:
        hid = str(e.get("hypothesis", ""))
        if not hid or hid in seen:
            continue
        v = doktores_gate.DoktoresVerdict(hypothesis_id=hid, coherent=bool(e.get("coherent")),
                                          topic=str(e.get("topic", "")))
        eid = log.append_episode(
            doktores_gate.build_episode(v, cycle=int(e.get("cycle", cycle)), tick=tick,
                                        config_hash=cfg))
        seen[hid] = {"episode_id": eid, "cycle": int(e.get("cycle", cycle))}
        logged += 1

    pending = log.pending_episode_ids()
    views = [_claim_view(c)
             for c in (claim_objects if claim_objects is not None else _claim_objects(cs))]
    by_id = {v.id: v for v in views}
    resolved = 0
    for hid, rec in list(seen.items()):
        eid = rec["episode_id"]
        if eid not in pending:
            continue
        cv = by_id.get(hid)
        if cv is None:
            continue
        out = doktores_gate.resolve(cv)
        if out is not None:
            log.append_outcome(OutcomeEvent(
                episode_id=eid, outcome=out, outcome_source="later_layer9_status",
                outcome_cycle=cycle, resolved_tick=tick, outcome_refs=(f"claim:{hid}",)))
            resolved += 1

    if len(seen) > _SEEN_CAP:
        for k in list(seen)[: len(seen) - _SEEN_CAP]:
            seen.pop(k, None)
    ext["episode_by_doktores"] = seen
    extensions["metacognition"] = ext
    return {"logged": logged, "resolved": resolved, "doktores_seen": len(entries)}


def observe_doktores_literature(cs, extensions: dict, cycle: int, tick: int, log: AuditLog, *,
                                review_entries=None, done_index=None) -> dict:
    """Log an episode per applicable literature-review commission (from the doktores_review
    signals), then resolve pending ones from a PR-outcome index
    ({component_key: 'success'|'failure'}). Unmatched commissions stay unknown - never coerced."""
    entries = review_entries if review_entries is not None \
        else extensions.get("doktores_review", [])
    idx = done_index or {}
    cfg = config_hash("doktores_literature")
    ext = extensions.setdefault("metacognition", {})
    seen: dict = ext.setdefault("episode_by_commission", {})   # component_key -> {episode_id,cycle}

    logged = 0
    for e in entries:
        if not e.get("applicable"):
            continue                                 # non-applicable reviews have no PR outcome
        key = str(e.get("component_key", ""))
        if not key or key in seen:
            continue
        src = str(e.get("source", ""))
        sig = doktores_literature_gate.ReviewSignal(
            component_key=key, applicable=True, served_model=str(e.get("served_model", "")),
            source=src, is_fulltext=("openalex" not in src.lower()))
        eid = log.append_episode(doktores_literature_gate.build_episode(
            sig, cycle=int(e.get("cycle", cycle)), tick=tick, config_hash=cfg))
        seen[key] = {"episode_id": eid, "cycle": int(e.get("cycle", cycle))}
        logged += 1

    pending = log.pending_episode_ids()
    resolved = 0
    for key, rec in list(seen.items()):
        eid = rec["episode_id"]
        if eid not in pending:
            continue
        out = doktores_literature_gate.outcome_for(idx.get(key, ""))
        if out is not None:
            log.append_outcome(OutcomeEvent(
                episode_id=eid, outcome=out, outcome_source="pr_outcome", outcome_cycle=cycle,
                resolved_tick=tick, outcome_refs=(f"commission:doktores:{key}",)))
            resolved += 1

    if len(seen) > _SEEN_CAP:
        for k in list(seen)[: len(seen) - _SEEN_CAP]:
            seen.pop(k, None)
    ext["episode_by_commission"] = seen
    extensions["metacognition"] = ext
    return {"logged": logged, "resolved": resolved, "reviews_seen": len(entries)}


__all__ = ["config_hash", "observe", "observe_conflicts", "observe_doktores",
           "observe_doktores_literature"]
