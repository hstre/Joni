"""Auswertung des Blindlaufs. Liest den Schlüssel - und erst jetzt, nach der Versiegelung.

Getrennt vom Läufer gehalten, weil die Reihenfolge die eigentliche Sicherung ist: ``run_blind.py``
kennt kein Gold, ``score_blind.py`` ändert keine Vorhersage. Beide Dateien werden über ihren
SHA-256 identifiziert; weicht er von dem im Versiegelungs-Commit ab, bricht die Auswertung ab.

Berichtet wird, was ``SCORING_PROTOCOL.md`` Schritt 7 verlangt - Trefferquote, Makro-F1,
Falschdurchlass- und Falschsperrquote, Verstoss-F1 mikro und makro, Stabilität über die Läufe -
und Schritt 8: die Trennung von **Normalisierungsfehlern** (die Struktur war falsch oder
unbestimmt) und **Regelfehlern** (die Struktur stimmte, die deterministische Kontrolle urteilte
falsch). Diese Trennung ist der Grund, warum die Strukturen überhaupt mitprotokolliert werden:
ohne sie sagt eine Fehlerquote nicht, welche Schicht sie verursacht hat.

Eine dritte Kategorie kommt aus der v2-Architektur selbst und wird eigens ausgewiesen: Fälle, in
denen das **Modell** richtig lag und erst eine Kontrolle das Verdikt kaputtgestuft hat - und
umgekehrt solche, in denen eine Kontrolle einen Modellfehler repariert hat. Erst diese beiden
Zahlen nebeneinander sagen, ob die Kontrollschicht ihren Preis wert ist.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

#: Verdikte, die einen Claim durchlassen. Ein strengeres Gold macht daraus einen
#: FALSCHDURCHLASS - die gefährliche Richtung, denn eine unbegründete Behauptung bekäme ein
#: Gütesiegel. Der umgekehrte Fehler kostet nur Prüfaufwand.
PASSING = {"entailed", "partially_entailed"}
VERDICTS = ["entailed", "partially_entailed", "compatible_not_entailed", "contradicted",
            "insufficient"]


def _f1(tp: int, fp: int, fn: int) -> float:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return 2 * p * r / (p + r) if p + r else 0.0


def _macro_f1(pairs: list[tuple[str, str]], labels: list[str]) -> tuple[float, dict]:
    per = {}
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        if tp + fn == 0 and tp + fp == 0:
            continue                     # Label kommt weder im Gold noch in der Vorhersage vor
        per[lab] = {"f1": round(_f1(tp, fp, fn), 3), "support": tp + fn}
    macro = sum(v["f1"] for v in per.values()) / len(per) if per else 0.0
    return macro, per


def _violation_f1(rows: list[dict], gold: dict) -> dict:
    """Mikro über alle Verstoss-Vorkommen, makro über die Verstossarten."""
    tp = fp = fn = 0
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        g = set(gold[r["case_id"]].get("gold_violations") or [])
        p = set(r["violations"])
        tp += len(g & p)
        fp += len(p - g)
        fn += len(g - p)
        for v in g | p:
            per[v][0] += v in g and v in p
            per[v][1] += v in p and v not in g
            per[v][2] += v in g and v not in p
    macro = ([_f1(*c) for c in per.values()])
    return {"micro_f1": round(_f1(tp, fp, fn), 3),
            "macro_f1": round(sum(macro) / len(macro), 3) if macro else 0.0,
            "tp": tp, "fp": fp, "fn": fn,
            "per_violation": {k: round(_f1(*c), 3) for k, c in sorted(per.items())}}


def _blame(r: dict, gold_v: str) -> str:
    """Schritt 8: welche Schicht hat den Fehler verursacht?

    Die Frage ist nicht rhetorisch. In v2 kann ein falsches Verdikt aus drei Quellen kommen, und
    sie verlangen völlig verschiedene Reaktionen: ein Modellfehler heisst Prompt oder Modell,
    ein Kontrollfehler heisst Katalog, ein Normalisierungsfehler heisst Parser.
    """
    model_v, final = r["model_verdict"], r["verdict"]
    if final == gold_v:
        return "korrigiert_durch_kontrolle" if model_v != gold_v else "korrekt"
    if model_v == gold_v and final != gold_v:
        # Das Modell hatte recht; erst die Kontrollschicht (oder die fehlende Mehrheit) brach es.
        if not r["vetoes"] and final == "insufficient":
            return "fehler_normalisierung_keine_mehrheit"
        undet = any(s.get("undetermined") for s in r["structures"].get("claim", [])) or \
            any(s.get("undetermined") for s in r["structures"].get("evidence", []))
        return "fehler_normalisierung_struktur" if undet else "fehler_regel_kontrolle"
    return "fehler_modell"


def _seal(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(pred_path: Path, gold: dict, *, label: str) -> dict:
    rows = [json.loads(x) for x in pred_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if r["case_id"] in gold]
    pairs = [(gold[r["case_id"]]["gold_verdict"], r["verdict"]) for r in rows]

    hits = sum(g == p for g, p in pairs)
    fp = sum(1 for g, p in pairs if p in PASSING and g not in PASSING)
    fb = sum(1 for g, p in pairs if p not in PASSING and g in PASSING)
    macro, per_label = _macro_f1(pairs, VERDICTS)
    blame = Counter(_blame(r, gold[r["case_id"]]["gold_verdict"]) for r in rows)

    # Wie gut trifft das Prüfsignal die Fehler? Es soll nicht urteilen, sondern zeigen, wo
    # ein Mensch hinschauen muss - also misst man es an genau dem.
    flagged = [r for r in rows if r["review_required"]]
    wrong = {r["case_id"] for r, (g, p) in zip(rows, pairs, strict=True) if g != p}
    caught = sum(1 for r in flagged if r["case_id"] in wrong)

    return {
        "label": label, "file": pred_path.name, "sha256": _seal(pred_path), "n": len(rows),
        "accuracy": round(hits / len(rows), 3) if rows else 0.0, "hits": hits,
        "false_pass": fp, "false_pass_rate": round(fp / len(rows), 3) if rows else 0.0,
        "false_block": fb, "false_block_rate": round(fb / len(rows), 3) if rows else 0.0,
        "macro_f1": round(macro, 3), "per_label": per_label,
        "violations": _violation_f1(rows, gold),
        "blame": dict(blame),
        "review_flagged": len(flagged), "review_caught": caught, "errors_total": len(wrong),
        "rows": [{"case_id": r["case_id"], "gold": g, "pred": p, "model": r["model_verdict"],
                  "agreement": r["model_agreement"], "review": r["review_required"],
                  "second": r["second_opinion_verdict"],
                  "vetoes": [v["control"] for v in r["vetoes"]],
                  "blame": _blame(r, g), "ok": g == p}
                 for r, (g, p) in zip(rows, pairs, strict=True)],
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Aufruf: score_blind.py <gold.json> <pred1.jsonl> [pred2.jsonl ...]")
        return 2
    gold_rows = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    gold = {c["case_id"]: c for c in gold_rows if c.get("gold_verdict")}
    reports = [score(Path(p), gold, label=f"Lauf {i}") for i, p in enumerate(argv[2:], 1)]

    for rep in reports:
        print(f"\n{'=' * 72}\n{rep['label']}  ·  {rep['file']}\n  SHA-256 {rep['sha256']}")
        print(f"  Trefferquote      : {rep['hits']}/{rep['n']}  ({rep['accuracy']:.1%})")
        print(f"  Makro-F1          : {rep['macro_f1']}")
        print(f"  Falschdurchlässe  : {rep['false_pass']}  ({rep['false_pass_rate']:.1%})"
              f"   <- gefährliche Richtung")
        print(f"  Falschsperren     : {rep['false_block']}  ({rep['false_block_rate']:.1%})")
        v = rep["violations"]
        print(f"  Verstösse         : mikro-F1 {v['micro_f1']} · makro-F1 {v['macro_f1']} "
              f"(tp {v['tp']} / fp {v['fp']} / fn {v['fn']})")
        print(f"  Fehlerherkunft    : {rep['blame']}")
        print(f"  Prüfsignal        : {rep['review_flagged']} markiert, davon "
              f"{rep['review_caught']} echte Fehler (von {rep['errors_total']})")
        print("  je Verdikt        : " + " · ".join(
            f"{k} {d['f1']} (n={d['support']})" for k, d in rep["per_label"].items()))
        bad = [r for r in rep["rows"] if not r["ok"]]
        if bad:
            print("  Fehlerliste:")
            for r in bad:
                mark = "‼" if r["pred"] in PASSING and r["gold"] not in PASSING else " "
                print(f"   {mark} {r['case_id']:<9} vorhergesagt {r['pred']:<24}"
                      f"gold {r['gold']:<24} [{r['blame']}]"
                      + (f" Vetos {r['vetoes']}" if r["vetoes"] else ""))

    if len(reports) > 1:
        a, b = reports[0], reports[1]
        by = {r["case_id"]: r["pred"] for r in a["rows"]}
        unstable = [r["case_id"] for r in b["rows"] if by.get(r["case_id"]) != r["pred"]]
        print(f"\n{'=' * 72}\nStabilität über die Läufe")
        print(f"  identische Verdikte : {b['n'] - len(unstable)}/{b['n']} "
              f"({1 - len(unstable) / b['n']:.1%})")
        print(f"  abweichend          : {unstable or 'keine'}")
        print("  Trefferquoten       : " + " · ".join(
            f"{r['label']} {r['hits']}/{r['n']}" for r in reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
