"""The public, static website - everything Joni does, in the open.

A single self-contained ``docs/index.html`` (data embedded, no build step, no backend)
suitable for GitHub Pages. It shows the live status, the budget, the topics Joni now
tracks, the peripheral improvements he built into himself, the open asks waiting on a
human, and the tail of the append-only protocol. ``docs/data.json`` is also written for
anyone who wants the raw record.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path


def build(data: dict) -> str:
    d = data
    s = d["snapshot"]
    b = d["budget"]
    w = d["window"]
    ext = d["extensions"]
    events = d["protocol"][-80:][::-1]

    def esc(x) -> str:
        return html.escape(str(x))

    rows = "\n".join(
        f"<tr><td class=ts>{esc(e.get('ts',''))}</td><td>c{esc(e.get('cycle',''))}</td>"
        f"<td><span class='k k-{esc(e.get('kind',''))}'>{esc(e.get('kind',''))}</span></td>"
        f"<td>{esc(e.get('summary',''))}</td>"
        f"<td class=m>{esc(e.get('model','')) or '—'}</td>"
        f"<td class=c>{format(e.get('cost_eur',0), '.4f') if e.get('cost_eur') else '—'}</td></tr>"
        for e in events
    )
    def _ask(a) -> str:
        ev = a.get("evidence", {}) if isinstance(a.get("evidence"), dict) else {}
        url = ev.get("source_url") or a.get("source_url", "#")
        rtype = a.get("request_type", "observation")
        comp = a.get("component", a.get("target", "protected core"))
        what = a.get("proposed_change", a.get("rationale", ""))
        return (
            f"<li><div><span class=chip>{esc(rtype)}</span> <b>{esc(comp)}</b></div>"
            f"<div class=asrow><span class=k>what</span> {esc(what)}</div>"
            f"<div class=asrow><span class=k>evidence</span> {esc(ev.get('source_title',''))} "
            f"<span class=src>(<a href='{esc(url)}'>source</a>)</span></div>"
            f"<div class=asrow><span class=k>risk</span> {esc(a.get('risk','—'))}</div></li>")

    asks = ext.get("asks", [])
    asks_html = "".join(_ask(a) for a in asks) or \
        "<li class=empty>none — Joni has not needed to touch the core.</li>"

    def _commission(c) -> str:
        ev = c.get("evidence", {}) if isinstance(c.get("evidence"), dict) else {}
        ev_txt = " · ".join(f"{esc(k)} {esc(v)}"
                            for k, v in ev.items() if not isinstance(v, list))

        def row(k, v):
            return f"<div class=asrow><span class=k>{k}</span> {esc(v)}</div>"
        return (
            f"<li><div><span class=chip>extension · non-core</span> "
            f"<b>{esc(c.get('title',''))}</b></div>"
            + row("component", c.get("component", ""))
            + row("why", c.get("motivation", ""))
            + row("build", c.get("desired_capability", ""))
            + row("done&nbsp;when", c.get("acceptance", ""))
            + f"<div class=asrow><span class=k>evidence</span> {ev_txt}</div>"
            + row("risk", c.get("risk", "—")) + "</li>")

    # Implemented Aufträge (by a human-gated Claude session), with date+time, so the page shows
    # not only what Joni asked for but what was actually built and when.
    done = d.get("commissions_done", []) if isinstance(d.get("commissions_done"), list) else []
    done_titles = {c.get("title", "") for c in done if isinstance(c, dict)}

    commissions = [c for c in ext.get("commissions", [])
                   if isinstance(c, dict) and c.get("title") and c.get("title") not in done_titles]
    commissions_html = "".join(_commission(c) for c in commissions) or \
        "<li class=empty>keine offenen — alle gestellten Aufträge sind umgesetzt.</li>"

    def _done(c) -> str:
        ts = esc(c.get("implemented_at", "—"))
        ref = c.get("ref", "")
        ref_html = f" <span class=src>({esc(ref)})</span>" if ref else ""
        return (
            f"<li><div><span class='chip' style='background:var(--good);color:#06210f'>"
            f"✓ umgesetzt</span> <b>{esc(c.get('title',''))}</b> "
            f"<span class=src>· {ts}</span>{ref_html}</div>"
            f"<div class=asrow><span class=k>component</span> {esc(c.get('component',''))}</div>"
            f"<div class=asrow><span class=k>note</span> {esc(c.get('note',''))}</div></li>")
    done_html = "".join(_done(c) for c in sorted(
        done, key=lambda c: c.get("implemented_at", ""), reverse=True)) or \
        "<li class=empty>noch keiner umgesetzt.</li>"

    # Humans & forums: people are a source, never an authority.
    stance = ext.get("forum_stance", "")
    reg = ext.get("forum_registry", {})
    reg_html = "".join(
        f"<span class=pill>{esc(p)}"
        f"{' · live' if v.get('registered') else ' · allowed'}</span>"
        for p, v in reg.items()) or "<span class=empty>no forums configured</span>"
    outbox = [d for d in ext.get("forum_outbox", []) if isinstance(d, dict)]
    posted_count = sum(1 for d in outbox if d.get("status") == "posted")
    outbox_html = "".join(
        f"<li><span class=chip>{esc(d.get('platform',''))} · "
        f"{esc(d.get('status','drafted'))}</span> <code>{esc(d.get('id',''))}</code> "
        f"{esc(d.get('question',''))}"
        + (f" <a href=\"{esc(d.get('posted_url'))}\" target=_blank rel=noopener>&#8599; ansehen</a>"
           if d.get("posted_url") else "")
        + "</li>"
        for d in reversed(outbox[-8:])) or "<li class=empty>no questions drafted yet</li>"
    mb = ext.get("forum_identity", {}).get("moltbook", {})
    mb_html = (
        f" &middot; als <a href=\"{esc(mb.get('profile_url'))}\" target=_blank rel=noopener>"
        f"@{esc(mb.get('name'))}</a> auf Moltbook" if mb.get("name") else "")
    approve_note = (
        "<div class=note style='margin-top:4px'><b>" + str(posted_count) + "</b> gepostet"
        + mb_html + " &middot; "
        "Agenten-Netze (Moltbook) postet Joni <b>autonom</b>; Menschen-Foren bleiben auf dem "
        "<i>&bdquo;du postest, Joni textet&ldquo;</i>-Weg &mdash; Entw&uuml;rfe warten in "
        "<code>docs/to_post.md</code>, bis ein Mensch sie postet.</div>")
    heard = [h for h in ext.get("forum_heard", []) if isinstance(h, dict)][-6:]
    heard_html = "".join(
        f"<li><div><b>{esc(h.get('platform',''))}:{esc(h.get('handle',''))}</b> "
        f"<span class=src>→ {esc(h.get('claim',''))}</span>"
        + (" <span class=chip>Reaktion auf willy-Post (Legacy)</span>"
           if h.get("origin") == "predecessor-thread" else "")
        + "</div>"
        f"<div class=asrow>{esc(h.get('text',''))}</div>"
        f"<div class=asrow><span class=k>treated as</span> {esc(h.get('treated_as',''))}</div></li>"
        for h in reversed(heard)) or \
        "<li class=empty>no human input yet — inbox at state/forum_inbox.json</li>"

    # Expert panel: what the Alexandria trio discussed the last time Joni was unsure.
    panel = ext.get("panel_last") if isinstance(ext.get("panel_last"), dict) else {}
    if isinstance(panel.get("phase3"), dict) and panel.get("phase3"):
        proles = panel.get("roles", {}) if isinstance(panel.get("roles"), dict) else {}
        voices = "".join(
            f"<li><div><span class=chip>{esc(name)} &middot; "
            f"{esc(proles.get(name, 'assessor'))}</span></div>"
            f"<div class=asrow>{esc(text)}</div></li>"
            for name, text in panel["phase3"].items()) or "<li class=empty>—</li>"
        panel_block = (
            "<div class=asrow><span class=k>unsicher bei</span> "
            f"{esc(panel.get('question', '')).replace(chr(10), '<br>')}</div>"
            f"<ul>{voices}</ul>"
            "<div class=note>Phase&nbsp;3 (&uuml;ber Kreuz): jede Stimme rekonstruiert die "
            "anderen; Dissens nur mit benannter abweichender Annahme. <b>Assessoren, keine "
            "Autorit&auml;t</b> &mdash; sie beraten, <b>Joni entscheidet</b>; Widerspruch "
            f"bleibt offen. Zyklus {esc(panel.get('cycle', ''))}.</div>")
    else:
        panel_block = ("<p class=empty>Noch keine Runde &mdash; das Trio wird nur einberufen, "
                       "wenn Joni unsicher ist (ein offener Widerspruch, den er h&auml;lt).</p>")

    # Semantic-engine telemetry: read off the capture log, never guessed from a €0 line.
    tele = d.get("telemetry", {}) if isinstance(d.get("telemetry"), dict) else {}
    # The honest quality metric (review #10): a strict per-claim AND of six conditions.
    eu = s.get("epistemically_usable", {})
    eu_pct = f"{eu.get('rate', 0) * 100:.0f}%" if isinstance(eu, dict) else "—"
    eu_title = ("typed AND source-anchored AND non-duplicate AND topic-valid AND scope-valid "
                "AND provenance-complete")

    def _tstat(label: str, value) -> str:
        return f"<div class=stat><span>{label}</span><span><b>{esc(value)}</b></span></div>"

    if tele.get("llm_calls"):
        by_model = " · ".join(f"{esc(m)}: {esc(n)}" for m, n in
                              sorted(tele.get("by_model", {}).items())) or "—"
        tele_block = (
            _tstat("LLM calls (total)", tele.get("llm_calls", 0))
            + _tstat("Granite calls", tele.get("granite_calls", 0))
            + _tstat("DeepSeek escalations", tele.get("deepseek_escalations", 0))
            + _tstat("Kevin calls", tele.get("kevin_calls", 0))
            + _tstat("cached (replayed)", tele.get("cached_calls", 0))
            + _tstat("live (real API)", tele.get("live_calls", 0))
            + _tstat("accepted claims", tele.get("accepted_claims", 0))
            + _tstat("accepted / live call", f"{tele.get('accepted_per_live_call', 0):.3f}")
            + _tstat("reserved budget", f"€{tele.get('reserved_budget_eur', 0):.2f}")
            + _tstat("est. API cost", f"€{tele.get('est_cost_eur', 0):.4f}")
            + _tstat("est. cost / accepted claim",
                     f"€{tele.get('est_cost_per_accepted_eur', 0):.4f}")
            + _tstat("last semantic call", tele.get("last_call") or "—")
            + _tstat("empty answers (live)", tele.get("empty_calls", 0))
            + _tstat("· truncated (token budget)", tele.get("empty_truncated", 0))
            + _tstat("· reasoning-only (adapter?)", tele.get("empty_with_reasoning", 0))
            + _tstat("· silent (nothing/filter)", tele.get("empty_silent", 0))
            + "<div class=note>Empty answers are <b>classified</b>, not guessed: "
            "<b>truncated</b> (finish_reason=length → the reasoning model spent the whole budget, "
            "content empty) vs <b>reasoning-only</b> (text was in a reasoning field → adapter bug) "
            "vs <b>silent</b> (nothing/filter). This is what tells the four failure classes apart "
            "instead of conflating them.</div>"
            + f"<div class=note>by model — {by_model}. Granite via prepaid OpenRouter; "
            "DeepSeek v4-pro via prepaid DeepSeek. <b>reserved</b> budget ≠ <b>estimated</b> API "
            "cost (per-call rate; exact spend on each provider's page). The number that matters: "
            "<b>accepted / live call</b> — how many real calls became an accepted claim. Real "
            "capture records (<code>state/model_calls/calls.jsonl</code>).</div>")
    else:
        tele_block = ("<p class=empty>Noch keine Modell-Calls erfasst &mdash; entweder ist die "
                      "semantische Schicht aus (<code>JONI_SEMANTIC_PROPOSALS</code>) oder dieser "
                      "Zyklus brauchte kein Modell. Sobald Granite/DeepSeek feuern, steht es "
                      "hier.</p>")

    # Kevin: what his far-analogy arm actually proposed, and whether the panel found it sensible.
    kevin_log = ext.get("kevin_llm", []) if isinstance(ext.get("kevin_llm"), list) else []
    panel_q = panel.get("question", "") if isinstance(panel, dict) else ""
    panel_verdict = ""
    if isinstance(panel.get("phase3"), dict) and panel.get("phase3"):
        n, t = next(iter(panel["phase3"].items()))
        panel_verdict = f"{esc(n)}: {esc(t[:200])}"
    kevin_items = []
    for entry in reversed(kevin_log[-6:]):
        topics = " &times; ".join(esc(t) for t in entry.get("topics", []))
        for p in entry.get("proposals", []):
            txt = p.get("text", "")
            assessed = bool(txt) and txt[:48] in panel_q
            pending = ("<div class=note>Bewertung der Expertenrunde steht noch aus &mdash; sie "
                       "tagt periodisch und beurteilt, ob es eine gute Idee ist "
                       "(und warum/warum nicht).</div>")
            verdict = (f"<div class=note><b>Expertenrunde:</b> {panel_verdict} "
                       "<span class=src>(berät; Joni entscheidet)</span></div>"
                       if assessed and panel_verdict else pending)
            kevin_items.append(
                f"<li><div><span class=chip>{topics}</span> "
                f"<span class=src>Zyklus {esc(entry.get('cycle',''))}</span></div>"
                f"<div class=asrow>{esc(txt)}</div>{verdict}</li>")
    kevin_props = "".join(kevin_items) or (
        "<li class=empty>Kevin hat noch keine Fernanalogie vorgeschlagen &mdash; er tagt nach "
        "Kadenz und nur auf Themen mit echtem Material (nicht auf <code>unsorted</code> oder "
        "dünnen Wortclustern).</li>")
    kevin_block = (
        f"<div class=stat><span>Methoden-Trials <span class=src>(synthetische Simulation)</span>"
        f"</span><span><b>{esc(s.get('method_trials',0))}</b></span></div>"
        f"<div class=stat><span>davon &bdquo;aktivierungsreif&ldquo; "
        f"<span class=src>(Sim-Artefakt)</span>"
        f"</span><span><b>{esc(s.get('methods_ready',0))}</b></span></div>"
        "<div class=note style='color:var(--warn)'>⚠ Die Methoden-Trials sind eine "
        "<b>synthetische Simulation</b> (Keyword-Shape-Overlap), <b>kein</b> semantischer oder "
        "empirischer Wirksamkeitsnachweis &mdash; <code>evaluation_mode=synthetic_mock, "
        "epistemic_weight=none</code>. Heißt: &bdquo;der Simulator stufte N als bestanden "
        "ein&ldquo;, nie &bdquo;N Methoden sind wirksam&ldquo;. Ein echtes Protokoll "
        "(frozen task set · Baseline vs. "
        "Intervention · Messgröße · Wiederholungen · Negativkontrolle · Layer-9-Proposal mit "
        "Provenienz) ist der vorgesehene Ersatz.</div>"
        "<h3 style='margin:10px 0 4px'>Fernanalogien (kreativer Arm, deepseek-v4-pro)</h3>"
        f"<ul>{kevin_props}</ul>"
        "<div class=note>Kevin schlägt vor (Cross-Domain-Hypothesen &amp; Methoden) und probiert "
        "Methoden durch &mdash; er <b>entscheidet nie</b>. Ob ein Vorschlag taugt, beurteilt die "
        "Expertenrunde; <b>Joni</b> entscheidet, was er aufnimmt.</div>")

    # The REAL method-trial (measured, provenance-bearing) - explicitly distinct from the synthetic
    # simulation above. The decision rests on the predefined metric, never on a model's opinion.
    rt = ext.get("real_trial", {}) if isinstance(ext.get("real_trial"), dict) else {}
    if rt.get("method_id"):
        better = "niedriger = besser" if rt.get("lower_is_better") else "höher = besser"
        verdict = ("<b style='color:var(--good)'>PASS</b>" if rt.get("passed")
                   else "<b style='color:var(--warn)'>kein Pass</b>")
        real_trial_block = (
            _tstat("Methode", rt.get("method_id", "—"))
            + _tstat("Task-Set", f"{esc(rt.get('task_set','—'))} · sha "
                     f"{esc(str(rt.get('task_set_sha',''))[:10])}")
            + _tstat(f"Metrik ({better})", rt.get("metric", "—"))
            + _tstat("Baseline (ohne Methode)", rt.get("baseline", "—"))
            + _tstat("Intervention (mit Methode)", rt.get("intervention", "—"))
            + _tstat("Negativkontrolle (Sham)", rt.get("negative_control", "—"))
            + _tstat("Δ (Effekt)", rt.get("delta", "—"))
            + _tstat("Wiederholungen", rt.get("repetitions", "—"))
            + _tstat("Richtung · Unsicherheit",
                     f"{esc(rt.get('direction','—'))} · {esc(rt.get('uncertainty','—'))}")
            + _tstat("Verdikt", verdict)
            + f"<div class=note>Echtes Protokoll <code>{esc(rt.get('evaluation_mode',''))}</code>, "
            f"<code>epistemic_weight={esc(rt.get('epistemic_weight',''))}</code> (gemessene "
            "Evidenz, aber noch <b>nicht</b> menschlich bestätigt). Die Pass/Fail-Entscheidung "
            "ruht <b>allein</b> auf der vorab definierten Messgröße + Schwelle + sauberer "
            "Negativkontrolle &mdash; nie auf einem Modell-Urteil. Modelle dürfen Fälle "
            "<i>bearbeiten</i>; entscheiden tut die Regel.</div>")
    else:
        real_trial_block = ("<p class=empty>Noch kein echter Trial gelaufen (kevin.real_trial "
                            "nicht verfügbar oder dieser Zyklus ohne Trial).</p>")

    from . import quality
    good_topics = [t for t in s.get("topics", []) if quality.is_good_topic(t)]
    topics = "".join(f"<span class=pill>{esc(t)}</span>" for t in good_topics)
    added = "".join(f"<span class='pill add'>{esc(t)}</span>"
                    for t in ext.get("topics_added", [])) or "<span class=empty>none yet</span>"
    notes = "".join(f"<li>{esc(n.get('note',''))} "
                    f"<span class=src>(<a href='{esc(n.get('source','#'))}'>src</a>)</span></li>"
                    for n in ext.get("notes", [])) or "<li class=empty>none yet</li>"
    spent_pct = (b["spent_eur"] / b["cap_eur"] * 100) if b.get("cap_eur") else 0
    lr = s.get("last_route")
    route_line = (f" · last route → {esc(lr['model'])} (~${lr['cost_usd']:.6f})"
                  if lr else "")
    vit = ext.get("vitality", {}) or {}
    vcol = {"developing": "var(--good)", "degenerating": "var(--rej)"}.get(
        vit.get("verdict"), "var(--warn)")
    # Show the HONEST quality metric (epistemically_usable), not the lenient
    # usable_semantic_rate which read ~100% even with 0 evidence links and unsupported ideas.
    vit_line = (
        f"<div class=note>Vitality: <b style='color:{vcol}'>{esc(vit.get('verdict','—'))}</b> "
        f"· development {esc(vit.get('development',0))} · degeneration "
        f"{esc(vit.get('degeneration',0))} · {esc(vit.get('unsupported_hypotheses',0))} "
        f"unsupported idea(s) · epistemically-usable {eu_pct} · stagnation "
        f"{esc(vit.get('stagnation_cycles',0))} cycle(s)</div>" if vit else "")

    def _movements(entry) -> str:
        return "".join(
            f"<div class=movement><h3>{esc(sec.get('title',''))}</h3>"
            f"<p>{esc(sec.get('text',''))}</p></div>"
            for sec in entry.get("sections", []))

    def _assessments(entry) -> str:
        return "".join(
            f"<li>{esc(a.get('text',''))} "
            f"<span class=src>(evidence {len(a.get('evidence', []))}, "
            f"counter {len(a.get('counterevidence', []))})</span></li>"
            for a in entry.get("assessments", [])) or "<li class=empty>no assessment</li>"

    diary = ext.get("diary") or ([ext["last_review"]] if ext.get("last_review") else [])
    if diary:
        latest = diary[-1]
        principles = "".join(f"<li>{esc(p)}</li>" for p in latest.get("principles", []))
        principles_html = (f"<div class=note style='margin-bottom:6px'>Standing principles "
                           f"(stated once, not repeated each report):</div><ul>{principles}</ul>"
                           if principles else "")
        review_html = (
            f"<div class=note><b>{esc(latest.get('ts',''))}</b> · written in the first person, "
            f"grounded in my own state — a report, not a performance. A fresh installment "
            f"every 10 runs; {len(diary)} entr{'y' if len(diary) == 1 else 'ies'} so far, "
            f"nothing overwritten.</div>"
            f"{principles_html}"
            f"<p class=lede>{esc(latest.get('headline',''))}</p>"
            f"{_movements(latest)}"
            f"<div class=note style='margin-top:12px'>The <i>provisional</i> beliefs this "
            f"review updated about myself (evidence-backed, never facts):</div>"
            f"<ul>{_assessments(latest)}</ul>")
        earlier = "".join(
            f"<details class=entry><summary>{esc(e.get('ts',''))} · "
            f"{esc(e.get('headline',''))}</summary>{_movements(e)}</details>"
            for e in diary[:-1][::-1])
        if earlier:
            review_html += (f"<h2 style='margin-top:18px'>Earlier entries — newest first</h2>"
                            f"{earlier}")
    else:
        review_html = "<p class=empty>No self-review yet (runs hourly).</p>"

    return f"""<!doctype html>
