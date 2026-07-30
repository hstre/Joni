"""Die Darstellung der Architekturkarte - eine einzelne, in sich geschlossene HTML-Datei.

Getrennt von ``architecture.py`` gehalten, weil die Analyse ohne den Renderer laufen koennen muss
(``--check`` in der CI) und weil eine Aenderung an der Darstellung nie eine Aenderung am Befund
sein darf. Hier wird nichts gerechnet: alles, was die Seite zeigt, kommt aus dem uebergebenen
Datensatz.

Kein Build-Schritt, keine externen Skripte, kein Backend - wie schon bei ``site.py``. Die Seite
laeuft auf GitHub Pages und auf einem iPad, und sie funktioniert auch dann noch, wenn in fuenf
Jahren niemand mehr die Werkzeugkette von heute hat.
"""
from __future__ import annotations

import html
import json

_CSS = """
:root{--bg:#0d1016;--panel:#161b23;--line:#2a3340;--ink:#e7edf4;--mut:#93a1b2;
--acc:#6ea8fe;--good:#54d6a6;--warn:#e6c14b;--rej:#e08c8c;--add:#b794f6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14.5px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:22px 22px 6px}
h1{margin:0;font-size:22px}h1 span{color:var(--acc)}
.tag{color:var(--mut);max-width:880px;margin-top:6px}
.stat{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mut);margin-top:12px}
.stat b{color:var(--ink);font-variant-numeric:tabular-nums}
.wrap{padding:14px 22px 60px;display:grid;gap:16px;
grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
@media(max-width:900px){.wrap{grid-template-columns:1fr}#detail{position:static}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;
min-width:0}
.card.full{grid-column:1/-1}
h2{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut)}
input[type=search]{width:100%;padding:9px 12px;border-radius:9px;border:1px solid var(--line);
background:#0f141b;color:var(--ink);font:inherit;margin-bottom:10px}
input[type=search]:focus{outline:none;border-color:var(--acc)}
.grp{border-top:1px solid var(--line)}
.grp:first-child{border-top:none}
.grp>button{width:100%;background:none;border:none;color:var(--ink);font:inherit;
padding:9px 2px;display:flex;gap:10px;align-items:baseline;cursor:pointer;text-align:left}
.grp>button:hover{color:var(--acc)}
.grp .n{color:var(--mut);font-size:12px;font-variant-numeric:tabular-nums;margin-left:auto;
white-space:nowrap}
.mods{display:none;padding:0 0 8px 6px}
.grp.open .mods{display:block}
.grp.open>button{color:var(--acc)}
.mod{display:block;width:100%;text-align:left;background:none;border:none;color:var(--ink);
font:inherit;padding:4px 8px;border-radius:7px;cursor:pointer;border-left:2px solid transparent}
.mod:hover{background:#1d2430}
.mod.sel{background:#1d2430;border-left-color:var(--acc)}
.mod .nm{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
.mod .fl{font-size:11px;color:var(--mut);margin-left:6px}
.note{color:var(--mut);font-size:13px;margin:2px 8px 10px;padding-left:9px;
border-left:2px solid var(--add)}
.note span,.inl-note{color:var(--add);font-size:11px;text-transform:uppercase;letter-spacing:.5px;
margin-right:5px}
.inl-note{border:1px solid var(--add);border-radius:999px;padding:1px 7px;white-space:nowrap;
margin:0}
#detail{position:sticky;top:14px;align-self:start;max-height:calc(100vh - 28px);overflow:auto}
.doc{margin:8px 0 14px;color:var(--ink)}
.doc code{background:#0f141b;border:1px solid var(--line);border-radius:5px;padding:0 4px;
font:12.5px/1.4 ui-monospace,Menlo,monospace}
.doc.none{color:var(--warn)}
.meta{color:var(--mut);font-size:12.5px;font-family:ui-monospace,Menlo,monospace;
word-break:break-all}
.dep{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 14px}
.dep button{background:#0f141b;border:1px solid var(--line);color:var(--acc);border-radius:7px;
padding:3px 8px;font:12.5px/1.4 ui-monospace,Menlo,monospace;cursor:pointer}
.dep button:hover{border-color:var(--acc)}
.dep button.ext{color:var(--mut);cursor:default}
.dep button.ext:hover{border-color:var(--line)}
.dep .empty{color:var(--mut);font-size:13px}
.pill{display:inline-block;font-size:11.5px;padding:2px 9px;border-radius:999px;
border:1px solid var(--line);color:var(--mut);margin:0 4px 4px 0}
.pill.warn{color:var(--warn);border-color:var(--warn)}
.pill.rej{color:var(--rej);border-color:var(--rej)}
.pill.good{color:var(--good);border-color:var(--good)}
.pill.acc{color:var(--acc);border-color:var(--acc)}
h3{margin:14px 0 2px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mut)}
.find{margin:0 0 16px}
.find:last-child{margin-bottom:0}
.find p,.hint{margin:4px 0 8px;color:var(--mut);max-width:760px}
.find code,.mono{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}
.list{display:flex;flex-wrap:wrap;gap:5px}
.list button{background:none;border:1px solid var(--line);color:var(--ink);border-radius:7px;
padding:2px 8px;font:12.5px/1.4 ui-monospace,Menlo,monospace;cursor:pointer}
.list button:hover{border-color:var(--acc);color:var(--acc)}
.bars{display:grid;gap:5px;margin-top:6px}
.bars>div{display:grid;grid-template-columns:minmax(0,1fr) 46px;gap:10px;align-items:center}
.bars .lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
font:12.5px/1.4 ui-monospace,Menlo,monospace}
.bars .lbl button{background:none;border:none;color:var(--ink);font:inherit;cursor:pointer;
padding:0}
.bars .lbl button:hover{color:var(--acc)}
.bars .v{text-align:right;color:var(--mut);font-variant-numeric:tabular-nums;font-size:12px}
.bar{grid-column:1/-1;height:5px;background:#1d2430;border-radius:999px;overflow:hidden;
margin-top:-3px}
.bar>i{display:block;height:100%;background:var(--acc)}
footer{padding:0 22px 40px;color:var(--mut);font-size:12.5px;max-width:880px}
footer a{color:var(--acc)}
"""

