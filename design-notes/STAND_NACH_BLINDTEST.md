# Stand nach dem Blindtest — Diskussionsgrundlage

**Datum:** 29. Juli 2026 · **Repo:** hstre/Joni, Branch `claude/kevin-creativity-architecture-ukz17g`
· **Commits:** `c8969d2b` (eingefroren) → `2cd68514` (versiegelt) → `31db3af3` (ausgewertet)

Diese Datei ist eigenständig lesbar. Sie setzt den Kenntnisstand des `BEFUNDBERICHT_DESI_MESSUNG.md`
**nicht** voraus, wiederholt aber nur so viel Vorgeschichte, wie zum Verstehen nötig ist. Der lange
Bericht bleibt die vollständige Quelle; hier steht, was seither passiert ist — und das ist das
Wichtigste, was in dieser Sache bisher gemessen wurde.

**Die Kurzfassung in vier Sätzen.** Der externe Blindsatz ist gelaufen, nach dem Protokoll des
Auswerters, mit versiegelten Vorhersagen. Die Sicherheitseigenschaft hält: null bzw. ein
Falschdurchlass auf 80 Urteilen über nie gesehene Fälle. Die Trefferquote hält nicht: 82,5 % statt
der 90 % vom Dev-Satz. Und die Kontrollschicht — genau das Stück, das „DESi" von „ein LLM mit gutem
Prompt" unterscheiden sollte — hat in 80 Urteilen nichts repariert und sechsmal geschadet.

---

## 0. Wo wir stehen: die Architektur in ihrer aktuellen Form

Gebaut wird ein **Claim–Evidence-Entailment-Auditor** für die MSCE-Kooperation: ein Prüfschritt an
der Grenze L2 → L3, der genau eine Frage beantwortet.

```
gegebene Evidenz + deklarierte Prämissen   ⟹   L3-Claim ?
```

Nicht: *ist der Claim wahr*. Nicht: *ist er nützlich*. Nur: *tragen die zitierten Belege ihn*.

Die Verdikte bilden eine Leiter, `contradicted` liegt daneben:

```
entailed  >  partially_entailed  >  compatible_not_entailed  >  insufficient
                        (contradicted — ausserhalb der Leiter)
```

Vier Schichten:

```
Modell        schlägt Verdikt vor          k=5 Ziehungen, strikte Mehrheit
Kontrollen    deterministisch, dürfen NUR abwärts    ← diese Schicht ist jetzt widerlegt
DESi          akzeptieren · herabstufen · Prüfung verlangen
Layer 9       persistiert nur das Gegovernte
```

**Zur Erinnerung, weil es die vorige Kehrtwende war:** v1 liess die *Regeln urteilen* und kam auf
7/20 mit drei Falschdurchlässen. Dasselbe Modell, das dort nur normalisieren durfte, urteilte direkt
mit 17–18/20 bei null Falschdurchlässen. Daraus v2: **Modell urteilt, Regeln beschränken.** Der
Blindtest prüft jetzt v2.

---

## 1. Der Blindtest — Aufbau

Der externe Auswerter hat neben dem Dev-Satz (20 Fälle, mit Gold, zum Entwickeln) einen
**versiegelten Testsatz von 40 Fällen** und ein eigenes Protokoll geliefert. Das Protokoll ist an der
richtigen Stelle streng:

| Schritt | Vorgabe | erfüllt |
|---|---|---|
| 2 | Code, Prompt, Parser-Modell, Anbieter, Commit-Hash einfrieren | ✓ `c8969d2b`, sauberer Baum |
| 3 | nur der Blindsatz wird gegeben | ✓ Skripte verweigern Pfade mit „PRIVATE" |
| 4 | Vorhersagen mit Fall-ID, Verdikt, Verstössen, **normalisierten Strukturen**, Feldzustimmung, Modell-ID, k, Prompt-Hash, Lauf-ID | ✓ JSONL, alle Felder |
| 5 | Ausgabe einfrieren, **bevor** der Schlüssel geöffnet wird | ✓ eigener Commit `2cd68514` |
| 7 | u. a. Stabilität über wiederholte Läufe | ✓ zwei vollständige Läufe |
| 9 | keine Testfälle nachträglich ändern | ✓ nichts geändert |

