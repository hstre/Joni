"""Ensemble aus zwei Modellen. Drei Strategien, gegen die Einzelmodelle gemessen.

Die Fehlerprofile sind fast disjunkt: von 20 Faellen liegen flash und pro nur bei zweien beide
falsch. Das legt ein Ensemble nahe - aber welche Kombinationsregel? Drei Kandidaten, und die
Auswahl darf nicht nach Trefferquote allein gehen, sondern muss die **Falschdurchlaesse** wiegen.

  agreement_or_weaker    einig -> nehmen; uneinig -> das SCHWAECHERE Verdikt.
                         Konservativ, passt zur Invariante (nur abwaerts).
  agreement_or_review    einig -> nehmen; uneinig -> insufficient.
                         Uneinigkeit als Signal, wie bei den Ziehungen innerhalb eines Modells.
  agreement_or_stronger  einig -> nehmen; uneinig -> das STAERKERE.
                         Nur als Kontrolle mitgefuehrt: es ist die unsichere Richtung und sollte
                         sich in den Falschdurchlaessen zeigen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LADDER = ("entailed", "partially_entailed", "compatible_not_entailed", "insufficient")
RANK = {v: i for i, v in enumerate(LADDER)}
PASS = {"entailed", "partially_entailed"}


def _weaker(a, b):
    if a not in RANK or b not in RANK:
        return a if a == b else "insufficient"
    return a if RANK[a] >= RANK[b] else b


def _stronger(a, b):
    if a not in RANK or b not in RANK:
        return a if a == b else "insufficient"
    return a if RANK[a] <= RANK[b] else b


STRATEGIES = {
    "flash allein": lambda a, b: a,
    "pro allein": lambda a, b: b,
    "agreement_or_weaker": lambda a, b: a if a == b else _weaker(a, b),
    "agreement_or_review": lambda a, b: a if a == b else "insufficient",
    "agreement_or_stronger": lambda a, b: a if a == b else _stronger(a, b),
}


def main(argv):
    cases = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    gold = {c["case_id"]: c["gold_verdict"] for c in cases if c.get("gold_verdict")}
    load = lambda f: {json.loads(x)["case_id"]: json.loads(x)["verdict"]  # noqa: E731
                      for x in Path(f).read_text(encoding="utf-8").splitlines() if x.strip()}
    fl, pr = load(argv[2]), load(argv[3])
    disagree = [c for c in gold if fl.get(c) != pr.get(c)]
    print(f"{len(gold)} Faelle · Modelle uneinig bei {len(disagree)}: {sorted(disagree)}\n")
    print(f"{'Strategie':<24}{'korrekt':>9}{'Falschdurchl.':>15}{'Falschsperren':>15}")
    for name, fn in STRATEGIES.items():
        hits = fp = fb = 0
        for c, g in gold.items():
            v = fn(fl.get(c, ""), pr.get(c, ""))
            hits += v == g
            if v != g:
                if v in PASS and g not in PASS:
                    fp += 1
                elif v not in PASS and g in PASS:
                    fb += 1
        print(f"{name:<24}{hits:>6}/{len(gold)}{fp:>15}{fb:>15}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
