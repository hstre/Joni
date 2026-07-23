"""H1+H2 of HindsightTag (design-notes/HINDSIGHT_REVIEW.md §5/§9): tag + capture window, and the
retroactive review-trigger, fed by real run signals.

Each cycle, READ-ONLY, this:

  * **ingests** the cycle's provisional material into the layer (H0 objects): the pattern hints
    barred from reflection (Priority 3) as ``weak_hint``, and the conflicts opened this cycle as
    ``open_contradiction``. Cheap attention-salience per kind; epistemic significance stays 0.0
    (measured only in a later stage);
  * **settles + tags** (H1): ephemeral -> provisional, and a provisional entry that clears the
    attention bar earns a short-lived tag with a bounded capture window;
  * **triggers review** (H2): if a *sufficiently salient later event* occurred this cycle (a benefit
    trial, a crystallised skill, a resolved conflict), the tagged entries still inside their capture
    window are reactivated to ``review_due`` - **content-independent temporal co-allocation**, the
    paper's move but as a *review trigger*, not a rescue. Whether any real relationship exists is
    decided later (H3); nothing is asserted or consolidated here.

Every trigger writes an append-only provenance record (triggering event, cycle, capture strength,
which entries) so a human can reconstruct why an entry was reactivated. Never writes Layer 9; never
consolidates; fail-open. Bounded: ingest and reactivation are capped per cycle.
"""
from __future__ import annotations

import contextlib
import json

from . import provisional as pv

MAX_INGEST_PER_CYCLE = 8
MAX_REVIEW_PER_EVENT = 5
EVENT_SALIENCE_THRESHOLD = 0.5

# Cheap, deterministic attention salience per kind (NOT epistemic significance, which stays measured
# and 0.0 here). An open contradiction is worth tagging; a barred recurrence hint mostly is not.
_ATTENTION = {
    pv.EntryKind.OPEN_CONTRADICTION: 0.6,
    pv.EntryKind.WEAK_HINT: 0.3,
    pv.EntryKind.OBSERVATION: 0.3,
    pv.EntryKind.UNUSUAL_EVENT: 0.7,
}


def _text_of(cs, cid: str) -> str:
    with contextlib.suppress(Exception):
        obj = cs.core.get(cid)
        if obj is not None:
            return str(getattr(obj, "text", "") or "")
    return ""


def ingest(cs, extensions: dict, *, cycle: int) -> list:
    """Form this cycle's ephemeral provisional entries from real signals (read-only). Capped."""
    out: list = []
    # barred pattern hints (Priority 3) -> weak hints worth keeping briefly checkable
    for hid in (extensions.get("hyp_pattern_hints") or []):
        if len(out) >= MAX_INGEST_PER_CYCLE:
            break
        text = _text_of(cs, str(hid)) or f"barred hypothesis {hid}"
        with contextlib.suppress(ValueError):
            out.append(pv.ProvisionalEntry(
                kind=pv.EntryKind.WEAK_HINT, content=text[:200], source="pattern_hint",
                refs=(str(hid),), created_cycle=cycle,
                attention_salience=_ATTENTION[pv.EntryKind.WEAK_HINT]))
    # conflicts opened this cycle -> open contradictions (a later event may sharpen or resolve them)
    for pair in (extensions.get("conflicts_opened") or []):
        if len(out) >= MAX_INGEST_PER_CYCLE:
            break
        refs = tuple(str(x) for x in pair) if isinstance(pair, (list, tuple)) else (str(pair),)
        with contextlib.suppress(ValueError):
            out.append(pv.ProvisionalEntry(
                kind=pv.EntryKind.OPEN_CONTRADICTION,
                content=f"conflict opened between {', '.join(refs)}"[:200],
                source="conflict_open", refs=refs, created_cycle=cycle,
                attention_salience=_ATTENTION[pv.EntryKind.OPEN_CONTRADICTION]))
    return out


def event_salience(extensions: dict) -> float:
    """How salient this cycle's *later events* are - the trigger side. Deterministic, bounded [0,1].
    A benefit trial, a crystallised skill, or a resolved conflict each counts as a salient event
    worth looking back for. Quiet cycles score low and trigger nothing (honestly)."""
    benefit = sum(1 for t in (extensions.get("sandbox_trials") or [])
                  if isinstance(t, dict) and t.get("verdict") == "benefit")
    skills = len(extensions.get("skills_proposed") or [])
    cr = extensions.get("conflict_resolved")
    resolved = len(cr) if isinstance(cr, (list, tuple)) else (1 if cr else 0)
    return min(1.0, 0.5 * (benefit + skills + resolved))


def _settle_and_tag(entries: list, *, cycle: int) -> list:
    return [pv.tag(pv.settle(e), cycle) for e in entries]


