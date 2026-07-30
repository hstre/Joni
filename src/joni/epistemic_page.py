"""Die Darstellung der epistemischen Karte - ``docs/flow.html``.

Gleiche Bauart wie ``architecture_page``: eine in sich geschlossene Datei, kein Build-Schritt,
keine externen Skripte, und hier wird nichts gerechnet. Alles kommt aus ``epistemic_map.analyse``.
"""
from __future__ import annotations

import html
import json

from joni.architecture_page import _CSS as _BASE_CSS

_CSS = _BASE_CSS + """
.matrix{width:100%;border-collapse:collapse;font-size:12px}
.matrix th{color:var(--mut);font-weight:400;text-align:left;padding:5px 7px;
border-bottom:1px solid var(--line);white-space:nowrap}
.matrix th.rot{writing-mode:vertical-rl;transform:rotate(180deg);height:150px;padding:4px 2px;
font-family:ui-monospace,Menlo,monospace}
.matrix td{padding:4px 7px;border-bottom:1px solid #1d2430;text-align:center}
.matrix td.h{text-align:left;font-family:ui-monospace,Menlo,monospace;color:var(--ink);
white-space:nowrap}
.yes{color:var(--good)}.no{color:var(--rej)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.flow{display:grid;gap:3px;margin-top:8px}
.flow>div{display:grid;grid-template-columns:150px minmax(0,1fr) 92px;gap:10px;
align-items:center;font-size:12.5px}
.flow .k{font-family:ui-monospace,Menlo,monospace;overflow:hidden;text-overflow:ellipsis}
.flow .t{height:16px;background:#1d2430;border-radius:4px;position:relative}
.flow .t>i{position:absolute;top:0;bottom:0;width:9px;border-radius:4px;background:var(--acc)}
.flow .t>i.mdl{background:var(--add)}
.flow .n{text-align:right;color:var(--mut);font-variant-numeric:tabular-nums;font-size:11.5px}
.site{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:var(--mut);
padding:3px 0 3px 10px;border-left:2px solid var(--line)}
.site b{color:var(--ink);font-weight:400}
.op{margin:0 0 14px}
.op>h4{margin:0 0 3px;font:13px/1.4 ui-monospace,Menlo,monospace;color:var(--acc)}
.op .tag{margin:0 0 5px;font-size:12.5px}
.big{font-size:26px;color:var(--ink);font-variant-numeric:tabular-nums}
.nav{padding:0 22px;margin-top:8px}
.nav a{color:var(--acc);margin-right:16px;font-size:13px}
.nav a.on{color:var(--ink);border-bottom:2px solid var(--acc);padding-bottom:3px}
"""


def _esc(x) -> str:
    return html.escape(str(x))


def _matrix(perm: dict) -> str:
    """Die Erlaubnistabelle. Ausgerechnet, nicht abgeschrieben."""
    ops = perm["operators"]
    auth = set(perm["authoritative"])
    ctrl = set(perm["control"])
    head = "".join(f'<th class=rot>{_esc(o)}</th>' for o in ops)
    rows = []
    for origin in perm["origins"]:
        allowed = set(perm["allowed"][origin])
        cells = "".join(
            f'<td class={"yes" if o in allowed else "no"}>{"ja" if o in allowed else "nein"}</td>'
            for o in ops)
        rows.append(f'<tr><td class=h>{_esc(origin)}</td>{cells}</tr>')
    ctrl_txt = ", ".join(f"<code>{_esc(c)}</code>" for c in sorted(ctrl))
    legend = (f'<p class=hint>{len(auth)} Operatoren sind <b>autoritativ</b> (sie verleihen '
              f'Geltung oder entscheiden Streit), {len(ctrl)} liegen auf der '
              f'<b>Kontrollebene</b>: {ctrl_txt}. '
              f'Genau diese sind fuer erzeugende Herkuenfte gesperrt.</p>')
    return (legend + '<div class=scroll><table class=matrix>'
            f'<tr><th>Herkunft</th>{head}</tr>{"".join(rows)}</table></div>')


