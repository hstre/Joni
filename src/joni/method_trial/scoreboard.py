"""Priority 1: measure success at the CONSOLIDATOR's output, not at claim growth.

The operator's point is sharp: watching the claim count rise says nothing about whether Joni is
actually *learning procedures*. The real question is what the Procedural Skill Consolidator makes.
This deterministic, READ-ONLY scoreboard answers exactly the metrics asked for, per cycle:

  * S0 episodes formed (new this cycle + total, resolved vs still-unknown);
  * validly crystallised skills (total, by lifecycle status);
  * repeated re-trials run this cycle (maturation actually happening, not asserted);
  * promote / hold / archive recommendations standing;
  * the ratio of VALID TESTS to DISCARDED MAPPINGS - trials that produced a measured verdict versus
    method->benchmark mappings that yielded no valid test (the honest denominator).

Like the collapse panel, it only reads (the append-only consolidator stores + this cycle's
``extensions``) and writes its own two artefacts under the governance allowlist:

  * ``state/consolidator_series.jsonl`` — one machine-readable row per cycle;
  * ``docs/consolidator.md``           — the short human/site summary of the latest row.

It never writes Layer 9, never activates a skill, and consults no LLM.
"""
from __future__ import annotations

import contextlib
import json


def _ratio(valid: int, discarded: int) -> float:
    """Valid tests per discarded mapping. 0 discarded -> the valid count itself (all mappings paid
    off); 0 valid and 0 discarded -> 0.0 (nothing measured yet). Kept bounded and honest."""
    if discarded <= 0:
        return float(valid)
    return round(valid / discarded, 3)


def _episode_stats(paths, new_count: int) -> dict:
    from . import episodes
    eps = episodes.load(getattr(paths, "episodes", None))
    resolved = sum(1 for e in eps if e.is_resolved())
    return {"new": new_count, "total": len(eps), "resolved": resolved,
            "unknown": len(eps) - resolved}


def _skill_stats(paths, extensions: dict) -> dict:
    from . import skill_lifecycle
    cands = skill_lifecycle.load_candidates(getattr(paths, "skill_candidates", None))
    by_status: dict[str, int] = {}
    for c in cands:
        by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
    new_admissible = sum(1 for p in (extensions.get("skills_proposed") or [])
                         if isinstance(p, dict) and p.get("admissible"))
    return {"total": len(cands), "by_status": by_status, "new_admissible": new_admissible}


def _hypothesis_stats(cs) -> dict:
    """Priority 3, made visible: score every current hypothesis 0-4 on well-formedness (mechanism/
    scope/expected-observation/refutation) and count how many are reflection-barred lexical
    recurrence. Read-only over the core; independent of cycle ordering."""
    from ..autonomy import hypothesis_form
    hyps = []
    if cs is not None:
        with contextlib.suppress(Exception):
            hyps = list(cs.hypotheses())
    by_score = {i: 0 for i in range(5)}
    well_formed = barred = 0
    for h in hyps:
        text = getattr(h, "text", "")
        by_score[hypothesis_form.completeness(text)] += 1
        if hypothesis_form.well_formed(text):
            well_formed += 1
        if hypothesis_form.is_reflection_barred(text):
            barred += 1
    return {"total": len(hyps), "well_formed": well_formed, "reflection_barred": barred,
            "by_score": by_score}


def _extension_stats(paths) -> dict:
    """Self-regulation sensor, made visible: which extensions the benefit-review has auto-disabled.
    An empty list is healthy; a non-empty one is a warning (the capped-log false-positive that took
    doktores offline for weeks would have shown here the same cycle it happened)."""
    disabled: list = []
    p = getattr(paths, "ext_disabled", None)
    if p is not None:
        with contextlib.suppress(OSError, json.JSONDecodeError):
            disabled = sorted(json.loads(p.read_text(encoding="utf-8")))
    return {"disabled": disabled}


def _hindsight_stats(paths) -> dict:
    """H4: measure the retroactive review-trigger. Current provisional entries by stage, plus the
    window-cumulative review outcomes read from the append-only provenance - and the honest
    headline: the 'coincidence share' (reviews that found nothing -> rejected), i.e. is the trigger
    surfacing signal or just reactivating noise? Read-only over the stores."""
    from . import provisional as pv
    entries = pv.load(getattr(paths, "provisional", None))
    by_stage: dict[str, int] = {}
    for e in entries:
        by_stage[e.stage.value] = by_stage.get(e.stage.value, 0) + 1
    reviews = 0
    outcomes: dict[str, int] = {}
    prov_path = getattr(paths, "hindsight_provenance", None)
    if prov_path is not None:
        with contextlib.suppress(OSError):
            for raw in prov_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for r in rec.get("reactivated", []):
                    if isinstance(r, dict):
                        reviews += 1
                        oc = r.get("outcome", "")
                        outcomes[oc] = outcomes.get(oc, 0) + 1
    coincidence = round(outcomes.get("rejected", 0) / reviews, 4) if reviews else 0.0
    return {"entries_total": len(entries), "by_stage": by_stage, "reviews": reviews,
            "outcomes": outcomes, "coincidence_share": coincidence}


def _recommendation_counts(extensions: dict) -> dict:
    counts = {"promote": 0, "hold": 0, "archive": 0}
    for a in (extensions.get("skill_lifecycle") or []):
        action = a.get("action") if isinstance(a, dict) else None
        if action in counts:
            counts[action] += 1
    return counts


