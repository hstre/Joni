"""Operator-in-the-loop conflict resolution — the ONLY path that settles a contradiction.

Joni's standing rule is **"open conflicts, never force-resolve"**: the autonomous loop never decides
which of two contradicting claims is right. But a contradiction that is *genuinely settled* is the
richest thing a persona can hold — "ich hielt X für wahr → es brach an Z → jetzt Y". The one
authority allowed to settle a dispute is the **trusted operator** (HUMAN). This module gives the
operator that lever, mirroring the "you post, Joni writes" forum pattern:

  1. **Surface** (deterministic, no LLM, no decision): Joni lists the open conflicts worth
     deciding — those with a clear evidence asymmetry (one side independently supported, the other
     less so), ranked, bounded — showing BOTH claims and their support. He only presents.
  2. **Decide**: the operator writes ``conflict_id | winner_claim_id | reason`` into a drop box.
  3. **Apply** (deterministic bookkeeping of the human decision): resolve the conflict in favour of
     the winner (recorded in the conflict's ``resolution`` field), supersede the loser, and revive
     the winner if it was only contested by this one conflict. Every step is a gate-recorded op.

The persona then reads the superseded loser + its resolved conflict as a real ``X → Y, weil Z``
correction, provenance = the operator. Nothing here decides; it transcribes a human's decision.
"""

from __future__ import annotations

import desi_layer9 as l9

_DECISIONS_TEMPLATE = (
    "# Konflikt entscheiden - eine pro Zeile, Format:\n"
    "#   konflikt_id | gewinner_claim_id | grund\n"
    "# Beispiel:\n"
    "#   X-12 | C-88 | C-88 ist unter Last unabhängig bestätigt, C-40 nur eine Forumsmeinung.\n"
    "# Joni wendet das im nächsten Zyklus an: der Konflikt wird zugunsten des Gewinners gelöst,\n"
    "# der Verlierer als SUPERSEDED markiert (Nachfolger = Gewinner). Danach wird diese Datei\n"
    "# geleert. Zeilen mit '#' werden ignoriert. Joni entscheidet nie selbst - nur du.\n"
)


def decidable_conflicts(cs, *, max_items: int = 3) -> list[dict]:
    """Open conflicts worth the operator's decision: two claims, with a clear evidence asymmetry
    (one side has more independent support than the other). Deterministic and read-only - it ranks
    and presents, it NEVER picks a winner. Bounded so the operator is never flooded."""
    from .homeostasis import _supports_on
    by_id = {c.id: c for c in cs.core.all(l9.ObjectType.CLAIM)}
    out: list[dict] = []
    for cf in cs.core.open_conflicts():
        if getattr(getattr(cf, "conflict_status", None), "value", "") != "open":
            continue
        ids = [i for i in (getattr(cf, "claim_ids", None) or ()) if i in by_id][:2]
        if len(ids) != 2:
            continue
        a, b = ids
        sa, sb = _supports_on(cs, a), _supports_on(cs, b)
        if max(sa, sb) < 1 or sa == sb:
            continue                       # nothing to lean on, or symmetric -> not surfaced
        out.append({"conflict_id": cf.id, "topic": by_id[a].topic or by_id[b].topic or "?",
                    "a": {"id": a, "text": by_id[a].text, "support": sa},
                    "b": {"id": b, "text": by_id[b].text, "support": sb}})
    out.sort(key=lambda d: (abs(d["a"]["support"] - d["b"]["support"]),
                            max(d["a"]["support"], d["b"]["support"])), reverse=True)
    return out[:max_items]


def parse_decisions(text: str) -> list[dict]:
    """Parse the operator's pasted decisions. One per line: ``conflict_id | winner_id | reason``
    (reason optional). Blank lines and '#' lines ignored. Pure."""
    out: list[dict] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|", 2)]
        if len(parts) >= 2 and parts[0] and parts[1]:
            out.append({"conflict_id": parts[0], "winner_id": parts[1],
                        "reason": parts[2].strip() if len(parts) == 3 else ""})
    return out


def _other_open(cs, claim_id: str, exclude_cid: str) -> bool:
    """Is the claim still contested by some OTHER open conflict (so it must stay contested)?"""
    for cf in cs.core.open_conflicts():
        status = getattr(getattr(cf, "conflict_status", None), "value", "")
        if cf.id == exclude_cid or status != "open":
            continue
        if claim_id in (getattr(cf, "claim_ids", None) or ()):
            return True
    return False