def _trust(perm: dict) -> str:
    """Herkuenfte, die autoritativ handeln duerfen, ohne ausdruecklich vertraut zu sein.

    Dieser Befund ist gerechnet, nicht bemerkt: Die Regel sperrt die *erzeugenden* Herkuenfte
    (Modell, Nutzer, Quelle) von autoritativen Operatoren aus. Wer weder erzeugend noch
    ausdruecklich vertrauenswuerdig ist, faellt durch diese Unterscheidung hindurch und wird
    behandelt wie ein Mensch. Beim Lesen der 44 Regelzeilen faellt das nicht auf.
    """
    odd = perm.get("trusted_by_default") or []
    if not odd:
        return ('<div class="card full"><h2>Vertrauen ohne Zusage</h2>'
                '<p class=hint>Keine Herkunft darf autoritativ handeln, ausser Mensch und '
                'deterministischem Operator.</p></div>')
    rows = "".join(
        f'<div class=op><h4>{_esc(o)}</h4><p class=hint>darf '
        f'{len(perm["authoritative_by_origin"][o])} autoritative Operatoren beantragen: '
        + ", ".join(f'<code>{_esc(x)}</code>'
                    for x in perm["authoritative_by_origin"][o]) + '</p></div>'
        for o in odd)
    return f"""<div class="card full"><h2>Vertrauen ohne Zusage</h2>
<p class=hint>Die Regel sperrt ausdruecklich die <em>erzeugenden</em> Herkuenfte - Modell,
Nutzer, Quelle - von autoritativen Operatoren. Sie sperrt nicht, was durch diese Unterscheidung
hindurchfaellt. {len(odd)} Herkunft/Herkuenfte duerfen deshalb bestaetigen, verwerfen, Streit
entscheiden und Methoden verbindlich machen, ohne dass irgendwo steht, dass ihnen zu trauen
waere:</p>
{rows}
<p class=hint>Das ist ein gerechneter Befund, kein Vorwurf: Beim Lesen der Regel faellt es nicht
auf, weil dort nur steht, wer <em>gesperrt</em> ist. Ob das so gewollt ist, ist eine Entscheidung
ueber Geltung - und die gehoert nicht in eine Karte, die sie gefunden hat. Sie steht hier, damit
sie getroffen werden kann.</p></div>"""


def _cycle(cyc: dict, *, limit: int = 26) -> str:
    """Der beobachtete Ablauf - gemessene erste Position im Zyklus, keine gedachte Reihenfolge."""
    ev = cyc["events"][:limit]
    if not ev:
        return "<p class=hint>Kein Protokoll vorhanden.</p>"
    top = max(e["in_cycles"] for e in ev) or 1
    rows = []
    for e in ev:
        left = e["position"] * 100
        mdl = " mdl" if e["model_backed"] else ""
        share = e["in_cycles"] / top
        rows.append(
            f'<div><span class=k>{_esc(e["kind"])}</span>'
            f'<span class=t><i class="{mdl.strip()}" style="left:calc({left:.1f}% - '
            f'{left / 100 * 9:.1f}px);opacity:{0.35 + 0.65 * share:.2f}"></i></span>'
            f'<span class=n>{e["in_cycles"]}/{cyc["cycles"]}</span></div>')
    return f'<div class=flow>{"".join(rows)}</div>'


def _sites(data: dict) -> str:
    """Wer beantragt welchen Schreibvorgang - je Operator, mit Datei und Zeile."""
    notes = data["operator_notes"]
    auth = set(data["permissions"]["authoritative"])
    out = []
    for op, sites in data["by_operator"].items():
        if op == "<nicht literal>":
            continue
        note = notes.get(op)
        badge = ' <span class="pill rej">autoritativ</span>' if op in auth else ""
        proposers = sorted({s["proposer"] for s in sites if s["proposer"]})
        pro = (" · Antragsteller: " + ", ".join(f"<code>{_esc(p)}</code>" for p in proposers)
               ) if proposers else ""
        rows = "".join(
            f'<div class=site><b>{_esc(s["module"])}</b>:{s["line"]} · '
            f'{_esc(s["function"])}()</div>' for s in sites)
        out.append(
            f'<div class=op><h4>{_esc(op)}{badge}</h4>'
            + (f'<p class="tag note"><span>von Hand</span> {_esc(note)}</p>' if note else "")
            + f'<p class=hint>{len(sites)} Stelle(n){pro}</p>{rows}</div>')
    return "".join(out)


