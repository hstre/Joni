"""Wer darf was - die zweite Sicht, ebenfalls abgeleitet statt beschrieben.

Die Architekturkarte (``joni.architecture``) beantwortet: *welches Modul haengt technisch an
welchem?* Sie beantwortet nicht: *wer darf einen Claim erzeugen, wer seinen Status aendern, wann
faellt ein Modellaufruf, was darf den geschuetzten Kern anfassen?* Das sind die Fragen, an denen
sich Missverstaendnisse festmachen - und sie sind aus einem Importgraphen nicht zu lesen.

Der Punkt bleibt derselbe wie bei der ersten Sicht: Eine von Hand aufgeschriebene Ablaufkarte
waere genau die Prosabeschreibung, die wir gerade abgeschafft haben - nur mit mehr Autoritaet,
weil sie neben einer gemessenen Karte steht. Deshalb kommt hier alles aus vier Quellen, die sich
nachrechnen lassen:

1. **Die Erlaubnistabelle** wird nicht gelesen, sondern *ausgerechnet*: ``policy.may_request``
   ist eine reine Funktion ueber zwei Aufzaehlungen, also wird sie fuer jedes Paar aufgerufen.
   Was hier steht, ist das Verhalten des laufenden Codes, nicht meine Zusammenfassung davon.
2. **Die Schreibstellen** kommen per ``ast`` aus den Aufrufen von ``make_proposal`` und dem
   Kuerzel ``_op``: welches Modul beantragt welchen Operator unter welchem Antragsteller.
3. **Das eine Tor**: welche Methoden des Kerns ueberhaupt schreiben, ermittelt aus Zuweisungen
   an den Objektspeicher und das Journal.
4. **Der beobachtete Zyklus** kommt aus ``protocol/protocol.jsonl`` - 54.791 tatsaechlich
   gelaufene Ereignisse, nicht ein gedachter Ablauf.

Was diese Karte **nicht** kann, und was auf der Seite auch so steht: Sie zeigt, *wer* schreiben
darf und *was* tatsaechlich gelaufen ist. Sie zeigt keinen echten Kontrollfluss. Die Reihenfolge
der Torpruefungen ist die syntaktische Reihenfolge im Quelltext, die Reihenfolge der Ereignisse
die gemessene Haeufigkeit ihrer ersten Position im Zyklus. Beides ist schwaecher als eine
Ablaufverfolgung zur Laufzeit - dafuer muesste die Schleife laufen, und sie steht.

Aufruf::

    python -m joni.epistemic_map          # schreibt docs/flow.html und docs/flow.json
    python -m joni.epistemic_map --check  # nur pruefen, ob die Seite zum Quelltext passt
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

#: Der einzige schreibende Eingang des Kerns. Alles andere liest.
WRITE_GATE = "submit"

#: Kurze deutsche Einordnung je Operator - **von Hand**, wie bei den Paketen der ersten Sicht,
#: und auf der Seite genauso markiert. Ein Operator ohne Eintrag bekommt keinen erfundenen Satz.
OPERATOR_NOTES = {
    "claim_create": "Eine Behauptung entsteht. Sie ist damit noch nicht guelt ig, nur vorhanden.",
    "claim_revise": "Der Status einer Behauptung aendert sich - der eigentliche Streitpunkt.",
    "claim_confirm": "Eine Behauptung wird bestaetigt. Autoritativ, deshalb fuer Modelle gesperrt.",
    "claim_reject": "Eine Behauptung wird verworfen. Ebenfalls autoritativ.",
    "conflict_resolve": "Ein Widerspruch wird entschieden. Nie durch ein Modell.",
    "method_promote": "Eine Methode wird verbindlich. Der teuerste Schritt, deshalb gesperrt.",
    "evidence_attach": "Belege werden angehaengt - additiv, kein Urteil.",
    "memory_record": "Eine Episode wird ins Gedaechtnis geschrieben.",
}


def permission_matrix() -> dict:
    """Die Erlaubnistabelle, ausgerechnet statt gelesen.

    ``may_request`` ist eine reine Funktion ueber (Herkunft, Operator). Statt ihre 44 Zeilen zu
    interpretieren, wird sie fuer jedes Paar aufgerufen. Wenn jemand die Regel aendert, aendert
    sich diese Tabelle beim naechsten Bau - ohne dass hier etwas nachgezogen werden muss.
    """
    from desi_layer9 import policy
    from desi_layer9.enums import Operator, OriginType

    origins = [o.value for o in OriginType]
    operators = [o.value for o in Operator]
    allowed: dict[str, list[str]] = {}
    for o in OriginType:
        allowed[o.value] = [op.value for op in Operator if policy.may_request(o, op)]

    return {
        "origins": origins,
        "operators": operators,
        "allowed": allowed,
        "authoritative": sorted(o.value for o in policy.AUTHORITATIVE_OPERATORS),
        "control": sorted(o.value for o in policy.CONTROL_OPERATORS),
        # Operatoren, die KEINE Herkunft beantragen darf, waeren toter Buchstabe - und
        # Operatoren, die JEDE darf, sind unbeschraenkt. Beides ist eine Aussage.
        "denied_to_all": sorted(
            op.value for op in Operator
            if not any(policy.may_request(o, op) for o in OriginType)),
        "open_to_all": sorted(
            op.value for op in Operator
            if all(policy.may_request(o, op) for o in OriginType)),
        # Welche Herkunft darf autoritativ handeln? Die Regel sperrt ausdruecklich die
        # *erzeugenden* Herkuenfte. Wer weder erzeugend noch ausdruecklich vertrauenswuerdig
        # ist, faellt durch diese Unterscheidung hindurch - und das faellt nur auf, wenn man
        # es ausrechnet statt die 44 Zeilen zu lesen.
        "authoritative_by_origin": {
            o.value: sorted(op.value for op in policy.AUTHORITATIVE_OPERATORS
                            if policy.may_request(o, op))
            for o in OriginType
        },
        "trusted_by_default": sorted(
            o.value for o in OriginType
            if o.value not in ("human", "deterministic_operator")
            and any(policy.may_request(o, op) for op in policy.AUTHORITATIVE_OPERATORS)),
    }


def _operator(node: ast.AST) -> str | None:
    """Nur ein echtes ``Operator.X`` zaehlt als bestimmt.

    ``entry.operator`` sieht syntaktisch genauso aus wie ``Operator.CLAIM_CREATE``, ist aber
    eine Variable - beim Wiedereinspielen des Journals steht dort erst zur Laufzeit ein Wert.
    Wer das nicht trennt, bekommt einen erfundenen Operator namens "entry.operator" in die
    Auswertung. Deshalb: Praefix pruefen, sonst unbestimmt.
    """
    if isinstance(node, ast.Attribute) and getattr(node.value, "id", None) == "Operator":
        return node.attr.lower()
    return None


def _string(node: ast.AST) -> str | None:
    """Eine literale Zeichenkette - ein aus einer Variablen gereichter Wert wird nicht geraten."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def write_sites(src: Path) -> list[dict]:
    """Wo im Quelltext ein Schreibvorgang beantragt wird, und mit welchem Operator.

    Erfasst werden ``make_proposal(ptype, operator, ...)`` und das Kuerzel ``_op(ptype, operator,
    ...)`` aus ``core_state``. Beide tragen den Operator an zweiter Stelle.
    """
    out: list[dict] = []
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        # Die umschliessende Funktion je Knoten - fuer die Angabe, WER schreibt.
        owner: dict[int, str] = {}
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                for n in ast.walk(fn):
                    owner.setdefault(id(n), fn.name)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            name = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if name not in ("make_proposal", "_op"):
                continue
            kw = {k.arg: _string(k.value) for k in n.keywords}
            out.append({
                "module": str(path.relative_to(src.parent)),
                "line": n.lineno,
                "function": owner.get(id(n), "<modulebene>"),
                "helper": name,
                "operator": _operator(n.args[1]) if len(n.args) > 1 else None,
                "proposer": kw.get("proposer"),
            })
    return out


