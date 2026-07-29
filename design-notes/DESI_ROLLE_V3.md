# DESi v3 — Vorgänge klassifizieren, nicht urteilen

**Status:** Architektur festgelegt, eine tragende Annahme **gemessen und widerlegt**, Konsequenz
eingebaut. Ersetzt `ENTAILMENT_ARCHITECTURE.md` (v2) in der Frage der Zuständigkeit; v2 bleibt als
Beschreibung dessen gültig, was gemessen wurde.

---

## 1. Die Korrektur der Zuständigkeit

Der Blindtest hat nicht DESi widerlegt. Er hat den Versuch widerlegt, aus DESi **zusätzlich** einen
deterministischen semantischen Richter zu machen. Die Verschiebung, die dahin geführt hat:

```
ursprünglich   DESi klassifiziert epistemische Vorgänge
später gebaut  DESi entscheidet, ob der Claim logisch folgt      ← Überdehnung
```

Die zurückgeholte Aufteilung:

```
Modell / Semantic Layer   erzeugt Interpretation oder Urteil
        ↓
DESi                      klassifiziert den VORGANG:
                          welche Evidenz wurde benutzt · welche Transformation fand statt ·
                          wurde verallgemeinert · wurde Modalität verändert · fehlen Belege ·
                          widersprechen sich Quellen · wie sicher und stabil war der Prozess
        ↓
Layer 9 / Policy          entscheidet nach Governance-Regeln über Persistenz
```

Der Unterschied ist keine Wortwahl. Eine Kontrolle sagte bisher:

```
Modalitätsunterschied  ⇒  Claim herabstufen
```

Das ist ein semantisches Urteil in Regelform. Richtig ist:

```
Modalitätsunterschied  ⇒  Beobachtung MODALITY_CHANGE
                          (Evidenz `possible`, Claim `asserted`, confidence 0.84)
                          ⇒ Policy msce_l2_l3_v1 ⇒ request_review
```

DESi behauptet damit nicht *„der Claim folgt nicht"*, sondern *„zwischen Evidenz und Claim wurde
eine epistemisch relevante Transformation beobachtet"*.

---

## 2. Was die Umbenennung **nicht** rettet

Eine falsche Beobachtung ist als Protokolleintrag genauso schädlich wie als Verdikt — wer sie liest,
wird identisch fehlgeleitet. Deshalb zuerst die Gegenprobe an den eingefrorenen Blinddaten: waren
die sechs Fehlauslösungen falsche *Ableitungen* (dann rettet die Umdeutung sie) oder falsche
*Klassifikationen* (dann nicht)?

| Auslösung | Klassifikation | rettet die Umdeutung sie? |
|---|---|---|
| TEST-007, -030 · `epistemic_hedge` | „Die Doku sagt X" als Hedge geführt | **nein** — sachlich falsch |
| TEST-026 · `scope_escalation` | „Eine 12 000-€-Rechnung" als `class` geführt | **nein** — ist `instance` |
| TEST-038 · `modality_escalation` | Claim „sofern der Emittent nicht ausfällt" als `asserted` | **nein** — Bedingung war erhalten |
| TEST-030 · `modality_escalation` | Evidenz `negated` vs. Claim `asserted` | teilweise — wahr, aber gehaltlos |

**Fünf von sechs Auslösungen beruhten auf einer sachlich falschen Klassifikation.** Die Umdeutung
allein hätte aus sechs falschen Verdikten sechs falsche Protokolleinträge gemacht.

---

## 3. Die zwei Beobachtungsklassen

Die Rettung liegt nicht in der Rolle, sondern in einer Trennung, die der Blindtest erzwingt: **die
Beobachtungen zerfallen in zwei Klassen mit völlig verschiedener Fehlerquelle.**

### Klasse A — Vorgangsfakten

Brauchen **keine semantische Normalisierung**. Exakt per Konstruktion, kosten nichts, können nicht
falsch klassifizieren:

```
MODEL_VERDICT_PROPOSED      Verdikt, k, Zustimmungsgrad
LOW_SAMPLE_AGREEMENT        die k Ziehungen waren uneinig
NO_MAJORITY                 keine Mehrheit — der Vorgang ist unentschieden
EVIDENCE_COUNT              Anzahl und IDs der zitierten Belege
NO_EVIDENCE_CITED           kein Beleg angegeben
CROSS_MODEL_DISAGREEMENT    zwei Häuser urteilen verschieden
RUN_INSTABILITY             das Urteil wechselte zwischen Läufen
COMPOUND_CLAIM              der Claim ist zusammengesetzt
SPLIT_UNDETERMINED          die Zerlegung hatte keine Mehrheit
SELF_SELECTED_EVIDENCE      die Evidenzauswahl stammt vom geprüften System
NO_COUNTEREVIDENCE_SEARCH   es wurde nicht nach Gegenbelegen gesucht
```