**Eingefrorene Konfiguration**

```
Modell (Urteil)   deepseek-v4-flash          k = 5, strikte Mehrheit
Zweitmeinung      google/gemma-4-31b-it      (Triage, ändert kein Verdikt)
aktive Kontrollen conjunction_coverage, epistemic_hedge,
                  modality_escalation, quantifier_escalation, scope_escalation
inaktiv           evidence_padding           (schon vorher als schädlich gemessen)
Prompt-Hashes     f73dd7f139054b7d (Urteil) · 87ccaff4f22ded86 (Normalisierung)
```

**Versiegelung.** Lauf 1 `b99aa58ea9d39405…`, Lauf 2 `46025b747b4b6ab8…`. Beide Hashes stehen im
Commit `2cd68514`, der **vor** dem Öffnen des Schlüssels geschrieben wurde. Das ist der Punkt, an dem
nachträgliches Schönen sichtbar würde.

---

## 2. Das Ergebnis

| Messgrösse | Lauf 1 | Lauf 2 |
|---|---|---|
| **Trefferquote v2 (mit Kontrollen)** | **29/40 — 72,5 %** | **31/40 — 77,5 %** |
| **Trefferquote Modell allein** (nachgerechnet) | **33/40 — 82,5 %** | **33/40 — 82,5 %** |
| **Falschdurchlässe** (durchgelassen, wo Gold strenger) | **0** | **1 — 2,5 %** |
| Falschsperren (gesperrt, wo Gold durchlässt) | 3 — 7,5 % | 3 — 7,5 % |
| Makro-F1 (Verdikte) | 0,523 | 0,534 |
| Verstösse mikro-F1 / makro-F1 | 0,581 / 0,527 | 0,508 / 0,465 |
| Verdikt-Stabilität über beide Läufe | 36/40 identisch — 90 % | 36/40 identisch — 90 % |

F1 je Verdikt (Lauf 2): `entailed` 0,90 (n=16) · `contradicted` 1,00 (n=6) ·
`compatible_not_entailed` 0,77 (n=13) · `partially_entailed` **0,00** (n=2) ·
`insufficient` **0,00** (n=3).

Nach Domäne (Lauf 2): technisch 4/4 · Wissenschaft 6/6 · klinisch 6/6 · Alltag 4/4 · Recht 2/2 ·
multi_evidence 1/1 — und dann Software 3/7 · Organisation 4/7 · Finanzen 1/3.

### Was das heisst

**Die Fehlerrichtung hält.** Das ist die Eigenschaft, für die diese Architektur überhaupt gebaut
wurde: sie soll lieber zu wenig durchlassen als zu viel, weil ein falsches `entailed` eine
unbegründete Behauptung mit Gütesiegel weiterreicht, während eine falsche Sperre nur Prüfaufwand
kostet. Null und ein Falschdurchlass auf 80 Urteilen über fremde Daten — das hat den ersten Kontakt
mit einer unbekannten Verteilung überstanden.

**Die Trefferquote hält nicht.** 90 % auf dem Dev-Satz gegen 82,5 % blind. Rund acht Punkte
Optimismus — genau die Grössenordnung, die man erwartet, wenn an denselben zwanzig Fällen gemessen
*und* justiert wurde. **Die Zahl, die nach aussen genannt werden darf, ist 82,5 %.**

**Die Fehler konzentrieren sich auf die inneren Sprossen.** `entailed` und `contradicted` sitzen
(F1 0,90 / 1,00), `partially_entailed` und `insufficient` sind komplett verfehlt — 0 von 2 und
0 von 3. Dazu unten §5, weil das keine Denkschwäche ist.

---

## 3. Der harte Befund: die Kontrollschicht ist widerlegt

| | Lauf 1 | Lauf 2 |
|---|---|---|
| Verdikte, die eine Kontrolle **repariert** hat | **0** | **0** |
| Verdikte, die eine Kontrolle **kaputtgestuft** hat | **4** | **2** |

Sechs Herabstufungen über zwei Läufe. **Jede einzelne falsch. Keine einzige Reparatur.** Alle sechs
haben ein korrektes `entailed` auf `partially_entailed` gezogen. Zwei Kontrollen tragen das:

**`epistemic_hedge`** — sollte verhindern, dass „zu X wurde nichts gefunden" als Beleg für „X ist
nicht passiert" durchgeht (Abwesenheit von Evidenz ist keine Widerlegung). Sie verwechselt das aber
mit *„eine Quelle sagt X"*:

> TEST-007 · Evidenz: „Die Doku sagt: 'Führe `npm install` aus, bevor du den Server startest.'"
> Claim: „Die Doku weist den Nutzer an, `npm install` auszuführen." → **Gold: entailed.**
> Modell: entailed. Kontrolle: herabgestuft.

> TEST-030 · Evidenz: „Die Richtlinie sagt, Auftragnehmer haben keine Entscheidungsbefugnis."
> Claim: „Die Richtlinie beschreibt Auftragnehmer als ohne Entscheidungsbefugnis." →
> **Gold: entailed.** Modell: entailed. Kontrolle: herabgestuft.

Der zweite Fall ist besonders bitter: **exakt dieser Satz steht in unserem eigenen API-README als
Beispiel** für den Konjunktionsdefekt, den wir gefunden und behoben hatten.

**`modality_escalation`** — sollte verhindern, dass ein Claim sicherer auftritt als seine Evidenz.
Sie stolpert über Negation: „Auftragnehmer haben **keine** Befugnis" wird zu `modality=negated`
(niedriger Rang), der Claim ist `asserted` (höher) — ein Rangsprung, der rein strukturell entsteht
und semantisch keiner ist.

Dazu: `scope_escalation` feuerte einmal falsch (TEST-026), `conjunction_coverage` **kein einziges
Mal**, `evidence_padding` war schon vorher abgeschaltet.

### Die Verallgemeinerung, und warum sie unbequem ist