def apply_decisions(cs, extensions: dict, proto, cycle: int, decisions: list[dict],
                    *, max_apply: int = 3) -> int:
    """Apply the operator's decisions (bounded, fail-open per item). For each: resolve the conflict
    in the winner's favour, supersede the loser(s), and revive the winner if it had no other open
    conflict. A decision naming a claim not in the conflict, or an already-closed conflict, is
    skipped with a note. Every mutation is a gate-recorded op; the loop transcribes, not decides.

    **Remonstration** (the manifesto's reasoned No, without breaking the HUMAN anchor): a decision
    that contradicts the measured evidence balance (the chosen winner has strictly LESS independent
    support than the losing side) is NOT applied immediately. Joni records a reasoned objection
    (protocolled, shown on the decision sheet) and the decision rests ONE round. Re-entering the
    same decision confirms it: it is then applied - the operator stays the final authority - but the
    objection is preserved immutably in the conflict's ``resolution_reason``, so a later correction
    carries the full story ("ich habe widersprochen, wurde überstimmt")."""
    from .homeostasis import _supports_on
    applied = 0
    done = set(extensions.setdefault("conflict_resolved", []))
    objections: dict = extensions.setdefault("conflict_objections", {})
    by_id = {c.id: c for c in cs.core.all(l9.ObjectType.CLAIM)}
    open_by_id = {cf.id: cf for cf in cs.core.open_conflicts()}
    for d in decisions:
        if applied >= max_apply:
            break
        cid, win = d.get("conflict_id"), d.get("winner_id")
        reason = (d.get("reason") or "").strip()
        cf = open_by_id.get(cid)
        if cf is None or getattr(getattr(cf, "conflict_status", None), "value", "") != "open":
            proto.record(cycle, "note", f"conflict {cid}: not an open conflict - skipped")
            continue
        ids = list(getattr(cf, "claim_ids", None) or ())
        if win not in ids or win not in by_id:
            proto.record(cycle, "note",
                         f"conflict {cid}: winner {win} is not a claim in this conflict - skipped")
            continue
        losers = [i for i in ids if i != win and i in by_id]

        # Remonstration check: measure the evidence balance the way the decision sheet does.
        sup_win = _supports_on(cs, win)
        sup_other = max((_supports_on(cs, x) for x in losers), default=0)
        pend = objections.get(cid)
        confirmed = isinstance(pend, dict) and pend.get("winner_id") == win
        if sup_win < sup_other and not confirmed:
            objections[cid] = {"winner_id": win, "cycle": cycle,
                               "sup_win": sup_win, "sup_other": sup_other,
                               "decision_reason": reason[:200]}
            proto.record(cycle, "einspruch",
                         f"{cid}: Einspruch - die Entscheidung für {win} widerspricht der "
                         f"Evidenzlage ({sup_win} vs {sup_other} unabhängige Belege). Eine Runde "
                         "aufgeschoben; erneutes Eintragen bestätigt und wird angewendet, der "
                         "Einspruch bleibt protokolliert.")
            continue                                 # held one round - the operator must confirm

        reason_txt = f"operator: {reason}" if reason else "operator decision"
        if confirmed:
            reason_txt += (f" · über protokollierten Einspruch entschieden (Evidenz {win}: "
                           f"{pend['sup_win']} vs Gegenseite: {pend['sup_other']})")
        try:
            cs.resolve_conflict(cid, winner_id=win, reason=reason_txt)
            for loser in losers:
                cs.supersede_claim(loser)
            if (getattr(getattr(by_id[win], "status", None), "value", "") == "contested"
                    and not _other_open(cs, win, cid)):
                cs.activate_claim(win)                      # its only contradiction is settled
        except Exception as exc:  # noqa: BLE001 - a stubborn op must never break the cycle
            proto.record(cycle, "note", f"conflict {cid}: resolution failed ({type(exc).__name__})")
            continue
        applied += 1
        done.add(cid)
        objections.pop(cid, None)                    # settled - the ledger holds the record now
        proto.record(cycle, "resolved",
                     f"{cid} settled by operator -> {win} wins, {', '.join(losers) or '-'} "
                     f"superseded · {reason[:80]}"
                     + (" · over recorded objection" if confirmed else ""))
    extensions["conflict_resolved"] = sorted(done)[-500:]
    # prune objections whose conflict is no longer open (settled some other way) + bound the dict
    still_open = {cf.id for cf in cs.core.open_conflicts()}
    extensions["conflict_objections"] = dict(sorted(
        ((k, v) for k, v in objections.items() if k in still_open),
        key=lambda kv: kv[1].get("cycle", 0))[-100:])
    return applied