def core_writers(src: Path) -> dict:
    """Welche Methoden des Kerns tatsaechlich schreiben - die Grundlage der Tor-Behauptung.

    Gesucht werden Zuweisungen an ``self._objects`` und Anhaenge an ``self._journal``. Wenn
    ausser ``submit`` etwas schreibt, ist die Behauptung "ein einziger Eingang" falsch, und das
    soll die Seite dann auch zeigen - nicht ich beim naechsten Mal wieder behaupten.
    """
    core = src / "desi_layer9" / "core.py"
    if not core.exists():
        return {"writers": [], "gate": WRITE_GATE, "single_gate": False}
    tree = ast.parse(core.read_text(encoding="utf-8"), filename=str(core))
    writers: set[str] = set()
    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef):
            continue
        for fn in cls.body:
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for n in ast.walk(fn):
                tgt = None
                if isinstance(n, ast.Assign):
                    tgt = n.targets[0]
                elif isinstance(n, ast.AugAssign | ast.AnnAssign):
                    tgt = n.target
                elif isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "append":
                    tgt = n.func.value
                base = tgt
                while isinstance(base, ast.Subscript | ast.Attribute):
                    if isinstance(base, ast.Attribute) and base.attr in ("_objects", "_journal"):
                        writers.add(fn.name)
                        break
                    base = base.value if isinstance(base, ast.Attribute) else base.value
    public = sorted(w for w in writers if not w.startswith("_"))
    return {"writers": sorted(writers), "public_writers": public, "gate": WRITE_GATE,
            "single_gate": public == [WRITE_GATE]}