def run(cs, extensions: dict, proto, cycle: int = 0, *, paths=None, store_path=None,
        provenance_path=None, panel_path=None) -> dict:
    """One cycle of the provisional layer: ingest -> settle+tag -> (on a salient event) reactivate
    tagged entries in-window to review_due -> expire lived-out -> persist. Never writes Layer 9;
    never consolidates. Returns a small summary and sets ``extensions['hindsight']``. Never raises.
    """
    store_path = store_path or (getattr(paths, "provisional", None) if paths else None)
    provenance_path = provenance_path or (getattr(paths, "hindsight_provenance", None)
                                          if paths else None)
    panel_path = panel_path or (getattr(paths, "hindsight_panel", None) if paths else None)
    try:
        stored = pv.load(store_path)
        fresh = _settle_and_tag(ingest(cs, extensions, cycle=cycle), cycle=cycle)
        changed = list(fresh)                              # entries to append this cycle

        salience = event_salience(extensions)
        reviewed: list = []
        if salience >= EVENT_SALIENCE_THRESHOLD:
            for e in stored:
                if len(reviewed) >= MAX_REVIEW_PER_EVENT:
                    break
                if pv.in_capture_window(e, cycle):
                    reviewed.append(pv.mark_review_due(e))
            changed.extend(reviewed)

        expired: list = []                                 # lived-out non-terminal entries retire
        _terminal = {pv.LifecycleStage.EXPIRED, pv.LifecycleStage.CONSOLIDATED,
                     pv.LifecycleStage.REJECTED, pv.LifecycleStage.LINKED_ONLY}
        reviewed_ids = {e.entry_id() for e in reviewed}
        for e in stored:
            if e.entry_id() in reviewed_ids or e.stage in _terminal:
                continue
            if pv.is_expired(e, cycle):
                expired.append(pv.expire(e))
        changed.extend(expired)

        pv.record(changed, store_path=store_path)
        if reviewed:
            _write_provenance(provenance_path, cycle, salience, reviewed, extensions)
        counts = _stage_counts(stored, fresh, reviewed, expired)
        _write_panel(panel_path, cycle, counts, salience)
        extensions["hindsight"] = counts
        proto.record(cycle, "hindsight",
                     f"ingested {len(fresh)} · tagged {counts['tagged_now']} · "
                     f"salience {salience} · reviews {len(reviewed)} · expired {len(expired)}")
        return {"ingested": len(fresh), "reviewed": len(reviewed), "expired": len(expired),
                "event_salience": salience}
    except Exception as exc:  # noqa: BLE001 - a read-only staging layer must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "hindsight", f"[hindsight error, skipped] {type(exc).__name__}")
        return {"ingested": 0, "reviewed": 0, "expired": 0, "event_salience": 0.0}


def _stage_counts(stored: list, fresh: list, reviewed: list, expired: list) -> dict:
    tagged_now = sum(1 for e in fresh if e.stage is pv.LifecycleStage.TAGGED)
    by_stage: dict[str, int] = {}
    for e in stored + fresh:
        by_stage[e.stage.value] = by_stage.get(e.stage.value, 0) + 1
    return {"ingested": len(fresh), "tagged_now": tagged_now, "reviews_triggered": len(reviewed),
            "expired": len(expired), "stored_total": len(stored), "by_stage": by_stage}


def _write_provenance(path, cycle: int, salience: float, reviewed: list, extensions: dict) -> None:
    if path is None or not reviewed:
        return
    benefit = sum(1 for t in (extensions.get("sandbox_trials") or [])
                  if isinstance(t, dict) and t.get("verdict") == "benefit")
    rec = {"cycle": cycle, "event_salience": round(float(salience), 4),
           "trigger": {"benefit_trials": benefit,
                       "skills_proposed": len(extensions.get("skills_proposed") or [])},
           "reactivated": [e.entry_id() for e in reviewed]}
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _write_panel(path, cycle: int, counts: dict, salience: float) -> None:
    if path is None:
        return
    stages = " · ".join(f"{k} {v}" for k, v in sorted(counts["by_stage"].items())) or "—"
    lines = [
        "# Joni — HindsightTag (Provisorien-Layer)",
        "",
        f"**Cycle {cycle}**  ",
        "",
        "_Retroaktiver Review-Trigger. Reaktivierung ist eine Prüfaufforderung, keine "
        "Konsolidierung — Layer 9 entscheidet (H3, noch offen)._",
        "",
        "| Größe | Wert |",
        "|---|---|",
        f"| Ingested (dieser Zyklus) | {counts['ingested']} ({counts['tagged_now']} getaggt) |",
        f"| Event-Salienz | {salience} |",
        f"| Reviews ausgelöst | {counts['reviews_triggered']} |",
        f"| Verfallen | {counts['expired']} |",
        f"| Stages (Bestand) | {stages} |",
        "",
    ]
    with contextlib.suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = ["ingest", "event_salience", "run", "MAX_INGEST_PER_CYCLE", "MAX_REVIEW_PER_EVENT",
           "EVENT_SALIENCE_THRESHOLD"]
