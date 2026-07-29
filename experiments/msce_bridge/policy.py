"""Layer-9-Policy: was darf mit einem klassifizierten Vorgang geschehen?

Getrennt von ``observations.py`` gehalten, weil die Trennung der ganze Punkt ist. Der Klassifikator
beschreibt einen Vorgang und ist **anwendungsunabhängig**; die Policy legt fest, was eine
Beschreibung in *diesem* Kontext bedeutet, und ist **versioniert und austauschbar**. Dieselbe
Beobachtung kann in einem klinischen Kontext eine Prüfung auslösen und in einem Logging-Kontext
nichts.

    Beobachtung   MODALITY_CHANGE (Evidenz `possible`, Claim `asserted`, confidence 0.84)
    Policy        msce_l2_l3_v1  ⇒  request_review

Die Policy sagt damit **nicht** „der Claim ist nicht entailed". Sie sagt: unter diesen Regeln wird
dieser Vorgang nicht ungeprüft persistent.

**Die tragende Invariante, aus dem Blindtest.** Beobachtungen der Klasse B (semantisch,
parserabhängig) beruhten dort in 5 von 6 Fällen auf einer sachlich falschen Klassifikation. Eine
Policy darf auf ihnen deshalb **niemals eine terminale Entscheidung** treffen - sie darf einen
Vorgang zur Prüfung markieren, aber nicht verwerfen und nicht durchwinken. Nur Klasse A
(Vorgangsfakten, exakt per Konstruktion) trägt terminale Aktionen.

**Und die zweite Invariante, aus der Klassifikationsmessung.** Klasse B wird **vom Modell bezogen**,
nicht von den Regeln: gegen dieselben Gold-Verstösse erreicht das Modell mikro-F1 0.727, der
deterministische Zweig 0.25 bei 10 Falschpositiven auf 4 Treffer. Eine Policy, die auf dem
Regelzweig auslöst, erzeugt vor allem Prüflast ohne Anlass. Die deterministischen Typen stehen
deshalb in **keiner** Regel dieser Policy.

Das ist die formale Fassung der Lehre: **eine unsichere Beobachtung darf Aufmerksamkeit erzeugen,
keine Konsequenz.**
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import observations as obs  # noqa: E402

#: Aktionen, aufsteigend nach Eingriffstiefe. `hold` ist die stärkste, `persist` die schwächste.
PERSIST = "persist"
REQUEST_REVIEW = "request_review"
HOLD = "hold"
_RANK = {PERSIST: 0, REQUEST_REVIEW: 1, HOLD: 2}

#: Aktionen, die eine Sache abschliessen. Auf einer Klasse-B-Beobachtung nicht zulässig.
TERMINAL = frozenset({PERSIST, HOLD})


@dataclass(frozen=True)
class Decision:
    action: str
    policy: str
    reasons: tuple[str, ...]
    #: Beobachtungen, die wegen ihrer Klasse *nicht* terminal wirken durften.
    advisory_only: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"action": self.action, "policy": self.policy, "reasons": list(self.reasons),
                "advisory_only": list(self.advisory_only)}


@dataclass(frozen=True)
class Policy:
    """Eine versionierte Regelmenge. Reine Daten - Änderungen sind Katalogänderungen, kein Code.

    ``rules`` bildet Beobachtungstyp auf Aktion ab. ``min_confidence`` unterdrückt
    Klasse-B-Beobachtungen, deren Normalisierung zu wackelig war, um überhaupt Aufmerksamkeit zu
    verdienen - ohne diese Schwelle würde die gemessene Parser-Fehlerrate als Prüflast
    weitergereicht.
    """

    name: str
    rules: dict[str, str]
    min_confidence: float = 0.6
    default: str = PERSIST

    def decide(self, items: list[obs.Observation]) -> Decision:
        action = self.default
        reasons: list[str] = []
        advisory: list[str] = []
        for o in items:
            want = self.rules.get(o.type)
            if want is None:
                continue
            if o.parser_dependent:
                # Die Schwelle greift nur, wo es überhaupt eine Konfidenz GIBT. `None` heisst
                # „nicht geschätzt", nicht „null" - sonst hätte der Filter ausgerechnet die
                # Modellquelle verschluckt, die keine Konfidenzzahl mitliefert und der gemessen
                # bessere Zweig ist. Die Deckelung auf REQUEST_REVIEW gilt trotzdem für beide.
                if o.confidence is not None and o.confidence < self.min_confidence:
                    advisory.append(f"{o.type} (confidence {o.confidence:.2f} "
                                    f"< {self.min_confidence})")
                    continue
                if want in TERMINAL:
                    # Invariante: eine parserabhängige Beobachtung darf nichts abschliessen.
                    advisory.append(f"{o.type} (Klasse B - terminale Aktion '{want}' "
                                    f"auf Prüfung herabgesetzt)")
                    want = REQUEST_REVIEW
            if _RANK[want] > _RANK[action]:
                action = want
            if _RANK[want] > 0:
                reasons.append(f"{o.type} ⇒ {want}")
        return Decision(action=action, policy=self.name, reasons=tuple(reasons),
                        advisory_only=tuple(advisory))


#: Die Startpolicy für den MSCE-Fall an der Grenze L2 → L3. Bewusst knapp: jede Regel hier ist eine
#: Behauptung darüber, was einen Vorgang prüfwürdig macht, und keine davon ist bisher gemessen.
MSCE_L2_L3_V1 = Policy(
    name="msce_l2_l3_v1",
    rules={
        # Klasse A - dürfen abschliessen
        "NO_MAJORITY": HOLD,                     # unentschieden ist kein Ergebnis
        "NO_EVIDENCE_CITED": HOLD,
        "SPLIT_UNDETERMINED": HOLD,
        "LOW_SAMPLE_AGREEMENT": REQUEST_REVIEW,
        "CROSS_MODEL_DISAGREEMENT": REQUEST_REVIEW,
        "RUN_INSTABILITY": REQUEST_REVIEW,
        # Klasse B aus der MODELLQUELLE - wird durch die erste Invariante auf REQUEST_REVIEW
        # gedeckelt, auch wenn sie der bessere Zweig ist.
        "MODEL_REPORTED_TRANSFORMATION": REQUEST_REVIEW,
        # Klasse B aus dem REGELZWEIG steht bewusst in keiner Regel: mikro-F1 0.25, 10
        # Falschpositive auf 4 Treffer. Er bleibt im Katalog als Vergleichszweig und
        # Messgegenstand, löst aber nichts aus. Wieder aufnehmen heisst: erst messen.
        "NORMALIZATION_UNDETERMINED": REQUEST_REVIEW,   # Ausnahme: sagt nur "unbestimmt",
        # das ist eine Aussage über die Messung selbst, nicht über den Satz.
    },
    min_confidence=0.6,
)

#: Beobachtungen wie SELF_SELECTED_EVIDENCE und NO_COUNTEREVIDENCE_SEARCH stehen absichtlich in
#: keiner Regel: sie treffen auf praktisch jeden Vorgang zu und wären als Auslöser wertlos. Sie
#: gehören ins Protokoll, damit sichtbar bleibt, unter welcher Erhebungslage geurteilt wurde.

__all__ = ["Policy", "Decision", "MSCE_L2_L3_V1", "PERSIST", "REQUEST_REVIEW", "HOLD", "TERMINAL"]
