"""The human-facing Layer-9 map - a *living map*, not a database dump.

A single self-contained ``docs/layer9.html`` (data embedded, vanilla JS, no build, no
backend) that lets a human see at a glance what Joni believes, what it rests on, what is
uncertain, what contradicts, what drives it, and what changed. First prototype, the five
elements the design calls for:

  1. Conversation View - what Joni appears to say;
  2. clickable provenance - any utterance decomposes into the state behind it;
  3. Claim / Evidence / Conflict graph - ordered sectors, not a chaos of nodes;
  4. a status-change timeline (the biography);
  5. a Taint & Authority influence map.

The central idea: *Joni looks like a person; Layer 9 shows the verifiable states that
impression is built from.* Colour never stands alone - every status also carries a symbol
and a word. Truth (epistemic status) and salience (how present a thing is) are shown on
separate visual channels, so a big, loud, weakly-supported thought is obvious.
"""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path

# status -> (fill, label, symbol). Colour + symbol + text, never colour alone.
_STATUS = {
    "confirmed": ("#54d6a6", "confirmed", "◉"),
    "active": ("#54d6a6", "active", "●"),
    "provisional": ("#e6c14b", "provisional", "◐"),
    "candidate": ("#e6c14b", "candidate", "○"),
    "contested": ("#e6925a", "contested", "⚠"),
    "rejected": ("#e08c8c", "rejected", "✖"),
    "quarantined": ("#e08c8c", "quarantined", "⚑"),
    "superseded": ("#7c8aa0", "superseded", "↻"),
    "expired": ("#7c8aa0", "expired", "⏳"),
}


def build(data: dict) -> str:
    payload = json.dumps({
        "export": data["export"],
        "budget": data.get("budget", {}),
        "window": data.get("window", {}),
        "generated": data["generated"],
    }, ensure_ascii=False)

    legend = "".join(
        f"<span class=lg><i style='background:{c}'></i>{sym} {esc(label)}</span>"
        for label, (c, _, sym) in _STATUS.items()
        if label in ("active", "provisional", "contested", "rejected", "superseded"))

    return _PAGE.replace("/*DATA*/", payload).replace("<!--LEGEND-->", legend)


def esc(x) -> str:
    return html.escape(str(x))


def render(path: Path, data: dict) -> None:
    data = {**data, "generated": datetime.now(UTC).isoformat(timespec="seconds")}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build(data), encoding="utf-8")


