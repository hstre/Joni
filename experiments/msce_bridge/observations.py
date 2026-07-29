"""DESi v3: **Vorgänge klassifizieren, nicht urteilen.**

Der Blindtest hat nicht DESi widerlegt, sondern den Versuch, aus DESi zusätzlich einen
deterministischen semantischen Richter zu machen. Diese Datei zieht die Zuständigkeit zurück:

    Modell / Semantic Layer   erzeugt Interpretation oder Urteil
    DESi (hier)               klassifiziert den VORGANG, urteilt nicht
    Layer 9 / Policy          entscheidet nach Governance-Regeln über Persistenz

Der Unterschied ist keine Wortwahl. Eine Kontrolle sagte bisher::

    Modalitätsunterschied  ⇒  Claim herabstufen

Das ist ein semantisches Urteil in Regelform. Hier heisst es::

    Modalitätsunterschied  ⇒  Beobachtung MODALITY_CHANGE (Evidenz `possible`, Claim `asserted`)

Was diese Beobachtung *bedeutet*, entscheidet eine versionierte Policy im Anwendungskontext -
nicht der Klassifikator.

**Die Korrektur, die der Blindtest erzwingt.** Die Umbenennung allein rettet die alten Kontrollen
nicht. Von ihren sechs Auslösungen auf dem Blindsatz beruhten **fünf auf einer sachlich falschen
Klassifikation**, nicht bloss auf einer falschen Ableitung:

    TEST-007/030  "Die Doku sagt X" als epistemischer Hedge geführt    falsch
    TEST-026      "Eine 12 000-€-Rechnung" als `class` geführt          falsch: das ist `instance`
    TEST-038      Claim "sofern der Emittent nicht ausfällt" `asserted`  falsch: Bedingung erhalten
    TEST-030      Evidenz `negated` vs. Claim `asserted`                wahr, aber gehaltlos - der
                  Claim behauptet ja gerade, dass die Richtlinie verneint

Eine falsche Beobachtung ist als Protokolleintrag genauso schädlich wie als Verdikt - ein Mensch,
der sie liest, wird identisch fehlgeleitet. Deshalb trennt diese Datei die Beobachtungen in **zwei
Klassen mit völlig verschiedener Verlässlichkeit**, und zwar sichtbar im Datentyp:

**Klasse A - Vorgangsfakten.** Brauchen *keine* semantische Normalisierung: Zustimmungsgrad über k
Ziehungen, Anzahl der Belege, Uneinigkeit zweier Modelle, Verdikt-Wechsel zwischen Läufen, wer die
Evidenz ausgewählt hat, ob überhaupt nach Gegenbelegen gesucht wurde. Sie sind **exakt per
Konstruktion**, kosten nichts und können nicht falsch sein. Hier ist DESi uneingeschränkt zuständig.

**Klasse B - semantische Transformationen.** Quantorenerweiterung, Modalitätsänderung,
Reichweitenwechsel, fallengelassene Bedingung. Sie erben die Fehlerrate des Parsers - blind
gemessen: 5 von 6 Emissionen falsch. Sie tragen deshalb `parser_dependent=True` und eine
`confidence`, die aus der Feldzustimmung der Normalisierung stammt, und eine Policy darf auf ihnen
**keine automatische Persistenzentscheidung** treffen.

**Und dann die Messung, die auch das noch kassiert.** Die Vermutung war, die alten Kontrollen seien
nur *falsch positioniert* gewesen - als Klassifikatoren statt als Richter wären sie brauchbar.
Gemessen auf dem Dev-Satz gegen die Gold-Verstösse, drei Quellen gegen dasselbe Gold::

    deterministisch (diese Datei)   mikro-F1 0.25    tp 4 / fp 10 / fn 14
    Modell (Verstossliste)          mikro-F1 0.727   tp 12 / fp 3 / fn 6
    Vereinigung                     mikro-F1 0.558   - der Regelzweig fügt vor allem Falsche hinzu

**Auch als reine Klassifikation ist der deterministische Zweig dem Modell dreifach unterlegen.** Das
Problem war also nicht die Rolle, sondern die Sache: das Erkennen einer semantischen Transformation
*ist* die schwere Aufgabe, nicht das Bewerten. Deshalb wird Klasse B in der Policy **vom Modell
bezogen** (``model_transformations``), und die deterministischen Emitter unten bleiben als
Messgegenstand und Vergleichszweig stehen - nicht als Auslöser.

Was hier bewusst NICHT passiert: kein Verdikt, keine Herabstufung, keine Wahrheitsaussage. Eine
Beobachtung sagt nie „der Claim folgt nicht", sondern „zwischen Evidenz und Claim wurde eine
epistemisch relevante Transformation beobachtet".
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entailment as ent  # noqa: E402

#: Beobachtungsklassen. Der Unterschied ist die Fehlerquelle, nicht der Gegenstand.
PROCESS = "process"        # exakt per Konstruktion, parserunabhängig
SEMANTIC = "semantic"      # normalisierungsabhängig, fehlerbehaftet, trägt confidence

#: Das geschlossene Beobachtungsvokabular. Erweiterungen sind eine Katalogänderung mit Version,
#: keine Codeänderung im Aufrufer.
OBSERVATIONS: dict[str, str] = {
    # ── Klasse A: Vorgangsfakten ────────────────────────────────────────────────────────────────
    "MODEL_VERDICT_PROPOSED": "Das Modell hat ein Urteil vorgeschlagen.",
    "LOW_SAMPLE_AGREEMENT": "Die k Ziehungen waren sich uneinig.",
    "NO_MAJORITY": "Keine Mehrheit über k Ziehungen - der Vorgang ist unentschieden.",
    "EVIDENCE_COUNT": "Anzahl der zitierten Belege.",
    "NO_EVIDENCE_CITED": "Es wurde kein Beleg angegeben.",
    "CROSS_MODEL_DISAGREEMENT": "Zwei Modelle aus verschiedenen Häusern urteilen verschieden.",
    "RUN_INSTABILITY": "Das Urteil wechselte zwischen wiederholten Läufen.",
    "SELF_SELECTED_EVIDENCE": "Die Evidenzauswahl stammt vom geprüften System selbst.",
    "NO_COUNTEREVIDENCE_SEARCH": "Es wurde nicht nach Gegenbelegen gesucht.",
    "COMPOUND_CLAIM": "Der Claim ist zusammengesetzt und wurde zerlegt.",
    "SPLIT_UNDETERMINED": "Die Zerlegung des Claims ergab keine Mehrheit.",
    # ── Klasse B: semantische Transformationen ──────────────────────────────────────────────────
    "MODALITY_CHANGE": "Claim und Evidenz stehen auf verschiedenen Sicherheitsstufen.",
    "QUANTIFIER_WIDENING": "Der Claim quantifiziert weiter als die Evidenz.",
    "SCOPE_CHANGE": "Der Claim spricht auf anderer Abstraktionsebene als die Evidenz.",
    "CONDITION_DROPPED": "Eine Bedingung der Evidenz fehlt im Claim.",
    "ENTITY_MISMATCH": "Kein Beleg berührt die Entitäten des Claims.",
    "CAUSAL_UPGRADE": "Der Claim behauptet Wirkung, die Evidenz nur Zusammenhang.",
    "NORMALIZATION_UNDETERMINED": "Ein Strukturfeld hatte keine Mehrheit.",
    "MODEL_REPORTED_TRANSFORMATION": "Das Modell hat eine epistemische Transformation benannt.",
}

#: Gemessene Güte der beiden Klasse-B-Quellen gegen die Gold-Verstösse des externen Dev-Satzes
#: (20 Fälle, ein Lauf, NICHT blind). Steht hier, damit niemand den deterministischen Zweig
#: einschaltet, ohne die Zahl gesehen zu haben.
MEASURED_F1 = {"deterministic": 0.25, "model": 0.727, "union": 0.558}

_CLASS = {k: (SEMANTIC if k in {
    "MODALITY_CHANGE", "QUANTIFIER_WIDENING", "SCOPE_CHANGE", "CONDITION_DROPPED",
    "ENTITY_MISMATCH", "CAUSAL_UPGRADE", "NORMALIZATION_UNDETERMINED",
    "MODEL_REPORTED_TRANSFORMATION"} else PROCESS)
          for k in OBSERVATIONS}

#: Herkunft einer Beobachtung. Nicht kosmetisch: die beiden Quellen haben gemessen sehr
#: verschiedene Fehlerraten, und eine Policy muss das unterscheiden können.
DETERMINISTIC = "deterministic"
MODEL = "model"

CATALOGUE_VERSION = "obs-v3.0.0"


@dataclass(frozen=True)
class Observation:
    """Ein klassifizierter Vorgang. **Kein Urteil, keine Wahrheitsaussage.**"""

    type: str
    detail: dict = field(default_factory=dict)
    #: Nur für Klasse B gesetzt. Klasse A hat keine Konfidenz, weil sie nichts schätzt.
    confidence: float | None = None
    evidence_refs: tuple[str, ...] = ()
    #: Wer hat klassifiziert - die Regeln oder das Modell? Gemessen unterscheiden sie sich um
    #: den Faktor drei (MEASURED_F1), also muss es im Datensatz stehen.
    source: str = DETERMINISTIC

    @property
    def observation_class(self) -> str:
        return _CLASS.get(self.type, SEMANTIC)

    @property
    def parser_dependent(self) -> bool:
        return self.observation_class == SEMANTIC

    def to_dict(self) -> dict:
        d = {"type": self.type, "class": self.observation_class, "source": self.source,
             "parser_dependent": self.parser_dependent,
             "description": OBSERVATIONS.get(self.type, ""), "detail": self.detail}
        if self.evidence_refs:
            d["evidence_refs"] = list(self.evidence_refs)
        if self.confidence is not None:
            d["confidence"] = round(self.confidence, 3)
        return d


def _agreement(s: ent.Structure, *fields: str) -> float:
    """Konfidenz einer Beobachtung = schwächste Feldzustimmung, auf der sie ruht.

    Eine Beobachtung über die Modalität ist höchstens so verlässlich wie die Mehrheit, mit der die
    Modalität normalisiert wurde. Fehlt der Wert, gilt 0.0 - **nicht** 1.0: eine unbekannte
    Verlässlichkeit ist keine hohe.
    """
    a = dict(s.agreement)
    return min((a.get(f, 0.0) for f in fields), default=0.0)


# ── Klasse A: Vorgangsfakten ────────────────────────────────────────────────────────────────────

def process_observations(*, model_verdict: str, agreement: float, k: int,
                         evidence: list[dict], propositions: list[str] | None = None,
                         split_undetermined: bool = False,
                         second_opinion: str | None = None,
                         prior_run_verdicts: tuple[str, ...] = (),
                         evidence_self_selected: bool = True,
                         counterevidence_searched: bool = False) -> list[Observation]:
    """Exakt per Konstruktion. Kostet keinen Modellaufruf und kann nicht falsch klassifizieren.

    Genau deshalb ist das die Schicht, auf der eine Policy ohne Vorbehalt handeln darf.
    """
    obs = [Observation("MODEL_VERDICT_PROPOSED",
                       {"verdict": model_verdict, "k": k, "agreement": agreement}),
           Observation("EVIDENCE_COUNT",
                       {"n": len(evidence),
                        "source_ids": [e.get("source_id", "") for e in evidence]})]
    if not evidence:
        obs.append(Observation("NO_EVIDENCE_CITED", {}))
    if agreement < 0.5:
        obs.append(Observation("NO_MAJORITY", {"agreement": agreement, "k": k}))
    elif agreement < 1.0:
        obs.append(Observation("LOW_SAMPLE_AGREEMENT", {"agreement": agreement, "k": k}))
    if second_opinion and second_opinion != model_verdict:
        obs.append(Observation("CROSS_MODEL_DISAGREEMENT",
                               {"primary": model_verdict, "second": second_opinion}))
    if prior_run_verdicts and any(v != model_verdict for v in prior_run_verdicts):
        obs.append(Observation("RUN_INSTABILITY",
                               {"this_run": model_verdict, "prior": list(prior_run_verdicts)}))
    if propositions and len(propositions) > 1:
        obs.append(Observation("COMPOUND_CLAIM", {"n": len(propositions),
                                                  "propositions": list(propositions)}))
    if split_undetermined:
        obs.append(Observation("SPLIT_UNDETERMINED", {}))
    # Zwei Beobachtungen über die Erhebung selbst. Sie sind der Grund, warum ein Auditor, der nur
    # die zitierte Evidenz sieht, systematisch blind ist - und sie kosten nichts, ausser dass man
    # sie hinschreibt.
    if evidence_self_selected:
        obs.append(Observation("SELF_SELECTED_EVIDENCE",
                               {"note": "Belege wurden vom geprüften System gewählt; nicht "
                                        "zitierte Gegenbelege sind unsichtbar"}))
    if not counterevidence_searched:
        obs.append(Observation("NO_COUNTEREVIDENCE_SEARCH", {}))
    return obs


# ── Klasse B: semantische Transformationen ──────────────────────────────────────────────────────

def _relevant(claim: ent.Structure, e: ent.Structure) -> bool:
    """Bezug über Entitäten, nicht nur über Relationsgleichheit."""
    return ent._overlaps(e.subject, claim.subject) or ent._overlaps(e.object, claim.object)


def semantic_observations(claim: ent.Structure,
                          evidence: list[ent.Structure]) -> list[Observation]:
    """Normalisierungsabhängig - und blind gemessen die schwache Hälfte.

    Jede Beobachtung hier ist ein *Vergleich zweier normalisierter Felder*, nicht ein Urteil über
    den Inhalt. Sie sagt „Evidenz steht auf `possible`, Claim auf `asserted`" - nicht „der Claim ist
    zu stark". Was das bedeutet, entscheidet die Policy.
    """
    obs: list[Observation] = []
    undet = tuple(claim.undetermined) + tuple(f for e in evidence for f in e.undetermined)
    if undet:
        obs.append(Observation("NORMALIZATION_UNDETERMINED",
                               {"fields": sorted(set(undet))}, confidence=0.0))

    rel = [e for e in evidence if _relevant(claim, e)]
    if evidence and not rel:
        obs.append(Observation("ENTITY_MISMATCH",
                               {"claim_subject": claim.subject, "claim_object": claim.object},
                               confidence=_agreement(claim, "subject", "object")))
        return obs                       # ohne Bezug sind die übrigen Vergleiche gegenstandslos
    if not rel:
        return obs

    refs = tuple(e.source_id for e in rel if e.source_id)

    ev_m = max(rel, key=lambda e: ent.MODAL_RANK.get(e.modality, 0))
    if ent.MODAL_RANK.get(claim.modality, 0) != ent.MODAL_RANK.get(ev_m.modality, 0):
        direction = ("strengthened" if ent.MODAL_RANK.get(claim.modality, 0)
                     > ent.MODAL_RANK.get(ev_m.modality, 0) else "weakened")
        obs.append(Observation("MODALITY_CHANGE",
                               {"evidence_modality": ev_m.modality,
                                "claim_modality": claim.modality, "direction": direction},
                               confidence=min(_agreement(claim, "modality"),
                                              _agreement(ev_m, "modality")),
                               evidence_refs=refs))

    ev_q = max(rel, key=lambda e: ent.QUANT_RANK.get(e.quantifier, 0))
    if ent.QUANT_RANK.get(claim.quantifier, 0) > ent.QUANT_RANK.get(ev_q.quantifier, 0):
        obs.append(Observation("QUANTIFIER_WIDENING",
                               {"evidence_quantifier": ev_q.quantifier,
                                "claim_quantifier": claim.quantifier},
                               confidence=min(_agreement(claim, "quantifier"),
                                              _agreement(ev_q, "quantifier")),
                               evidence_refs=refs))

    ev_s = max(rel, key=lambda e: ent.SCOPE_RANK.get(e.scope_level, 0))
    if ent.SCOPE_RANK.get(claim.scope_level, 0) != ent.SCOPE_RANK.get(ev_s.scope_level, 0):
        # Richtung mitführen und NICHT bewerten: eine Verengung (class → instance) ist ein völlig
        # normaler Schluss. Genau das hat die alte Kontrolle auf TEST-026 falsch gemacht, indem sie
        # jede Differenz als Erweiterung las.
        direction = ("widened" if ent.SCOPE_RANK.get(claim.scope_level, 0)
                     > ent.SCOPE_RANK.get(ev_s.scope_level, 0) else "narrowed")
        obs.append(Observation("SCOPE_CHANGE",
                               {"evidence_scope": ev_s.scope_level,
                                "claim_scope": claim.scope_level, "direction": direction},
                               confidence=min(_agreement(claim, "scope_level"),
                                              _agreement(ev_s, "scope_level")),
                               evidence_refs=refs))

    dropped = [c for e in rel for c in e.conditions
               if not any(ent._overlaps(c, cc) for cc in claim.conditions)]
    if dropped:
        obs.append(Observation("CONDITION_DROPPED",
                               {"evidence_conditions":
                                    sorted({c for e in rel for c in e.conditions}),
                                "claim_conditions": list(claim.conditions),
                                "missing": sorted(set(dropped))},
                               confidence=min(_agreement(claim, "conditions"),
                                              min(_agreement(e, "conditions") for e in rel)),
                               evidence_refs=refs))

    if claim.relation in ent.CAUSAL and all(e.relation == "correlates_with" for e in rel):
        obs.append(Observation("CAUSAL_UPGRADE",
                               {"evidence_relation": "correlates_with",
                                "claim_relation": claim.relation},
                               confidence=min(_agreement(claim, "relation"),
                                              min(_agreement(e, "relation") for e in rel)),
                               evidence_refs=refs))
    return obs


def model_transformations(violations: list[str]) -> list[Observation]:
    """Klasse B **aus der Modellquelle** - der gemessen dreifach bessere Zweig (0.727 vs. 0.25).

    Das Modell liefert seine Transformationsliste ohnehin neben dem Urteil; sie kostet nichts extra.
    Sie wird hier als Beobachtung geführt, nicht als Urteil: ``modal_strengthening`` heisst „eine
    Verstärkung wurde benannt", nicht „der Claim ist unzulässig".

    Ohne ``confidence``-Zahl, weil es keine gibt: die Verstösse entstehen aus demselben
    Mehrheitsentscheid wie das Verdikt, aber pro Verstoss, nicht pro Fall. Eine erfundene Konfidenz
    wäre schlechter als keine.
    """
    return [Observation("MODEL_REPORTED_TRANSFORMATION", {"transformation": v}, source=MODEL)
            for v in violations]


__all__ = ["Observation", "OBSERVATIONS", "CATALOGUE_VERSION", "PROCESS", "SEMANTIC",
           "DETERMINISTIC", "MODEL", "MEASURED_F1",
           "process_observations", "semantic_observations", "model_transformations"]
