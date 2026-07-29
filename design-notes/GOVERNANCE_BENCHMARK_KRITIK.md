# Kritik des Governance-Value-Benchmarks v1

Geprüft, bevor eine Zahl daraus zitiert wird. Die sechs Fragen des Auftrags werden am Ende einzeln
beantwortet; zuerst die Befunde, weil zwei davon die Aussagekraft des Benchmarks grundsätzlich
begrenzen.

---

## Befund 1 — Schlüsselpräsenz ersetzt jede Prüfung

Vier Beobachtungstypen beruhen auf einem *Vergleich zweier Werte*:

```
evidence_changed_after_audit        content_hash        vs  content_hash_at_audit
prompt_changed_after_validation     prompt_hash         vs  prompt_hash_at_validation
model_changed_without_revalidation  judge_model         vs  judge_model_at_validation
run_instability                     repeat_run_verdicts  untereinander
```

Der jeweils zweite Wert steht **nur in den defekten Fällen** im JSON. In den sauberen Fällen fehlt
das Feld ganz.

| | Dev (20) | Blind (40) |
|---|---|---|
| Fälle mit `content_hash_at_audit` | 2 | 2 |
| davon mit **abweichendem** Wert | **2** | **2** |
| Fälle mit `prompt_hash_at_validation` | 2 | 2 |
| davon abweichend | **2** | **2** |
| Fälle mit `judge_model_at_validation` | 1 | 2 |
| davon abweichend | **1** | **2** |
| Fälle mit `repeat_run_verdicts` | 1 | 3 |
| davon instabil | **1** | **3** |

**Es gibt im gesamten Datensatz keinen einzigen Gegenfall.** Damit gilt ausnahmslos

```
optionaler Schlüssel vorhanden   ⇔   Regel verletzt
```

Ein Programm, das **nichts vergleicht** und nur `"content_hash_at_audit" in evidence` prüft, ist von
einer echten Integritätsprüfung nicht unterscheidbar. Genau dafür ist der dritte Arm `null` gebaut,
und er liefert auf allen 60 Fällen (Dev + Blind) exakt dieselbe Ausgabe wie die vollständige
Implementierung.

**Folge:** Keine Zahl aus diesem Benchmark stützt die Aussage, ein System *erkenne* Manipulation an
Evidenz, Prompt oder Modell. Sie stützt nur, dass es ein Feld findet.

---

## Befund 2 — der Vertrag ist nicht selbsttragend

Der `contract` enthält 11 Regeln, das Gold 16 Beobachtungstypen. Drei Typen haben **keine
Vertragsregel**:

```
missing_evidence_reference      keine Regel im Vertrag
evidence_changed_after_audit    keine Regel im Vertrag
confidence_missing              keine Regel im Vertrag
```

Ein System, das genau den mitgelieferten Vertrag umsetzt — also das, was die Aufgabenstellung
nahelegt —, verfehlt drei von sechzehn Typen. Wer sie trifft, hat sie **aus dem Entwicklungssatz
abgeschrieben**, nicht aus der Spezifikation abgeleitet.

---

## Befund 3 — die Aktionsschwere steht nirgends

Der Vertrag kennt drei Regelformen (`require_*`, `forbid_*`, `review_on_*`), das Gold vier Aktionen.
Die Zuordnung ist nicht ableitbar, und zwar nachweisbar nicht:

```
require_valid_ledger_hash   verletzt  →  reject_persist
require_complete_lineage    verletzt  →  hold
```

Beides sind `require`-Regeln, und sie führen zu verschieden schweren Aktionen. Ebenso führt
`require_stable_prompt_and_model` nur zu `request_review`, `require_strict_majority` dagegen zu
`hold`. Die Schweretabelle ist **ausschliesslich aus den Beispielen lernbar**.

Damit misst der Benchmark zu einem Teil, ob jemand den Entwicklungssatz gelesen hat, und nicht, ob
sein System Governance kann. In unserem Aufbau bekommen deshalb **alle Arme dieselbe Tabelle** — sonst
wäre der Vergleich eine Konventionsprüfung.

---

## Befund 4 — es kommt keine Sprache vor

Alle 40 Blindfälle tragen denselben Claim-Text: `"Synthetic persistence candidate."` Neun weitere
Felder sind über alle 40 Fälle konstant.

