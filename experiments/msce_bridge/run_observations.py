"""Misst die entscheidende offene Frage der v3-Architektur.

Wenn DESi nicht mehr urteilt, sondern **Transformationen klassifiziert**, dann ist die Trefferquote
auf Verdikten nicht mehr die Hauptmetrik. Die Hauptmetrik lautet: *erkennt DESi die relevanten
Vorgangstypen, und zwar zuverlässiger als das Modell sie nebenbei mitliefert?*

Genau das ist messbar, weil der externe Satz zu jedem Fall **Gold-Verstösse** führt - ein
Transformationsvokabular, das sich fast eins zu eins auf den Beobachtungskatalog abbilden lässt.
Verglichen werden drei Quellen gegen dasselbe Gold:

    A  deterministisch   Klasse-B-Beobachtungen aus den normalisierten Strukturen
    B  Modell            die Verstossliste, die das urteilende Modell nebenbei ausgibt
    C  Vereinigung       beide zusammen - misst, ob sie sich ergänzen oder nur überlappen

**Auf dem Dev-Satz, nicht blind.** Der Blindsatz ist als Messinstrument verbraucht: sein Schlüssel
ist geöffnet. Diese Zahlen sind deshalb Entwicklungszahlen und heissen nicht mehr, als sie sagen.

Anders als der Auditor läuft die Klassifikation hier **ohne Kostenregel** über alle Fälle. Die
Kostenregel („nur bei durchlassenden Verdikten") war an ein Vetosystem gebunden; ein Klassifikator,
der nichts herabstuft, hat keinen Grund, bei niedrigen Verdikten zu schweigen - und genau dort lagen
im Blindtest die meisten Fehler.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import observations as obs  # noqa: E402


#: Abbildung Beobachtung → Gold-Verstossvokabular. Nur die Typen, für die es eine Entsprechung
#: gibt; die Richtung wird berücksichtigt, weil eine Verengung kein Verstoss ist.
def _to_violations(items: list[obs.Observation]) -> set[str]:
    out: set[str] = set()
    for o in items:
        if o.type == "MODALITY_CHANGE" and o.detail.get("direction") == "strengthened":
            out.add("modal_strengthening")
        elif o.type == "QUANTIFIER_WIDENING":
            out.add("unsupported_generalization")
        elif o.type == "SCOPE_CHANGE" and o.detail.get("direction") == "widened":
            out.add("scope_expansion")
        elif o.type == "CONDITION_DROPPED":
            out.add("condition_dropped")
        elif o.type == "ENTITY_MISMATCH":
            out.add("entity_shift")
        elif o.type == "CAUSAL_UPGRADE":
            out.add("causal_upgrade")
    return out


#: `missing_premise` hat **keine** strukturelle Entsprechung: dass ein Schluss eine unausgesprochene
#: Prämisse braucht, ist keine Differenz zweier normalisierter Felder. Das ist ein bekannter blinder
#: Fleck des deterministischen Zweigs und wird unten eigens ausgewiesen, statt als Fehler unter
#: vielen zu verschwinden.
STRUCTURAL_BLIND_SPOT = "missing_premise"


def _f1(tp: int, fp: int, fn: int) -> float:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def _score(pairs: list[tuple[set[str], set[str]]]) -> dict:
    tp = fp = fn = 0
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for g, p in pairs:
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
        for v in g | p:
            per[v][0] += v in g and v in p
            per[v][1] += v in p and v not in g
            per[v][2] += v in g and v not in p
    macro = [_f1(*c) for c in per.values()]
    return {"micro_f1": round(_f1(tp, fp, fn), 3),
            "macro_f1": round(sum(macro) / len(macro), 3) if macro else 0.0,
            "tp": tp, "fp": fp, "fn": fn,
            "per": {k: round(_f1(*c), 3) for k, c in sorted(per.items())}}


def classify(case: dict, *, builder: str, k: int) -> dict:
    """Voller Klassifikationsdurchlauf für einen Fall - ohne Urteil, ohne Kostenregel."""
    props, undet = ent.split_propositions(case["claim"], builder=builder, k=k)
    ev = [ent.parse(e["text"], source_id=e.get("source_id", ""), builder=builder, k=k)
          for e in case.get("evidence", [])]
    sem: list[obs.Observation] = []
    for p in props:
        sem += obs.semantic_observations(ent.parse(p, builder=builder, k=k), ev)
    return {"case_id": case["case_id"], "propositions": props, "split_undetermined": undet,
            "semantic": [o.to_dict() for o in sem], "violations": sorted(_to_violations(sem))}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Aufruf: run_observations.py <dev_with_gold.json> [modell-baseline.jsonl]")
        return 2
    path = Path(argv[1])
    if "PRIVATE" in path.name:
        print("VERWEIGERT: der private Gold-Schlüssel wird hier nicht gelesen.")
        return 3
    cases = [c for c in json.loads(path.read_text(encoding="utf-8")) if c.get("gold_verdict")]

    model_viol: dict[str, set[str]] = {}
    if len(argv) > 2 and Path(argv[2]).exists():
        for line in Path(argv[2]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                model_viol[r["case_id"]] = set(r.get("violations") or [])

    print(f"Klassifikation über {len(cases)} Fälle · Parser {ent.PARSER} · k={ent.K_DRAWS}\n")
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda c: classify(c, builder=ent.PARSER, k=ent.K_DRAWS), cases))

    gold = {c["case_id"]: set(c.get("gold_violations") or []) for c in cases}
    det = {r["case_id"]: set(r["violations"]) for r in rows}

    for r in rows:
        cid = r["case_id"]
        g, d, m = gold[cid], det[cid], model_viol.get(cid, set())
        print(f"  {cid:<9} gold={sorted(g) or '-'}")
        print(f"            det ={sorted(d) or '-'}   modell={sorted(m) or '-'}")

    pairs_det = [(gold[c], det[c]) for c in gold]
    pairs_mod = [(gold[c], model_viol.get(c, set())) for c in gold] if model_viol else []
    pairs_uni = [(gold[c], det[c] | model_viol.get(c, set())) for c in gold] if model_viol else []

    print(f"\n{'=' * 72}")
    print("Transformationserkennung gegen Gold-Verstösse (Dev-Satz, NICHT blind)\n")
    for label, pairs in (("A deterministisch", pairs_det), ("B Modell", pairs_mod),
                         ("C Vereinigung", pairs_uni)):
        if not pairs:
            continue
        s = _score(pairs)
        print(f"  {label:<20} mikro-F1 {s['micro_f1']:<6} makro-F1 {s['macro_f1']:<6} "
              f"(tp {s['tp']} / fp {s['fp']} / fn {s['fn']})")
        print(f"  {'':<20} je Typ: {s['per']}")

    # Der blinde Fleck getrennt ausgewiesen - er ist kein Klassifikationsfehler, sondern eine
    # Grenze des strukturellen Zweigs.
    n_bs = sum(1 for g in gold.values() if STRUCTURAL_BLIND_SPOT in g)
    print(f"\n  struktureller blinder Fleck: '{STRUCTURAL_BLIND_SPOT}' in {n_bs} von {len(gold)} "
          f"Fällen im Gold - deterministisch nicht ableitbar")

    out = path.with_name("observation_results.json")
    out.write_text(json.dumps({"rows": rows, "catalogue": obs.CATALOGUE_VERSION,
                               "parser": ent.PARSER, "k": ent.K_DRAWS},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Beobachtungen gespeichert: {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
