"""Schlafmodus S4: the handover from the sleeping to the waking Joni.

Two artefacts, written once, on the wake transition:

  * ``state/wake_queue.json`` - the ranked list of what the awake Joni should look at FIRST.
    Ranked by how close an item is to a measurable outcome, not by how new it is: drain targets
    (a real procedure that is structurally complete and could be trialed today) come before defect
    reports, which come before associative links. The queue is a suggestion; nothing consumes it
    automatically and nothing on it is activated.
  * ``docs/sleep_report.md`` - the human view, and it leads with the one number that matters.

The report's headline is the maturation delta, NOT the activity count. A sleep window that
refragmented four hundred entries and matured nothing reads as **"nichts gereift"** in bold on the
first line. That ordering is the whole point: we have already been burned once by a metric that
counted motion (the capped activity log that took Doktores offline for weeks), and a sleep mode is
exactly the kind of machinery that can look busy forever while producing nothing.

Read-only over everything else; writes only its own two artefacts; never touches Layer 9.
"""
from __future__ import annotations

import contextlib
import json

MAX_QUEUE = 20


def build_queue(passes: dict) -> list[dict]:
    """Rank what the waking Joni should pick up first: closest-to-a-measurable-outcome wins."""
    aud = passes.get("audit") or {}
    queue: list[dict] = []
    # The finding that outranks every individual item: if NOT ONE candidate method is shaped like a
    # procedure, the trial pipeline is starved at the source, not at the benchmark. Measured on the
    # first live audit (73 of 74 real procedure names scored 0/3), and it changes what to work on.
    scored = int(aud.get("scored") or 0)
    by_score = aud.get("by_score") or {}
    zero = int(by_score.get(0, by_score.get("0", 0)) or 0)
    if scored and not (aud.get("complete") or []):
        queue.append({"kind": "structural_finding", "priority": 0,
                      "name": f"{zero}/{scored} Methoden ohne jede Verfahrensstruktur",
                      "why": "keine einzige Methode ist trialbar geformt - die Trial-Pipeline "
                             "hungert an der Quelle, nicht am Benchmark"})
    for row in aud.get("complete") or []:
        queue.append({"kind": "drain_target", "priority": 1, "method_id": row.get("id", ""),
                      "name": row.get("name", ""),
                      "why": "strukturell vollständig und ungetestet - heute trialbar"})
    for rev in passes.get("revisions") or []:
        queue.append({"kind": "defect_report", "priority": 2, "method_id": rev.get("method_id", ""),
                      "name": rev.get("name", ""), "why": rev.get("defect", "")})
    for link in (passes.get("refragment") or {}).get("links") or []:
        queue.append({"kind": "associative_link", "priority": 3,
                      "fragment": link.get("fragment", ""), "entries": link.get("entries", []),
                      "why": "geteiltes Fragment - nur eine Assoziation, keine Herleitung"})
    queue.sort(key=lambda r: r["priority"])
    return queue[:MAX_QUEUE]


def render(sleep_state: dict, passes: dict, queue: list[dict]) -> str:
    """The human sleep report. The maturation verdict comes FIRST, before any activity count."""
    lw = sleep_state.get("last_wake") or {}
    delta = lw.get("delta") or {}
    matured = bool(lw.get("matured"))
    verdict = "**gereift**" if matured else "**nichts gereift**"
    frag = passes.get("refragment") or {}
    aud = passes.get("audit") or {}
    revs = passes.get("revisions") or []
    by_score = aud.get("by_score") or {}
    score_cells = " · ".join(f"{k}/3: {v}" for k, v in sorted(by_score.items())) or "—"
    lines = [
        "# Joni — Schlafbericht",
        "",
        f"**Schlaf über {lw.get('slept_cycles', 0)} Zyklen → {verdict}**",
        "",
        "_Die Reifung steht zuerst, die Betriebsamkeit danach. Ein Fenster, das viel bewegt und "
        "nichts reifen lässt, ist ein Fehlschlag — kein Arbeitsnachweis._",
        "",
        "| Reifungszähler | Δ über den Schlaf |",
        "|---|---|",
    ]
    for key, label in (("valid_tests", "Valide Tests"), ("skills", "Kristallisierte Skills"),
                       ("episodes_resolved", "Aufgelöste Episoden"),
                       ("hindsight_reviews", "Abgeschlossene Reviews")):
        lines.append(f"| {label} | {delta.get(key, 0):+d} |")
    lines += [
        "",
        "## Was im Schlaf gelaufen ist",
        "",
        "| Pass | Ergebnis |",
        "|---|---|",
        f"| S1 Refragmentierung | {frag.get('links_total', 0)} Verknüpfungen aus "
        f"{frag.get('considered', 0)} Einträgen ({frag.get('thin_discarded', 0)} zu dünn "
        "verworfen) — Assoziation, keine Herleitung |",
        f"| S2 Struktur-Audit | {aud.get('scored', 0)} Methoden bewertet ({score_cells}); "
        f"{aud.get('skipped_titles', 0)} Papertitel übersprungen |",
        f"| S3 Defektberichte | {len(revs)} (nichts angewendet, nichts erfunden) |",
        "",
        f"## Wach-Warteschlange ({len(queue)})",
        "",
    ]
    if queue:
        lines += ["| # | Art | Gegenstand | Warum |", "|---|---|---|---|"]
        for i, row in enumerate(queue, 1):
            what = row.get("name") or row.get("fragment", "")
            lines.append(f"| {i} | {row['kind']} | {str(what)[:70]} | {row.get('why', '')} |")
    else:
        lines.append("_Leer — der Schlaf hat nichts übergeben._")
    lines += ["", "_Nichts hiervon ist aktiviert. Layer 9 und der Mensch entscheiden._", ""]
    return "\n".join(lines) + "\n"


def run_report(sleep_state: dict, passes: dict, proto, cycle: int, *, paths) -> dict:
    """Write the wake queue + report. Called once, on the transition back to AWAKE. Fail-open."""
    try:
        queue = build_queue(passes)
        qp = getattr(paths, "wake_queue", None)
        if qp is not None:
            qp.parent.mkdir(parents=True, exist_ok=True)
            qp.write_text(json.dumps({"cycle": cycle, "items": queue}, ensure_ascii=False),
                          encoding="utf-8")
        rp = getattr(paths, "sleep_report", None)
        if rp is not None:
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(render(sleep_state, passes, queue), encoding="utf-8")
        lw = sleep_state.get("last_wake") or {}
        proto.record(cycle, "sleep_report",
                     f"aufgewacht nach {lw.get('slept_cycles', 0)} Zyklen - "
                     f"{'gereift' if lw.get('matured') else 'NICHTS gereift'}; "
                     f"{len(queue)} Posten in der Wach-Warteschlange")
        return {"items": queue}
    except Exception as exc:  # noqa: BLE001 - the report must never break a cycle
        with contextlib.suppress(Exception):
            proto.record(cycle, "sleep_report", f"[Bericht übersprungen] {type(exc).__name__}")
        return {}


__all__ = ["build_queue", "render", "run_report", "MAX_QUEUE"]