**Hier ist DESi uneingeschränkt zuständig.** Diese Schicht ist der Teil der ursprünglichen
DESi-Idee, der nie in Frage stand und nie gemessen werden muss — sie zählt und protokolliert, sie
interpretiert nicht. Die letzten beiden Einträge sind die wichtigsten und die billigsten: sie machen
sichtbar, dass ein Auditor, der nur zitierte Evidenz sieht, systematisch blind ist.

### Klasse B — semantische Transformationen

Brauchen Normalisierung, erben deren Fehlerrate:

```
MODALITY_CHANGE · QUANTIFIER_WIDENING · SCOPE_CHANGE · CONDITION_DROPPED
ENTITY_MISMATCH · CAUSAL_UPGRADE · NORMALIZATION_UNDETERMINED
```

Sie tragen `parser_dependent=True`, eine `confidence` aus der Feldzustimmung und eine **Herkunft**
(`deterministic` oder `model`). Warum die Herkunft im Datensatz steht, sagt §4.

---

## 4. Die Messung, die auch den Regelzweig kassiert

Die verbliebene Hoffnung war: die alten Kontrollen waren nur *falsch positioniert* — als
Klassifikatoren statt als Richter wären sie brauchbar. **Das ist prüfbar**, weil der externe Satz zu
jedem Fall Gold-Verstösse führt, also ein Transformationsvokabular. Drei Quellen gegen dasselbe
Gold, Dev-Satz, ein Lauf:

| Quelle | mikro-F1 | makro-F1 | tp / fp / fn |
|---|---|---|---|
| **deterministisch** (Regeln über Strukturen) | **0,25** | 0,333 | 4 / **10** / 14 |
| **Modell** (Verstossliste neben dem Urteil) | **0,727** | 0,723 | 12 / 3 / 6 |
| Vereinigung beider | 0,558 | 0,573 | 12 / 13 / 6 |

**Auch als reine Klassifikation ist der deterministische Zweig dem Modell dreifach unterlegen** —
zehn Falschpositive auf vier Treffer. Und die Vereinigung ist *schlechter* als das Modell allein: der
Regelzweig steuert fast nur Falsche bei.

> Das Problem war nicht die Rolle, sondern die Sache. **Das Erkennen einer semantischen
> Transformation ist die schwere Aufgabe, nicht das Bewerten.**

Das ist die dritte Bestätigung desselben Musters an einem Tag — nach „Regeln urteilen schlechter als
das Modell" und „Kontrollen schaden mehr als sie nützen" nun „Regeln klassifizieren schlechter als
das Modell". Die Grenze verläuft nicht zwischen *urteilen* und *beschreiben*, sondern zwischen
*Sprache verarbeiten* und *zählen*.

Nebenbefund: eine Konfidenzschwelle von 0,6 drückt die Falschpositiven von 10 auf 3, aber die Treffer
von 4 auf 3. Das ist eine Verbesserung der Präzision durch fast vollständigen Verzicht auf
Abdeckung — und es ist auf dem Dev-Satz angepasst, also keine Zahl, auf die man bauen darf.

**Blinder Fleck, ausdrücklich:** `missing_premise` — in 5 von 20 Dev-Fällen und 10 von 40
Blindfällen im Gold — hat **keine** strukturelle Entsprechung. Dass ein Schluss eine unausgesprochene
Prämisse braucht, ist keine Differenz zweier normalisierter Felder. Der deterministische Zweig kann
diesen Typ prinzipiell nicht sehen.

---

## 5. Die Konsequenz im Code

```
Klasse A   → DESi deterministisch, exakt, trägt terminale Policy-Aktionen
Klasse B   → vom MODELL bezogen (MODEL_REPORTED_TRANSFORMATION), niemals terminal
Regelzweig → bleibt als Vergleichszweig und Messgegenstand, löst NICHTS aus
```

Zwei Invarianten, beide getestet:

1. **Eine parserabhängige Beobachtung darf nichts abschliessen.** Eine Policy-Regel, die auf einer
   Klasse-B-Beobachtung `persist` oder `hold` verlangt, wird automatisch auf `request_review`
   gedeckelt und im Feld `advisory_only` vermerkt. *Unsichere Beobachtung ⇒ Aufmerksamkeit, keine
   Konsequenz.*