_JS = """
const D = window.__ARCH__;
const BY = Object.fromEntries(D.modules.map(m => [m.name, m]));
const esc = s => String(s).replace(/[&<>"]/g, c =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// Die Docstrings sind in reStructuredText geschrieben. Nur die Inline-Auszeichnung wird
// aufgeloest - keine Umformulierung, kein Kuerzen: es bleibt derselbe Text.
const rst = s => esc(s)
  .replace(/``([^`]+)``/g, '<code>$1</code>')
  .replace(/(^|\\s)\\*\\*([^*]+)\\*\\*/g, '$1<b>$2</b>')
  .replace(/(^|\\s)\\*([^*\\s][^*]*)\\*/g, '$1<i>$2</i>');

function flags(m){
  const f = [];
  if (D.entry_points.includes(m.name)) f.push(['acc','Einstiegspunkt']);
  if (!m.reachable) f.push(['warn','von keinem Einstieg erreichbar']);
  if (m.in_cycle) f.push(['rej','in einem Zyklus']);
  if (m.deferred.length) f.push(['','verzoegerte Importe: ' + m.deferred.length]);
  return f;
}

function btns(names, cls){
  if (!names.length) return '<div class=empty>keine</div>';
  return names.map(n => BY[n]
    ? `<button data-go="${esc(n)}">${esc(n)}</button>`
    : `<button class="ext ${cls||''}">${esc(n)}</button>`).join('');
}

function show(name){
  const m = BY[name];
  if (!m) return;
  const el = document.getElementById('detail');
  el.innerHTML = `<h2>Modul</h2>
    <div class=meta>${esc(m.path)} · ${m.loc} Zeilen · Gruppe <b>${esc(m.group)}</b></div>
    <div>${flags(m).map(([c,t]) => `<span class="pill ${c}">${esc(t)}</span>`).join('')}</div>
    <div class="doc${m.doc ? '' : ' none'}">${m.doc ? rst(m.doc)
      : 'Kein Docstring - dieses Modul erklaert sich nicht selbst.'}</div>
    <h3>haengt ab von (${m.imports.length})</h3>
    <div class=dep>${btns(m.imports)}</div>
    <h3>wird gebraucht von (${m.dependents.length})</h3>
    <div class=dep>${btns(m.dependents)}</div>
    <h3>ausserhalb (${m.external.length})</h3>
    <div class=dep>${btns(m.external, 'ext')}</div>`;
  document.querySelectorAll('.mod').forEach(b =>
    b.classList.toggle('sel', b.dataset.go === name));
  const grp = document.querySelector(`.grp[data-g="${CSS.escape(m.group)}"]`);
  if (grp) grp.classList.add('open');
  const btn = document.querySelector(`.mod[data-go="${CSS.escape(name)}"]`);
  if (btn) btn.scrollIntoView({block:'nearest'});
  if (window.matchMedia('(max-width:900px)').matches)
    el.scrollIntoView({behavior:'smooth', block:'start'});
  location.hash = name;
}

document.addEventListener('click', e => {
  const go = e.target.closest('[data-go]');
  if (go) { show(go.dataset.go); return; }
  const g = e.target.closest('.grp > button');
  if (g) g.parentElement.classList.toggle('open');
});

const GRP = Object.fromEntries(D.groups.map(g =>
  [g.name, ((g.label || '') + ' ' + (g.note || '')).toLowerCase()]));

const q = document.getElementById('q');
q.addEventListener('input', () => {
  const t = q.value.trim().toLowerCase();
  document.querySelectorAll('.grp').forEach(grp => {
    // Der deutsche Paketsatz zaehlt als Treffer fuer die ganze Gruppe - sonst faende eine
    // deutsche Suche nichts, weil fast alle Docstrings englisch sind.
    const gHit = !!t && (GRP[grp.dataset.g] || '').includes(t);
    let hits = 0;
    grp.querySelectorAll('.mod').forEach(b => {
      const m = BY[b.dataset.go];
      const hit = !t || gHit || m.name.toLowerCase().includes(t)
        || (m.doc || '').toLowerCase().includes(t)
        || m.path.toLowerCase().includes(t);
      b.style.display = hit ? '' : 'none';
      if (hit) hits++;
    });
    grp.style.display = hits ? '' : 'none';
    if (t) grp.classList.toggle('open', hits > 0);
  });
});

if (location.hash) show(decodeURIComponent(location.hash.slice(1)));
"""


