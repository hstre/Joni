"""Was Joni ist, aus dem Quelltext gelesen - nicht aus der Erinnerung erzaehlt.

Diese Datei baut die oeffentliche Seite ``docs/index.html``: eine Karte aller Module und ihrer
tatsaechlichen Abhaengigkeiten. Der Punkt ist die Herkunft der Angaben. Der Abhaengigkeitsgraph
wird mit ``ast`` aus den ``import``-Anweisungen gelesen, der Erklaertext ist der erste Absatz des
Modul-Docstrings. Nichts davon ist hier von Hand eingetragen.

Das ist kein Stilfrage, sondern der Zweck: eine handgeschriebene Architekturseite beschreibt, was
der Autor zu bauen glaubte. Diese hier beschreibt, was dasteht. Wenn beides auseinanderlaeuft,
soll die Seite die Seite des Quelltexts nehmen - dann wird der Unterschied sichtbar, statt sich
in einer wohlwollenden Beschreibung zu verstecken.

Grenzen, damit die Karte nicht mehr behauptet, als sie weiss:

* ``import`` ist nicht Benutzung. Ein Modul kann importiert und nie aufgerufen werden.
* Verzoegerte Importe in Funktionsrumpfen werden mitgezaehlt (sie sind echte Abhaengigkeiten),
  ``importlib``-Aufrufe und Zeichenketten-Nachschlagen nicht - die sieht ``ast`` nicht.
* Ein leerer Docstring erzeugt keinen erfundenen Text, sondern einen sichtbaren Vermerk.

Aufruf::

    python -m joni.architecture            # schreibt docs/index.html und docs/architecture.json
    python -m joni.architecture --check    # nur pruefen, ob die Seite zum Quelltext passt
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: Wurzelpakete, die als "eigen" gelten. Alles andere ist eine externe Abhaengigkeit und wird
#: gezaehlt, aber nicht als Knoten gefuehrt.
OWN_ROOTS = ("joni", "desi_layer9")

#: Einstiegspunkte, die nirgends deklariert sind: ``__main__``-Module sind per Konvention
#: aufrufbar. Alle uebrigen werden gelesen, nicht geraten - siehe ``entry_points()``.
_CONVENTIONAL_ENTRIES = ("joni.__main__", "joni.autonomy.__main__", "joni.relay.__main__")


def entry_points(repo: Path, known: set[str]) -> list[str]:
    """Die Einstiegspunkte aus ``pyproject.toml`` und den Workflows lesen, nicht raten.

    Erreichbarkeit ist nur so gut wie die Liste der Startpunkte. Eine handgepflegte Liste haette
    genau den Fehler, den diese Seite vermeiden soll: Sie beschreibt, was ich fuer den Einstieg
    halte, nicht was tatsaechlich gestartet wird. ``joni-layer9-convert`` etwa steht in
    ``pyproject.toml`` und waere mir nicht eingefallen.
    """
    found: set[str] = {e for e in _CONVENTIONAL_ENTRIES if e in known}

    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        in_scripts = False
        for line in pyproject.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("["):
                in_scripts = s == "[project.scripts]"
            elif in_scripts and "=" in s:
                target = s.split("=", 1)[1].strip().strip('"').split(":")[0]
                if target in known:
                    found.add(target)

    wf = repo / ".github" / "workflows"
    if wf.exists():
        import re
        for f in sorted(wf.glob("*.y*ml")):
            for hit in re.findall(r"python3?\s+-m\s+([A-Za-z0-9_.]+)",
                                  f.read_text(encoding="utf-8")):
                if hit in known:
                    found.add(hit)
    return sorted(found)

#: Beschriftung und Einordnung der Pakete - **von Hand geschrieben**, im Gegensatz zu allem
#: anderen auf der Seite.
#:
#: Die Modultexte sind woertlich die Docstrings aus dem Quelltext; sie koennen deshalb nicht
#: davon abweichen, was dasteht. Nur: 206 von 215 sind auf Englisch. Fuer eine Seite, deren
#: Zweck das schnelle Erkennen von Missverstaendnissen ist, waere das eine Huerde. Deshalb hier
#: je Paket ein deutscher Satz zur Orientierung - und auf der Seite sichtbar als *meine*
#: Zuschreibung markiert, nicht als Befund. Ein Paket, das hier fehlt, bekommt keinen erfundenen
#: Satz, sondern keinen.
GROUPS = {
    "joni": ("Kern",
             "Zustand, Operatoren, Gedaechtnis, Persistenz. Der Teil, der ohne die Schleife und "
             "ohne Modellaufrufe laeuft - und der einzige, den die Grundlagenpflicht (basis) "
             "bereits durchzieht."),
    "joni.autonomy": ("Autonomie-Schleife",
                      "Der stuendliche Lauf: lesen, urteilen lassen, protokollieren, Seite neu "
                      "bauen. Mit 72 Modulen der mit Abstand groesste Block - und derjenige, in "
                      "dem die meisten DESi-Annahmen stecken."),
    "joni.autonomy.metacognition": ("Metakognition",
                                    "Schleifen ueber die Schleife: Aufsicht, Gates, Kennzahlen."),
    "joni.autonomy.verifier": ("Verifizierer", "Bewertung und Eskalation einzelner Vorgaenge."),
    "joni.autonomy.rule_artifacts": ("Regel-Artefakte", None),
    "joni.layer9_v2": ("layer9_v2 (das Modul, nicht das Papier)",
                       "Wichtig zur Vermeidung genau der Verwechslung, die diese Seite mit "
                       "auffangen soll: Dieses Paket ist nicht die Umsetzung des Papiers "
                       "*Layer 9*. Es traegt nur denselben Namen."),
    "joni.layer9_v2.adapters": ("layer9_v2 · Adapter", None),
    "joni.layer9_v2.checks": ("layer9_v2 · Pruefungen", None),
    "joni.layer9_v2.graph": ("layer9_v2 · Graph", None),
    "joni.layer9_v2.journal": ("layer9_v2 · Journal", None),
    "joni.layer9_v2.runtime": ("layer9_v2 · Laufzeit", None),
    "joni.layer9_v2.spaces": ("layer9_v2 · Raeume", None),
    "joni.layer9_v2.storage": ("layer9_v2 · Ablage", None),
    "joni.method_trial": ("Methoden-Erprobung",
                          "Der Apparat, der Methoden an Gold-Aufgaben misst, statt sie zu "
                          "glauben. Hier haengt ``motivated_by`` an - noch unbefuellt."),
    "joni.solution_space": ("Loesungsraum",
                            "Kartierung und Navigation moeglicher Zuege."),
    "joni.relay": ("Relay", "Weiterleitung nach aussen."),
    "joni.constitution": ("Konstitution", "Das Tor, durch das Aenderungen am Kern muessen."),
    "joni.personal": ("Persoenliches", "Getrennte Ablage fuer persoenliche Eingaben."),
    "desi_layer9": ("DESi-Kern (eingebettet)",
                    "Der eingebettete Kern aus DESi - Objekte, Regeln, Provenienz, Snapshot. "
                    "Die meistgebrauchte Einheit im ganzen Repository, und damit die teuerste "
                    "Stelle fuer jeden Umbau."),
    "desi_layer9.semantics": ("DESi-Kern · Semantik",
                              "Der Teil des Kerns, der Bedeutung zuschreibt - also genau der, "
                              "gegen den die Messungen ausfielen."),
}

#: Nur die Namen, fuer den Renderer.
GROUP_LABELS = {k: v[0] for k, v in GROUPS.items()}


@dataclass
class Module:
    """Ein Modul, wie es im Quelltext steht."""

    name: str
    path: str
    group: str
    doc: str
    loc: int
    imports: set[str] = field(default_factory=set)
    external: set[str] = field(default_factory=set)
    #: Importe, die erst im Funktionsrumpf stehen - oft ein Zeichen fuer einen Zyklus, der
    #: umgangen statt aufgeloest wurde.
    deferred: set[str] = field(default_factory=set)


def _first_paragraph(doc: str | None) -> str:
    """Der erste Absatz des Docstrings - das ist der Erklaertext, mehr wird nicht erfunden."""
    if not doc or not doc.strip():
        return ""
    para: list[str] = []
    for line in doc.strip().splitlines():
        if not line.strip():
            break
        para.append(line.strip())
    return " ".join(para)


def _module_name(path: Path, src: Path) -> str:
    rel = path.relative_to(src).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve(node: ast.ImportFrom, owner: str) -> str | None:
    """Einen relativen Import auf den absoluten Modulnamen zurueckrechnen."""
    if not node.level:
        return node.module
    base = owner.split(".")
    # Ein Paket-``__init__`` ist selbst schon die Ebene, ein Modul liegt eine darunter.
    up = node.level - 1
    base = base[: len(base) - up - 1] if up >= 0 else base
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base) if base else None


def _is_own(name: str) -> bool:
    return name.split(".")[0] in OWN_ROOTS


def scan(src: Path) -> dict[str, Module]:
    """Alle Module unter ``src`` einlesen und den Importgraphen aufbauen."""
    mods: dict[str, Module] = {}
    files = sorted(p for p in src.rglob("*.py"))
    known = {_module_name(p, src) for p in files}

    def _nearest(target: str) -> str | None:
        """Ein Import zeigt oft auf ein Symbol, nicht auf ein Modul - dann das Paket nehmen."""
        while target:
            if target in known:
                return target
            target = target.rpartition(".")[0]
        return None

    for path in files:
        name = _module_name(path, src)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        mod = Module(
            name=name,
            path=str(path.relative_to(src.parent)),
            group=name.rpartition(".")[0] if "." in name else name,
            doc=_first_paragraph(ast.get_docstring(tree)),
            loc=sum(1 for line in text.splitlines() if line.strip()),
        )
        # Ein Paket-``__init__`` gehoert in seine eigene Gruppe, nicht in die des Elternteils.
        if path.name == "__init__.py":
            mod.group = name

        # Importe im Modulrumpf gelten als direkt, alles tiefer als verzoegert.
        toplevel = {id(n) for n in ast.iter_child_nodes(tree)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = _resolve(node, name)
                if base is None:
                    continue
                targets = [f"{base}.{a.name}" for a in node.names] or [base]
                if not _is_own(base):
                    targets = [base]
            else:
                continue
            for t in targets:
                if not _is_own(t):
                    mod.external.add(t.split(".")[0])
                    continue
                hit = _nearest(t)
                if hit and hit != name:
                    mod.imports.add(hit)
                    if id(node) not in toplevel:
                        mod.deferred.add(hit)
        mods[name] = mod
    return mods


def dependents(mods: dict[str, Module]) -> dict[str, set[str]]:
    """Die Umkehrung: wer haengt an mir? Die Frage, die beim Ausbauen zaehlt."""
    back: dict[str, set[str]] = {n: set() for n in mods}
    for name, m in mods.items():
        for dep in m.imports:
            back.setdefault(dep, set()).add(name)
    return back


def cycles(mods: dict[str, Module]) -> list[list[str]]:
    """Zyklen als starke Zusammenhangskomponenten (Tarjan, iterativ)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on: set[str] = set()
    out: list[list[str]] = []
    counter = 0

    for root in sorted(mods):
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, pi = work[-1]
            if pi == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on.add(node)
            kids = sorted(mods[node].imports & mods.keys())
            if pi < len(kids):
                work[-1] = (node, pi + 1)
                nxt = kids[pi]
                if nxt not in index:
                    work.append((nxt, 0))
                elif nxt in on:
                    low[node] = min(low[node], index[nxt])
            else:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        w = stack.pop()
                        on.discard(w)
                        comp.append(w)
                        if w == node:
                            break
                    if len(comp) > 1:
                        out.append(sorted(comp))
    return sorted(out, key=lambda c: (-len(c), c[0]))