def _window_totals(series_path, funnel: dict) -> dict:
    """Sum the trial funnel across this window's prior scoreboard rows + this cycle, so the
    valid:discarded ratio reads over the window, not just one noisy cycle."""
    valid = int(funnel.get("trialed", 0))
    discarded = int(funnel.get("discarded", 0))
    matched = int(funnel.get("matched", 0))
    if series_path is not None:
        with contextlib.suppress(OSError):
            for raw in series_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    prev = json.loads(line).get("trial_funnel", {})
                except json.JSONDecodeError:
                    continue
                valid += int(prev.get("trialed", 0))
                discarded += int(prev.get("discarded", 0))
                matched += int(prev.get("matched", 0))
    return {"valid_tests": valid, "discarded_mappings": discarded, "matched": matched,
            "valid_to_discarded": _ratio(valid, discarded)}


def compute(cs, extensions: dict, *, paths, cycle: int, run: int) -> dict:
    """The full scoreboard record for this cycle. Pure read; no writes."""
    funnel = extensions.get("trial_funnel") or {"considered": 0, "matched": 0, "trialed": 0,
                                                "discarded": 0}
    retrials = len(extensions.get("skill_retrials") or [])
    return {
        "cycle": cycle, "run": run,
        "episodes": _episode_stats(paths, len(extensions.get("episodes_new") or [])),
        "skills": _skill_stats(paths, extensions),
        "retrials_this_cycle": retrials,
        "recommendations": _recommendation_counts(extensions),
        "hypotheses": _hypothesis_stats(cs),
        "hindsight": _hindsight_stats(paths),
        "extensions": _extension_stats(paths),
        "trial_funnel": funnel,
        "window": _window_totals(getattr(paths, "scoreboard_series", None), funnel),
    }


def render_summary(rec: dict) -> str:
    ep, sk = rec["episodes"], rec["skills"]
    rc, w = rec["recommendations"], rec["window"]
    hy = rec.get("hypotheses", {"total": 0, "well_formed": 0, "reflection_barred": 0})
    hs = rec.get("hindsight", {"entries_total": 0, "reviews": 0, "outcomes": {},
                               "coincidence_share": 0.0})
    hs_out = " · ".join(f"{k} {v}" for k, v in sorted(hs["outcomes"].items())) or "—"
    ex = rec.get("extensions", {"disabled": []})
    ex_cell = ("🟢 alle aktiv" if not ex["disabled"]
               else "⚠️ deaktiviert: " + ", ".join(ex["disabled"]))
    status = " · ".join(f"{k} {v}" for k, v in sorted(sk["by_status"].items())) or "—"
    lines = [
        "# Joni — Consolidator-Scoreboard",
        "",
        f"**Cycle {rec['cycle']} · Run {rec['run']}**  ",
        "",
        "_Erfolg am Output des Consolidators gemessen, nicht am Claim-Wachstum. Read-only; "
        "nichts aktiviert sich selbst — Layer 9 bleibt die Autorität._",
        "",
        "| Größe | Wert |",
        "|---|---|",
        f"| S0-Episoden | {ep['new']} neu · {ep['total']} gesamt "
        f"({ep['resolved']} resolved, {ep['unknown']} unknown) |",
        f"| Kristallisierte Skills | {sk['total']} gesamt ({status}); "
        f"{sk['new_admissible']} neu diesen Zyklus |",
        f"| Re-Trials (Reifung) | {rec['retrials_this_cycle']} diesen Zyklus |",
        f"| Empfehlungen | {rc['promote']} promote · {rc['hold']} hold · {rc['archive']} archive |",
        f"| Hypothesen-Wohlgeformtheit (0-4) | {hy['total']} gesamt · {hy['well_formed']} "
        f"wohlgeformt (4/4) · {hy['reflection_barred']} als Musterhinweis gesperrt |",
        f"| Valide Tests : verworfene Zuordnungen | {w['valid_tests']} : {w['discarded_mappings']} "
        f"= **{w['valid_to_discarded']}** (Fenster; {w['matched']} gematcht) |",
        f"| HindsightTag (Provisorien) | {hs['entries_total']} Einträge · {hs['reviews']} Reviews "
        f"→ {hs_out}; Koinzidenz-Anteil **{hs['coincidence_share']}** |",
        f"| Selbstregulation (Extensions) | {ex_cell} |",
        "",
    ]
    return "\n".join(lines) + "\n"


def run_scoreboard(cs, extensions: dict, proto, cycle: int, *, run: int, paths) -> dict:
    """Compute + persist the scoreboard for this cycle. Fail-open: any error is swallowed so it can
    never break the loop. Writes ONLY its two artefacts and one protocol line — never Layer 9."""
    try:
        rec = compute(cs, extensions, paths=paths, cycle=cycle, run=run)
        series = paths.scoreboard_series
        series.parent.mkdir(parents=True, exist_ok=True)
        with series.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        paths.scoreboard_panel.parent.mkdir(parents=True, exist_ok=True)
        paths.scoreboard_panel.write_text(render_summary(rec), encoding="utf-8")
        ep, sk, w = rec["episodes"], rec["skills"], rec["window"]
        proto.record(cycle, "scoreboard",
                     f"episodes {ep['new']}(+{ep['total']}) · skills {sk['total']} · "
                     f"retrials {rec['retrials_this_cycle']} · "
                     f"valid:discarded {w['valid_tests']}:{w['discarded_mappings']}")
        return rec
    except Exception as exc:  # noqa: BLE001 - a read-only scoreboard must never break the cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "scoreboard", f"[scoreboard error, skipped] {type(exc).__name__}")
        return {}


__all__ = ["compute", "render_summary", "run_scoreboard"]