Der Benchmark hat damit genau den Teil entfernt, an dem Regeln in allen bisherigen Messungen
gescheitert sind (Sprache), und genau den behalten, an dem sie nicht scheitern können (Boolesche
Felder). Das ist keine Unfairness zugunsten von DESi im Sinne eines Lecks — beide Arme sehen
dasselbe —, aber es ist eine **Aufgabenwahl, die das Ergebnis vorwegnimmt**: sie kann nicht
beantworten, ob DESi in einer echten Pipeline nützt, sondern nur, ob eine Regelmaschine Regeln
ausführen kann.

---

## Befund 5 — die Zirkularität, und der schwerste Einwand

Der Benchmark liefert die Prozessfakten **bereits extrahiert und strukturiert**:

```json
"selected_by": "independent_retriever",
"source_resolvable": true,
"content_hash_at_audit": "e0882f61c1108bd1",
"strict_majority": true
```

In einem realen System **ist genau deren Erzeugung die Arbeit**. Wer `selected_by` zuverlässig
befüllt, hat die Instrumentierung schon gebaut; die anschliessende Anwendung von elf Regeln ist für
jedes System trivial — für einen Regelinterpreter, für ein LLM, und, wie Befund 1 zeigt, sogar für
fünfzehn Zeilen ohne Vergleich.

> Der Benchmark setzt voraus, was die eigentliche Leistung wäre, und misst dann den Rest.

Eine hohe Punktzahl belegt damit „eine Regelmaschine kann Regeln ausführen" — was nie bezweifelt
wurde. Das ist kein Fehler in der Ausführung des Benchmarks, sondern in seiner Anlage.

---

## Befund 6 — Ein-Defekt-Matrix statt Konfliktfälle

```
Blindfälle mit 0 Defekten   4
mit genau 1 Defekt         34
mit 2 Defekten              2
```

Die zwei Doppelfälle sind zudem gekoppelt (`self_selected_evidence` zieht
`counterevidence_search_missing` nach sich), also kein echter Konflikt. Es gibt **keinen einzigen
Fall**, in dem zwei Regeln in verschiedene Richtungen zeigen oder eine Vorrangfrage entsteht — und
genau dort verdient eine Policy-Maschine ihr Geld. Was hier vorliegt, ist eine Unit-Test-Matrix für
einen Regelinterpreter, kein Benchmark.

---

## Befund 7 — die Metriken können keinen inkrementellen Nutzen zeigen

Das Protokoll verlangt als Primärmetrik 6 „inkrementellen Nutzen von DESi gegenüber der Baseline".
Dafür bräuchte es eine Fallklasse, in der die Baseline plausibel scheitert. Der Datensatz enthält
keine: keine adversarialen Fälle, keine Ablenkungsfelder, keine Fälle, in denen ein Feld defekt
*aussieht* und es nicht ist, keine Vertragsvariation. Alles liegt an der Decke, und an der Decke ist
keine Differenz messbar.

Dazu kommt eine methodische Lücke: Eine Ergebnismetrik kann grundsätzlich nicht zwischen **„kann
nicht scheitern"** und **„ist hier nicht gescheitert"** unterscheiden. Genau diese Unterscheidung
wäre aber der einzige verbliebene Anspruch einer deterministischen Governance-Schicht. Sie ist keine
Messfrage, sondern eine Beweisfrage — dazu §*Ein besserer Benchmark*.

---

## Die sechs Fragen des Auftrags, einzeln

**1. Enthält das Gold nur objektive Prozessinformationen?**
Ja. Jede Gold-Beobachtung ist an ein explizites Feld gebunden; es gibt keine semantische Bewertung.
In diesem Punkt ist der Benchmark sauber gebaut — er hält, was er verspricht.

**2. Enthält das Gold versteckte Designannahmen zugunsten von DESi?**
Ja, drei — aber nicht die, die man erwarten würde. Das Vokabular des Golds ist praktisch identisch
mit DESis Klasse-A-Katalog (Befund 2 und 3 zeigen, dass es über den Vertrag hinausgeht und sich an
den Beispielen orientiert). Wichtiger: die *Aufgabenform* — vollständig strukturierte Eingaben ohne
Sprache — ist DESis günstigster Fall (Befund 4, 5). Das ist keine Manipulation, aber es ist eine
Vorentscheidung.

