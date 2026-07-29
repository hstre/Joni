"""Entailment-Auditor v2: das Modell urteilt, die Kontrollen vetoen.

Umsetzung von ``design-notes/ENTAILMENT_ARCHITECTURE.md``. v1 liess Regeln über normalisierten
Strukturen *urteilen* und erreichte 7/20 auf der externen Blind-Evaluation, mit drei
Falschdurchlässen. Dasselbe Modell, das dort nur normalisieren durfte, urteilt direkt mit 17-18/20
bei null Falschdurchlässen (drei Läufe). Daraus die Umkehrung:

    Modell        schlägt Verdikt + Begründung vor
    Kontrollen    prüfen deterministisch die GEMESSENEN Gefahrenmuster
    DESi          akzeptiert · stuft herab · verlangt Prüfung
    Layer 9       persistiert nur das Gegovernte

**Die tragende Invariante:** Kontrollen bewegen ein Verdikt ausschliesslich auf der
Durchlass-Leiter nach unten. Sie erzeugen kein Urteil, heben keines, und setzen niemals
``contradicted`` - einen Widerspruch zu *behaupten* ist eine positive Aussage, und genau daran sind
Regeln nachweislich gescheitert (Negations-Heuristik: 43 % Falschmeldungen).

Damit kehrt sich die Fehlerrichtung um. In v1 konnte ein Parserfehler einen **Falschdurchlass**
erzeugen (ein verschluckter Konjunkt wurde zu ``entailed``). Hier speist der Parser nur die
Kontrollen: ein Fehler verfehlt entweder eine Kontrolle (Modellurteil bleibt stehen) oder löst eine
falsch aus (Herabstufung). **Beides ist die sichere Seite.**

Kostenregel, die aus der Invariante folgt: Kontrollen laufen nur auf durchlassenden Verdikten. Wer
nur herabstufen darf, hat bei einem bereits niedrigen Verdikt nichts zu tun.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402
import llm_baseline as base  # noqa: E402

#: Die Durchlass-Leiter, von stark nach schwach. `contradicted` liegt AUSSERHALB - eine Kontrolle
#: darf es nie setzen.
LADDER = ("entailed", "partially_entailed", "compatible_not_entailed", "insufficient")
_RANK = {v: i for i, v in enumerate(LADDER)}

#: Nur auf diesen Verdikten laufen Kontrollen überhaupt.
PASSING = frozenset({"entailed", "partially_entailed"})

CONTROLS = ("evidence_padding", "conjunction_coverage", "epistemic_hedge",
            "quantifier_escalation", "modality_escalation", "scope_escalation")

#: Welche Kontrollen tatsächlich herabstufen dürfen.
#:
#: **`evidence_padding` ist abgeschaltet, weil gemessen schädlich.** Der Katalog war aus v1s
#: Defektliste übernommen - ohne zu prüfen, ob v2 diese Defekte überhaupt erbt. Es erbt sie nicht:
#:
#:   Auffüll-Angriff       Modell unverändert `compatible_not_entailed`, Zustimmung 1.0
#:   Konjunktion (v1-Killer)  Modell `contradicted`  ✓
#:   epistemischer Hedge      Modell `compatible_not_entailed`  ✓
#:   Quantorensprung          Modell `compatible_not_entailed`  ✓
#:   Modalitätsverstärkung    Modell `compatible_not_entailed`  ✓
#:
#: Die Auffüll-Verwundbarkeit war eine Eigenschaft von v1s max-Aggregation, nicht des Modells. Als
#: Veto richtete die Kontrolle nur Schaden an: auf dem Dev-Satz drei Falschsperren (DEV-004, -015,
#: -018) und null gefangene Angriffe, weil ihr `_supports` auf Wortüberlappung beruht und legitime,
#: nur anders formulierte Stützung durchfallen lässt - derselbe Proxy-Fehler wie in v1.
#:
#: Die Lehre, allgemein: **ein Kontrollkatalog muss aus den gemessenen Fehlern des Systems
#: abgeleitet sein, das er bewacht - nicht aus denen seines Vorgängers.**
#:
#: Der Code bleibt stehen, damit die Kontrolle wieder aktiviert werden kann, sobald ein Modell
#: gemessen anfällig ist. Aktiviert wird sie dann über diese Menge, nicht durch Auskommentieren.
ACTIVE_CONTROLS = frozenset(CONTROLS) - {"evidence_padding"}


@dataclass(frozen=True)
class Veto:
    """Eine ausgelöste Kontrolle. Trägt ihren Grund und die Stufe, auf die sie herabsetzt."""

    control: str
    reason: str
    downgrade_to: str

    def to_dict(self) -> dict:
        return {"control": self.control, "reason": self.reason,
                "downgrade_to": self.downgrade_to, "can_upgrade": False}


def _weaker(verdict: str, steps: int = 1) -> str:
    """Eine Stufe (oder mehr) hinunter. Nie hinauf, nie aus der Leiter heraus."""
    i = _RANK.get(verdict)
    if i is None:                       # contradicted o.ä. - nicht auf der Leiter
        return verdict
    return LADDER[min(i + steps, len(LADDER) - 1)]


def apply_vetoes(verdict: str, vetoes: list[Veto]) -> str:
    """Wendet Vetos an. **Nur abwärts, nie über die Leiter hinaus, nie zu contradicted.**"""
    if verdict not in _RANK or not vetoes:
        return verdict
    worst = verdict
    for v in vetoes:
        if _RANK.get(v.downgrade_to, -1) > _RANK.get(worst, 0):
            worst = v.downgrade_to
    return worst


# ── Die Kontrollen ──────────────────────────────────────────────────────────────────────────────

def _overlaps(a: str, b: str) -> bool:
    return ent._overlaps(a, b)


def _supports(claim: ent.Structure, e: ent.Structure) -> bool:
    """Trägt dieser Beleg den Claim überhaupt - über Entität, nicht nur über Relation?"""
    rel_ok = (e.relation == claim.relation
              or (claim.relation in ent.CAUSAL and e.relation in ent.CAUSAL))
    return rel_ok and (_overlaps(e.subject, claim.subject) or _overlaps(e.object, claim.object))


def run_controls(claim: ent.Structure, evidence: list[ent.Structure], *,
                 verdict: str, propositions_covered: bool = True) -> list[Veto]:
    """Die deterministischen Kontrollen. Jede stammt aus einem gemessenen Fehlschlag."""
    if verdict not in PASSING:
        return []                        # Kostenregel: nichts herabzustufen
    vetoes: list[Veto] = []

    support = [e for e in evidence if _supports(claim, e)]

    # §7g - Evidenz-Auffüllen. ABGESCHALTET, siehe ACTIVE_CONTROLS: gemessen schädlich, weil das
    # Modell gegen den Angriff immun ist und der Entitätsproxy legitime Stützung verwirft.
    if "evidence_padding" in ACTIVE_CONTROLS and evidence and not support:
        vetoes.append(Veto("evidence_padding",
                           "kein Beleg berührt die Entitäten des Claims; unverwandte Evidenz "
                           "kann ihn nicht tragen",
                           _weaker(verdict, 2)))
        return vetoes                    # ohne Stützung sind die übrigen Prüfungen gegenstandslos

    # §7f - Konjunktionsabdeckung: jede Proposition muss getragen sein.
    if not propositions_covered:
        vetoes.append(Veto("conjunction_coverage",
                           "nicht jede Proposition der zusammengesetzten Aussage ist gedeckt",
                           _weaker(verdict)))

    # DEV-017 - epistemischer Hedge: Aussagen über die Evidenzlage tragen keinen Sachclaim.
    if support and all(e.epistemic_hedge for e in support) and not claim.epistemic_hedge:
        vetoes.append(Veto("epistemic_hedge",
                           "die stützenden Belege sprechen über die Evidenzlage ('keine Hinweise "
                           "gefunden'), nicht über die Sache",
                           _weaker(verdict)))

    if support:
        ev_q = max(ent.QUANT_RANK.get(e.quantifier, 0) for e in support)
        if ent.QUANT_RANK.get(claim.quantifier, 0) > ev_q:
            vetoes.append(Veto("quantifier_escalation",
                               f"Claim quantifiziert '{claim.quantifier}', stützende Evidenz nur "
                               f"'{ent.QUANTIFIER[ev_q]}'", _weaker(verdict)))
        ev_m = max(ent.MODAL_RANK.get(e.modality, 4) for e in support)
        if ent.MODAL_RANK.get(claim.modality, 4) > ev_m:
            vetoes.append(Veto("modality_escalation",
                               f"Claim ist '{claim.modality}', stärkster stützender Beleg nur "
                               f"'{ent.MODALITY[ev_m]}'", _weaker(verdict)))
        ev_s = max(ent.SCOPE_RANK.get(e.scope_level, 0) for e in support)
        if ent.SCOPE_RANK.get(claim.scope_level, 0) > ev_s:
            vetoes.append(Veto("scope_escalation",
                               f"Claim spricht auf Ebene '{claim.scope_level}', Evidenz nur "
                               f"'{ent.SCOPE[ev_s]}'", _weaker(verdict)))
    return vetoes


# ── Die Kette ───────────────────────────────────────────────────────────────────────────────────

@dataclass
class Result:
    claim: str
    verdict: str
    model_verdict: str
    model_agreement: float
    violations: list[str] = field(default_factory=list)
    vetoes: list[Veto] = field(default_factory=list)
    justification: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"claim": self.claim, "verdict": self.verdict,
                "model_verdict": self.model_verdict,
                "model_agreement": self.model_agreement,
                "violations": self.violations,
                "vetoes": [v.to_dict() for v in self.vetoes],
                "justification": self.justification,
                "downgraded": self.verdict != self.model_verdict,
                "provenance": {"verdict_proposed_by": "model",
                               "verdict_constrained_by": "deterministic controls",
                               "controls_can_upgrade": False}}


def audit(claim: str, evidence: list[dict], *, declared_assumptions: tuple[str, ...] = (),
          model_alias: str = None, k: int = None) -> Result:
    """Volle Kette: Modell urteilt → Kontrollen vetoen → Ergebnis mit Herkunft."""
    model_alias = model_alias or ent.PARSER
    k = k or ent.K_DRAWS

    case = {"claim": claim, "evidence": evidence,
            "declared_assumptions": list(declared_assumptions)}
    judged = base.judge(case, model_alias=model_alias, k=k)
    verdict = judged["verdict"]
    just = [f"Modellurteil '{verdict}' (Zustimmung {judged['agreement']})"]

    # Unbestimmtes Modellurteil: keine Mehrheit ⇒ kein geratenes Verdikt.
    if judged["agreement"] < 0.5:
        return Result(claim=claim, verdict="insufficient", model_verdict=verdict,
                      model_agreement=judged["agreement"], violations=judged["violations"],
                      justification=just + ["keine Mehrheit über k Ziehungen - nicht entschieden"])

    if verdict not in PASSING:
        return Result(claim=claim, verdict=verdict, model_verdict=verdict,
                      model_agreement=judged["agreement"], violations=judged["violations"],
                      justification=just + ["Kontrollen übersprungen (nichts herabzustufen)"])

    # Nur jetzt lohnt sich die Normalisierung: die Kontrollen brauchen Strukturen.
    props, split_undet = ent.split_propositions(claim, builder=model_alias)
    ev_structs = [ent.parse(e["text"], source_id=e.get("source_id", ""), builder=model_alias)
                  for e in evidence]
    claim_structs = [ent.parse(p, builder=model_alias) for p in props]

    all_vetoes: list[Veto] = []
    for cs in claim_structs:
        covered = not split_undet
        all_vetoes += run_controls(cs, ev_structs, verdict=verdict,
                                   propositions_covered=covered)

    final = apply_vetoes(verdict, all_vetoes)
    just += [f"Kontrolle {v.control}: {v.reason}" for v in all_vetoes]
    if final != verdict:
        just.append(f"herabgestuft {verdict} → {final}")
    return Result(claim=claim, verdict=final, model_verdict=verdict,
                  model_agreement=judged["agreement"], violations=judged["violations"],
                  vetoes=all_vetoes, justification=just)


__all__ = ["audit", "Result", "Veto", "run_controls", "apply_vetoes", "LADDER", "PASSING",
           "CONTROLS"]