# --------------------------------------------------------------------------- #
# The page: structure + CSS + a vanilla-JS renderer over the embedded data.
# --------------------------------------------------------------------------- #
_PAGE = r"""<!doctype html>
<html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Layer 9 · Joni's epistemic map</title>
<style>
:root{--bg:#0d1016;--panel:#161b23;--line:#2a3340;--ink:#e7edf4;--mut:#93a1b2;
--acc:#6ea8fe;--good:#54d6a6;--warn:#e6c14b;--rej:#e08c8c;--cont:#e6925a;--ctrl:#6ea8fe}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14.5px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:18px 24px 6px}h1{margin:0;font-size:21px}h1 span{color:var(--acc)}
.sub{color:var(--mut);max-width:880px;margin-top:4px}
.tabs{display:flex;gap:6px;padding:10px 24px 0;flex-wrap:wrap}
.tab{padding:7px 14px;border:1px solid var(--line);border-bottom:none;border-radius:9px 9px 0 0;
background:#11151c;color:var(--mut);cursor:pointer;font-size:13px}
.tab.on{background:var(--panel);color:var(--ink);border-color:var(--acc)}
.wrap{padding:14px 24px 60px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:14px}
h2{margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--mut)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
.stat{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mut)}.stat b{color:var(--ink)}
.pill{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;border:1px solid var(--line);
color:var(--mut);margin:3px 4px 0 0}
.lg{display:inline-flex;align-items:center;gap:5px;font-size:12px;color:var(--mut);margin-right:12px}
.lg i{width:11px;height:11px;border-radius:3px;display:inline-block}
.conv{max-height:340px;overflow:auto}
.utt{padding:9px 11px;border:1px solid var(--line);border-radius:9px;margin-bottom:8px;cursor:pointer;background:#12161d}
.utt:hover{border-color:var(--acc)}.utt.on{border-color:var(--acc);background:#13202e}
.utt .meta{color:var(--mut);font-size:11px;font-family:ui-monospace,monospace;margin-top:4px}
.prov .row{display:flex;gap:8px;padding:5px 0;border-bottom:1px solid #20262f;font-size:13px}
.prov .row b{font-family:ui-monospace,monospace;color:var(--acc)}
.chip{font-size:10.5px;padding:1px 6px;border-radius:999px;border:1px solid var(--line)}
.empty{color:var(--mut)}
svg{width:100%;height:560px;background:#0f131a;border-radius:10px;display:block}
.node text{font:10px ui-monospace,monospace;fill:var(--mut)}
.tip{position:fixed;pointer-events:none;background:#0b0e13;border:1px solid var(--acc);border-radius:8px;
padding:8px 10px;font-size:12px;max-width:320px;display:none;z-index:9;box-shadow:0 4px 18px #0008}
.tip b{color:var(--acc)} .tip .k{color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
td{padding:5px 8px;border-bottom:1px solid #20262f;vertical-align:top}
.ts{color:var(--mut);font-family:ui-monospace,monospace;white-space:nowrap}
.bar{height:10px;background:#1d2430;border-radius:999px;overflow:hidden;margin:3px 0 8px}
.bar>i{display:block;height:100%}
.flag{color:var(--rej);font-weight:600}
.conflict{border-left:3px solid var(--cont);padding-left:10px;margin:8px 0}
.k-supports{color:var(--good)} .k-contradictory,.k-tension{color:var(--cont)}
.k-duplicate,.k-unrelated,.k-insufficient-semantic-evidence{color:var(--mut)}
.k-complementary{color:var(--acc)}
a.back{color:var(--acc);text-decoration:none;font-size:12px}
</style></head><body>
<header>
<h1><span>Layer 9</span> — the epistemic map</h1>
<p class=sub>Joni looks like a person. This shows the verifiable states that impression is
built from: what it believes, what that rests on, what is uncertain, what contradicts,
what drives it, and what changed. <a class=back href="index.html">&larr; dashboard</a></p>
<div><!--LEGEND--><span class=lg style=color:var(--mut)>fill = status · size = salience · border = evidence · dashed = taint</span></div>
</header>
<div class=tabs id=tabs></div>
<div class=wrap id=view></div>
<div class=tip id=tip></div>
<script>
const DATA = /*DATA*/;
const X = DATA.export;
const STATUS = {
 confirmed:["#54d6a6","confirmed","◉"], active:["#54d6a6","active","●"],
 provisional:["#e6c14b","provisional","◐"], candidate:["#e6c14b","candidate","○"],
 contested:["#e6925a","contested","⚠"], rejected:["#e08c8c","rejected","✖"],
 quarantined:["#e08c8c","quarantined","⚑"], superseded:["#7c8aa0","superseded","↻"],
 expired:["#7c8aa0","expired","⏳"]
};
const esc = s => (s==null?"":String(s)).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const stat = s => STATUS[s] || ["#7c8aa0", s||"?", "•"];
// one index of every object by id, for provenance lookups
const INDEX = {}; const TYPE = {};
function idx(list, type){ (list||[]).forEach(o=>{ INDEX[o.id]=o; TYPE[o.id]=type; }); }
idx(X.claims,"claim"); idx(X.conflicts,"conflict"); idx(X.methods,"method");
idx(X.self_model,"self-model"); idx(X.semantic_clusters,"semantic"); idx(X.preferences,"preference");
idx(X.memory,"memory"); idx(X.narratives,"narrative");
function label(o){ return o.text||o.name||o.summary||o.subject||o.decision||o.id; }

const tip = document.getElementById('tip');
function showTip(html,e){ tip.innerHTML=html; tip.style.display='block';
  tip.style.left=Math.min(e.clientX+14,innerWidth-340)+'px'; tip.style.top=(e.clientY+14)+'px'; }
function hideTip(){ tip.style.display='none'; }

const TABS = [["overview","Overview"],["graph","Epistemic graph"],["audit","Audit & timeline"]];
let active = "overview";
const tabsEl = document.getElementById('tabs');
TABS.forEach(([id,name])=>{ const b=document.createElement('div'); b.className='tab'+(id==active?' on':'');
  b.textContent=name; b.onclick=()=>{active=id; render();}; b.dataset.id=id; tabsEl.appendChild(b); });

function render(){
 [...tabsEl.children].forEach(b=>b.classList.toggle('on',b.dataset.id==active));
 const v=document.getElementById('view'); v.innerHTML='';
 v.appendChild(dualView());
 if(active=="overview") v.appendChild(overview());
 if(active=="graph") v.appendChild(graphView());
 if(active=="audit"){ v.appendChild(timelineView()); v.appendChild(taintView()); }
}

// 1 + 2 — Conversation View with clickable provenance ----------------------
function dualView(){
 const c=card("Conversation View &nbsp;·&nbsp; click an utterance to see its provenance");
 const g=document.createElement('div'); g.className='grid2';
 const left=document.createElement('div'); left.className='conv';
 const right=document.createElement('div'); right.className='prov';
 right.innerHTML="<p class=empty>Pick an utterance on the left.</p>";
 const utts=(X.narratives||[]).slice().reverse();
 if(!utts.length) left.innerHTML="<p class=empty>No utterances recorded yet.</p>";
 utts.forEach(u=>{
   const d=document.createElement('div'); d.className='utt';
   d.innerHTML="“"+esc((u.text||"").split("\n")[0].slice(0,220))+"”"+
     "<div class=meta>"+esc(u.id)+" · day "+esc(u.tick)+" · ledger "+esc(u.ledger_event||"—")+"</div>";
   d.onclick=()=>{ [...left.children].forEach(x=>x.classList.remove('on')); d.classList.add('on');
     right.innerHTML=provenance(u); };
   left.appendChild(d);
 });
 g.appendChild(left); g.appendChild(right); c.appendChild(g); return c;
}
function provenance(u){
 let h="<h2>Utterance "+esc(u.id)+"</h2><div class=row><span class=k>says</span><div>“"+
   esc(u.text)+"”</div></div>";
 h+="<div class=row><b>basis</b><div>"+(u.basis&&u.basis.length?u.basis.map(refChip).join(" "):"<span class=empty>none</span>")+"</div></div>";
 h+="<div class=row><span class=k>renderer</span><div>narrative · untrusted (language only — never writes state)</div></div>";
 h+="<div class=row><span class=k>ledger</span><div><b>"+esc(u.ledger_event||"—")+"</b></div></div>";
 // expand each basis object inline
 (u.basis||[]).forEach(id=>{ const o=INDEX[id]; if(!o) return;
   const s=stat(o.status);
   h+="<div class=row><b>"+esc(id)+"</b><div><span class=chip style='border-color:"+s[0]+";color:"+s[0]+"'>"+
     s[2]+" "+esc(o.status)+"</span> <span class=chip>"+esc(TYPE[id])+"</span> "+esc(label(o).slice(0,120))+"</div></div>"; });
 return h;
}
function refChip(id){ const o=INDEX[id]; const s=o?stat(o.status):["#7c8aa0","?","?"];
 return "<span class=chip style='border-color:"+s[0]+";color:"+s[0]+"'>"+esc(id)+"</span>"; }

// Overview -----------------------------------------------------------------
function overview(){
 const c=card("Overview");
 const C=X.counts, b=DATA.budget||{}, w=DATA.window||{};
 c.innerHTML+="<div class=stat>"+
  stcell("day", X.tick)+stcell("claims", C.claims)+stcell("evidence", C.evidence_links)+
  stcell("conflicts open", (X.conflicts||[]).filter(x=>x.conflict_status=='open'||x.conflict_status=='under_review').length)+
  stcell("methods", C.methods)+stcell("self-model", C.self_model)+stcell("memory", C.memory)+
  stcell("semantic notes", C.semantic_clusters)+stcell("ledger", C.ledger)+
  stcell("spend", "€"+(b.spent_eur!=null?b.spent_eur.toFixed(4):"0"))+"</div>";
 // conflicts prominent
 const conf=document.createElement('div'); conf.className='card';
 conf.innerHTML="<h2>Open conflicts — shown, never smoothed away</h2>";
 const open=(X.conflicts||[]).filter(x=>x.conflict_status!='resolved'&&x.conflict_status!='superseded');
 if(!open.length) conf.innerHTML+="<p class=empty>none open</p>";
 open.forEach(x=>{ conf.innerHTML+="<div class=conflict><b>"+esc(x.id)+"</b> ["+esc(x.conflict_status)+
   " · "+esc(x.severity)+"] "+x.claim_ids.map(refChip).join(" vs ")+
   (x.reason?" — "+esc(x.reason):"")+"</div>"; });
 // notable taint
 const tn=document.createElement('div'); tn.className='card';
 tn.innerHTML="<h2>Notable taint</h2>"+taintBars()+(X.tainted_authoritative.length?
   "<p class=flag>⚠ "+X.tainted_authoritative.length+" contaminated object(s) reached high authority: "+
   X.tainted_authoritative.map(esc).join(", ")+"</p>":"<p class=empty>no contaminated object holds high authority</p>");
 // recent changes
 const rc=document.createElement('div'); rc.className='card';
 rc.innerHTML="<h2>Latest changes</h2>"+ledgerTable(X.ledger.slice(-12).reverse());
 const g=document.createElement('div'); g.className='grid2'; g.appendChild(conf); g.appendChild(tn);
 const box=document.createElement('div'); box.appendChild(c); box.appendChild(g); box.appendChild(rc);
 return box;
}
function stcell(k,v){ return "<span>"+esc(k)+" <b>"+esc(v)+"</b></span>"; }

// 3 — Claim / Evidence / Conflict graph (ordered sectors) ------------------
function graphView(){
 const c=card("Epistemic graph — ordered sectors, not a chaos of nodes");
 const W=1000,H=560,cx=W/2,cy=H/2;
 const sectors=[["claim",X.claims,-90],["semantic",X.semantic_clusters,-30],
   ["method",X.methods,30],["self-model",X.self_model,90],
   ["memory",X.memory,150],["preference",X.preferences,210],["conflict",X.conflicts,270]];
 const pos={};
 let svg="<svg viewBox='0 0 "+W+" "+H+"'>";
 // sector labels + node placement
 sectors.forEach(([name,list,deg])=>{
   const a=deg*Math.PI/180;
   const lx=cx+Math.cos(a)*235, ly=cy+Math.sin(a)*235;
   svg+="<text x="+lx+" y="+ly+" text-anchor=middle style='fill:#6ea8fe;font-size:11px'>"+name.toUpperCase()+"</text>";
   (list||[]).slice(0,26).forEach((o,i)=>{
     const ring=70+ (i%6)*26, spread=(Math.floor(i/6)-1)*14 + ((i%6)-2.5)*7;
     const aa=a + spread*Math.PI/180;
     pos[o.id]=[cx+Math.cos(aa)*ring, cy+Math.sin(aa)*ring];
   });
 });
 // edges: evidence-link -> claim; conflict -> its claims; derived_from
 function edge(a,b,col,w){ if(!pos[a]||!pos[b])return"";
   return "<line x1="+pos[a][0]+" y1="+pos[a][1]+" x2="+pos[b][0]+" y2="+pos[b][1]+
     " stroke='"+col+"' stroke-width="+(w||1)+" opacity=.5 />"; }
 let edges="";
 (X.evidence_links||[]).forEach(el=>{ edges+=edge(el.claim_id, el.evidence_id||el.claim_id, "#54d6a6", 1); });
 (X.conflicts||[]).forEach(x=>{ if(x.claim_ids.length>=2) edges+=edge(x.claim_ids[0],x.claim_ids[1],"#e6925a",1.6);
   pos[x.id] && x.claim_ids.forEach(ci=>edges+=edge(x.id,ci,"#e6925a",1)); });
 (X.claims||[]).forEach(c2=>(c2.derived_from||[]).forEach(p=>edges+=edge(c2.id,p,"#6ea8fe",.8)));
 (X.semantic_clusters||[]).forEach(s=>(s.members||[]).forEach(m=>edges+=edge(s.id,m,"#7c8aa0",.7)));
 svg+=edges;
 // center
 svg+="<circle cx="+cx+" cy="+cy+" r=16 fill='#11151c' stroke='#6ea8fe' stroke-width=2 />"+
   "<text x="+cx+" y="+(cy+30)+" text-anchor=middle style='fill:#e7edf4;font-size:11px'>current state</text>";
 // nodes
 Object.keys(pos).forEach(id=>{ const o=INDEX[id]; if(!o)return; const [x,y]=pos[id];
   const s=stat(o.status), r=Math.min(16,5+(o.salience||0)*1.4),
     sw=Math.min(5,1+(o.evidence_strength||0)), dash=(o.taint&&o.taint.length)?" stroke-dasharray='3 2'":"";
   const shape = TYPE[id]=="conflict"
     ? "<rect x="+(x-r)+" y="+(y-r)+" width="+(2*r)+" height="+(2*r)+" transform='rotate(45 "+x+" "+y+")' rx=2 fill='"+s[0]+"22' stroke='"+s[0]+"' stroke-width="+sw+dash+" />"
     : "<circle cx="+x+" cy="+y+" r="+r+" fill='"+s[0]+"22' stroke='"+s[0]+"' stroke-width="+sw+dash+" />";
   svg+="<g class=node data-id='"+esc(id)+"'>"+shape+"</g>";
 });
 svg+="</svg>";
 c.innerHTML+=svg;
 // tooltips
 c.querySelectorAll('.node').forEach(g=>{ const o=INDEX[g.dataset.id];
   g.onmousemove=e=>showTip(nodeTip(o),e); g.onmouseleave=hideTip; });
 return c;
}
function nodeTip(o){ const s=stat(o.status);
 let h="<b>"+esc(o.id)+"</b> <span class=chip>"+esc(TYPE[o.id])+"</span><br>"+esc(label(o).slice(0,160))+"<br>"+
  "<span class=k>status</span> "+s[2]+" "+esc(o.status)+" · <span class=k>authority</span> "+esc(o.authority);
 if(o.support!=null) h+="<br><span class=k>support</span> "+o.support+" · <span class=k>salience</span> "+(o.salience||0);
 if(o.evidence_strength!=null) h+=" · <span class=k>evidence</span> "+o.evidence_strength;
 if(o.taint&&o.taint.length) h+="<br><span class=flag>taint: "+o.taint.map(esc).join(", ")+"</span>";
 if(o.decision) h+="<br><span class=k>semantic</span> "+esc(o.decision)+" / "+esc(o.semantic_state);
 return h;
}

// 4 — Timeline of status changes -------------------------------------------
function timelineView(){
 const c=card("Audit timeline — how the state came to be (newest first)");
 const evs=X.ledger.filter(e=>e.decision!='submitted');
 c.innerHTML+=ledgerTable(evs.slice().reverse());
 return c;
}
function ledgerTable(evs){
 if(!evs.length) return "<p class=empty>no events</p>";
 let h="<table><tr><td class=ts>day</td><td>event</td><td>operator</td><td>decision</td><td>what</td><td>hash</td></tr>";
 evs.forEach(e=>{ const dc=e.decision=='rejected'?'var(--rej)':e.decision=='accepted'?'var(--good)':'var(--mut)';
  h+="<tr><td class=ts>"+esc(e.tick)+"</td><td class=ts>"+esc(e.id)+"</td><td>"+esc(e.operator)+
   "</td><td style='color:"+dc+"'>"+esc(e.decision)+"</td><td>"+esc(e.reason||"")+
   " "+(e.output_refs||[]).map(esc).join(" ")+"</td><td class=ts>"+esc(e.event_hash||"")+"</td></tr>"; });
 return h+"</table>";
}

// 5 — Taint & Authority influence map --------------------------------------
function taintView(){
 const c=card("Taint & authority — the influence map");
 c.innerHTML+="<div class=grid2><div><h2>Contamination across objects</h2>"+taintBars()+"</div>"+
  "<div><h2>Authority distribution</h2>"+authBars()+
  (X.tainted_authoritative.length?"<p class=flag>⚠ tainted object(s) at high authority: "+
   X.tainted_authoritative.map(esc).join(", ")+"</p>":"<p class=empty>clean: nothing contaminated holds high authority</p>")+
  "</div></div>"+
  "<h2 style=margin-top:14px>A claim's path into the state</h2>"+
  "<p class=empty>user turn → analyst/source output → claim proposal → reviewer → Layer-9 decision. "+
  "Taint propagates along this path and never disappears through rephrasing.</p>";
 return c;
}
function taintBars(){ const t=X.taint_summary||{}; const max=Math.max(1,...Object.values(t));
 const rows=[["source_exposed","var(--warn)"],["interaction_exposed","var(--warn)"],
  ["affective_pressure","var(--rej)"],["adversarial_source","var(--rej)"],
  ["unverified_model_output","var(--cont)"],["human_validated","var(--good)"]];
 return rows.map(([k,col])=>{ const v=t[k]||0;
  return "<div><span class=stat>"+esc(k.replace(/_/g,' '))+" <b>"+v+"</b></span>"+
   "<div class=bar><i style='width:"+(100*v/max)+"%;background:"+col+"'></i></div></div>"; }).join("");
}
function authBars(){ const a=X.authority_summary||{}; const max=Math.max(1,...Object.values(a));
 const order=[["untrusted","var(--mut)"],["candidate","var(--warn)"],["reviewed","var(--acc)"],
  ["authoritative","var(--good)"],["control","var(--ctrl)"]];
 return order.map(([k,col])=>{ const v=a[k]||0;
  return "<div><span class=stat>"+esc(k)+" <b>"+v+"</b></span>"+
   "<div class=bar><i style='width:"+(100*v/max)+"%;background:"+col+"'></i></div></div>"; }).join("");
}

function card(title){ const d=document.createElement('div'); d.className='card';
 d.innerHTML="<h2>"+title+"</h2>"; return d; }

render();
</script>
</body></html>
"""