def _bars(rows: list[tuple[str, int]], *, linkable: bool = True) -> str:
    """Eine kleine Balkenliste. ``rows`` ist bereits sortiert - hier wird nichts umsortiert."""
    if not rows:
        return "<div class=empty>keine</div>"
    top = max(v for _, v in rows) or 1
    out = []
    for label, value in rows:
        e = html.escape(label)
        lbl = f'<button data-go="{e}">{e}</button>' if linkable else e
        out.append(f'<div><span class=lbl>{lbl}</span><span class=v>{value}</span>'
                   f'<span class=bar><i style="width:{value / top * 100:.1f}%"></i></span></div>')
    return f'<div class=bars>{"".join(out)}</div>'


def _list(names: list[str], *, limit: int | None = None) -> str:
    if not names:
        return "<div class=empty>keine</div>"
    shown = names if limit is None else names[:limit]
    rest = "" if limit is None or len(names) <= limit else \
        f'<span class=pill>und {len(names) - limit} weitere</span>'
    return ('<div class=list>'
            + "".join(f'<button data-go="{html.escape(n)}">{html.escape(n)}</button>'
                      for n in shown)
            + rest + '</div>')


def _note(text: str | None) -> str:
    """Die deutsche Einordnung eines Pakets - sichtbar getrennt vom Befund.

    Alles andere auf der Seite ist aus dem Quelltext gelesen. Dieser eine Satz ist es nicht, und
    genau deshalb steht er hier in eigener Auszeichnung: ein Leser muss auf einen Blick sehen
    koennen, welcher Satz sich nicht selbst pruefen kann.
    """
    if not text:
        return ""
    return f'<div class=note><span>von Hand</span> {html.escape(text)}</div>'


