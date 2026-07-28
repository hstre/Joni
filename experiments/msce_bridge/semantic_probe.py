"""Der Lauf OHNE Einschränkungen: DESis echter Semantic Layer auf den MSCE-L3-Einträgen.

Der erste Prototyp (``adjudicate.py``) hatte drei selbstgesetzte Grenzen: kein Semantic Layer, keine
Widerspruchserkennung, nur deterministische Prüfungen. Dieses Skript hebt sie auf und misst, was
dabei herauskommt. Voraussetzungen (beide hier nachinstalliert, nicht Teil von Jonis Laufzeit):

    DESI_ROOT=<checkout von hstre/DESi>   # liefert desi.frames / desi.logic / desi.frame_tension
    pip install fastembed                 # liefert BAAI/bge-small-en-v1.5, den Embedding-Kanal

Gemessen wird in drei Stufen, und jede Stufe hat ihr eigenes Ergebnis:

**Stufe 1 - Einzelsatz.** FrameDetector und LogicalAuditor auf jeden L3-Eintrag einzeln. Beide
liefern für *jeden* Eintrag dasselbe: ``frame_undeclared`` (confidence 0.0, "no marker, no rule
bucket matched") und ``gap_detected`` ("no 'Therefore' marker found"). Das ist **kein**
Domänenproblem - dieselben Werte kommen für klinische Sätze heraus, für die DESi gebaut wurde. Die
beiden Komponenten beurteilen *Argumentationsketten mit expliziten Markern*, nicht freistehende
Behauptungen. Ein L3-Eintrag ist eine freistehende Behauptung. Sie beantworten also schlicht eine
andere Frage.

**Stufe 2 - paarweise, ohne Embedding.** Layer 9 verweigert korrekt das Urteil: *"frame undeclared /
undecidable and no semantic projector - cannot decide"* → ``insufficient`` /
``human-review-required``. Es fällt **nicht** auf die lexikalische Notlösung zurück. Das ist die
Governance-Eigenschaft, die wir immer behauptet haben, und sie hält.

**Stufe 3 - paarweise, mit Embedding.** Jetzt entscheidet Layer 9 - und hier liegt der Befund.
Über alle Paare des Korpus werden **66 von 153 (43 %) als ``contradictory`` geurteilt**, obwohl der
Korpus fast ausschließlich aus *einander stützenden* Aussagen über dieselbe Umgebung besteht. Es
gibt darin kein einziges echtes A-und-nicht-A.

Die Ursache ist präzise lokalisierbar. ``_polarity_clash`` ist
``antonym_clash(a,b) or (is_negated(a) != is_negated(b))``, und in allen geprüften Fehlurteilen ist
``antonym_clash`` **False** - es feuert allein die *Negationswort-Asymmetrie*:

    "Alpine uses musl libc"                  is_negated=False
    "Alpine containers ship musl libc,
     no glibc"                               is_negated=True    → 'opposed'

Die beiden Sätze stimmen überein. In ``decision._from_distance`` trifft das dann auf

    if d <= DIST_SUPPORTS and m.polarity_clash:
        return (CONTRADICTORY, SYNTHESIS_REJECTED, "close in meaning but opposed in polarity")

Nah beieinander + ein Negationswort auf einer Seite ⇒ Widerspruch behauptet. Damit steht an genau
dieser Stelle eine **lexikalische Heuristik als semantisches Urteil** - dieselbe Regel, die das
Modul an jeder anderen Stelle ausdrücklich verbietet.

**Der vorgeschlagene Fix, hier nur simuliert, nicht angewandt:** eine lexikalische Polarität darf
eine Verschmelzung *verhindern*, aber keinen Widerspruch *behaupten*. Bei undeklarierten Frames also
``insufficient / human-review-required`` statt ``contradictory``. Wirkung auf dem Korpus: 66 → 0
Falschmeldungen. Der Preis ist ehrlich zu nennen: das **eine** echte Gegensatzpaar
("ships musl libc, no glibc" vs. "ships glibc") wird dann ebenfalls nur noch zur menschlichen
Prüfung geleitet statt abgelehnt. Mit Embedding + Negationsmarker allein ist es nicht von einer
Übereinstimmung zu unterscheiden - beide sind nah und negations-asymmetrisch.

Für ein Validierungs-Tor ist das die richtige Richtung: nicht zu entscheiden ist sicher, korrektes
Wissen fälschlich zu verwerfen nicht. Aber es heißt eben auch: **DESi liefert auf diesen Daten
derzeit keine Widerspruchserkennung.**

``decision.py`` liegt übrigens *außerhalb* von ``joni_core.lock`` (der sperrt 17 Module direkt unter
``desi_layer9/``, aber nicht das ``semantics/``-Unterpaket). Der Fix wäre also technisch erlaubt -
er wird hier trotzdem nicht angewandt, weil er Jonis Konfliktbildung, AleXiona und alles andere
mitbetrifft, was auf dieser Regel steht. Das ist eine Architekturentscheidung, kein Nebenbefund.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))


def load_entries(corpus: Path) -> list[str]:
    rows = json.loads(corpus.read_text(encoding="utf-8"))
    return sorted({f"{e['label']} {e['description']}"
                   for r in rows
                   for facet in ("environment", "inference", "constraints")
                   for e in (r.get("structure") or {}).get(facet) or []})


def stage1_single(entries: list[str]) -> dict:
    """Frame + logical audit per single entry. Expect: no discrimination at all."""
    from desi.frames.detector import FrameDetector
    from desi.logic.audit import LogicalAuditor
    fd, la = FrameDetector(), LogicalAuditor()
    frames: dict[str, int] = {}
    audits: dict[str, int] = {}
    for i, t in enumerate(entries):
        f = fd.detect(claim_id=f"c{i}", source_text=t)
        a = la.audit(t, claim_id=f"c{i}")
        frames[str(f.frame_kind.value)] = frames.get(str(f.frame_kind.value), 0) + 1
        audits[str(a.state.value)] = audits.get(str(a.state.value), 0) + 1
    return {"frames": frames, "audits": audits}


def stage3_pairs(entries: list[str]) -> dict:
    """All pairs through the full Layer 9 decision, plus the simulated fix."""
    from desi_layer9.semantics import decision as dec
    from joni.autonomy import desi_semantics as ds
    layer = ds.get_semantic_layer()
    now: dict[str, int] = {}
    fixed: dict[str, int] = {}
    false_contradictions: list[tuple] = []
    for a, b in itertools.combinations(entries, 2):
        m = layer.analyse_pair(a_id="a", a_text=a, b_id="b", b_text=b)
        d, _s, _why = dec.classify(m)
        now[d.value] = now.get(d.value, 0) + 1
        # simulated fix: a lexical polarity may WITHHOLD a merge, never ASSERT opposition
        v = ("insufficient-semantic-evidence"
             if d.value == "contradictory" and not m.frames_declared else d.value)
        fixed[v] = fixed.get(v, 0) + 1
        if d.value == "contradictory":
            false_contradictions.append((round(m.cosine_distance or 0.0, 3), a, b))
    return {"now": now, "fixed": fixed, "flagged": sorted(false_contradictions)}


def main() -> int:
    corpus = Path(__file__).with_name("corpus.json")
    entries = load_entries(corpus)
    print(f"L3-Einträge: {len(entries)}  ->  Paare: {len(entries) * (len(entries) - 1) // 2}\n")

    s1 = stage1_single(entries)
    print("Stufe 1 - Einzelsatz (Frame / logisches Audit):")
    print(f"   Frames: {s1['frames']}")
    print(f"   Audits: {s1['audits']}")
    print("   -> keinerlei Differenzierung; die Komponenten prüfen Argumentketten, "
          "nicht Behauptungen.\n")

    from joni.autonomy import embeddings
    chan = (f"aktiv - {embeddings.info()}" if embeddings.available()
            else "FEHLT (pip install fastembed)")
    print(f"Embedding-Kanal: {chan}\n")

    s3 = stage3_pairs(entries)
    print("Stufe 3 - alle Paare durch Layer 9:")
    print(f"   IST : {dict(sorted(s3['now'].items(), key=lambda kv: -kv[1]))}")
    print(f"   FIX : {dict(sorted(s3['fixed'].items(), key=lambda kv: -kv[1]))}")
    n = sum(s3["now"].values())
    c = s3["now"].get("contradictory", 0)
    print(f"\n   als Widerspruch geurteilt: {c}/{n} ({c / n:.0%}) - in einem Korpus ohne "
          "echte Gegensätze")
    for cos, a, b in s3["flagged"][:10]:
        print(f"      cos={cos:<6} {a[:44]:<44} || {b[:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