def render_sheet(items: list[dict], objections: dict | None = None) -> str:
    """Render the decidable conflicts as a copy-paste decision sheet for the operator - plus any
    pending remonstrations (Joni's reasoned objections awaiting the operator's confirmation)."""
    lines = [
        "# Joni's Konflikt-Mappe",
        "",
        "Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never",
        "force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -",
        "**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:",
        "`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer",
        "als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …\".",
        "",
        f"_{len(items)} entscheidbare(r) Konflikt(e)._",
        "",
    ]
    if objections:
        lines += [
            "## Einsprüche — von dir zu bestätigen",
            "",
            "Diese Entscheidungen widersprechen der gemessenen Evidenzlage; Joni hat begründet",
            "Einspruch erhoben und sie **eine Runde aufgeschoben**. Du bleibst die Autorität:",
            "dieselbe Zeile erneut eintragen = bestätigen (wird angewendet, der Einspruch bleibt",
            "unlöschbar protokolliert). Oder anders entscheiden.",
            "",
        ]
        for cid, o in sorted(objections.items()):
            lines += [
                f"- **{cid}** · deine Wahl: {o.get('winner_id')} · Einspruch: die Gegenseite hat "
                f"mehr unabhängige Belege ({o.get('sup_win')} vs {o.get('sup_other')}).",
                f"  ```\n  {cid} | {o.get('winner_id')} | <dein grund>\n  ```",
                "",
            ]
    if not items:
        return "\n".join([*lines, "Gerade nichts zu entscheiden."]) + "\n"
    for it in items:
        a, b = it["a"], it["b"]
        lines += [
            f"## {it['conflict_id']} · Thema: {it['topic']}",
            "",
            f"- **{a['id']}** ({a['support']} Belege): {a['text']}",
            f"- **{b['id']}** ({b['support']} Belege): {b['text']}",
            "",
            f"```\n{it['conflict_id']} | <gewinner: {a['id']} oder {b['id']}> | <grund>\n```",
            "",
        ]
    return "\n".join(lines) + "\n"


def _fold_and_apply(cs, extensions: dict, proto, cycle: int, paths) -> int:
    """Fold the operator's pasted decisions, apply them, then reset the drop box."""
    dp = paths.conflict_decisions
    if not dp.exists():
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_text(_DECISIONS_TEMPLATE, encoding="utf-8")
        return 0
    decisions = parse_decisions(dp.read_text(encoding="utf-8"))
    if not decisions:
        return 0
    applied = apply_decisions(cs, extensions, proto, cycle, decisions)
    dp.write_text(_DECISIONS_TEMPLATE, encoding="utf-8")      # consumed - reset the drop box
    return applied


def interact(cs, extensions: dict, proto, cycle: int, *, paths) -> dict:
    """One cycle of operator-in-the-loop conflict resolution: apply any pasted decisions, then
    regenerate the decision sheet from the currently-decidable open conflicts. Fail-open: any error
    is swallowed so it can never break the loop."""
    try:
        applied = _fold_and_apply(cs, extensions, proto, cycle, paths)
        items = decidable_conflicts(cs)
        sheet = paths.resolve_sheet
        sheet.parent.mkdir(parents=True, exist_ok=True)
        sheet.write_text(render_sheet(items, extensions.get("conflict_objections")),
                         encoding="utf-8")
        if applied:
            proto.record(cycle, "resolved", f"applied {applied} operator conflict decision(s)")
        return {"applied": applied, "surfaced": len(items)}
    except Exception as exc:  # noqa: BLE001 - a read-layer helper must never break the cycle
        return {"applied": 0, "surfaced": 0, "error": type(exc).__name__}
