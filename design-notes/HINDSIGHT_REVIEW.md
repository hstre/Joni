# HindsightTag für Joni — ein retroaktiver Review-Trigger zwischen Kurzzeit und Layer 9

*Design-Note. Extrahiert, nicht adoptiert. Kein Verhaltens-Code; dieser Text legt Lebenszyklus,
Leitplanken und Stufenplan fest, bevor eine Zeile Engine-Code entsteht — wie bei
`PROCEDURAL_SKILL_CONSOLIDATOR.md`.*

Quelle: **HindsightTag: A Synaptic Tagging-and-Capture Framework for Retroactive Memory
Consolidation in LLM Agents** (Dudhat, unabhängige Arbeit; von uns aus dem geteilten PDF gelesen).
Die Arbeit validiert sich selbst als *„initial, limited-scale, not mature"* — wir übernehmen die
**Idee und das Design-Prinzip**, nicht die Zahlen.

---

## 1. Was das ist — und was nicht

Es ist **kein neues Langzeitgedächtnis** und **kein zweiter Gedächtniskern**. Es ist ein
**retroaktiver Aufmerksamkeitsmechanismus** in der *mittleren* Gedächtnisschicht: ein späteres,
potenziell relevantes Ereignis löst eine **kontrollierte Neubewertung** eines früheren, noch nicht
konsolidierten Eintrags aus. Layer 9 bleibt der eine Store of record und die eine Autorität.

Der Kern-Move, den wir vom Paper übernehmen: die Wichtigkeit einer Erinnerung wird **nicht** zur
Schreibzeit fixiert (die *encoding-time-monotonic salience assumption*, die das Paper kritisiert).
Ein schwacher, sonst vergessener Eintrag kann durch ein späteres, zeitnahes Ereignis wieder
prüfbar werden — auditierbar, diskret, schwellenwert-gegated.

## 2. Das Problem, das es bei Joni löst

Jonis „Kurzzeitgedächtnis" vermischt heute funktional Verschiedenes: aktuellen Arbeitskontext,
offene Aufgaben, beiläufige Beobachtungen, unfertige Hypothesen, schwache Hinweise, offene
Widersprüche, Aussagen unklarer Bedeutung. Solange all das eine Schicht ist, gibt es **keine
Lebenszykluslogik**: kein klares „was bleibt kurz prüfbar, was wird reaktiviert, was darf nach
Prüfung in Layer 9".

## 3. Die entscheidende Änderung gegenüber dem Paper: Rescue-Operator → Review-Trigger

> **Paper:** spätes salientes Ereignis → früherer Eintrag wird **gerettet und konsolidiert**
> (schwellenwert-gegateter Rescue-Operator, der direkt promotet).
>
> **Joni:** spätes relevantes Ereignis → früherer Eintrag wird zur **retrospektiven Prüfung
> reaktiviert** (`review_due`). Erst danach entscheidet die Konsolidierungslogik / DESi.

Das ist keine Abschwächung, sondern die **korrekte Governance-Übersetzung**. Ein Auto-Rescue würde
„Modelle schlagen vor, Layer 9 entscheidet" verletzen. Als Review-Trigger wird sogar der riskanteste
Teil des Papers sicher — die **inhaltsunabhängige temporale Ko-Allokation** (Einträge verknüpfen,
weil sie zeitnah geschrieben wurden). Beim Paper *behauptet* diese Verknüpfung eine Bindung; bei uns
löst sie nur eine **Prüfung** aus, und die Konsolidierungslogik entscheidet dann:

- Gibt es tatsächlich eine Beziehung?
- Ist sie **semantisch, kausal, zeitlich — oder bloße Koinzidenz**?
- Ändert das spätere Ereignis die Bewertung des früheren Eintrags?
- Wird daraus ein Claim, ein Evidenzstück, ein Konflikt — oder nur eine interessante Koinzidenz?
- Muss der Eintrag langfristig erhalten bleiben?