**3. Könnte eine normale Audit- oder Logging-Lösung dasselbe erreichen?**
Ja, nachweislich, und schlimmer: **eine entartete kann es auch.** Fünfzehn Zeilen ohne einen
einzigen Vergleich erreichen dasselbe Ergebnis wie die vollständige Implementierung (Befund 1).

**4. Sind die Governance-Regeln implementierungsunabhängig formuliert?**
Nein. Die Regeln sind es, die **Schwereabbildung** ist es nicht (Befund 3), und drei Beobachtungen
haben gar keine Regel (Befund 2). Ein unabhängiges Team käme ohne den Entwicklungssatz nicht auf
dieselbe Abbildung.

**5. Gibt es Lecks, durch die DESi Informationen erhält, die die Baseline nicht besitzt?**
Nein — beide Arme sehen dasselbe JSON, denselben Vertrag, dasselbe Vokabular, dieselbe
Schweretabelle. Das Leck läuft nicht zwischen den Armen, sondern **vom Gold in die Datenstruktur**
(Befund 1): die Antwort steht in der Schlüsselmenge.

**6. Sind die Metriken geeignet, inkrementellen Nutzen zu messen?**
Nein (Befund 7). Bei gesättigten Werten ist eine Differenz nicht darstellbar, und die entscheidende
Eigenschaft — Garantie statt Beobachtung — ist mit Ergebnismetriken prinzipiell nicht erreichbar.

---

## Ein besserer Benchmark

Was gemessen werden müsste, damit die Frage überhaupt entscheidbar wird. Reihenfolge nach
Wichtigkeit:

**A. Das Schlüsselleck schliessen.** Jedes optionale Vergleichsfeld muss in sauberen Fällen
*vorhanden und übereinstimmend* sein. Vorschlag: 50 % der Fälle tragen `content_hash_at_audit` mit
identischem Wert. Damit trennt sich Vergleich von Schlüsselzählung — und der `null`-Arm bricht sofort
ein. **Das ist die billigste und wirksamste einzelne Änderung.**

**B. Die Prozessfakten nicht mitliefern.** Statt `selected_by: "independent_retriever"` ein
Roh-Trace, aus dem hervorgeht, wer die Evidenz gewählt hat. Erst dann wird gemessen, was in einer
echten Pipeline die Arbeit ist.

**C. Konflikt- und Vorrangfälle.** Fälle mit 2–4 gleichzeitigen, teils gegenläufigen Beobachtungen
und einer *spezifizierten* Vorrangordnung. Dort entscheidet sich, ob eine Policy-Maschine mehr ist
als eine Liste.

**D. Adversariale Fälle.** Felder, die defekt aussehen und es nicht sind; ein Aktor, der plausible
aber falsche Hashes liefert; ein Paket, das die Vokabelnamen selbst im Text nennt (Prompt-Injection
gegen den Baseline-Arm). Erst hier kann sich „kann nicht scheitern" von „ist nicht gescheitert"
trennen.

**E. Vertragsvariation.** Ein zweiter Vertrag mit anderer Schwereabbildung, nur im Blindteil. Misst
Generalisierung statt Memorierung — und macht Befund 3 unschädlich.

**F. Invarianzprüfung statt nur Wiederholung.** Nicht zweimal dasselbe Paket, sondern dasselbe Paket
mit umgestellten Schlüsseln, umbenannten Feldern, zusätzlichem Rauschen. Eine Regelmaschine ist dagegen
per Konstruktion invariant, ein Prompt nicht. **Das ist die einzige Metrik in dieser Liste, die den
Unterschied zwischen Garantie und Zufall überhaupt sichtbar machen kann.**

**G. Eine Fallklasse, in der die Baseline scheitern muss.** Ohne sie ist „inkrementeller Nutzen"
keine Messgrösse. Kandidaten: sehr lange Pakete (Kontextverlust), 40 statt 16 Beobachtungstypen
(Vokabeldruck), Pakete mit widersprüchlichen Feldern.

Ohne A und G ist der Benchmark nicht reparierbar, sondern nur wiederholbar.
