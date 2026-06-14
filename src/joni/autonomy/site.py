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

    commissions = [c for c in ext.get("commissions", []) if isinstance(c, dict) and c.get("title")]
    commissions_html = "".join(_commission(c) for c in commissions) or \
        "<li class=empty>none yet — no non-core capability gap has held long enough.</li>"
    topics = "".join(f"<span class=pill>{esc(t)}</span>" for t in s.get("topics", []))
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
    vit_line = (
        f"<div class=note>Vitality: <b style='color:{vcol}'>{esc(vit.get('verdict','—'))}</b> "
        f"· development {esc(vit.get('development',0))} · degeneration "
        f"{esc(vit.get('degeneration',0))} · {esc(vit.get('unsupported_hypotheses',0))} "
        f"unsupported idea(s) · semantic-usable "
        f"{int((vit.get('usable_semantic_rate',0) or 0)*100)}% · stagnation "
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
    <div class=note>Most work is deterministic (€0). A model is used only when DESi measures
      the free answer inadequate, and only the cheapest tier within budget.</div>
    <h2 style=margin-top:16px>Capability notes</h2>
    <ul>{notes}</ul>
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
    <ul>{commissions_html}</ul>
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