Damit bleibt genau die lexikalische-Koinzidenz-Falle zu, die wir in Priorität 3 (Wortrekurrenz ≠
Hypothese) bekämpft haben: Nähe in der Zeit ist ein **Prüfanlass**, keine Behauptung.

## 4. Die drei Schichten

1. **Arbeitsgedächtnis** — sehr kurzlebig, auf die aktuelle Operation bezogen (Dialog, Toolausgaben,
   aktueller Plan, Zwischenergebnisse). Darf chaotisch sein, solange begrenzt und regelmäßig
   geleert. *In Joni faktisch schon vorhanden:* der LLM-Kontext + das `extensions`-Dict pro Zyklus,
   das jeden Zyklus neu entsteht.
2. **Provisorisch-episodisches Gedächtnis** — überlebt den unmittelbaren Arbeitsschritt, gilt aber
   **noch nicht als gesicherter Zustand**: Beobachtungen, schwache Hinweise, unfertige Hypothesen,
   ungewöhnliche Ereignisse, offene Widersprüche, unklare Aussagen. **Hierhin gehört HindsightTag.**
   *In Joni teils vorhanden:* der **S0-Episodenspeicher** (`state/episodes.jsonl`) ist bereits ein
   append-only, timestamped, provenienz-tragender Provisorien-Store; die **Musterhinweise** aus
   Priorität 3 sind bereits „schwache Hinweise / unklare Aussagen". Beide sind heute enger gefasst
   als diese Schicht — H0 (unten) weitet sie.
3. **Layer 9 — konsolidiertes epistemisches Gedächtnis** — epistemisch bearbeitete Zustände: Claims,
   Evidenz, Entscheidungen, Constraints, Konflikte, Unsicherheiten, verworfene Alternativen,
   Provenienz + Revisionsgeschichte. Kein bloßer Gesprächsrest. *Schon vorhanden.*

Es ist also zu ~60 % **Reorganisation** von Vorhandenem und zu ~40 % ein **genuin neuer
Mechanismus** (der Review-Trigger + die Zwei-Salienz-Trennung).

## 5. Der Lebenszyklus

```
ephemeral
    ↓
provisional
    ↓
tagged                (kurzlebiger Tag; begrenzte Lebensdauer)
    ↓
review_due            (ein späteres Ereignis hat eine Neubewertung ausgelöst)
   ↙   ↓   ↘
expired  |  consolidated → Layer 9
         |
   weitere Ausgänge von review_due:
     • rejected               (Prüfung ergab: irrelevant / kein Zusammenhang)
     • linked_only            (Beziehung real, aber nur assoziativ — POSSIBLE_RELATED, kein Claim)
     • contradiction_detected (das spätere Ereignis widerspricht dem früheren → Konflikt)
     • hypothesis_opened      (die Neubewertung erzeugt eine prüfbare Hypothese)
```

Ein späteres Ereignis macht die Vergangenheit also **nicht einfach „wichtiger"**, sondern löst eine
**kontrollierte Neubewertung mit typisiertem Ausgang** aus. Jeder Übergang schreibt einen
**Provenienz-Record** (Trigger-Ereignis, Timestamp, berechnete capture-Stärke) — nicht optional,
genau wie im Paper (Sektion 4.8): ein Mensch/Audit muss rekonstruieren können, *warum* ein Eintrag
gehalten oder konsolidiert wurde.

## 6. Zwei getrennte Größen (die zentrale Verfeinerung)

Das Paper arbeitet mit *einer* Salienz. Für Joni trennen wir **mindestens zwei**:

- **Aufmerksamkeitssalienz** — wie auffällig, neu oder dringlich etwas ist. Darf **heuristisch/billig**
  sein (Neuheit, Recency, Ungewöhnlichkeit einer Toolausgabe).
- **Epistemische Bedeutung** — wie stark es Claims, Entscheidungen oder das Weltmodell verändert.
  Muss **gemessen, nicht LLM-geschätzt** sein: „berührt es einen realen Claim / Konflikt / eine
  Entscheidung?" ist deterministisch beantwortbar (rules for logic).

