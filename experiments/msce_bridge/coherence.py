"""Passen die Teile zusammen? Eine Schnittstellen-Sonde statt einer Kompatibilitätsmatrix.

Nach einem Tag Messungen liegen mehrere Bauteile nebeneinander, die alle irgendetwas mit „was
bedeutet dieser Satz" zu tun haben:

    A  FrameDetector        (desi.frames)      Frame eines Satzes - erwartet Deklarationen
    B  LogicalAuditor       (desi.logic)       Argumentkette - erwartet 'Therefore'
    C  Embedding-Kosinus    (fastembed)        Abstand zweier Sätze
    D  polarity_clash       (desi_semantics)   lexikalische Gegensätzlichkeit
    E  Layer-9 classify     (desi_layer9)      paarweises Verdikt aus A-D
    F  SPL-Builder π(s)     (spl_builder)      Relationsverteilung P_r → H_norm, JSD, E0-E4
    G  Entailment-Parser    (entailment)       volle Struktur: Relation, Modalität, Quantor,
                                               Reichweite, Bedingungen - je k-mal gezogen
    H  Entailment-Regeln    (entailment)       Ableitungsurteil über G

Die Frage ist nicht, welche davon *plausibel* zusammenpassen, sondern welche Übergabe tatsächlich
trägt. Deshalb wird nichts behauptet, sondern dieselben Sätze durch mehrere Bauteile geschickt und
verglichen. Vier Sonden:

**P1 Redundanz F↔G.** Beide bestimmen eine Relation. Stimmen sie überein? Wenn ja, ist F in G
enthalten und ein Modellaufruf-Pfad überflüssig.

**P2 Synthese G→SPL.** Die *Feld-Zustimmung* von G (wie einig sich k Ziehungen sind) ist selbst ein
Mehrdeutigkeitsmass. Korreliert `1 - agreement(relation)` mit F's `H_norm`? Falls ja, können die
Emissionsregeln E0-E4 direkt auf G laufen, und F entfällt als eigenes Bauteil.

**P3 Konflikt E↔H.** Beide fällen ein Urteil über zwei Aussagen - E paarweise-semantisch,
H als Ableitungsprüfung. Sagen sie bei denselben Paaren dasselbe? Wo sie auseinandergehen, ist eine
der beiden Ebenen falsch verdrahtet.

**P4 Anschlussfähigkeit A.** Erzeugt der FrameDetector auf realem Material *je* einen brauchbaren
Frame? Ohne das ist die Kante A→E tot, egal wie gut E ist.

Nichts hiervon urteilt über Qualität - nur über **Anschlussfähigkeit**. Ein Bauteil kann für sich
gut und trotzdem nicht anschlussfähig sein.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import spl_builder as sb  # noqa: E402

#: Bewusst gemischt: scharf, mehrdeutig, prozedural, inhaltsleer.
STATEMENTS = [
    ("Alpine containers ship musl libc.", "scharf"),
    ("Smoking is associated with lung cancer.", "scharf"),
    ("Loading a glibc-linked binary wheel inside Alpine raises a dynamic-link error.", "scharf"),
    ("Vitamin D supplementation may reduce fracture risk in the elderly.", "mehrdeutig"),
    ("Regular exercise is good for cardiovascular health.", "mehrdeutig"),
    ("The approach seems promising.", "leer"),
]

#: Paare für P3: (A, B, was inhaltlich gilt)
PAIRS = [
    ("Alpine containers ship musl libc, no glibc.", "Alpine containers ship glibc.", "widerspruch"),
    ("Alpine containers ship musl libc, no glibc.", "Alpine uses musl libc.", "uebereinstimmung"),
    ("Binary wheels fail on musl.", "Node projects group source under src/.", "unverwandt"),
]


def probe1_and_2() -> None:
    """F↔G: dieselbe Relation? Und: ist G's Uneinigkeit ein Mehrdeutigkeitsmass wie F's H_norm?"""
    print("── P1 Redundanz (SPL-Builder vs Entailment-Parser) + P2 Synthese ──\n")
    agree = 0
    pts: list[tuple[float, float]] = []
    for text, kind in STATEMENTS:
        f = sb.project(text, "beta", n=ent.K_DRAWS)
        g = ent.parse(text, builder="beta")
        f_rel = max(f.P_r, key=f.P_r.get) if f.P_r else "-"
        g_agree = dict(g.agreement).get("relation", 0.0)
        same = f_rel == g.relation
        agree += int(same)
        pts.append((f.h_norm, 1.0 - g_agree))
        print(f"[{kind:<10}] {text[:52]}")
        print(f"     F Builder : {f_rel:<16} H_norm={f.h_norm:.3f}")
        print(f"     G Parser  : {g.relation:<16} Uneinigkeit={1 - g_agree:.3f}  "
              f"{'✓ gleich' if same else '✗ VERSCHIEDEN'}")
    print(f"\n  P1: Relation identisch in {agree}/{len(STATEMENTS)} Fällen")
    if len(pts) > 2:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        try:
            r = statistics.correlation(xs, ys)
            print(f"  P2: Korrelation H_norm ↔ Parser-Uneinigkeit  r = {r:+.3f}")
        except statistics.StatisticsError:
            print("  P2: Korrelation nicht berechenbar (eine Reihe ist konstant)")
            print(f"      H_norm: {[round(x, 3) for x in xs]}")
            print(f"      Uneing: {[round(y, 3) for y in ys]}")
    print()


def probe3() -> None:
    """E↔H: sagen Layer-9-Semantik und Ableitungsprüfung bei denselben Paaren dasselbe?"""
    print("── P3 Konflikt (Layer-9 classify vs Entailment-Auditor) ──\n")
    try:
        from desi_layer9.semantics import decision as dec
        from joni.autonomy import desi_semantics as ds
        layer = ds.get_semantic_layer()
    except Exception as exc:  # noqa: BLE001
        print(f"  Layer-9-Pfad nicht verfügbar ({type(exc).__name__}) - E-Seite übersprungen\n")
        layer = None
    for a, b, truth in PAIRS:
        e_verdict = "—"
        if layer is not None:
            m = layer.analyse_pair(a_id="a", a_text=a, b_id="b", b_text=b)
            d, _s, _w = dec.classify(m)
            e_verdict = d.value
        h = ent.audit(a, [{"text": b, "source_id": "ev"}])
        print(f"  inhaltlich: {truth}")
        print(f"     A: {a[:58]}")
        print(f"     B: {b[:58]}")
        print(f"     E Layer-9 : {e_verdict}")
        print(f"     H Auditor : {h['verdict']}  {h['violations']}")
    print()


def probe4() -> None:
    """A: erzeugt der FrameDetector auf realem Material je einen brauchbaren Frame?"""
    print("── P4 Anschlussfähigkeit (FrameDetector) ──\n")
    try:
        from desi.frames.detector import FrameDetector
    except Exception as exc:  # noqa: BLE001
        print(f"  desi nicht importierbar ({type(exc).__name__}) - übersprungen\n")
        return
    fd = FrameDetector()
    kinds: dict[str, int] = {}
    for i, (text, _k) in enumerate(STATEMENTS):
        f = fd.detect(claim_id=f"c{i}", source_text=text)
        kinds[f.frame_kind.value] = kinds.get(f.frame_kind.value, 0) + 1
    print(f"  Frames über {len(STATEMENTS)} Sätze: {kinds}")
    usable = sum(v for k, v in kinds.items() if k != "frame_undeclared")
    print(f"  brauchbar (nicht 'undeclared'): {usable}/{len(STATEMENTS)}")
    print("  -> Kante A→E trägt nur, wenn stromaufwärts jemand Frames DEKLARIERT.\n")


def main() -> int:
    probe1_and_2()
    probe3()
    probe4()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