def reachable(mods: dict[str, Module], entries: list[str]) -> set[str]:
    """Was von den Einstiegspunkten aus erreichbar ist."""
    seen: set[str] = set()
    todo = [e for e in entries if e in mods]
    while todo:
        cur = todo.pop()
        if cur in seen:
            continue
        seen.add(cur)
        todo.extend(mods[cur].imports & mods.keys())
    return seen


def analyse(src: Path, repo: Path | None = None) -> dict:
    """Der ganze Befund als reine Daten - das ist, was die Seite anzeigt."""
    mods = scan(src)
    back = dependents(mods)
    entries = entry_points(repo or src.parent, set(mods))
    reach = reachable(mods, entries)
    cyc = cycles(mods)
    in_cycle = {n for c in cyc for n in c}

    #: Wer aus Joni heraus am eingebetteten DESi-Kern haengt. Die Frage fuer den Umbau.
    on_desi = sorted(
        n for n, m in mods.items()
        if n.startswith("joni") and any(d.startswith("desi_layer9") for d in m.imports)
    )

    nodes = []
    for name in sorted(mods):
        m = mods[name]
        nodes.append({
            "name": name,
            "path": m.path,
            "group": m.group,
            "doc": m.doc,
            "loc": m.loc,
            "imports": sorted(m.imports),
            "deferred": sorted(m.deferred),
            "external": sorted(m.external),
            "dependents": sorted(back.get(name, ())),
            "fan_in": len(back.get(name, ())),
            "fan_out": len(m.imports),
            "reachable": name in reach,
            "in_cycle": name in in_cycle,
        })

    groups: dict[str, dict] = {}
    for n in nodes:
        label, note = GROUPS.get(n["group"], (n["group"], None))
        g = groups.setdefault(n["group"], {
            "name": n["group"], "label": label,
            # Von Hand geschrieben - auf der Seite als solches ausgewiesen.
            "note": note, "modules": [], "loc": 0,
        })
        g["modules"].append(n["name"])
        g["loc"] += n["loc"]

    edges: dict[tuple[str, str], int] = {}
    by_name = {n["name"]: n for n in nodes}
    for n in nodes:
        for dep in n["imports"]:
            a, b = n["group"], by_name[dep]["group"]
            if a != b:
                edges[(a, b)] = edges.get((a, b), 0) + 1

    return {
        "generated_from": "ast",
        "modules": nodes,
        "groups": sorted(groups.values(), key=lambda g: (-len(g["modules"]), g["name"])),
        "group_edges": [{"from": a, "to": b, "weight": w}
                        for (a, b), w in sorted(edges.items(), key=lambda kv: -kv[1])],
        "cycles": cyc,
        "entry_points": entries,
        "unreachable": sorted(n["name"] for n in nodes if not n["reachable"]),
        "undocumented": sorted(n["name"] for n in nodes if not n["doc"]),
        "joni_on_desi": on_desi,
        "totals": {
            "modules": len(nodes),
            "edges": sum(len(n["imports"]) for n in nodes),
            "loc": sum(n["loc"] for n in nodes),
            "groups": len(groups),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=None, help="Quellverzeichnis (Vorgabe: src/ im Repo)")
    ap.add_argument("--docs", default=None, help="Ausgabeverzeichnis (Vorgabe: docs/)")
    ap.add_argument("--check", action="store_true",
                    help="nur pruefen, ob die Seite noch zum Quelltext passt")
    args = ap.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    src = Path(args.src) if args.src else repo / "src"
    docs = Path(args.docs) if args.docs else repo / "docs"

    data = analyse(src, repo)
    from joni.architecture_page import render  # lokal, damit --check ohne Renderer laeuft

    payload = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    if args.check:
        old = (docs / "architecture.json")
        if not old.exists():
            print("architecture.json fehlt - die Seite wurde nie gebaut.")
            return 1
        if old.read_text(encoding="utf-8") != payload:
            print("Die Seite passt nicht mehr zum Quelltext. "
                  "Neu bauen mit: python -m joni.architecture")
            return 1
        print(f"Seite aktuell: {data['totals']['modules']} Module, "
              f"{data['totals']['edges']} Kanten.")
        return 0

    docs.mkdir(parents=True, exist_ok=True)
    (docs / "architecture.json").write_text(payload, encoding="utf-8")
    (docs / "index.html").write_text(render(data), encoding="utf-8")
    t = data["totals"]
    print(f"docs/index.html: {t['modules']} Module, {t['edges']} Kanten, "
          f"{t['groups']} Gruppen, {len(data['cycles'])} Zyklen, "
          f"{len(data['unreachable'])} nicht erreichbar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