<html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Joni · off the leash</title>
<style>
:root{{--bg:#0d1016;--panel:#161b23;--line:#2a3340;--ink:#e7edf4;--mut:#93a1b2;
--acc:#6ea8fe;--good:#54d6a6;--warn:#e6c14b;--rej:#e08c8c;--add:#b794f6}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:14.5px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
header{{padding:22px 26px 8px}}h1{{margin:0;font-size:22px}}h1 span{{color:var(--acc)}}
.tag{{color:var(--mut);max-width:900px;margin-top:4px}}
.wrap{{padding:14px 26px 50px;display:grid;gap:16px;grid-template-columns:1fr 1fr}}
@media(max-width:860px){{.wrap{{grid-template-columns:1fr}}}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}}
.card.full{{grid-column:1/-1}}
h2{{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut)}}
.stat{{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--mut)}}
.stat b{{color:var(--ink)}}
.bar{{height:8px;background:#1d2430;border-radius:999px;overflow:hidden;margin-top:8px}}
.bar>i{{display:block;height:100%;background:var(--good)}}
.pill{{display:inline-block;font-size:12px;padding:2px 9px;border-radius:999px;
border:1px solid var(--line);color:var(--mut);margin:3px 4px 0 0}}
.pill.add{{color:var(--add);border-color:var(--add)}}
ul{{margin:6px 0 0;padding-left:18px}}.empty{{color:var(--mut)}}
.src a{{color:var(--acc);text-decoration:none}}
table{{width:100%;border-collapse:collapse;font-size:12.5px}}
td{{padding:5px 8px;border-bottom:1px solid #20262f;vertical-align:top}}
.ts{{color:var(--mut);white-space:nowrap;font-family:ui-monospace,monospace}}
.m{{color:var(--mut)}}.c{{text-align:right;font-family:ui-monospace,monospace}}
.k{{font-size:11px;padding:1px 6px;border-radius:999px;border:1px solid var(--line)}}
.k-improved{{color:var(--add);border-color:var(--add)}}
.k-asked{{color:var(--warn);border-color:var(--warn)}}
.k-judged,.k-fetched{{color:var(--mut)}}.k-changed_mind{{color:var(--rej);border-color:var(--rej)}}
.k-method,.k-trialed{{color:var(--good);border-color:var(--good)}}
.k-retired{{color:var(--rej);border-color:var(--rej)}}
.note{{color:var(--mut);font-size:12px;margin-top:8px}}
.chip{{font-size:10.5px;padding:1px 7px;border-radius:999px;border:1px solid var(--warn);
color:var(--warn);text-transform:uppercase;letter-spacing:.4px}}
.asrow{{font-size:12.5px;margin:3px 0 0 2px}}.asrow .k{{color:var(--mut);margin-right:6px}}
li{{margin-bottom:10px}}
.lede{{color:var(--ink);font-size:15px;margin:10px 0 14px;font-style:italic}}
.movement{{margin:12px 0;padding-left:12px;border-left:2px solid var(--line)}}
.movement h3{{margin:0 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;
color:var(--acc)}}
.movement p{{margin:0;color:var(--ink);max-width:760px}}
.entry{{border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0;
background:#12161d}}
.entry summary{{cursor:pointer;color:var(--mut);font-family:ui-monospace,monospace;
font-size:12.5px}}
.entry[open] summary{{color:var(--ink);margin-bottom:6px}}
</style></head><body>
<header>
<h1><span>Joni</span> — off the leash, on the record</h1>
<p class=tag>An operative identity running under one DESi rule: it may research and build
<i>peripheral</i> improvements into itself, but it may not change its protected core
without asking. Everything it does is logged here. {esc(d['generated'])}.</p>
<p class=tag><a href="layer9.html" style="color:var(--acc);text-decoration:none">
&rarr; open the <b>Layer 9 epistemic map</b></a> — what Joni believes, what it rests on,
what is uncertain, what contradicts, and what changed.</p>
</header>
<div class=wrap>
  <div class=card>
    <h2>Status</h2>
    <div class=stat>
      <span>day <b>{esc(s.get('tick',0))}</b> of the week</span>
      <span>run <b>{esc(w.get('runs',0))}</b></span>
      <span>topics <b>{esc(len(s.get('topics',[])))}</b></span>
      <span>claims <b>{esc(s.get('claims_active',0))}</b>/{esc(s.get('claims_total',0))}</span>
      <span>memory <b>{esc(s.get('memory',0))}</b></span>
      <span>ledger <b>{esc(s.get('ledger',0))}</b></span>
      <span>methods for Kevin <b>{esc(s.get('methods',0))}</b></span>
      <span>method trials <b>{esc(s.get('method_trials',0))}</b></span>
      <span>activation-ready <b>{esc(s.get('methods_ready',0))}</b></span>
      <span>evidence links <b>{esc(s.get('evidence_links',0))}</b></span>
      <span>hypotheses <b>{esc(s.get('hypotheses',0))}</b></span>
      <span>self-model <b>{esc(s.get('self_model',0))}</b></span>
      <span>conflicts open <b>{esc(s.get('open_conflicts',0))}</b></span>
      <span>research topics <b>{esc(s.get('research_topics',0))}</b></span>
      <span title="{eu_title}">epistemically usable <b>{eu_pct}</b></span>
    </div>
    <div class=note>Runtime window: started {esc(w.get('start','?'))} · run {esc(w.get('runs',0))}
      {'· <b style=color:var(--rej)>RETIRED</b>' if w.get('retired') else '· active (1 week)'}</div>
    <div class=note>Routing engine: <b>{esc(s.get('routing_engine','?'))}</b>
      · day {esc(s.get('days_running','?'))} of the week{route_line}</div>
    {vit_line}
    <div style=margin-top:12px><b>topics tracked</b><br>{topics}</div>
    <div style=margin-top:10px><b>self-added topics</b><br>{added}</div>
  </div>
  <div class=card>
    <h2>Budget (frugal · cheapest model that suffices)</h2>
    <div class=stat><span>spent <b>€{b['spent_eur']:.4f}</b> / €{b['cap_eur']:.0f} per week</span>
      <span>runs <b>{esc(b.get('runs',0))}</b></span></div>
    <div class=bar><i style="width:{min(100,spent_pct):.1f}%"></i></div>
    <div class=note>The Layer-9 governance core is deterministic (€0). The semantic engine
      (Granite proposals + DeepSeek escalation) runs as a non-authoritative proposal layer —
      its real activity and cost are in the telemetry card below, not in this counter.</div>
    <h2 style=margin-top:16px>Capability notes</h2>
    <ul>{notes}</ul>
  </div>
  <div class=card>
    <h2>Semantic engine — telemetry (real capture records, not a guess)</h2>
    {tele_block}
  </div>
  <div class="card full">
    <h2>Self-review · hourly · provisional self-model (not facts)</h2>
    {review_html}
  </div>
  <div class="card full">
    <h2>Asks — waiting on a human (protected core)</h2>
    <ul>{asks_html}</ul>
  </div>
  <div class="card full">
    <h2>Aufträge an Claude — extend Joni (non-core, implemented via PR)</h2>
    <h3 style='margin:4px 0'>Offen</h3>
    <ul>{commissions_html}</ul>
    <h3 style='margin:10px 0 4px'>Umgesetzt (mit Datum &amp; Uhrzeit)</h3>
    <ul>{done_html}</ul>
  </div>
  <div class="card full">
    <h2>Menschen &amp; Foren — a source, not an authority</h2>
    <p class=note>{stance}</p>
    <div style='margin:6px 0'>{reg_html}</div>
    <h3 style='margin:10px 0 4px'>Fragen &amp; Posts</h3>
    <ul>{outbox_html}</ul>
    {approve_note}
    <h3 style='margin:10px 0 4px'>Heard from people — and how it was treated</h3>
    <ul>{heard_html}</ul>
  </div>
  <div class="card full">
    <h2>Kevin — was er vorschlägt &amp; ob es taugt</h2>
    {kevin_block}
  </div>
  <div class="card full">
    <h2>Echter Methoden-Trial — real_trial_protocol_v1 (gemessen, provisional)</h2>
    {real_trial_block}
  </div>
  <div class="card full">
    <h2>Expertenrunde — Alexandria, über Kreuz (berät; Joni entscheidet)</h2>
    {panel_block}
  </div>
  <div class="card full">
    <h2>Protocol — append-only, newest first</h2>
    <table><tr><td class=ts>time</td><td>cyc</td><td>kind</td><td>what</td><td class=m>model</td>
      <td class=c>€</td></tr>{rows}</table>
  </div>
</div></body></html>
"""


def render(index_path: Path, data_path: Path, data: dict) -> None:
    data = {**data, "generated": datetime.now(UTC).isoformat(timespec="seconds")}
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(build(data), encoding="utf-8")
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