def _groups(data: dict) -> str:
    by = {m["name"]: m for m in data["modules"]}
    out = []
    for g in data["groups"]:
        mods = sorted(g["modules"], key=lambda n: (-by[n]["fan_in"], n))
        items = []
        for n in mods:
            m = by[n]
            marks = []
            if n in data["entry_points"]:
                marks.append("start")
            if not m["reachable"]:
                marks.append("unerreicht")
            if m["in_cycle"]:
                marks.append("zyklus")
            note = f' <span class=fl>{" · ".join(marks)}</span>' if marks else ""
            items.append(f'<button class=mod data-go="{html.escape(n)}">'
                         f'<span class=nm>{html.escape(n.rpartition(".")[2] or n)}</span>'
                         f'{note}</button>')
        out.append(
            f'<div class=grp data-g="{html.escape(g["name"])}">'
            f'<button><b>{html.escape(g["label"])}</b>'
            f'<span class=n>{len(mods)} Module · {g["loc"]} Zeilen</span></button>'
            f'<div class=mods>{_note(g["note"])}{"".join(items)}</div></div>')
    return "".join(out)


def _findings(data: dict) -> str:
    by = {m["name"]: m for m in data["modules"]}
    t = data["totals"]

    cyc = "".join(
        f'<div class=find><p>{len(c)} Module: gegenseitige Abhaengigkeit.</p>{_list(c)}</div>'
        for c in data["cycles"]) or "<p>Keine.</p>"

    top_in = _bars([(m["name"], m["fan_in"])
                    for m in sorted(data["modules"], key=lambda m: -m["fan_in"])[:12]])
    top_out = _bars([(m["name"], m["fan_out"])
                     for m in sorted(data["modules"], key=lambda m: -m["fan_out"])[:12]])

    return f"""
<div class=card><h2>Wovon am meisten abhaengt</h2>
  <p class=hint>Anzahl der Module, die dieses hier importieren. Was oben steht, kostet beim
  Umbau am meisten.</p>{top_in}</div>

<div class=card><h2>Was am meisten braucht</h2>
  <p class=hint>Anzahl eigener Importe. Ein hoher Wert heisst nicht "schlecht", aber er heisst:
  dieses Modul kann ohne halb Joni nicht laufen.</p>{top_out}</div>

<div class="card full"><h2>Der eingebettete DESi-Kern</h2>
  <div class=find><p>
  <code>desi_layer9</code> ist eingebettet, nicht importiert von aussen - und mit
  {by.get("desi_layer9", {}).get("fan_in", 0)} abhaengigen Modulen die meistgebrauchte Einheit im
  ganzen Repository. {len(data["joni_on_desi"])} Module unter <code>joni</code> haengen direkt
  daran. Das ist der Umfang dessen, was ein Umbau des Kerns beruehrt - keine Schaetzung, sondern
  die gezaehlten Kanten.</p>
  {_list(data["joni_on_desi"])}</div></div>

<div class="card full"><h2>Zyklen</h2>
  <p class=hint>Module, die sich gegenseitig importieren. Sie sind einzeln nicht mehr
  herausloesbar - und die verzoegerten Importe im Funktionsrumpf sind meist die Stelle, an der
  der Zyklus umgangen statt aufgeloest wurde.</p>{cyc}</div>

<div class="card full"><h2>Von keinem Einstiegspunkt erreichbar</h2>
  <p class=hint>{len(data["unreachable"])} von {t["modules"]} Modulen. Die Einstiegspunkte sind
  aus <code>pyproject.toml</code> und den Workflows gelesen, nicht geraten. Unerreichbar heisst
  <em>nicht</em> tot: Tests und Werkzeuge stehen hier zu Recht. Es heisst: dieses Modul laeuft in
  keinem der deklarierten Ablaeufe mit. Wer etwas ausbauen will, faengt hier an zu fragen.</p>
  {_list(data["unreachable"])}</div>

<div class="card full"><h2>Einstiegspunkte</h2>
  <p class=hint>Gelesen aus <code>[project.scripts]</code> und den
  <code>python -m</code>-Aufrufen in <code>.github/workflows/</code>.</p>
  {_list(data["entry_points"])}</div>
"""