2. **Der deterministische Klasse-B-Zweig steht in keiner Regel der Startpolicy.** Wieder aufnehmen
   heisst: erst messen.

Dazu eine Falle, die beim Bauen zugeschnappt ist und deshalb einen eigenen Test hat: die Modellquelle
liefert **keine** Konfidenzzahl. Ein Filter, der `None` als 0.0 liest, hätte ausgerechnet den
besseren Zweig still unterdrückt und die Policy auf dem schwachen sitzen lassen. `None` heisst „nicht
geschätzt", nicht „null".

### Die Ausgabe

```json
{
  "observations": [
    {"type": "MODEL_VERDICT_PROPOSED", "class": "process", "source": "deterministic",
     "detail": {"verdict": "entailed", "k": 5, "agreement": 0.8}},
    {"type": "LOW_SAMPLE_AGREEMENT", "class": "process", "source": "deterministic",
     "detail": {"agreement": 0.8, "k": 5}},
    {"type": "EVIDENCE_COUNT", "class": "process", "detail": {"n": 3, "source_ids": ["tr_3", "tr_4", "tr_9"]}},
    {"type": "SELF_SELECTED_EVIDENCE", "class": "process"},
    {"type": "NO_COUNTEREVIDENCE_SEARCH", "class": "process"},
    {"type": "MODEL_REPORTED_TRANSFORMATION", "class": "semantic", "source": "model",
     "parser_dependent": true, "detail": {"transformation": "modal_strengthening"}}
  ],
  "decision": {"action": "request_review", "policy": "msce_l2_l3_v1",
               "reasons": ["LOW_SAMPLE_AGREEMENT ⇒ request_review",
                           "MODEL_REPORTED_TRANSFORMATION ⇒ request_review"],
               "advisory_only": []},
  "decision_authority": {"semantic_verdict": "model", "persistence_decision": "layer_9"}
}
```

Ob das Ganze am Ende `partially_entailed` oder `compatible_not_entailed` heisst, ist eine
nachgelagerte Konvention — und genau deshalb sitzt sie nicht mehr im Kern.

---

## 6. Die neue Evaluationsfrage

Die bisherige Goldfrage — *hat DESi das richtige Entailment-Verdikt geliefert?* — war für DESi die
falsche Hauptmetrik. Die passendere:

1. Erkennt DESi relevante Vorgangstypen? → **gemessen: Regelzweig 0,25 / Modellzweig 0,727**
2. Ordnet es sie nachvollziehbar zu? → Herkunft, Konfidenz und Belegbezug stehen im Datensatz
3. Sind die Klassifikationen reproduzierbar? → **offen**, Klasse A per Konstruktion ja, Klasse B
   ungemessen über Läufe
4. Kann ein Mensch den Entscheidungsweg rekonstruieren? → `reasons` + `advisory_only` + Policy-Name
5. Verhindert die Governance, dass ungeprüfte Transformationen unsichtbar persistieren? → **offen**,
   das ist die Frage, die ein neuer versiegelter Satz beantworten muss

Punkt 5 ist die eigentliche Behauptung dieser Architektur, und sie ist **nicht gemessen**. Beide
vorhandenen Sätze sind als Messinstrument verbraucht.

---

## 7. Was offen bleibt

* **Reproduzierbarkeit der Klasse-B-Klassifikation über Läufe** — nie gemessen. Die Verdikte lagen
  bei 90 % Stabilität; für die Transformationsliste gibt es keine Zahl.
* **Ein frischer versiegelter Satz**, diesmal mit Gold auf *Vorgangstypen*, nicht nur auf Verdikten.
  Ohne ihn ist die neue Hauptmetrik so ungemessen wie die alte es war.
* **Die Policy-Regeln selbst.** Jede Regel in `msce_l2_l3_v1` ist eine Behauptung darüber, was einen
  Vorgang prüfwürdig macht. Keine davon ist gemessen. Das ist derselbe Zustand, in dem der
  Kontrollkatalog war, bevor er widerlegt wurde — und deshalb steht es hier.
* **Prüflast.** Wenn `MODEL_REPORTED_TRANSFORMATION` bei jedem Verstoss eine Prüfung auslöst, ist zu
  messen, wie viele Vorgänge das trifft. Eine Governance, die alles markiert, markiert nichts.

---

## Dateien

```
experiments/msce_bridge/observations.py       Katalog, Klasse A und B, Herkunft, Konfidenz
experiments/msce_bridge/policy.py             versionierte Regelmengen, Invarianten
experiments/msce_bridge/run_observations.py   die Messung aus §4
tests/test_observations.py                    11 Invariantentests
```
