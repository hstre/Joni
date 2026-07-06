"""Method Zustandsbuch — a deterministic, READ-ONLY per-method state ledger (Joni Auftrag #5,
method-trialing).

It consolidates the scattered method-lifecycle signals — the ``METHOD`` object's status, the
sealed ``METHOD_TRIAL_EVENT`` records in the append-only ledger, and retirement — into ONE
auditable per-method history: which state each method is in, and each transition with its reason
and trial id.

It is a *view* over the existing ledger, NOT a new source of truth: the sealed trial records stay
authoritative; this projects them, never duplicates or re-decides them. Strictly read-only wrt
Layer 9 — it reads METHOD objects and trial envelopes and writes only its own two artefacts under
the governance allowlist:

  * ``state/method_ledger.md``     — the current per-method state table (rewritten each cycle)
  * ``state/method_ledger.jsonl``  — append-only TRANSITION events (one row only when a method's
    derived state actually changes), so the history is kept without per-cycle bloat.

No LLM; deterministic; fail-open (a read-only projector must never break the cycle).
"""
from __future__ import annotations

import contextlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import desi_layer9 as l9

# The canonical lifecycle states, ordered from birth to end.
PROPOSED, TRIALED, READY, SHELVED, ACTIVE, RETIRED = (
    "proposed", "trialed", "ready", "shelved", "active", "retired")

_POSITIVE = {"success", "partial_success"}      # earns readiness
_NEGATIVE = {"no_benefit", "harmful"}           # falsified → shelved (the honest 'ceiling-null')


def _verdicts_by_method(core) -> dict[str, list[str]]:
    """Map method_id → the trial verdicts recorded for it, read from the sealed trial envelopes
    (payload['method_id'], payload['decision']['verdict']). The ledger is authoritative; this only
    reads it."""
    out: dict[str, list[str]] = defaultdict(list)
    with contextlib.suppress(Exception):
        for env in core.method_trial_events():
            payload = (env.get("payload") if isinstance(env, dict) else None) or {}
            mid = payload.get("method_id")
            verdict = (payload.get("decision") or {}).get("verdict")
            if mid:
                out[str(mid)].append(str(verdict or "not_evaluated"))
    return out


def _state_for(status, verdicts: list[str]) -> str:
    """Derive one canonical lifecycle state from the METHOD status + its trial verdicts."""
    st = getattr(status, "value", str(status))
    if st == "rejected":
        return RETIRED
    if st == "active":
        return ACTIVE
    if not verdicts:
        return PROPOSED
    if any(v in _POSITIVE for v in verdicts):
        return READY
    if verdicts and all(v in _NEGATIVE for v in verdicts):
        return SHELVED
    return TRIALED                              # trialed but inconclusive/mixed


def snapshot(cs) -> list[dict]:
    """One row per method: id, name, status, derived state, trial count, verdicts. Pure read."""
    verdicts = _verdicts_by_method(cs.core)
    rows: list[dict] = []
    for m in cs.core.all(l9.ObjectType.METHOD):
        mid = str(m.id)
        vs = verdicts.get(mid, [])
        rows.append({
            "method_id": mid,
            "name": str(getattr(m, "name", "") or "")[:80],
            "status": getattr(m.status, "value", str(m.status)),
            "state": _state_for(m.status, vs),
            "n_trials": len(vs),
            "last_verdict": vs[-1] if vs else None,
        })
    rows.sort(key=lambda r: (r["state"], r["method_id"]))
    return rows


def _last_states(series_path: Path) -> dict[str, str]:
    """Reconstruct the last recorded state per method from the transition log (read-only)."""
    last: dict[str, str] = {}
    if not series_path.exists():
        return last
    with contextlib.suppress(Exception):
        for line in series_path.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                e = json.loads(line)
                if e.get("method_id"):
                    last[e["method_id"]] = e.get("to")
    return last


def transitions(rows: list[dict], last: dict[str, str], cycle: int) -> list[dict]:
    """The transition events for methods whose derived state changed since their last log entry.
    A newly-seen method transitions from None → its state."""
    out: list[dict] = []
    for r in rows:
        prev = last.get(r["method_id"])
        if prev != r["state"]:
            out.append({"cycle": cycle, "method_id": r["method_id"], "name": r["name"],
                        "from": prev, "to": r["state"], "reason": r["last_verdict"] or r["status"]})
    return out


def render_table(rows: list[dict], cycle: int) -> str:
    """The current per-method state table (Markdown). Descriptive only."""
    counts = Counter(r["state"] for r in rows)
    order = [PROPOSED, TRIALED, READY, SHELVED, ACTIVE, RETIRED]
    summary = " · ".join(f"{s} {counts.get(s, 0)}" for s in order)
    lines = [
        "# Joni — Methoden-Zustandsbuch",
        "",
        f"**Cycle {cycle} · {len(rows)} Methoden** — {summary}  ",
        "",
        "_Read-only View auf das versiegelte Trial-Ledger. Es projiziert die Historie — "
        "es entscheidet keine Verdikte und schreibt nichts nach Layer 9._",
        "",
        "| Methode | Zustand | Status | Trials | letztes Verdikt |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['name'] or r['method_id']} | **{r['state']}** | {r['status']} "
                     f"| {r['n_trials']} | {r['last_verdict'] or '—'} |")
    return "\n".join(lines) + "\n"


def run_ledger(cs, proto, cycle: int, *, paths) -> dict:
    """Compute + persist the method Zustandsbuch for this cycle. Fail-open; writes ONLY its two
    state artefacts and one protocol line — never Layer 9. Returns a small summary."""
    try:
        rows = snapshot(cs)
        series = paths.method_ledger_series
        series.parent.mkdir(parents=True, exist_ok=True)
        changes = transitions(rows, _last_states(series), cycle)
        if changes:
            with series.open("a", encoding="utf-8") as f:
                for ev in changes:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        paths.method_ledger.write_text(render_table(rows, cycle), encoding="utf-8")
        counts = Counter(r["state"] for r in rows)
        proto.record(cycle, "method_ledger",
                     f"{len(rows)} methods · ready {counts.get(READY, 0)} · "
                     f"shelved {counts.get(SHELVED, 0)} · retired {counts.get(RETIRED, 0)} · "
                     f"{len(changes)} transition(s)")
        return {"methods": len(rows), "transitions": len(changes)}
    except Exception as exc:  # noqa: BLE001 - a read-only projector must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "method_ledger", f"[ledger error, skipped] {type(exc).__name__}")
        return {}
