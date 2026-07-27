# Schlafmodus — Design-Note

## Warum

Joni nimmt schneller auf, als er verdaut. Das Regal wächst, aber nichts darauf reift.
Der Schlafmodus ist der bewusste Gegenzug: **aufhören zu essen, weiterverarbeiten.**

Er ist ausdrücklich *kein* neuer Denker. Die Pässe, die im Schlaf laufen, sind die, die
es schon gibt — Trials, Re-Trials, Hindsight-Review, Streitfragen, Method-Breakdown.
Der Schlafmodus ist ein **Orchestrierungs-Layer** darüber, kein monolithischer
Schlafagent.

## Die vier Zustände

```
AWAKE ──Druck / Zeit──▶ SLEEP_LIGHT ──Druck hält an──▶ SLEEP_DEEP
  ▲                          │                              │
  └── WAKE_TRANSITION ◀───────┴──── Druck weg / Obergrenze ──┘
        (genau 1 Zyklus)
```

Persistiert in `state/sleep_state.json`. Zwei Trigger, beide deterministisch, ohne Modell:

| Trigger | Bedingung | Env |
|---|---|---|
| **Druck** | Verdauung steht seit N Zyklen (kein Test, keine bearbeitete Streitfrage, kein Hindsight-Review) | `JONI_SLEEP_STALL` (2) |
| **Zeit** | seit N Zyklen wach | `JONI_SLEEP_AWAKE_CYCLES` (24) |

Hysterese auf beiden Seiten plus harte Obergrenze, damit die Maschine weder flattern
noch hängenbleiben kann:

| Schranke | Bedeutung | Env |
|---|---|---|
| `MIN_AWAKE` (6) | nach dem Aufwachen nicht sofort wieder einschlafen | `JONI_SLEEP_MIN_AWAKE` |
| `MIN_SLEEP` (2) | nicht nach einem Zyklus schon wieder aufwachen | `JONI_SLEEP_MIN` |
| `DEEP_AFTER` (3) | Leichtschlaf → Tiefschlaf nur solange der Druck anhält | `JONI_SLEEP_DEEP_AFTER` |
| `MAX_SLEEP` (8) | **ein Schlaf, der nicht endet, ist ein Fehler, kein Zustand** | `JONI_SLEEP_MAX` |

Die Obergrenze zählt ab dem *Einschlafen*, nicht ab dem Vertiefen — Tiefschlaf kann den
Schlaf also nicht still verlängern.

## Schatten zuerst — nichts aktiviert sich selbst

Die Zustandsmaschine läuft und wird **jeden Zyklus gemessen und persistiert**, aber sie
**drosselt die Aufnahme nur bei `JONI_SLEEP=1`**. Ohne das Flag ist sie reine Beobachtung:
_wie oft würde Joni schlafen, und hätten diese Fenster überhaupt etwas reifen lassen?_

Das ist dieselbe Messen-vor-Übernehmen-Regel wie bei jedem anderen Arm hier. Die
Autorität wird erst übergeben, wenn die Daten sie rechtfertigen.

## Die Messung: Reifung, nicht Betriebsamkeit

Der Aufwachbericht vergleicht vier **monotone Reifungszähler** vor dem Einschlafen und
nach dem Aufwachen (gelesen aus der letzten Consolidator-Scoreboard-Zeile):

* `valid_tests` — gemessene Trial-Verdikte
* `skills` — kristallisierte Skills
* `episodes_resolved` — aufgelöste prozedurale Episoden
* `hindsight_reviews` — abgeschlossene Reviews

`matured: false` heißt: das Fenster war beschäftigt, aber nichts ist gereift. **Das muss
sich als Fehlschlag lesen, nicht als Arbeit.** „400 Einträge refragmentiert" ist kein
Fortschritt; ein geschlossenes Verdikt, ein gereifter Skill, eine aufgelöste Episode ist
einer. Genau diese Verwechslung hat zuletzt die capped-log-Metrik in `extension_review`
wochenlang danebenliegen lassen — der Zähler stieg, ohne etwas zu bedeuten.

## Sichtbarkeit

Eine Zeile im Consolidator-Scoreboard (`docs/consolidator.md`):