def render(data: dict) -> str:
    """Die ganze Seite. ``data`` kommt aus ``architecture.analyse`` und wird nicht veraendert."""
    t = data["totals"]
    # Die Sprachlage ist selbst ein Befund und wird gezaehlt, nicht behauptet.
    de = sum(1 for m in data["modules"] if m["doc"] and any(
        w in f' {m["doc"]} ' for w in (" der ", " die ", " das ", " und ", " nicht ")))
    docd = t["modules"] - len(data["undocumented"])
    de_note = (f"Grund: {docd - de} der {docd} vorhandenen Modul-Docstrings sind auf Englisch, "
               f"und uebersetzen hiesse, sie durch meine Worte zu ersetzen.")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Der einzige Weg, wie Inhalt hier zu Code werden koennte, ist ein Tag im Datensatz. Nur
    # ``</`` zu ersetzen reicht nicht: schon ein ``<script`` im Text bringt den Parser in einen
    # anderen Zustand. Deshalb geht jedes ``<`` als ``\\u003c`` - gueltiges JSON, gleicher Text
    # nach dem Einlesen. ``U+2028/2029`` sind in JSON erlaubt, in JavaScript aber Zeilenenden.
    for raw, safe in (("<", "\\u003c"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(raw, safe)

    return f"""<!doctype html>
<html lang=de><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Joni · Architektur</title>
<style>{_CSS}</style>
</head><body>
<header>
<h1>Joni · <span>Architektur</span></h1>
<p class=tag>Die Karte wird aus dem Quelltext gelesen, nicht beschrieben: der Abhaengigkeitsgraph
aus den <code>import</code>-Anweisungen (<code>ast</code>), der Erklaertext pro Modul ist der erste
Absatz seines eigenen Docstrings. Was hier steht, steht so im Code - und wo ein Modul sich nicht
selbst erklaert, bleibt die Stelle leer statt gefuellt.</p>
<p class=tag>Eine Ausnahme, und sie ist markiert: die deutschen Saetze zu den Paketen
(<span class=inl-note>von Hand</span>) sind meine Zuschreibung. {de_note} Wo also
Beschreibung und Bau auseinandergehen koennen, ist genau dieser eine Satz - die Modultexte
koennen es nicht.</p>
<div class=stat>
<span><b>{t["modules"]}</b> Module</span>
<span><b>{t["edges"]}</b> Abhaengigkeiten</span>
<span><b>{t["loc"]}</b> Zeilen</span>
<span><b>{t["groups"]}</b> Gruppen</span>
<span><b>{len(data["cycles"])}</b> Zyklen</span>
<span><b>{len(data["unreachable"])}</b> nicht erreichbar</span>
<span><b>{len(data["undocumented"])}</b> ohne Docstring</span>
</div>
</header>

<div class=wrap>
<div class=card>
<h2>Module</h2>
<input type=search id=q placeholder="suchen - Name oder Erklaertext" autocomplete=off>
{_groups(data)}
</div>

<div class=card id=detail>
<h2>Modul</h2>
<p class=tag>Eine Gruppe aufklappen, ein Modul waehlen. Hier stehen dann sein Erklaertext,
wovon es abhaengt und wer es braucht - beides anklickbar.</p>
</div>

{_findings(data)}
</div>

<footer>
<p>Erzeugt mit <code>python -m joni.architecture</code>. Die Seite wird nach jedem Umbau neu
gebaut; <code>--check</code> in der CI faellt durch, wenn sie nicht mehr zum Quelltext passt.
Der rohe Datensatz liegt daneben in <a href=architecture.json>architecture.json</a>.</p>
<p>Was die Karte <em>nicht</em> weiss: ob ein Import auch benutzt wird, und was ueber
Zeichenketten oder <code>importlib</code> nachgeladen wird. Sie zeigt deklarierte Abhaengigkeiten,
nicht ausgefuehrte.</p>
<p>Die fruehere Statusseite der Autonomie-Schleife steht unveraendert unter
<a href=status.html>status.html</a> - stehengeblieben am 27.07.2026, als die Schleife
angehalten wurde.</p>
</footer>

<script>window.__ARCH__ = {payload};</script>
<script>{_JS}</script>
</body></html>
"""


__all__ = ["render"]
