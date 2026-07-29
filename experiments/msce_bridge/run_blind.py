"""Der Blindlauf. Einmal, gegen den versiegelten Testsatz, ohne Rückkanal.

Dies ist der Punkt, auf den die ganze Messreihe zuläuft. Die Regeln stehen im
``SCORING_PROTOCOL.md`` des externen Satzes, und sie sind streng aus gutem Grund - jede
Nachjustierung nach Sicht der Ergebnisse verwandelt die Evaluation in eine Anpassung:

    Schritt 2  Code, Prompt, Parser-Modell, Anbieter, Commit-Hash einfrieren
    Schritt 4  Vorhersagen mit Fall-ID, Verdikt, Verstössen, normalisierten Strukturen,
               Feldzustimmung, Modell-ID, k, Prompt-Hash, Lauf-ID
    Schritt 5  diese Ausgabe einfrieren, BEVOR der private Schlüssel geöffnet wird
    Schritt 7  darunter auch: Stabilität über wiederholte Läufe
    Schritt 9  keine Testfälle nachträglich ändern

Dieses Skript deckt 2, 4, 5 und den Wiederholungsteil von 7 ab. Es **weigert sich**, eine Datei
mit "PRIVATE" im Namen zu lesen, und es weigert sich, eine bereits geschriebene
Vorhersagedatei zu überschreiben - der zweite Lauf bekommt einen eigenen Namen. Beides ist
Absicht: die einzige Sicherung gegen unbewusstes Nachbessern ist, dass Nachbessern technisch
auffällt.

Der Hash der Vorhersagedatei wird am Ende gedruckt. Er ist die Versiegelung: nach ihm darf sich
an den Vorhersagen nichts mehr ändern, und beim Auswerten lässt sich zeigen, dass es das nicht
tat.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_v2 as v2  # noqa: E402
import entailment as ent  # noqa: E402
import llm_baseline as base  # noqa: E402
import spl_builder as sb  # noqa: E402

#: Gleichzeitige Fälle. Jeder Fall kostet selbst schon k Modellaufrufe je Aussage; mehr
#: Parallelität hier bringt vor allem Ratenbegrenzungen ein.
WORKERS = 4


def _commit() -> str:
    try:
        h = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip()[:8]
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                               cwd=Path(__file__).resolve().parent, check=True).stdout.strip()
        return h + ("+dirty" if dirty else "")
    except Exception:  # noqa: BLE001 - fehlendes git ist kein Grund, den Lauf abzubrechen
        return "unknown"


def _config() -> dict:
    """Die eingefrorene Konfiguration, wie Schritt 2 sie verlangt - im Vorhersagesatz mitgeführt."""
    return {
        "commit": _commit(),
        "model_id": sb.BUILDERS[ent.PARSER],
        "model_alias": ent.PARSER,
        "second_opinion_model_id": sb.BUILDERS[v2.SECOND_OPINION],
        "second_opinion_alias": v2.SECOND_OPINION,
        "provider": "deepseek + openrouter",
        "k": ent.K_DRAWS,
        "judge_prompt_sha256_16": hashlib.sha256(base._SYSTEM.encode()).hexdigest()[:16],
        "parse_prompt_sha256_16": hashlib.sha256(ent._PARSE_SYSTEM.encode()).hexdigest()[:16],
        "active_controls": sorted(v2.ACTIVE_CONTROLS),
        "inactive_controls": sorted(set(v2.CONTROLS) - v2.ACTIVE_CONTROLS),
        "architecture": "v2 - Modell urteilt, Kontrollen vetoen (nur abwärts)",
    }


def _one(case: dict, cfg: dict, run_id: str) -> dict:
    r = v2.audit(case["claim"], case.get("evidence", []),
                 declared_assumptions=tuple(case.get("declared_assumptions") or ()),
                 second_opinion=v2.SECOND_OPINION)
    return {
        "case_id": case["case_id"],
        "run_id": run_id,
        "verdict": r.verdict,
        "violations": r.violations,
        "model_verdict": r.model_verdict,
        "model_agreement": r.model_agreement,
        "downgraded": r.verdict != r.model_verdict,
        "vetoes": [v.to_dict() for v in r.vetoes],
        "review_required": r.review_required,
        "second_opinion_verdict": r.second_opinion,
        "structures": r.structures,
        "justification": r.justification,
        **{k: cfg[k] for k in ("model_id", "k", "judge_prompt_sha256_16",
                               "parse_prompt_sha256_16", "commit")},
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Aufruf: run_blind.py <entailment_test_blind.json> [lauf-nr]")
        return 2
    path = Path(argv[1])
    if "PRIVATE" in path.name:
        print("VERWEIGERT: der private Gold-Schlüssel wird hier nicht gelesen.")
        return 3
    if not path.exists():
        print(f"nicht gefunden: {path}")
        return 2
    lauf = argv[2] if len(argv) > 2 else "1"

    cases = json.loads(path.read_text(encoding="utf-8"))
    out = path.with_name(f"blind_predictions_run{lauf}.jsonl")
    if out.exists():
        print(f"VERWEIGERT: {out.name} existiert bereits. Ein Blindlauf wird nicht überschrieben "
              f"- ein Wiederholungslauf bekommt eine eigene Nummer.")
        return 4

    cfg = _config()
    run_id = f"blind-{lauf}-{uuid.uuid4().hex[:8]}"
    print("=== EINGEFRORENE KONFIGURATION ===")
    for k, v in cfg.items():
        print(f"  {k:<26}: {v}")
    print(f"  {'run_id':<26}: {run_id}")
    print(f"\n{len(cases)} Fälle, versiegelt - kein Gold sichtbar.\n")

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(lambda c: _one(c, cfg, run_id), cases))

    for i, r in enumerate(rows, 1):
        flag = " ⚑Prüfung" if r["review_required"] else ""
        down = f"  (Modell: {r['model_verdict']})" if r["downgraded"] else ""
        print(f"  [{i:>2}] {r['case_id']:<9} {r['verdict']:<24} "
              f"Zust.={r['model_agreement']}{down}{flag}")

    body = "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows) + "\n"
    out.write_text(body, encoding="utf-8")
    seal = hashlib.sha256(body.encode()).hexdigest()

    meta = out.with_suffix(".meta.json")
    meta.write_text(json.dumps({"run_id": run_id, "config": cfg, "n_cases": len(rows),
                                "predictions_file": out.name,
                                "predictions_sha256": seal}, ensure_ascii=False, indent=2),
                    encoding="utf-8")

    from collections import Counter
    print(f"\n{'=' * 70}")
    print(f"Verteilung   : {dict(Counter(r['verdict'] for r in rows))}")
    print(f"Herabstufungen: {sum(r['downgraded'] for r in rows)}")
    print(f"Prüfung nötig : {sum(r['review_required'] for r in rows)} von {len(rows)}")
    print(f"eingefroren  : {out.name}")
    print(f"SHA-256      : {seal}")
    print("\nDer private Schlüssel bleibt zu, bis dieser Hash notiert ist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