```
| Schlafmodus | 😴 SLEEP_DEEP seit Zyklus 12 (Druck hält an) · Beobachtung (drosselt nicht);
                 letzter Schlaf 4 Zyklen → **nichts gereift** |
```

Sie sagt drei Dinge auf einmal: welcher Zustand, ob das Gate überhaupt scharf ist, und
ob der letzte Schlaf etwas gebracht hat.

## Governance

* Schreibt genau **ein** Artefakt: `state/sleep_state.json` (innerhalb der Allowlist).
* Rührt Layer 9 nicht an, fragt kein Modell, fasst den geschützten Kern nicht an.
* Fail-open: jeder Fehler ⇒ `{}` ⇒ AWAKE ⇒ nichts wird gedrosselt.
* Ein fehlgeschlagener `step()` unterdrückt niemals Aufnahme.

## Phasen

| Phase | Inhalt | Status |
|---|---|---|
| **S0** | Zustandsmaschine, Trigger, Intake-Unterdrückung, Sichtbarkeit, Reifungsmessung | **gebaut** |
| **S1** | Read-only Refragmentierung der Provisorien → Assoziationsvorschläge | **gebaut** |
| **S2** | Struktur-Audit: Auslöser / Schritte / Prüfkriterium je Kandidatenmethode | **gebaut** |
| **S3** | Defektberichte, nur bei genau **einer** fehlenden Komponente; nichts angewendet | **gebaut** |
| **S4** | `state/wake_queue.json` + `docs/sleep_report.md` als Übergabe | **gebaut** |

## Arbeit ≠ Fasten

Die Pässe S1–S3 laufen, wenn die Zustandsmaschine **Schlaf sagt** — unabhängig davon, ob
das Intake-Gate scharf ist. Im Beobachtungsmodus tut Joni also die Schlaf-*Arbeit* ohne
das Schlaf-*Fasten*. Damit ist die Frage „bringt Schlafarbeit überhaupt Reifung?"
beantwortbar, **bevor** die Aufnahme je gestoppt wird.

## Was die erste Messung an echten Daten ergab

Beide Befunde stammen aus einem Lauf gegen den Live-Bestand, nicht aus Testdaten:

**S1 hätte 100 % Müll produziert.** Alle sechs gefundenen „Verknüpfungen" waren dieselbe
generierte Schablone mit einem ausgetauschten Wort (*„across my forum claims **X** recurs
through line worth testing…"*). Geteilt war die Satzform, nicht der Inhalt — und
ausgerechnet das einzige bedeutungstragende Token war das, das sich unterschied. Daraus
zwei zusätzliche Sperren, beide gezählt und sichtbar:

* **Grad-Deckel** — ein Fragment in mehr als `MAX_LINK_DEGREE` Einträgen ist eine Form,
  kein Fund. Eine echte Assoziation ist *selten*.
* **Schablonenfamilie** — mehrere Fragmente, die sich in genau einem Token unterscheiden,
  werden als Familie komplett verworfen.

Danach: **0 statt 6** Verknüpfungen. Das ist die ehrliche Antwort — im Provisorien-Store
steht derzeit keine echte Assoziation, nur Boilerplate.

**S2 erklärt, warum die Trial-Pipeline hungert.** Von 250 Kandidatenmethoden sind 176
Papertitel (übersprungen). Von den 74 echten Verfahrensnamen erreichen **73 einen Score
von 0/3** und einer 1/3 — **keine einzige** ist als Verfahren geformt. Es fehlt also nicht
am Benchmark, sondern an der Quelle: was auf dem Regal liegt, sind keine Verfahren.

Deshalb ist genau dieser Befund der oberste Posten der Wach-Warteschlange
(`structural_finding`, Priorität 0) — er rangiert über jedem Einzelposten, weil er
verändert, woran überhaupt zu arbeiten ist.

S3 feuert auf diesen Daten folgerichtig **nie**: ein Defektbericht setzt genau *eine*
fehlende Komponente voraus, hier fehlen überall alle drei. Das ist kein Fehler der
Mechanik, sondern ihr Urteil über den Bestand.

Alles bleibt Vorschlag: Layer 9 und der Mensch entscheiden.