def render(data: dict) -> str:
    t = data["totals"]
    gate = data["gate"]
    cyc = data["cycle"]
    perm = data["permissions"]

    nonlit = data["by_operator"].get("<nicht literal>", [])
    nonlit_rows = "".join(
        f'<div class=site><b>{_esc(s["module"])}</b>:{s["line"]} · {_esc(s["function"])}()</div>'
        for s in nonlit)

    intern = ", ".join(f"<code>{_esc(w)}()</code>"
                       for w in gate["writers"] if w.startswith("_"))
    gate_verdict = (
        f'<p class=hint>Der Kern hat <b>{"genau einen" if gate["single_gate"] else "mehrere"}'
        f'</b> oeffentlichen schreibenden Eingang: '
        + ", ".join(f'<code>{_esc(w)}()</code>' for w in gate["public_writers"])
        + f'. Ermittelt aus den Zuweisungen an Objektspeicher und Journal in '
          f'<code>desi_layer9/core.py</code> - nicht aus der Beschreibung im Docstring. '
          f'Intern schreiben zusaetzlich {intern}, '
          f'beide nur ueber diesen Eingang erreichbar.</p>')

    models = "".join(
        f'<tr><td class=h>{_esc(m["name"])}</td><td>{m["events"]}</td>'
        f'<td>{m["cost_eur"]:.4f}</td></tr>' for m in cyc["models"])

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for raw, safe in (("<", "\\u003c"), (" ", "\\u2028"), (" ", "\\u2029")):
        payload = payload.replace(raw, safe)

    return f"""<!doctype html>
<html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Joni · Wer darf was</title>
<style>{_CSS}</style>
</head><body>
<header>
<h1>Joni · <span>Wer darf was</span></h1>
<p class=tag>Die Architekturkarte beantwortet, welches Modul technisch an welchem haengt. Sie
beantwortet nicht, wer eine Behauptung erzeugen darf, wer ihren Status aendern darf und wann ein
Modell ins Spiel kommt. Diese Seite tut das - und zwar aus vier nachrechenbaren Quellen: die
Erlaubnistabelle wird <em>ausgerechnet</em> (die Regelfunktion wird fuer jedes Paar aufgerufen),
die Schreibstellen kommen per <code>ast</code> aus dem Quelltext, das Schreibtor aus den
Zuweisungen im Kern, der Ablauf aus {cyc["total"]} tatsaechlich gelaufenen Protokollereignissen.</p>
<div class=stat>
<span><b>{t["write_sites"]}</b> Schreibstellen</span>
<span><b>{t["operators_used"]}</b>/{t["operators_total"]} Operatoren benutzt</span>
<span><b>{len(perm["authoritative"])}</b> autoritativ</span>
<span><b>{cyc["cycles"]}</b> beobachtete Zyklen</span>
<span><b>{len(data["protected_core"])}</b> geschuetzte Kernpfade</span>
</div>
</header>
<div class=nav><a href=index.html>Architektur</a><a href=# class=on>Wer darf was</a>
<a href=status.html>Statusseite (angehalten)</a></div>

<div class=wrap>

<div class="card full"><h2>Das Schreibtor</h2>{gate_verdict}
<p class=hint>Das ist die tragende Eigenschaft: Es gibt keinen zweiten Weg, den Zustand zu
aendern. Jede Aenderung laeuft als Antrag durch dieselbe Pruefung und landet vorher im Journal -
auch ein abgelehnter. Wenn diese Seite hier je <em>mehrere</em> Eingaenge meldet, ist die
Eigenschaft verloren, und niemand muss sich darauf verlassen, dass es jemandem auffaellt.</p></div>

<div class="card full"><h2>Erlaubnistabelle: welche Herkunft darf welchen Operator beantragen</h2>
{_matrix(perm)}
<p class=hint>Diese Tabelle ist nicht abgeschrieben. Beim Bau der Seite wird die echte
Regelfunktion fuer jedes Paar aus Herkunft und Operator aufgerufen; was hier steht, ist das
Verhalten des laufenden Codes. Aendert jemand die Regel, aendert sich die Tabelle beim naechsten
Bau von selbst.</p></div>

{_trust(perm)}

<div class=card><h2>Beobachteter Zyklus</h2>
<p class=hint>Waagerecht die gemessene <em>erste</em> Stelle, an der eine Ereignisart im Zyklus
auftritt; rechts, in wie vielen der {cyc["cycles"]} Zyklen sie ueberhaupt vorkam. Violett heisst:
mindestens einmal modellgestuetzt. Das ist ein gemessener Ablauf, kein entworfener - und keine
Kontrollflussverfolgung: Haeufigkeit ist keine Kausalitaet.</p>
{_cycle(cyc)}</div>

<div class=card><h2>Wovon der Ablauf getragen wird</h2>
<p class=hint>Das ueberraschendste Ergebnis dieser Karte: der beobachtete Betrieb ist fast
vollstaendig deterministisch. Modelle kommen nur an wenigen Stellen vor.</p>
<div class=scroll><table class=matrix>
<tr><th>Quelle</th><th>Ereignisse</th><th>EUR</th></tr>{models}</table></div>
<p class=hint>Die Kostenspalte stammt aus den Protokollzeilen selbst. Sie belegt, was schon
gestern klar wurde: teuer war nicht Joni.</p></div>

<div class="card full"><h2>Wer beantragt welchen Schreibvorgang</h2>
<p class=hint>Aus den Aufrufen von <code>make_proposal</code> und dem Kuerzel <code>_op</code>,
mit Datei und Zeile. Ein Operator, der hier auftaucht, wird an dieser Stelle wirklich beantragt -
ob der Antrag durchkommt, entscheidet die Tabelle oben.</p>
{_sites(data)}</div>

<div class=card><h2>Nicht bestimmbare Stellen</h2>
<p class=hint>{len(nonlit)} von {t["write_sites"]} Schreibstellen reichen den Operator aus einer
Variablen durch. Sie werden <em>nicht</em> geraten - beim Wiedereinspielen des Journals etwa steht
dort erst zur Laufzeit ein Wert. Eine Karte, die hier etwas einsetzt, waere genauer aussehend und
falscher.</p>{nonlit_rows}</div>

<div class=card><h2>Vokabular ohne Gebrauch</h2>
<p class=hint>{len(data["unused_operators"])} Operatoren existieren, werden aber an keiner Stelle
beantragt. Das ist kein Fehler - ein Vokabular darf breiter sein als sein Gebrauch. Es ist aber
eine Frage wert, denn jeder unbenutzte Operator ist eine Zusage, die niemand einloest.</p>
<div class=list>{"".join(f"<button>{_esc(o)}</button>" for o in data["unused_operators"])
                or "<span class=hint>keine</span>"}</div></div>

</div>

<footer>
<p>Erzeugt mit <code>python -m joni.epistemic_map</code>; der rohe Datensatz liegt in
<a href=flow.json>flow.json</a>. <code>--check</code> und der Test
<code>tests/test_epistemic_map.py</code> schlagen fehl, wenn die Seite nicht mehr zum Quelltext
passt.</p>
<p><b>Was diese Karte nicht ist.</b> Sie zeigt, <em>wer</em> schreiben darf und <em>was</em>
tatsaechlich gelaufen ist. Sie zeigt keinen Kontrollfluss. Die Reihenfolge oben ist gemessene
Haeufigkeit, nicht Ursache und Wirkung; welche Pruefung vor und welche nach einem Modellaufruf
liegt, laesst sich daraus <em>nicht</em> ablesen. Dafuer braeuchte es eine Ablaufverfolgung zur
Laufzeit - und dafuer muesste die Schleife laufen. Sie steht seit dem 27.07.2026.</p>
</footer>

<script>window.__FLOW__ = {payload};</script>
</body></html>
"""


__all__ = ["render"]
