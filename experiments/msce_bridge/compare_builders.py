"""Builder-Vergleich: misst das Instrument den Text - oder das Modell?

Bisher waren beide Builder aus derselben Familie (deepseek-v4-pro / -flash). Wenn JSD(alpha, beta)
etwas über die *Aussage* sagen soll und nicht über die Modellwahl, muss sich das an wirklich
unabhängigen Buildern zeigen. Hier: **IBM Granite 4.1-8b (via OpenRouter) gegen DeepSeek v4-pro** -
verschiedene Häuser, verschiedene Trainingsdaten, verschiedene Grössenordnung.

Drei Fragen:

1. **Übereinstimmung.** Wählen beide bei scharfen Aussagen dieselbe Relation? Wenn ja, misst die
   Projektion den Satz. Wenn nein, misst sie das Modell - und der ganze Ansatz trägt nicht.
2. **Mehrdeutigkeit.** Streuen beide bei denselben Sätzen? Ein Instrument taugt nur, wenn zwei
   unabhängige Beobachter *dieselben* Fälle als unklar erkennen.
3. **Cross-Vendor-JSD.** Ist die Divergenz zwischen Häusern grösser als innerhalb einer Familie?
   Falls ja, wäre E4 (BRANCH_CANDIDATE) mit Geschwister-Buildern systematisch zu blind.

**Der Confound und seine Kontrolle.** Granite 4.1-8b ist deutlich kleiner als deepseek-v4-pro - ein
Unterschied kann Modellgrösse sein statt Anbieter. Deshalb ist ``BUILDER_B`` umschaltbar:
``granite`` misst ueber Anbietergrenzen, ``beta`` (deepseek-v4-flash) ist die **Kontrolle** -
kleines Modell, aber dieselbe Familie. Zeigt beta dieselbe H_norm-Inversion, ist es ein Groessen-
und kein Anbietereffekt.
"""
from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import spl_builder as sb  # noqa: E402
from spl import EmissionEngine  # noqa: E402

N = 9

#: Welcher Builder gegen die Referenz (deepseek-v4-pro) geprüft wird. `granite` misst über
#: Anbietergrenzen, `beta` (deepseek-v4-flash) ist die **Kontrolle**: kleines Modell, aber
#: dieselbe Familie. Zeigt beta dieselbe H_norm-Inversion wie granite, ist es ein Grössen-,
#: kein Anbietereffekt - und der Confound aus dem Granite-Lauf ist aufgelöst.
BUILDER_B = os.getenv("BUILDER_B", "granite")

CASES = [
    ("A surface-code qubit needs many physical qubits per logical one.", "scharf", "requires"),
    ("Smoking is associated with lung cancer.", "scharf", "correlates_with"),
    ("Loading a glibc-linked binary wheel inside Alpine raises a dynamic-link error.",
     "scharf", "causes"),
    ("Avoid binary wheels on Alpine.", "scharf", "recommends"),
    ("Vitamin D supplementation may reduce fracture risk in the elderly.", "mehrdeutig", None),
    ("Regular exercise is good for cardiovascular health.", "mehrdeutig", None),
    ("The approach seems promising.", "leer", None),
]


def _proj(text: str, builder: str):
    p = sb.project(text, builder, n=N)
    EmissionEngine().emit(p)
    return p


def main() -> int:
    print(f"B = {BUILDER_B} ({sb.BUILDERS[BUILDER_B]})  vs  A = alpha ({sb.BUILDERS['alpha']}), "
          f"n={N} Ziehungen\n")
    agree_crisp = total_crisp = 0
    jsd_cross: list[float] = []
    rows = []
    for text, kind, expected in CASES:
        g = _proj(text, BUILDER_B)
        d = _proj(text, "alpha")
        jsd = sb.compute_jsd(g.P_r, d.P_r) if (g.P_r and d.P_r) else float("nan")
        jsd_cross.append(jsd)
        gdom = max(g.P_r, key=g.P_r.get) if g.P_r else "-"
        ddom = max(d.P_r, key=d.P_r.get) if d.P_r else "-"
        if kind == "scharf":
            total_crisp += 1
            agree_crisp += int(gdom == ddom)
        rows.append((text, kind, expected, g, d, gdom, ddom, jsd))
        print(f"[{kind:<10}] {text[:56]}")
        if expected:
            ok_g = "✓" if gdom == expected else "✗"
            ok_d = "✓" if ddom == expected else "✗"
            print(f"    erwartet: {expected}")
            print(f"    B  {BUILDER_B:<8}: {gdom:<16} {ok_g}  H={g.h_norm:.3f}  "
                  f"{ {k: round(v, 2) for k, v in g.P_r.items()} }  p_ill={g.p_illegal}")
            print(f"    A  alpha   : {ddom:<16} {ok_d}  H={d.h_norm:.3f}  "
                  f"{ {k: round(v, 2) for k, v in d.P_r.items()} }")
        else:
            print(f"    B  {BUILDER_B:<8}: H={g.h_norm:.3f}  "
                  f"{ {k: round(v, 2) for k, v in g.P_r.items()} }  p_ill={g.p_illegal}")
            print(f"    A  alpha   : H={d.h_norm:.3f}  "
                  f"{ {k: round(v, 2) for k, v in d.P_r.items()} }")
        print(f"    Regel B={g.emission_rule.value if g.emission_rule else '-'} · "
              f"A={d.emission_rule.value if d.emission_rule else '-'} · "
              f"cross-JSD={jsd:.3f}")
        print()

    print("=" * 72)
    print(f"Einigkeit bei scharfen Aussagen: {agree_crisp}/{total_crisp}")
    crisp_h = [(r[3].h_norm, r[4].h_norm) for r in rows if r[1] == "scharf"]
    amb_h = [(r[3].h_norm, r[4].h_norm) for r in rows if r[1] == "mehrdeutig"]
    if crisp_h:
        print(f"H_norm scharf     - B({BUILDER_B}) Ø "
              f"{statistics.fmean(h for h, _ in crisp_h):.3f} · "
              f"A(alpha) Ø {statistics.fmean(d for _, d in crisp_h):.3f}")
    if amb_h:
        print(f"H_norm mehrdeutig - B({BUILDER_B}) Ø {statistics.fmean(h for h, _ in amb_h):.3f} · "
              f"A(alpha) Ø {statistics.fmean(d for _, d in amb_h):.3f}")
    valid = [j for j in jsd_cross if j == j]
    if valid:
        print(f"JSD(A,B)          - Ø {statistics.fmean(valid):.3f} · max {max(valid):.3f}")
    print(f"illegale Masse B  - Ø {statistics.fmean(r[3].p_illegal for r in rows):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
