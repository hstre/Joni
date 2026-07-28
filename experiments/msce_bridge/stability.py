"""Ist der LLM-Builder ein Instrument oder eine Anekdote? Die Stabilitätsmessung.

Der erste Lauf zeigte, dass die Kette funktioniert: scharfe Aussagen → H_norm ≈ 0 → E1 (emittiert),
echt mehrdeutige → H_norm ≈ 0.9 → E3 (blockiert). Das war ein Lauf über acht Sätze. Ob daraus ein
*Messgerät* wird, entscheidet eine andere Frage:

    **Bekommt derselbe Satz reproduzierbar dieselbe Emissionsregel?**

Das ist die einzige Stabilität, die praktisch zählt. H_norm darf schwanken - wenn ein Satz aber
zwischen E1 (Claim wird emittiert) und E3 (Claim wird blockiert) hin und her springt, ist die
Schicht als Tor unbrauchbar, egal wie hübsch die Zahlen im Mittel aussehen.

Zu erwarten ist echtes Rauschen: P_r ist eine empirische Häufigkeit aus n Ziehungen. Bei n=7 und
einem wahren p=0.5 liegt die Standardabweichung des Anteils schon bei ~0.19. Die Messung prüft
deshalb beides - die Streuung von H_norm und, wichtiger, die Konstanz der Regel - und zwar für
zwei Stichprobengrößen, damit sichtbar wird, ob mehr Ziehungen das Problem lösen.

Aufruf::

    source .../secrets/ds.env
    SPL_ROOT=<spl> python experiments/msce_bridge/stability.py
"""
from __future__ import annotations

import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spl_builder as sb  # noqa: E402
from spl import EmissionEngine  # noqa: E402

REPEATS = int(os.getenv("REPEATS", "4"))
SIZES = (7, 15)

CASES = [
    ("A surface-code qubit needs many physical qubits per logical one.", "scharf"),
    ("Smoking is associated with lung cancer.", "scharf"),
    ("Vitamin D supplementation may reduce fracture risk in the elderly.", "mehrdeutig"),
    ("Regular exercise is good for cardiovascular health.", "mehrdeutig"),
]


def one_projection(text: str, n: int) -> tuple[float, str, str]:
    """Eine vollständige Projektion → (H_norm, Emissionsregel, dominante Relation)."""
    proj = sb.project(text, "alpha", n=n)
    EmissionEngine().emit(proj)
    rule = proj.emission_rule.value if proj.emission_rule else "-"
    dom = max(proj.P_r, key=proj.P_r.get) if proj.P_r else "-"
    return proj.h_norm, rule, dom


def main() -> int:
    print(f"Stabilität: {REPEATS} Wiederholungen je Satz, Stichprobengrößen {SIZES}\n")
    for n in SIZES:
        print(f"===== n = {n} Ziehungen je Projektion =====")
        for text, kind in CASES:
            def _run(_i, _t=text, _n=n):
                return one_projection(_t, _n)

            with ThreadPoolExecutor(max_workers=REPEATS) as pool:
                runs = list(pool.map(_run, range(REPEATS)))
            hs = [r[0] for r in runs]
            rules = [r[1] for r in runs]
            doms = [r[2] for r in runs]
            stable = len(set(rules)) == 1
            spread = (max(hs) - min(hs))
            sd = statistics.pstdev(hs) if len(hs) > 1 else 0.0
            mark = "✓" if stable else "✗ INSTABIL"
            print(f"  [{kind:<10}] {text[:50]}")
            print(f"      H_norm: {[round(h, 3) for h in hs]}  "
                  f"(Ø {statistics.fmean(hs):.3f}, SD {sd:.3f}, Spanne {spread:.3f})")
            print(f"      Regel : {rules}  {mark}")
            print(f"      dom.  : {sorted(set(doms))}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
