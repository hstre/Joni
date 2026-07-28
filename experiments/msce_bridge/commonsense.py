"""Ein kleiner, versionierter Commonsense-Regelbestand — das Brauchbare an der Cyc-Idee.

OpenCyc selbst taugt dafür nicht mehr: 2017 eingestellt, letzter Stand 2012, ein reduzierter
Ausschnitt des eigentlichen Cyc, schwächere Provenienz als Wikidata, und eine Integration wäre
Aufwand ohne langfristig stabile Quelle. Die *Idee* dahinter ist aber richtig — Faktenkataloge
allein reichen nicht, es fehlt das Alltagswissen, das Schlüsse überhaupt erst trägt.

Also ein eigener Bestand, klein und transparent, mit drei Eigenschaften, die OpenCyc nicht bietet:
**versioniert**, **prüfbar** (jede Regel trägt ihre eigenen Positiv- und Negativbeispiele, über die
ein Test läuft) und mit **ausdrücklichen Anwendungsgrenzen**.

Die tragende Einschränkung, und sie ist strukturell:

    **Eine Regel erzeugt nie ein Urteil, sondern benennt eine Annahme.**

Diese Regeln sind *defeasible* — sie gelten „normalerweise". Wer daraus ``entailed`` machte, hätte
genau den Fehler wieder, den die externe Evaluation aufgedeckt hat: Abwesenheit erkannter Verstösse
als Anwesenheit von Stützung zu lesen. Eine angewandte Regel liefert deshalb eine **benannte,
zitierbare Annahme mit Regel-ID** — und ein Verdikt darf dadurch höchstens ``partially_entailed``
werden, nie ``entailed``. Das ist dieselbe Haltung wie beim Weltwissens-Adapter: die Lücke
benennen, nicht füllen.

Die Regeln hier sind aus **gemessenen** Fehlschlägen der externen Blind-Evaluation abgeleitet, nicht
aus Vermutung — jede nennt den Fall, der sie motiviert hat.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

RULEBASE_VERSION = "0.1.0"


@dataclass(frozen=True)
class Rule:
    """Eine defeasible Alltagsregel. Datenobjekt, kein Code - damit sie prüfbar bleibt."""

    id: str
    version: str
    statement: str
    #: Was die Regel LIZENZIERT - immer eine Annahme, nie ein Verdikt.
    licenses: str
    #: Wann sie ausdrücklich NICHT gilt. Ohne Grenze keine Regel.
    boundary: str
    #: Woher sie kommt: der gemessene Fall, der sie nötig gemacht hat.
    motivated_by: str
    #: Prüfbarkeit: Fälle, in denen sie greift bzw. nicht greift.
    applies_to: tuple[str, ...] = field(default_factory=tuple)
    does_not_apply_to: tuple[str, ...] = field(default_factory=tuple)
    defeasible: bool = True

    def fingerprint(self) -> str:
        blob = f"{self.id}|{self.version}|{self.statement}|{self.licenses}|{self.boundary}"
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


RULES: tuple[Rule, ...] = (
    Rule(
        id="containment-transitivity",
        version="1.0",
        statement="Liegt X in Y und Y in Z, so liegt X normalerweise auch in Z.",
        licenses="die Annahme, dass X in Z liegt - als benannte Annahme, nicht als Feststellung",
        boundary="Gilt nicht bei Rollen-, Zeit- oder Zuständigkeitsgrenzen: eine Exklave liegt "
                 "geografisch in Z, staatsrechtlich aber nicht. Nicht auf Mitgliedschaft in "
                 "Organisationen übertragen.",
        motivated_by="allgemein; Grundlage für Kettenschlüsse",
        applies_to=("Ulm liegt in Baden-Württemberg; Baden-Württemberg liegt in Deutschland",),
        does_not_apply_to=("Büsingen liegt in Deutschland; Deutschland liegt in der EU-Zollunion",),
    ),
    Rule(
        id="dependency-chain",
        version="1.0",
        statement="Setzt A B voraus und ist B nicht verfügbar, ist A normalerweise behindert.",
        licenses="die Annahme, dass A nicht ohne Weiteres möglich ist - NICHT, dass A unmöglich "
                 "ist, und nur, wenn B und das Fehlende DIESELBE Entität sind",
        boundary="Greift nicht, wenn das Fehlende eine ANDERE Entität ist als die vorausgesetzte, "
                 "und nicht, wenn Alternativen/Ersatz möglich sind.",
        motivated_by="DEV-011 (gilt) und DEV-012 (gilt NICHT): dort war die vorausgesetzte "
                     "Bibliothek B, nicht verfügbar war aber C - der Auditor meldete trotzdem "
                     "entailed. Genau diese Unterscheidung fehlte.",
        applies_to=("A hängt von B ab; B ist auf der Zielplattform nicht verfügbar",),
        does_not_apply_to=("A hängt von B ab; C ist auf der Zielplattform nicht verfügbar",),
    ),
    Rule(
        id="temporal-role-succession",
        version="1.0",
        statement="Wird eine Funktion erst von A und später von B besetzt, ist das ohne "
                  "Zeitqualifikation kein Widerspruch.",
        licenses="das Zurückhalten eines Widerspruchsurteils, bis Zeitangaben vorliegen",
        boundary="Gilt nur für zeitlich besetzbare Rollen. Bei Eigenschaften, die per Definition "
                 "unveränderlich sind (Geburtsort), ist die Abweichung sehr wohl ein Widerspruch.",
        motivated_by="Lücke der Widerspruchsregel: sie vergleicht Modalität ohne Zeitbezug",
        applies_to=("A war Vorsitzender; B ist Vorsitzender",),
        does_not_apply_to=("A wurde in Ulm geboren; A wurde in Berlin geboren",),
    ),
    Rule(
        id="intervention-does-not-prove-cause",
        version="1.0",
        statement="Verschwindet ein Symptom nach Austausch von X, ist damit nicht erwiesen, dass "
                  "X die Ursache war.",
        licenses="die Annahme, dass X eine PLAUSIBLE Ursache ist - alternative Ursachen bleiben "
                 "offen und müssen genannt werden",
        boundary="Greift immer bei Einzelinterventionen ohne Kontrolle. Nur ein kontrollierter "
                 "Wechsel (Wiedereinsetzen reproduziert den Fehler) hebt sie auf.",
        motivated_by="DEV-014: 'Lampe ging nicht' + 'Birne getauscht, ging wieder' ⟹ 'Birne war "
                     "defekt' wurde als entailed gemeldet. Das ist Abduktion, kein Entailment.",
        applies_to=("Lampe ging nicht; Birne getauscht; Lampe geht - also war die Birne defekt",),
        does_not_apply_to=("Birne getauscht: geht. Alte Birne wieder eingesetzt: geht wieder "
                           "nicht.",),
    ),
    Rule(
        id="absence-is-not-refutation",
        version="1.0",
        statement="Erwähnt eine Quelle eine Behauptung nicht, ist das keine Widerlegung.",
        licenses="gar nichts - die Regel VERBIETET einen Schluss, statt einen zu erlauben",
        boundary="Umgekehrt gilt sie nicht: eine Quelle, die für Vollständigkeit einsteht "
                 "(ein Register), erlaubt sehr wohl einen Schluss aus dem Fehlen.",
        motivated_by="DEV-017: 'no evidence of data loss was found' ⟹ 'data loss did not occur' "
                     "wurde als entailed gemeldet. Im Weltwissens-Adapter bereits strukturell "
                     "verankert (Lookup.absence_is_not_refutation).",
        applies_to=("Der Bericht erwähnt keinen Datenverlust",),
        does_not_apply_to=("Das Melderegister führt die Person nicht",),
        defeasible=False,          # diese Regel ist strikt: sie verbietet, sie erlaubt nicht
    ),
)

BY_ID = {r.id: r for r in RULES}


def rulebase_fingerprint() -> str:
    """Identität des gesamten Bestands - für Versiegelung neben einer Messung."""
    return hashlib.sha256(
        "|".join(f"{r.id}:{r.fingerprint()}" for r in RULES).encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Application:
    """Eine angewandte Regel. Ergebnis ist eine ANNAHME mit Herkunft, kein Verdikt."""

    rule_id: str
    rule_version: str
    assumption: str
    boundary: str
    defeasible: bool

    def to_dict(self) -> dict:
        return {"rule_id": self.rule_id, "rule_version": self.rule_version,
                "assumption": self.assumption, "boundary": self.boundary,
                "defeasible": self.defeasible,
                "upgrades_verdict": False}


def apply_rule(rule_id: str, *, about: str) -> Application | None:
    """Wendet eine Regel benannt an. Liefert die Annahme, die dadurch AUSGESPROCHEN wird."""
    r = BY_ID.get(rule_id)
    if r is None:
        return None
    return Application(rule_id=r.id, rule_version=r.version,
                       assumption=f"{r.licenses} (bezogen auf: {about})",
                       boundary=r.boundary, defeasible=r.defeasible)


#: Die Obergrenze, die eine Regelanwendung setzt. Eine defeasible Regel kann ein Verdikt NIE auf
#: 'entailed' heben - sie macht eine Annahme explizit, sie beweist nichts.
MAX_VERDICT_WITH_RULE = "partially_entailed"


def cap_verdict(verdict: str, applications: list[Application]) -> str:
    """Deckelt ein Verdikt, sobald es auf einer defeasible Regel ruht.

    Ohne diese Deckelung wäre der Regelbestand ein Werkzeug, um Claims durchzuwinken - genau der
    Fehler, den die externe Evaluation an drei Fällen zugleich aufgedeckt hat."""
    if verdict == "entailed" and any(a.defeasible for a in applications):
        return MAX_VERDICT_WITH_RULE
    return verdict


__all__ = ["Rule", "RULES", "BY_ID", "Application", "apply_rule", "cap_verdict",
           "rulebase_fingerprint", "RULEBASE_VERSION", "MAX_VERDICT_WITH_RULE"]