def observed_cycle(protocol: Path, *, min_cycles: int = 20) -> dict:
    """Der tatsaechlich gelaufene Zyklus, aus dem append-only Protokoll.

    Fuer jede Ereignisart wird festgehalten, in wie vielen Zyklen sie ueberhaupt vorkam und an
    welcher relativen Stelle sie dort *zuerst* auftrat. Der Mittelwert dieser Stelle ergibt eine
    beobachtete Reihenfolge - keine gedachte. Arten unter ``min_cycles`` Zyklen bleiben drin,
    werden aber mit ihrer Zyklenzahl gezeigt, damit Seltenes nicht wie Regel aussieht.
    """
    if not protocol.exists():
        return {"events": [], "cycles": 0, "total": 0, "models": []}

    per_cycle: dict[int, list[str]] = defaultdict(list)
    models: Counter = Counter()
    cost: Counter = Counter()
    kind_model: dict[str, Counter] = defaultdict(Counter)
    total = 0
    with protocol.open(encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except (ValueError, TypeError):
                continue
            total += 1
            per_cycle[e.get("cycle")].append(e.get("kind"))
            m = e.get("model") or "-"
            models[m] += 1
            cost[m] += e.get("cost_eur") or 0.0
            kind_model[e.get("kind")][m] += 1

    positions: dict[str, list[float]] = defaultdict(list)
    counts: Counter = Counter()
    for kinds in per_cycle.values():
        seen: dict[str, float] = {}
        span = max(1, len(kinds) - 1)
        for i, k in enumerate(kinds):
            seen.setdefault(k, i / span)
            counts[k] += 1
        for k, v in seen.items():
            positions[k].append(v)

    events = []
    for k, v in positions.items():
        mm = kind_model[k]
        det = mm.get("deterministic", 0)
        events.append({
            "kind": k,
            "position": round(sum(v) / len(v), 3),
            "in_cycles": len(v),
            "events": counts[k],
            "deterministic": det,
            "model_backed": sum(mm.values()) - det,
            "models": sorted(m for m in mm if m != "deterministic"),
        })
    events.sort(key=lambda e: (e["position"], -e["in_cycles"]))

    return {
        "events": events,
        "cycles": len(per_cycle),
        "total": total,
        "models": [{"name": m, "events": n, "cost_eur": round(cost[m], 4)}
                   for m, n in models.most_common()],
    }


def analyse(src: Path, repo: Path) -> dict:
    sites = write_sites(src)
    by_op: dict[str, list[dict]] = defaultdict(list)
    for s in sites:
        by_op[s["operator"] or "<nicht literal>"].append(s)

    perm = permission_matrix()
    gate = core_writers(src)
    cyc = observed_cycle(repo / "protocol" / "protocol.jsonl")

    try:
        from joni.autonomy import governance
        protected = sorted(getattr(governance, "PROTECTED_CORE", ()) or ())
    except Exception:  # noqa: BLE001 - die Karte muss auch ohne die Schleife bauen
        protected = []

    # Operatoren, die es gibt, die aber an keiner Stelle beantragt werden. Das ist kein Fehler -
    # ein Vokabular darf breiter sein als sein Gebrauch. Es ist aber eine Frage wert, denn jeder
    # unbenutzte Operator ist eine Zusage, die niemand einloest.
    used = {k for k in by_op if k != "<nicht literal>"}
    unused = sorted(set(perm["operators"]) - used)

    return {
        "permissions": perm,
        "write_sites": sites,
        "unused_operators": unused,
        "by_operator": {k: sorted(v, key=lambda s: (s["module"], s["line"]))
                        for k, v in sorted(by_op.items())},
        "gate": gate,
        "cycle": cyc,
        "protected_core": protected,
        "operator_notes": OPERATOR_NOTES,
        "totals": {
            "write_sites": len(sites),
            "non_literal": sum(1 for s in sites if not s["operator"]),
            "operators_used": len([k for k in by_op if not k.startswith("<")]),
            "operators_total": len(perm["operators"]),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Die epistemische Karte: wer darf was.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    src, docs = repo / "src", repo / "docs"
    data = analyse(src, repo)
    payload = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)

    if args.check:
        old = docs / "flow.json"
        if not old.exists() or old.read_text(encoding="utf-8") != payload:
            print("Die epistemische Karte ist nicht mehr aktuell. "
                  "Neu bauen: python -m joni.epistemic_map")
            return 1
        print("Karte aktuell.")
        return 0

    from joni.epistemic_page import render
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "flow.json").write_text(payload, encoding="utf-8")
    (docs / "flow.html").write_text(render(data), encoding="utf-8")
    t = data["totals"]
    print(f"docs/flow.html: {t['write_sites']} Schreibstellen "
          f"({t['non_literal']} nicht literal), {t['operators_used']}/{t['operators_total']} "
          f"Operatoren benutzt, {data['cycle']['cycles']} beobachtete Zyklen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
