"""Der Auditor gegen den Testsatz. Erwartete Verdikte sind vorab festgelegt, nicht nachträglich.

Die MSCE-Kontrollen tragen bewusst `expect_verdict: null` - für sie gibt es keine Vorab-Wahrheit,
sie laufen mit, um zu sehen, was der Auditor auf echter Ausgabe sagt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402

CASES = Path(__file__).with_name("entailment_cases.json")


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    scored = hits = 0
    viol_hits = viol_total = 0
    for c in cases:
        res = ent.audit(c["claim"], c["evidence"],
                        declared_assumptions=tuple(c.get("declared_assumptions") or ()))
        exp_v = c.get("expect_verdict")
        print(f"[{c['kind']}]")
        print(ent.render(res))
        cs = res["claim_structure"]
        und = cs.get("undetermined") or []
        print(f"     Claim-Struktur: {cs['relation']} · {cs['modality']} · {cs['quantifier']} · "
              f"{cs['scope_level']}"
              + (f"   ⚠ unbestimmt: {und}" if und else f"   Zustimmung {cs.get('agreement', {})}"))
        for e in res["evidence_structures"]:
            print(f"     Beleg {e['source_id']:<6}: {e['relation']} · {e['modality']} · "
                  f"{e['quantifier']} · {e['scope_level']}"
                  + (f" · cond={e['conditions']}" if e["conditions"] else ""))
        if exp_v is not None:
            scored += 1
            ok = res["verdict"] == exp_v
            hits += int(ok)
            print(f"     erwartet: {exp_v}  →  {'✓' if ok else '✗ ' + res['verdict']}")
            exp_viol = set(c.get("expect_violations") or [])
            if exp_viol:
                got = set(res["violations"])
                viol_total += len(exp_viol)
                viol_hits += len(exp_viol & got)
                missing = exp_viol - got
                if missing:
                    print(f"     nicht erkannt: {sorted(missing)}")
        print()
    print("=" * 72)
    print(f"Verdikte korrekt : {hits}/{scored}")
    if viol_total:
        print(f"Verstösse erkannt: {viol_hits}/{viol_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