Jede Kontrolle dieses Katalogs stammt aus **genau einem** beobachteten Fehlschlag. `epistemic_hedge`
aus DEV-017. `conjunction_coverage` aus einem Fall. `evidence_padding` aus einem. In der
Architekturnotiz stand die Herkunftsspalte als *Qualitätsmerkmal* („jede Kontrolle nennt den
gemessenen Fall, der sie nötig gemacht hat"). Sie war in Wahrheit die Warnung:

> **Ein Kontrollkatalog, der aus Einzelfällen abgeleitet ist, ist eine Sammlung von
> Überanpassungen.** Keine dieser Kontrollen hat je einen zweiten Fall gefangen.

Und der Fehler, den ich dabei gemacht habe, ist benennbar: Auf dem Dev-Satz war die Schicht
**wirkungslos** (0–1 Herabstufungen, kein messbarer Schaden). Ich habe das als *unschädlich*
gelesen. Es hiess nur, dass jene zwanzig Fälle sie nie herausgefordert haben.

> **Wirkungslosigkeit auf den Entwicklungsdaten ist kein Nachweis der Unschädlichkeit.**

Die eigene Messregel in der Architekturnotiz sagte übrigens genau voraus, was zu tun ist: *„Die
Nachfolgearchitektur muss mindestens die Baseline erreichen. Liegt sie darunter, schaden die
Kontrollen mehr als sie nützen."* Blind liegt sie darunter — 29/31 gegen 33.

### Warum die Schicht trotzdem noch drin ist

Abgeschaltet habe ich sie **nicht**. Eine Konfigurationsänderung nach Sicht des Schlüssels wäre eine
Anpassung an den Testsatz, und die 33/40 sind eine **Nachrechnung auf denselben Daten**, keine
unabhängige Messung. Die Abschaltung braucht einen frischen versiegelten Satz — oder eine bewusste
Entscheidung, dass man sie ungemessen vornimmt und das so sagt.

Das ist eine Entscheidung für dich, nicht für mich.

---

## 4. Das Triage-Signal war ein Artefakt

Die dritte Architekturschicht („Prüfung verlangen") sollte über eine **Zweitmeinung aus einem anderen
Modellhaus** ausgelöst werden: sind sich zwei unabhängige Modelle uneinig, markiere den Fall für
einen Menschen — ohne das Verdikt zu ändern. Auf dem Dev-Satz sah das scharf aus: 2 von 3 Fehlern
gefangen bei 10 % markierten Fällen.

Blind:

```
Lauf 1   alle 7 Modellfehler ausserhalb der Reichweite der Triage
Lauf 2   6 von 7 ausserhalb; erfasst wurde genau der eine Falschdurchlass (TEST-039)
```

Der Grund ist strukturell, nicht statistisch: **die Kostenregel fragt die Zweitmeinung nur bei
durchlassenden Verdikten** (weil Kontrollen nur abwärts dürfen, ist bei niedrigen Verdikten nichts zu
tun). Sie wurde deshalb nur bei **15 bzw. 16 von 40 Fällen** überhaupt eingeholt — und die Fehler
liegen fast alle in den anderen 25.

Auf dem Teilsatz, den sie sah, war gemma 14/15 bzw. 14/16 richtig. **Das Modell ist in Ordnung, die
Platzierung des Signals ist es nicht.**

Ein Hinweis auf einen Fehler in meiner eigenen ersten Auswertung, weil er lehrreich ist: Ich habe die
25 nie gestellten Anfragen als „Zweitmeinung sagt nichts" gelesen und daraus eine Gemma-Quote von
14/40 errechnet — und wäre damit fast zu dem Schluss gekommen, gemma sei auf fremden Daten
zusammengebrochen. Es war ein Auswertungsfehler, kein Modellbefund. Die Korrektur steht im
Befundbericht.

**Damit hat die dritte Schicht wieder keinen validierten Auslöser.**

---

## 5. Die sieben Modellfehler sind eine Konventionslücke, kein Denkfehler

Sie sind über beide Läufe fast identisch und haben eine gemeinsame Form: **das Modell wählt die
mittlere Sprosse, wo der Schlüssel die äussere meint.**

| Fall | Evidenz ⟹ Claim | Modell | Gold |
|---|---|---|---|
| TEST-006 | „`npm install` steht in der Doku" ⟹ „Die Doku weist es an" | `compatible_not_entailed` | `insufficient` |
| TEST-027 | „Rechnungen über 10 000 € brauchen zwei Unterschriften" ⟹ „Eine 8 000-€-Rechnung braucht zwei" | `compatible_not_entailed` | `insufficient` |
| TEST-037 | „Fonds X gewann 12 % letztes Jahr" ⟹ „…wird 12 % nächstes Jahr gewinnen" | `compatible_not_entailed` | `insufficient` |
| TEST-003 | „Ein glibc-Wheel scheiterte in **zwei** Alpine-Containern" ⟹ „glibc-Wheels scheitern **oft**" | `compatible_not_entailed` | `partially_entailed` |
| TEST-025 | „Personal **darf** das Labor nach der Sicherheitsschulung betreten" ⟹ „Schulung ist **hinreichend**" | `entailed` / `compatible_not_entailed` | `partially_entailed` |
| TEST-005 | „Installation scheiterte vor libffi-dev, gelang danach, keine andere Änderung" ⟹ „libffi-dev verursachte den Erfolg **in diesem Lauf**" | `compatible_not_entailed` | `entailed` |
| TEST-039 | „Bond Y zahlt 4 %, **wenn der Emittent nicht ausfällt**" ⟹ „Bond Y garantiert 4 % unter **allen** Umständen" | `contradicted` / `partially_entailed` | `compatible_not_entailed` |

Alle drei `insufficient`-Fälle tragen im Gold den Verstoss `missing_premise`. Die Regel des
Auswerters lautet offenbar:

> **Verlangt der Schluss eine unausgesprochene Prämisse, ist das Verdikt `insufficient`, nicht
> `compatible_not_entailed`.**

Unser Prompt definiert `insufficient` enger („unverwandte Entitäten, gebrochene Schlusskette, keine
Evidenz gegeben") — und `compatible_not_entailed` als Auffangbecken für alles, was nicht
widersprochen, aber ungetragen ist. Beide Definitionen sind vertretbar. Sie sind nur nicht dieselbe.

Zwei weitere Fälle zeigen dasselbe an der anderen Grenze: TEST-005 ist eine singuläre
Kausalbehauptung mit expliziter Ereignisreichweite („in diesem Lauf") — der Schlüssel sagt
`entailed`, unser Prompt trägt eine ausdrückliche Regel, dass eine Intervention, die ein Symptom
beseitigt, die Ursache nicht beweist. **Diese Regel haben wir gestern bewusst eingebaut**, nachdem
eine Lockerung genau dafür einen konsistenten Falschdurchlass an anderer Stelle erzeugt hatte. Der
Schlüssel zieht die Grenze anders.

**Das ist eine Spezifikationslücke, kein Fehlurteil.** Und es ist der Grund, warum Schritt 9 des
Protokolls existiert: Der Prompt liesse sich in zehn Minuten an diese Konvention anpassen und käme
vermutlich über 90 %. Das wäre dann keine Messung mehr, sondern eine Anpassung an den Schlüssel. Es
ist nicht geschehen und darf auf diesem Satz auch nicht mehr geschehen.

---

## 6. Was seit dem letzten Bericht sonst noch gemessen wurde

Drei Vorarbeiten, alle auf dem Dev-Satz (20 Fälle), die zur eingefrorenen Konfiguration geführt
haben.

### 6a. Liegt das Modell bei denselben Fällen falsch wie die Regeln?

**Nein — und das war die Entwarnung, die den Umbau gerechtfertigt hat.**

```
v1 (Regeln urteilen)   15 Fehler
flash (Modell urteilt)  2 Fehler   (DEV-010, DEV-013)
Schnittmenge            1          (DEV-010)
```

Hätten sich die Fehlermengen gedeckt, wäre die Aufgabe selbst zu schwer gewesen und kein Umbau hätte
geholfen. Sie decken sich fast nicht: die Regeln scheiterten an *anderen* Dingen als das Modell.
DEV-010 ist der eine Fall, an dem beide scheitern — und er ist konstruktionsbedingt schwer.

### 6b. Ensemble aus zwei Modellen: bringt nichts

| Strategie | korrekt | Falschdurchl. | Falschsperren |
|---|---|---|---|
| flash allein | **18/20** | 0 | 2 |
| pro allein | 16/20 | 0 | 3 |
| agreement_or_weaker (bei Uneinigkeit das schwächere) | 16/20 | 0 | 3 |
| agreement_or_review (bei Uneinigkeit `insufficient`) | 16/20 | 0 | 3 |
| agreement_or_stronger | 18/20 | 0 | 2 |

Uneinigkeit bei 2 von 20 Fällen. **Keine Kombinationsregel schlägt das bessere Einzelmodell** — weil
die Uneinigkeiten genau die Fälle sind, in denen einer richtig und einer falsch liegt, und keine
blinde Regel wählen kann, welcher. Zweimal gemessen (flash+pro, flash+gemma), beide Male dasselbe.

Daraus die Umdeutung: Uneinigkeit nicht als *Urteilskombinierer*, sondern als *Triage-Signal*. Das
sah gut aus — und ist blind gescheitert (§4).

### 6c. Vier Modelle aus vier Häusern

| Modell | Haus | korrekt | Falschdurchlässe | Fehlermenge |
|---|---|---|---|---|
| `deepseek-v4-flash` | DeepSeek | **18/20** | **0** | DEV-010, -013 |
| `google/gemma-4-31b-it` | Google | **18/20** | **0** | DEV-005, -010 |
| `deepseek-v4-pro` | DeepSeek | 16/20 | 0 | DEV-004, -005, -010, -013 |
| `qwen/qwen3-30b-a3b` | Alibaba | 13/20 | 1 | 7 Fälle |
| `mistral-small-3.2-24b` | Mistral | 12/20 | **5** | 8 Fälle |

Zwei Befunde:

* **Mistral ist disqualifiziert**, nicht wegen der Trefferquote, sondern wegen der *Richtung*: fünf
  Falschdurchlässe. Ein Modell, das in die gefährliche Richtung irrt, ist für diese Rolle
  unbrauchbar, auch wenn seine Gesamtquote nur wenig schlechter wäre.
* **flash und gemma sind gleichauf und fast komplementär falsch** (nur DEV-010 gemeinsam). Genau das
  machte gemma zur Zweitmeinung — sie ist aus einem anderen Haus, nicht ein Geschwistermodell.
  Geschwister taugen nicht: flash und pro waren sich bei 18 von 20 Fällen einig.

**Nebenbefund zu den Kosten:** flash ist das billigste der geprüften Modelle und zugleich das beste.
Es gibt hier keinen Grössen-/Preis-Effekt, den man ausnutzen müsste.

---

## 7. Was jetzt gilt — und was nicht mehr

| Aussage | Status |
|---|---|
| Fehlerrichtung: lieber sperren als durchlassen | **blind bestätigt**, 0–1 Falschdurchlässe auf 80 Urteilen |
| Modell urteilt besser als Regeln | **bestätigt**, 33/40 vs. 7/20-Niveau; disjunkte Fehlermengen |
| Trefferquote ≈ 90 % | **zurückgezogen** — blind 82,5 % |
| Kontrollschicht schützt | **widerlegt** — 0 Reparaturen, 6 Schäden |
| Kontrollschicht ist wenigstens harmlos | **widerlegt** — sie kostet 2–4 richtige Verdikte je Lauf |
| Uneinigkeit zweier Häuser ist ein scharfes Prüfsignal | **widerlegt** in dieser Platzierung — sieht nur 15 von 40 Fällen |
| Ensemble verbessert das Urteil | **widerlegt**, zweimal |
| Verdikte sind stabil | **bestätigt**, 36/40 identisch; Modellschicht stabiler als die Gesamtkette |
| Beide Sätze sind als Messinstrument verbraucht | **neu** — jede Folgeänderung braucht einen frischen versiegelten Satz |

Was nach dem Blindtest ehrlich übrig bleibt, wenn man die widerlegten Teile abzieht: **ein Modell mit
Mehrheitsentscheid über k=5 Ziehungen, eine Verweigerung bei fehlender Mehrheit, eine
Protokollierung, die jeden Teil des Urteils seiner Herkunft zuweist, und eine Leiter, auf der nur
abwärts korrigiert werden darf.** Das ist weniger, als der Bericht heute Morgen behauptet hat. Es ist
aber gemessen statt behauptet, und die eine Eigenschaft, auf die es ankommt, hält.

---

## 8. Die Fragen, um die es jetzt geht

1. **Kontrollschicht abschalten — jetzt oder nach einem neuen Satz?** Sie ist gemessen schädlich.
   Sie jetzt abzuschalten heisst, eine Konfiguration auszuliefern, deren einzige Messung eine
   Nachrechnung auf dem Satz ist, der sie widerlegt hat. Sie drinzulassen heisst, wissentlich 2–4
   richtige Verdikte je 40 zu verschenken. Ich neige zu: abschalten, aber die 82,5 % **nicht** als
   Zahl dieser Variante ausgeben, sondern als Zahl der gemessenen Variante — und die Abschaltung als
   ungemessene Änderung deklarieren.

2. **Gibt es überhaupt eine Kontrolle, die trägt?** Sechs Kandidaten, sechs aus Einzelfällen
   abgeleitet, null Treffer. Ist die richtige Antwort „bessere Kontrollen" oder „die deterministische
   Schicht gehört nicht ins Entailment-Urteil, sondern nur in die Governance danach"? Der zweite
   Gedanke ist die zweite Kehrtwende an derselben Stelle innerhalb von zwei Tagen — deshalb bin ich
   misstrauisch gegen ihn.

3. **Labelkonvention klären, bevor weiter gemessen wird.** Die `missing_premise` → `insufficient`-
   Regel des Auswerters ist vertretbar und unsere ist es auch. Solange das nicht festgeschrieben ist,
   misst jede Trefferquote zum Teil eine Vokabelfrage. Das ist auch die erste Sache, die man den
   MSCE-Leuten sagen müsste: *welche Konvention wollt ihr?*

4. **Wo gehört das Prüfsignal hin?** Wenn die Zweitmeinung nur durchlassende Verdikte sieht, kann sie
   die häufigste Fehlerklasse nie sehen. Zweitmeinung immer einholen (verdoppelt die Kosten)? Oder
   gezielt bei `compatible_not_entailed`, wo blind die meisten Fehler sitzen?

5. **Was sagen wir MSCE?** Meine Empfehlung ist unverändert *noch nicht antworten mit Zahlen, die als
   Versprechen gelesen werden*. Was berichtsfähig ist: **82,5 % Trefferquote bei 0–1 Falschdurchlass
   auf 40 unabhängig gebauten Fällen, zwei Läufe, 90 % Verdikt-Stabilität** — und die offene
   Konventionsfrage dazu. `API_README.md` sagt das inzwischen selbst, inklusive der Falsifikation der
   Kontrollschicht.

---

## Anhang A — alle 40 Blindfälle

Kürzel: `E` entailed · `PE` partially_entailed · `CNE` compatible_not_entailed · `C` contradicted ·
`INS` insufficient. Spalte „Modell" = Vorschlag des Modells vor den Kontrollen (Lauf 1).

| Fall | Domäne | Gold | Lauf 1 | Lauf 2 | Modell (L1) | |
|---|---|---|---|---|---|---|
| TEST-001 | software | E | E | E | E | ✓✓ |
| TEST-002 | software | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-003 | software | PE | CNE | CNE | CNE | ✗✗ |
| TEST-004 | software | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-005 | software | E | CNE | CNE | CNE | ✗✗ |
| TEST-006 | software | INS | CNE | CNE | CNE | ✗✗ |
| TEST-007 | software | E | PE | PE | **E** | ✗✗ ← Kontrolle |
| TEST-008 | technical | E | E | E | E | ✓✓ |
| TEST-009 | technical | C | C | C | C | ✓✓ |
| TEST-010 | technical | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-011 | technical | E | E | E | E | ✓✓ |
| TEST-012 | science | E | E | E | E | ✓✓ |
| TEST-013 | science | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-014 | science | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-015 | science | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-016 | science | E | E | E | E | ✓✓ |
| TEST-017 | science | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-018 | clinical | E | E | E | E | ✓✓ |
| TEST-019 | clinical | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-020 | clinical | E | E | E | E | ✓✓ |
| TEST-021 | clinical | C | C | C | C | ✓✓ |
| TEST-022 | clinical | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-023 | clinical | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-024 | organizational | C | C | C | C | ✓✓ |
| TEST-025 | organizational | PE | INS | CNE | E | ✗✗ |
| TEST-026 | organizational | E | PE | E | **E** | ✓· ← Kontrolle (L1) |
| TEST-027 | organizational | INS | CNE | CNE | CNE | ✗✗ |
| TEST-028 | organizational | C | C | C | C | ✓✓ |
| TEST-029 | organizational | C | C | C | C | ✓✓ |
| TEST-030 | organizational | E | PE | PE | **E** | ✗✗ ← Kontrolle |
| TEST-031 | everyday | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-032 | everyday | E | E | E | E | ✓✓ |
| TEST-033 | everyday | CNE | CNE | CNE | CNE | ✓✓ |
| TEST-034 | everyday | E | E | E | E | ✓✓ |
| TEST-035 | legal | C | C | C | C | ✓✓ |
| TEST-036 | legal | E | E | E | E | ✓✓ |
| TEST-037 | finance | INS | CNE | CNE | CNE | ✗✗ |
| TEST-038 | finance | E | PE | E | **E** | ✓· ← Kontrolle (L1) |
| TEST-039 | finance | CNE | INS | PE | C | ✗✗ |
| TEST-040 | multi_evidence | E | E | E | E | ✓✓ |

Die vier über die Läufe schwankenden Fälle sind TEST-025, -026, -038, -039 — drei davon
Kontrollartefakte, einer (TEST-039) echte Modellvarianz.

## Anhang B — Reproduzierbarkeit

```
Repo      hstre/Joni · Branch claude/kevin-creativity-architecture-ukz17g
Läufer    experiments/msce_bridge/run_blind.py    (kennt kein Gold, verweigert "PRIVATE"-Pfade)
Auswerter experiments/msce_bridge/score_blind.py  (ändert keine Vorhersage)
Kette     experiments/msce_bridge/audit_v2.py

python run_blind.py  <blindsatz.json> 1
python score_blind.py <gold.json> blind_predictions_run1.jsonl blind_predictions_run2.jsonl
```

Umgebung: `DEEPSEEK_API_KEY` (Urteil), `OPENROUTER_API_KEY` (Zweitmeinung), `ENTAIL_K=5`,
`ENTAIL_PARSER=beta`. Der private Schlüssel liegt **ausserhalb** des Repos und wurde nie
eingecheckt.

**Offener Punkt, unabhängig von der Sache:** die beiden API-Schlüssel wurden im Chat eingefügt und
sind zu rotieren.