Ein Unfall, eine emotionale Formulierung oder eine ungewöhnliche Toolausgabe kann hoch salient sein
**ohne** epistemisch bedeutend zu sein; ein unscheinbarer Versionswechsel oder eine kleine
Messabweichung kann epistemisch sehr wichtig werden. Nur die **epistemische** Größe darf Richtung
Konsolidierung ziehen; die Aufmerksamkeitssalienz steuert nur, was überhaupt *getaggt* und
*reaktiviert* wird. Diese Trennung ist dieselbe Disziplin wie `V_operational ≠ V_epistemic`.

## 7. Verhältnis zum Vorhandenen und zu den offenen Prioritäten

HindsightTag ist **kein sechstes Nebenprojekt**, sondern das **Dach**, unter das zwei offene
Prioritäten als Lebenszyklus-Übergänge passen:

- **Priorität 4** (Zustandswechsel nach 2 evidenzfreien Neubewertungen → TEST / WAIT_FOR_EVIDENCE /
  ARCHIVE) **ist** die `review_due → {hypothesis_opened(TEST) | tagged(WAIT) | expired(ARCHIVE)}`-
  Verzweigung. Statt eines Sonder-Zählers in `strengthen` wird es ein Übergang im Lebenszyklus.
- **Priorität 5** (Konflikte thematisch verdichten) speist den Ausgang **`contradiction_detected`**:
  ein reaktivierter Eintrag, der einem späteren Ereignis widerspricht, wird zu einer Streitfrage
  verdichtet statt zu einem weiteren Paar-Konflikt.
- **Priorität 1** (Scoreboard) liefert die Messung: `reviews_triggered → {consolidated / rejected /
  linked_only / contradiction_detected / hypothesis_opened}` als Verhältnis — sonst wissen wir nicht,
  ob der Trigger Nützliches rettet oder nur Rauschen reaktiviert.
- **Priorität 2** (Intake ↔ Verdauung) wird natürlicher: „ein Zyklus darf neue Claims nur voll
  aufnehmen, wenn zugleich verdaut wird" heißt hier konkret **≥1 `review_due` bearbeitet**.

## 8. Leitplanken (verbindlich)

- **Kein zweiter Gedächtniskern.** Der Provisorien-Layer ist eine **Staging-Zone, die durch Review
  in Layer 9 einspeist** — nie ein alternativer Store of record. (Dieselbe Leitplanke wie bei
  MSCE/MemOS.)
- **Nichts konsolidiert sich selbst.** `review_due → consolidated` ist ein **Vorschlag** an Layer 9 /
  einen Menschen; die eigentliche Aufnahme läuft über die bestehenden Gates. Recording ≠ Promotion.
- **Provenienz-Pflicht.** Jeder Tag, jede Ko-Allokation, jeder Review-Trigger schreibt append-only,
  wer/was/wann/wie-stark — rekonstruierbar. Kein stiller Rescue.
- **Zeitliche Nähe ist ein Prüfanlass, keine Behauptung.** Temporale Ko-Allokation erzeugt nie direkt
  einen Link/Claim; sie setzt nur `review_due`.
- **Epistemische Bedeutung wird gemessen, nicht geschätzt.** LLM nur für Sprache (Beschreibung eines
  Eintrags), nie für die Konsolidierungs-Entscheidung.
- **Peripher, an Hooks.** Wie im Paper: hängt sich an den Lebenszyklus, ohne das Default-Verhalten zu
  ändern; `joni_core.lock` bleibt unberührt; `python -m joni.autonomy verify` muss grün bleiben.
- **Begrenzte Lebensdauer + Kappung.** Der Provisorien-Layer wächst nicht unbegrenzt: `ephemeral`
  läuft schnell ab, das capture-Fenster ist beschränkt, pro Zyklus wird nur eine kleine Zahl
  Reaktivierungen bearbeitet (budget-metered).

