"""Externe Blind-Evaluation des Entailment-Auditors — Vorhersagen erzeugen, nicht bewerten.

Der Testsatz wurde **unabhängig** konstruiert (dev 20 mit Gold, test 40 blind, plus ein privater
Schlüssel). Das ist das Gegenmittel gegen den Fehler, der in diesem Projekt zweimal auftrat:
selbst geschriebene Testfälle prüfen nur das eigene Modell der Sache.

Dieses Skript hält sich an `SCORING_PROTOCOL.md`:

* Dev darf zur Integration gelesen werden.
* Für den Blind-Test wird **eine JSONL-Datei mit eingefrorenen Vorhersagen** geschrieben, die alles
  mitführt, was zur Nachprüfung nötig ist: Fall-ID, Verdikt, Verstösse, normalisierte Strukturen,
  Feld-Zustimmung, Modell-ID, k, Prompt-Hash, Run-ID.
* **Der private Gold-Schlüssel wird hier nicht gelesen** und darf erst nach dem Einfrieren geöffnet
  werden. Die Bewertung findet ausserhalb dieses Kontexts statt.

Der Prompt-Hash deckt beide Prompts (Normalisierung + Zerlegung) und den Relationsraum ab, damit
eine spätere Auswertung eindeutig sagen kann, gegen welche Konfiguration gemessen wurde.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import spl_builder as sb  # noqa: E402


def prompt_hash() -> str:
    """Identität der Konfiguration: beide Prompts + der geschlossene Relationsraum."""
    blob = (ent._PARSE_SYSTEM + "\x00" + ent._SPLIT_SYSTEM + "\x00" + "|".join(sb.RELATIONS))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def run_id(cases_path: Path, run_index: int) -> str:
    seed = f"{cases_path.name}:{prompt_hash()}:{sb.BUILDERS[ent.PARSER]}:{ent.K_DRAWS}:{run_index}"
    return "run-" + hashlib.sha256(seed.encode()).hexdigest()[:12]


def predict(case: dict) -> dict:
    res = ent.audit(case["claim"],
                    [{"text": e["text"], "source_id": e.get("source_id", "")}
                     for e in case.get("evidence", [])],
                    declared_assumptions=tuple(case.get("declared_assumptions") or ()),
                    context=case.get("context", ""))
    return {
        "case_id": case["case_id"],
        "verdict": res["verdict"],
        "violations": res["violations"],
        "propositions": res.get("propositions", []),
        "per_proposition": res.get("per_proposition", []),
        "claim_structure": res.get("claim_structure", {}),
        "evidence_structures": res.get("evidence_structures", []),
        "justification": res.get("notes", []),
    }


def main(argv: list[str]) -> int:
    cases_path = Path(argv[1]) if len(argv) > 1 else None
    if cases_path is None or not cases_path.exists():
        print("Aufruf: run_external_eval.py <cases.json> [out.jsonl] [run_index]")
        return 2
    if "PRIVATE" in cases_path.name:
        print("VERWEIGERT: der private Gold-Schlüssel wird von diesem Skript nicht gelesen.")
        return 3
    out = Path(argv[2]) if len(argv) > 2 else cases_path.with_suffix(".predictions.jsonl")
    idx = int(argv[3]) if len(argv) > 3 else 1

    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    meta = {
        "model_id": sb.BUILDERS[ent.PARSER],
        "parser_alias": ent.PARSER,
        "k": ent.K_DRAWS,
        "prompt_hash": prompt_hash(),
        "run_id": run_id(cases_path, idx),
        "cases_file": cases_path.name,
        "code_commit": os.getenv("FREEZE_COMMIT", ""),
    }
    print(f"Konfiguration eingefroren: {json.dumps(meta, ensure_ascii=False)}")
    print(f"{len(cases)} Fälle -> {out.name}\n")

    rows = []
    for i, case in enumerate(cases, 1):
        p = predict(case)
        p.update(meta)
        rows.append(p)
        n_props = len(p["propositions"])
        print(f"  [{i:>2}/{len(cases)}] {p['case_id']:<10} {p['verdict']:<24}"
              f"{'(' + str(n_props) + ' Prop.)' if n_props > 1 else ''} {p['violations']}")

    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                   encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()[:16]
    print(f"\nEingefroren: {out}  sha256[:16]={digest}")

    from collections import Counter
    print(f"Verdikt-Verteilung: {dict(Counter(r['verdict'] for r in rows))}")

    # Nur wenn der Satz sein Gold selbst mitbringt (dev) - der private Schlüssel wird nie geöffnet.
    if any("gold_verdict" in c for c in cases):
        gold = {c["case_id"]: c["gold_verdict"] for c in cases}
        hits = sum(1 for r in rows if r["verdict"] == gold.get(r["case_id"]))
        print(f"\nDEV-Selbstauswertung: {hits}/{len(rows)} Verdikte korrekt")
        for r in rows:
            g = gold.get(r["case_id"])
            if r["verdict"] != g:
                print(f"   ✗ {r['case_id']}: erwartet {g}, bekommen {r['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
