"""v2 gegen den Dev-Satz. Messregel: mindestens die Baseline (17-18/20), sonst schaden die
Kontrollen mehr als sie nuetzen."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_v2 as v2  # noqa: E402

_PASSING = {"entailed", "partially_entailed"}


def main(argv):
    cases = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    scored = [c for c in cases if c.get("gold_verdict")]
    hits = fp = fb = downgrades = 0
    for i, c in enumerate(scored, 1):
        r = v2.audit(c["claim"], c.get("evidence", []),
                     declared_assumptions=tuple(c.get("declared_assumptions") or ()))
        gold = c["gold_verdict"]
        ok = r.verdict == gold
        hits += ok
        downgrades += r.verdict != r.model_verdict
        if not ok:
            if r.verdict in _PASSING and gold not in _PASSING:
                fp += 1
            elif r.verdict not in _PASSING and gold in _PASSING:
                fb += 1
        arrow = f" (Modell: {r.model_verdict})" if r.verdict != r.model_verdict else ""
        print(f"  [{i:>2}] {c['case_id']:<9} {'✓' if ok else '✗'} {r.verdict:<24}"
              f"(gold {gold:<24}){arrow}")
        for v in r.vetoes:
            print(f"        ↓ {v.control}: {v.reason[:70]}")
    n = len(scored)
    print(f"\n{'=' * 66}")
    print(f"Verdikte korrekt : {hits}/{n} ({hits/n:.0%})")
    print(f"Falschdurchlaesse: {fp}   Falschsperren: {fb}")
    print(f"Herabstufungen   : {downgrades}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