## 9. Stufenplan (jede Stufe einzeln umsetzbar & prüfbar)

| Stufe | Inhalt | Akzeptanz |
|---|---|---|
| **H0 — Provisorien-Layer** | Den S0-Episodenspeicher zu einem echten Provisorien-Layer öffnen: breitere Eintragstypen (Beobachtung, schwacher Hinweis, offener Widerspruch, unklare Aussage), plus Lebenszyklus-Feld (`ephemeral/provisional/tagged/review_due/…`), Lebensdauer und die zwei Salienz-Werte. Append-only, read-only ggü. Layer 9. | Ein Eintrag durchläuft `ephemeral→provisional` deterministisch; nichts erfunden; `unknown` bleibt `unknown`. |
| **H1 — Tag + capture-Fenster** | Ein kurzlebiger Tag mit begrenztem Fenster; ein Eintrag mit ausreichender Aufmerksamkeitssalienz wird `tagged`. Schwellenwert-gegated, auditierbar. | Ein getaggter Eintrag verfällt nach Fensterablauf sauber (`expired`), wenn kein Trigger kam. |
| **H2 — temporale Ko-Allokation → Review-Trigger** | Ein späteres Ereignis, das zeitnah + (schwellenwert) relevant ist, setzt zeitnahe getaggte Einträge auf `review_due` — mit Provenienz-Record. **Kein** Link, **keine** Konsolidierung hier. | Ein späteres Ereignis reaktiviert genau die Einträge im Fenster; jeder Trigger ist im Record rekonstruierbar. |
| **H3 — Konsolidierungs-Entscheidung** | `review_due` wird durch deterministische Logik / DESi in genau einen Ausgang überführt: `expired / consolidated / rejected / linked_only / contradiction_detected / hypothesis_opened`. `consolidated`/`hypothesis_opened` sind **Vorschläge** an Layer 9 (human/gate). Hier docken **#4** und **#5** an. | Jeder Ausgang ist typisiert und belegt; nichts wird auto-aktiv; Konflikt-Ausgänge laufen in die Streitfragen-Verdichtung. |
| **H4 — Messung** | Scoreboard-Zeile: reaktivierte Reviews und ihre Ausgangs-Verteilung; Anteil „nur Koinzidenz". | Man sieht messbar, ob der Trigger Signal oder Rauschen rettet. |

## 10. Was es ausdrücklich NICHT tut

- **Kein Auto-Consolidate**, kein Auto-Link, keine Selbst-Aktivierung. Vorschlagen, nicht entscheiden.
- **Kein LLM-Salienz-Orakel für Epistemik.** Die epistemische Größe bleibt regelbasiert.
- **Kein Ersatz** für den Metabolismus (der Aufnahme↔Konsolidierung *quantitativ* koppelt) oder für
  den Skill-Consolidator (prozedurale Achse). HindsightTag ergänzt die **deklarative/episodische**
  Achse um eine retroaktive Prüf-Dimension.
- **Keine inhaltsunabhängige Bindung** als Assertion — temporale Nähe triggert nur Review.

## 11. Risiken

- **Reaktivierungs-Rauschen.** Zeitnähe ist billig; ohne die epistemische Größe als Filter könnte der
  Trigger viel Belangloses reaktivieren. Gegenmittel: Aufmerksamkeitssalienz-Schwelle + Kappung +
  H4-Messung; wenn der „nur-Koinzidenz"-Anteil hoch bleibt, ist der Mechanismus zu locker.
- **Layer-Wildwuchs.** Der Provisorien-Layer könnte zum heimlichen zweiten Kern werden. Gegenmittel:
  harte Lebensdauer, append-only, kein Query-Pfad, der ihn wie einen Store of record behandelt.
- **Unreife Evidenz im Paper.** Wir übernehmen das Prinzip, nicht die Wirkungsbehauptung — deshalb H4
  vor jedem Ausbau.
