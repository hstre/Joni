"""Baseline: das Modell urteilt direkt über Entailment. Entscheidet eine Architekturfrage.

Der regelbasierte Auditor kommt auf der externen Blind-Evaluation auf 7/20 (und nach einem
Verschärfungsversuch auf 5/20). Die Diagnose lautete: Entailment braucht Weltwissen (39,1 °C ist
Fieber) und mehrstufige Komposition — beides steckt im Modell, nicht in einer Strukturregel.

Daraus folgte der Vorschlag „Modell urteilt, Regeln vetoen". **Das ist eine Vermutung.** Dieses
Skript prüft sie, bevor darauf gebaut wird:

    Kommt das Modell allein deutlich über 7/20, ist der Umbau begründet.
    Kommt es ebenfalls auf ~7/20, ist die Aufgabe schwerer als angenommen —
    und niemand sollte irgendwem irgendetwas versprechen.

**Fairness ist hier die halbe Messung.** Ein schwacher Prompt würde die Regeln gut aussehen lassen
und nichts beweisen. Deshalb:

* dasselbe Verdikt- und Verstoss-Vokabular wie die Regeln, mit denselben Definitionen;
* dieselbe Stichprobenzahl ``k`` und Mehrheitsentscheid, damit das bekannte Ziehungsrauschen
  kontrolliert ist und nicht als Unterschied durchgeht;
* beide Modelle (flash und pro), weil Modellabhängigkeit gemessen wurde;
* derselbe Dev-Satz — der Blind-Satz bleibt versiegelt.

Gemessen wird nicht nur die Trefferquote, sondern getrennt die **Falschdurchlässe** (`entailed`
oder `partially_entailed`, wo das Gold strenger ist). Das ist die gefährliche Richtung: ein
falsches `entailed` lässt eine unbegründete Behauptung mit Gütesiegel passieren.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import spl_builder as sb  # noqa: E402

VERDICTS = list(ent.VERDICTS)
VIOLATIONS = list(ent.VIOLATIONS)

#: Bewusst stark formuliert - dieselben Definitionen, die die Regeln umsetzen.
_SYSTEM = """You audit whether cited evidence ENTAILS a claim. You judge derivation, not truth.

Answer with exactly one verdict:

  entailed                 every part of the claim is carried by the evidence
  partially_entailed       the core holds, but a qualifier or condition from the evidence
                           was dropped
  compatible_not_entailed  not contradicted, but the evidence does not carry the claim
                           (e.g. it generalises beyond it, strengthens a hedge into an
                           assertion, upgrades a correlation to a cause, or infers the best
                           explanation while alternatives remain open)
  contradicted             an item of evidence asserts the same proposition, denied
  insufficient             the evidence cannot decide it at all (unrelated entities, a
                           broken inference chain, no evidence given)

And list zero or more violations from exactly this closed set:

  missing_premise             an unstated premise is required
  causal_upgrade              claim asserts causation, evidence only association
  modal_strengthening         claim is more certain than the evidence
  scope_expansion             claim speaks about a broader class than the evidence
  unsupported_generalization  claim quantifies more widely than the evidence
  entity_shift                claim is about entities the evidence does not cover
  condition_dropped           a condition the evidence depends on is missing from the claim

Rules of judgement:
- Absence of evidence is NOT refutation.
- "No evidence of X was found" is a statement about a search, not about X.
- An intervention that removes a symptom does not prove the cause.
- Domain conventions (what counts as "fever", "elevated") may be assumed if standard, but if
  the claim depends on a threshold the evidence does not state, that is missing_premise.

Return JSON exactly: {"verdict":"<one>","violations":["..."]}"""


def _one_draw(case: dict, model_alias: str) -> dict | None:
    ev = "\n".join(f"- [{e.get('source_id', '')}] {e['text']}" for e in case.get("evidence", []))
    user = (f"EVIDENCE:\n{ev or '(none)'}\n\n"
            f"DECLARED ASSUMPTIONS: {case.get('declared_assumptions') or '(none)'}\n\n"
            f"CLAIM: {case['claim']}")
    try:
        raw = sb._call(sb.BUILDERS[model_alias], f"{_SYSTEM}\n\n{user}", temperature=0.0)
    except Exception:  # noqa: BLE001 - eine misslungene Ziehung ist Datum, kein Absturz
        return None
    v = str(raw.get("verdict", "")).strip().lower()
    viols = [x for x in (raw.get("violations") or []) if x in VIOLATIONS]
    return {"verdict": v if v in VERDICTS else "", "violations": viols}


def judge(case: dict, *, model_alias: str, k: int) -> dict:
    """k Ziehungen, Mehrheitsentscheid — dieselbe Behandlung wie beim Parser."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(k, 8)) as pool:
        draws = [d for d in pool.map(lambda _: _one_draw(case, model_alias), range(k)) if d]
    if not draws:
        return {"verdict": "insufficient", "violations": [], "agreement": 0.0}
    counts = Counter(d["verdict"] for d in draws if d["verdict"])
    if not counts:
        return {"verdict": "insufficient", "violations": [], "agreement": 0.0}
    top, n = counts.most_common(1)[0]
    viol = Counter(v for d in draws for v in d["violations"])
    return {"verdict": top,
            "violations": sorted(v for v, c in viol.items() if c * 2 > len(draws)),
            "agreement": round(n / len(draws), 2)}


#: Verdikte, die einen Claim durchlassen. Ein Gold, das strenger ist, macht daraus einen
#: FALSCHDURCHLASS - die gefährliche Richtung.
_PASSING = {"entailed", "partially_entailed"}


def main(argv: list[str]) -> int:
    cases_path = Path(argv[1]) if len(argv) > 1 else None
    if cases_path is None or not cases_path.exists():
        print("Aufruf: llm_baseline.py <dev_with_gold.json> [modell-alias] [k]")
        return 2
    if "PRIVATE" in cases_path.name:
        print("VERWEIGERT: der private Gold-Schlüssel wird hier nicht gelesen.")
        return 3
    alias = argv[2] if len(argv) > 2 else "beta"
    k = int(argv[3]) if len(argv) > 3 else ent.K_DRAWS

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    scored = [c for c in cases if c.get("gold_verdict")]
    print(f"Baseline: Modell urteilt direkt · {sb.BUILDERS[alias]} · k={k} · "
          f"{len(scored)} bewertete Fälle\n")

    hits = false_pass = false_block = 0
    rows = []
    for i, c in enumerate(scored, 1):
        r = judge(c, model_alias=alias, k=k)
        gold = c["gold_verdict"]
        ok = r["verdict"] == gold
        hits += ok
        if not ok:
            if r["verdict"] in _PASSING and gold not in _PASSING:
                false_pass += 1
            elif r["verdict"] not in _PASSING and gold in _PASSING:
                false_block += 1
        rows.append({**r, "case_id": c["case_id"], "gold": gold, "correct": ok})
        mark = "✓" if ok else "✗"
        print(f"  [{i:>2}] {c['case_id']:<9} {mark} {r['verdict']:<24} "
              f"(gold {gold:<24}) Zust.={r['agreement']}")

    n = len(scored)
    print(f"\n{'=' * 66}")
    print(f"Verdikte korrekt : {hits}/{n}  ({hits / n:.0%})")
    print(f"Falschdurchlässe : {false_pass}   <- gefährliche Richtung")
    print(f"Falschsperren    : {false_block}")
    print(f"Verteilung       : {dict(Counter(r['verdict'] for r in rows))}")
    out = cases_path.with_name(f"baseline_{alias}_k{k}.jsonl")
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    print(f"eingefroren      : {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
