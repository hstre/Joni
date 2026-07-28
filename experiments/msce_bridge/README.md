# DESi ↔ MSCE — Prototyp einer Read-only-Validierungsschicht

**Status: Experiment. Nicht Teil von Jonis autonomer Schleife. Kein Ergebnis, das man
veröffentlichen sollte — eine Vorprüfung, bevor irgendjemand irgendetwas zusagt.**

Das MSCE-Team (Yang Zhang u. a., arXiv 2607.16621, Code in `MemTensor/MemOS` unter
`apps/memos-local-plugin`) hat angeboten, DESi als epistemische Validierungsschicht an der
L2→L3-Konsolidierungsgrenze zu prototypisieren. Vor einer Zusage war eine Frage zu klären:

> **Produziert DESi auf einem echten MSCE-L3-Kandidaten überhaupt ein differenziertes Urteil —
> oder nur `insufficient-semantic-evidence`?**

Antwort: **ja, differenziert.** Wie belastbar das ist, steht unter „Was das *nicht* zeigt".

## Die Architektur, in einem Satz

MSCE konsolidiert `L1-Traces → L2-Policies f²=(φ,π,κ,ℬ,{f¹}) → L3-Weltmodell f³=(ℰ,ℐ,𝒞,{f²})`.
Der L3-Schritt nimmt eine Kohorte von L2-Policies über **Embedding-Zentroid-Ähnlichkeit
(θ_sim = 0.62)** auf, übergibt sie einem LLM-Prompt und speichert das Ergebnis.

Die Nachprüfung in `core/memory/l3/abstract.ts` verifiziert: `title` ist ein nicht-leerer String,
und `environment` / `inference` / `constraints` sind Arrays. **Das ist alles.** Nicht geprüft wird,
ob ein Eintrag durch die zitierten Belege gedeckt ist, ob er überhaupt welche zitiert, oder ob er
Gespeichertem widerspricht.

## Warum Layer 9 dafür schon Vokabular hat

Layer 9 kennt eine Stufe für „billige Rekurrenz hat die Mitglieder gefunden":
`LEXICAL_CANDIDATE`. Ihre Regel lautet, dass so ein Cluster **keine Synthese speisen darf**, bis er
semantisch gemessen wurde (`SEMANTIC_MEASURED`).

Eine θ_sim-Kohorte *ist* genau ein lexikalisch/embedding-basierter Kandidat. MSCE geht in einem
Schritt Kohorte → LLM → gespeichertes L3. Die beiden Architekturen sind sich also über **genau eine
Sache** uneinig, und für diese Sache existiert in Layer 9 bereits ein Zustand.

Deshalb erfindet der Prototyp kein neues Urteilsvokabular, sondern gibt `SemanticState` zurück:

| Layer 9 | Bedeutung für MSCE |
|---|---|
| `synthesis-eligible` | zulässig — belegt, richtig typisiert, deklarativ |
| `lexical-candidate` | als **Hypothese** halten, nicht konsolidieren |
| `human-review-required` | Typisierung prüfen (als Tatsache abgelegt, als Schluss formuliert) |
| `synthesis-rejected` | Schichtfehler oder Widerspruch |
| `insufficient-semantic-evidence` | nicht entscheidbar |

## Die fünf Prüfungen

Alle deterministisch, **kein Modellaufruf**.

| | Prüfung | Grundlage |
|---|---|---|
| C1 | **Verankerung** — löst jedes `evidenceIds` in die `policyIds`/`sourceEpisodeIds` der Zeile auf? | ein nicht auflösbares Zitat ist keine Provenienz |
| C2 | **Facetten-Typisierung** — ℰ = Existenz-Tatsachen, ℐ = Ursache→Wirkung, 𝒞 = die Umwelt-Tatsache, die etwas unsicher macht | MSCEs *eigener* Prompt-Vertrag |
| C3 | **Prozedurale Drift** — Handlungsanweisungen gehören nach L2 | derselbe Prompt verbietet sie ausdrücklich |
| C4 | **Annahme** — unbeschränkte Verallgemeinerung ohne Beleg | Annahme als Beobachtung ausgegeben |
| C5 | **Konfidenz-Provenienz** — gemeldet, nie verwendet | MSCEs `confidence` = LLM-Selbsteinschätzung × Embedding-Kohäsion; keines der Maße ist Evidenz über die Welt |

## Ergebnis auf dem Korpus

`python experiments/msce_bridge/adjudicate.py`

**Echte Fixture-Zeilen (11 Einträge aus ihren Tests):**

| Urteil | Anteil |
|---|---|
| `lexical-candidate` | 7 (64 %) |
| `synthesis-rejected` | 3 (27 %) |
| `synthesis-eligible` | 1 (9 %) |

**Verankert: 1 von 11.** Die drei Ablehnungen sind Schichtfehler, die MSCEs eigener Vertrag
verbietet und ihr Struktur-Validator durchlässt:

- `inference: "binary wheels fail" / "must compile from source"` — „must" ist Anweisung, nicht Ursache→Wirkung
- `constraints: "no --prebuilt" / "avoid binary wheels"` — die Form, die ihr Prompt wörtlich als **BAD** führt
- `constraints: "No pre-built wheels" / "avoid binary on alpine"` — dieselbe Form

## Der Gold-Standard — und ein Fehler, den er gefangen hat

MSCEs Prompt führt eigene **GOOD**-Beispiele. Ein Prüfer, der die ablehnt, ist falsch. Sie liegen
deshalb als fünfte Zeile im Korpus und sind durch einen Test verankert.

Der erste Entwurf ist daran durchgefallen. Er triggerte auf das bloße Verb „install" und verwarf

> „node_modules/ is rewritten by **npm install**; manual edits are lost on the next sync"

— eines ihrer GOOD-Beispiele. „npm install" benennt dort ein Kommando und schreibt nichts vor.
Das Muster prüft jetzt **Modal- und Vermeidungsverben, die sich an einen Leser richten**, nicht
jedes Verb, das eine Handlung bezeichnet. Nach der Korrektur: **0 von 7** GOOD-Beispielen
fälschlich abgelehnt oder fehltypisiert.

Das ist derselbe Fehlermodus wie an drei anderen Stellen dieses Projekts: ein lexikalischer Test
übertriggert, und nur echte Daten zeigen es.

## Was das *nicht* zeigt

Wichtiger als das Ergebnis:

1. **Der Korpus sind Test-Fixtures und Prompt-Beispiele, keine Produktions-LLM-Ausgabe.**
   Fixtures sind von Hand geschrieben, um die Pipeline zu treiben. Das Ergebnis zeigt, dass **das
   Tor durchlässig ist** — nicht, wie oft die Realität dagegen drückt. Die Quote „27 % Schichtfehler"
   ist **keine** Aussage über MSCEs echte Ausgabe.
2. **Die 0/7-Verankerung bei den GOOD-Beispielen ist ein Artefakt meines Korpus**, nicht ein Befund:
   ich habe diese Zeile aus dem Prompt-Text gebaut, sie hat konstruktionsbedingt keine `policyIds`.
3. **Widerspruchserkennung ist nicht implementiert.** Layer 9s `CONTRADICTORY` bräuchte den
   DESi Semantic Layer (FrameDetector, LogicalAuditor) laufend auf *ihrer* Domäne. Ob der auf
   Agenten-Interaktions-Traces sinnvolle Frames produziert, ist die eigentliche offene Frage — und
   sie ist empirisch, nicht durch Nachdenken zu beantworten.
4. **Es wurde kein Modell befragt.** Nur deterministische Prüfungen.

---

# Nachtrag: der Lauf **ohne** die Einschränkungen

Die drei Grenzen oben wurden aufgehoben: `hstre/DESi` ausgecheckt (`DESI_ROOT`), `fastembed`
installiert (BAAI/bge-small-en-v1.5), Semantic Layer und Widerspruchserkennung scharf.
Reproduzierbar mit `experiments/msce_bridge/semantic_probe.py`.

**Was nicht ging:** In dieser Umgebung liegt kein LLM-API-Key (der DeepSeek-Key ist ein
GitHub-Secret, nur für den Runner). Echte L3-Produktionsausgabe erzeugen war deshalb weiterhin
nicht möglich — der Korpus bleibt Fixtures.

## Stufe 1 — Einzelsatz: keinerlei Differenzierung

`FrameDetector` und `LogicalAuditor` liefern für **alle 18** Einträge dasselbe:
`frame_undeclared` (confidence 0.0) und `gap_detected` („no 'Therefore' marker found").

**Das ist kein Domänenproblem.** Dieselben Werte kommen für klinische Sätze heraus, für die DESi
gebaut wurde. Die Komponenten beurteilen *Argumentationsketten mit expliziten Markern*, nicht
freistehende Behauptungen. Ein L3-Eintrag ist eine freistehende Behauptung. Meine frühere Vermutung
(„greift auf dieser Domäne vielleicht nicht") war richtig — aber aus dem falschen Grund.

## Stufe 2 — ohne Embedding: Layer 9 verweigert korrekt

> `insufficient` / `human-review-required` — *„frame undeclared / undecidable and no semantic
> projector — cannot decide"*

Kein lexikalischer Rückfall. Die Governance-Eigenschaft hält.

## Stufe 3 — mit Embedding: der Befund

| | IST | mit simuliertem Fix |
|---|---|---|
| `contradictory` | **66** | 0 |
| `supports` | 43 | 43 |
| `insufficient` | 29 | 95 |
| `complementary` | 14 | 14 |
| `duplicate` | 1 | 1 |

**66 von 153 Paaren (43 %) als Widerspruch geurteilt** — in einem Korpus, der fast ausschließlich
aus einander *stützenden* Aussagen über dieselbe Umgebung besteht. Kein einziges echtes A-und-nicht-A.

Beispiele für Fehlurteile:

```
Alpine uses musl libc                 ||  Alpine containers ship musl libc, no glibc
musl no glibc                         ||  shared libs musl-only
Binary wheels fail musl incompatible  ||  pip fails binary wheels mismatch
```

Alle drei Paare **stimmen überein**.

### Ursache, präzise

`_polarity_clash = antonym_clash(a,b) or (is_negated(a) != is_negated(b))`.
In allen geprüften Fehlurteilen ist `antonym_clash` **False** — es feuert allein die
**Negationswort-Asymmetrie**. Das trifft in `decision._from_distance` auf:

```python
if d <= DIST_SUPPORTS and m.polarity_clash:
    return (CONTRADICTORY, SYNTHESIS_REJECTED, "close in meaning but opposed in polarity")
```

Nah beieinander + ein Negationswort auf *einer* Seite ⇒ Widerspruch **behauptet**. Damit steht an
genau dieser Stelle eine lexikalische Heuristik als semantisches Urteil — die Regel, die das Modul
an jeder anderen Stelle ausdrücklich verbietet.

### Vorgeschlagener Fix (simuliert, **nicht** angewandt)

Eine lexikalische Polarität darf eine Verschmelzung *verhindern*, aber keinen Widerspruch
*behaupten*. Bei undeklarierten Frames also `insufficient / human-review-required`.
Wirkung: 66 → 0 Falschmeldungen.

**Der ehrliche Preis:** das eine echte Gegensatzpaar („ships musl libc, no glibc" vs. „ships
glibc") wird dann ebenfalls nur zur menschlichen Prüfung geleitet statt abgelehnt. Mit Embedding +
Negationsmarker allein ist es von einer Übereinstimmung nicht unterscheidbar — beide sind nah und
negations-asymmetrisch.

Für ein Validierungs-Tor ist das die richtige Richtung (nicht entscheiden ist sicher, korrektes
Wissen verwerfen nicht). Es heißt aber auch: **DESi liefert auf diesen Daten derzeit keine
Widerspruchserkennung.**

`decision.py` liegt *außerhalb* von `joni_core.lock` (gesperrt sind 17 Module direkt unter
`desi_layer9/`, nicht das `semantics/`-Unterpaket). Der Fix wäre technisch erlaubt — er wird hier
trotzdem nicht angewandt, weil er Jonis Konfliktbildung, AleXiona und alles andere mitbetrifft, was
auf dieser Regel steht. Architekturentscheidung, kein Nebenbefund.

## Was der Lauf ohne Einschränkungen unterm Strich sagt

Der Wert des Prototyps kam **vollständig aus den fünf deterministischen Prüfungen** (Verankerung,
Typisierung, Drift). Der semantische Kern hat nichts beigetragen: Stufe 1 differenziert nicht,
Stufe 2 verweigert, Stufe 3 produziert überwiegend Falschmeldungen.

Dem MSCE-Team „DESi validiert eure L3-Abstraktionen" zu schreiben, wäre damit **nicht gedeckt**.
Gedeckt ist: eine Provenienz- und Typisierungsdisziplin, die ihr strukturelles Tor heute nicht hat.

---

# Nachtrag 2: der **echte** End-to-End-Lauf — und was er widerlegt

Mit einem LLM-Schlüssel fiel auch die letzte Einschränkung. `live_run.py` extrahiert MSCEs L2- und
L3-Prompts **verbatim aus ihrem Quelltext** (nicht paraphrasiert), wendet sie auf **echte L1-Traces**
an — Jonis eigenes Protokoll, reale Langzeit-Agenten-Erfahrung, genau MSCEs Zieldomäne — und lässt
sie von `deepseek-v4-pro` ausführen. Ergebnis: 5 echte L2-Policies → 1 echtes L3-Weltmodell mit
18 Einträgen (`live_l2.json`, `live_l3.json`).

## Was der echte Lauf widerlegt

**Die Verankerungs-Zahl aus dem Fixture-Korpus hält nicht.**

| | Fixtures | echte Ausgabe |
|---|---|---|
| verankert (`evidenceIds` auflösbar) | 1 / 11 | **18 / 18** |

Das LLM hat auf echten Daten **jeden einzelnen Eintrag** mit auflösbaren Belegen versehen. Die
„1 von 11" war ein Artefakt handgeschriebener Test-Fixtures, **kein Befund über MSCEs Pipeline.**
C1 — die Prüfung, die ich für die stärkste hielt — findet auf echter Ausgabe nichts zu beanstanden.

## Und die restlichen Flags sind Fehler *meines* Prüfers

Auf den 18 echten Einträgen meldete der Adjudikator 4 × Schichtfehler und 4 × Fehltypisierung.
Ich habe alle acht im Volltext geprüft. **Praktisch alle sind Falschmeldungen:**

| Text (echte MSCE-Ausgabe) | mein Urteil | tatsächlich |
|---|---|---|
| „they **do not have** decision authority, which rests with Layer 9" | Handlungsanweisung | reine Tatsache — `do not` als Verneinung, nicht als Verbot |
| „Source identifiers **must conform** to recognized prefixes" | Handlungsanweisung | Umwelt-Anforderung, beschreibende Modalität |
| „the proposal cycle **must be repeated**" | Handlungsanweisung | beschreibt eine Systemfolge |
| „…returns fewer items, **causing** a shortfall" | fehltypisiert | ist kausal — mein Muster kennt `cause`, nicht `causing` |
| „…**leading to** bottlenecks" | fehltypisiert | ist kausal — Muster kennt `lead`, nicht `leading` |

Zwei getrennte Defekte in meinem Code: `_CAUSAL` erfasst die **-ing-Formen nicht**, und
`_PRESCRIPTIVE` verwechselt **beschreibende Modalität** („must conform", „do not have") mit einer
Anweisung an den Agenten. Zusätzlich war meine Annahme falsch, `constraints` müssten
„observation"-Sprache haben — MSCEs eigenes GOOD-Beispiel für `constraints` ist selbst kausal.

## Der ehrliche Stand nach dem echten Lauf

**Wir haben keinen belastbaren Befund gegen MSCEs Pipeline.** Auf echter Ausgabe findet der
Prototyp im Moment nichts, was nach Prüfung standhält:

- C1 (Verankerung): 18/18 sauber — nichts zu beanstanden
- C2 / C3: melden, aber ihre Meldungen sind überwiegend eigene Fehler
- Semantic Layer: trägt gar nichts bei (siehe Nachtrag 1)

Das aus Nachtrag 1 bleibt bestehen, weil es *nicht* von diesen Prüfungen abhängt: der Semantic
Layer differenziert auf freistehenden Behauptungen nicht, und die Widerspruchsregel produziert bei
aktivem Embedding 43 % Falschmeldungen. Das ist ein Befund über **DESi**, nicht über MSCE.

## Das eigentliche Muster

Das ist innerhalb dieses einen Experiments der **sechste** Fall, in dem eine lexikalische Prüfung
übertriggert: Rekurrenz-Hypothesen, Papertitel-Methoden, Refragmentierungs-Schablonen, „npm
install", die Negations-Asymmetrie in `_polarity_clash`, und jetzt `must` / `do not` / `-ing`.

Die Konsequenz ist nicht, das Muster ein siebtes Mal zu flicken. Sie lautet: **eine lexikalische
Regel kann dieses Urteil nicht tragen.** Wer Beobachtung von Schlussfolgerung von Anweisung
trennen will, braucht dafür eine semantische Messung — und genau die ist das, was DESi heute für
freistehende Behauptungen nicht liefert.

Damit ist die Frage an das MSCE-Team klarer, aber auch bescheidener geworden, als sie vor dem
Ausprobieren aussah.

---

# Nachtrag 3: π(s) gebaut — der SPL misst

Der SPL enthält den Formalismus vollständig (`compute_jsd`, `compute_h_norm`, E0–E4, Gateway), aber
**keinen Projektor**: jede `P_r` im Repo ist ein Literal in `test_app.py`. Der einzige existierende
Builder, AleXionas `clinical_spl._build_P_r`, konstruiert die Verteilung deterministisch aus zwei
LLM-Skalaren (`claim_type`, `ess`) — `H_norm` ist dort eine reine Funktion von `ess` und misst die
Selbsteinschätzung des Extraktors, nicht den Text.

`spl_builder.py` baut π(s) so, wie die Architektur es vorsieht: **LLM für Sprache, Regeln für
Logik.** Zwei *verschiedene* Modelle als unabhängige Builder (`deepseek-v4-pro` / `-flash`), ein
geschlossener versionierter Relationsraum, illegale Masse als `p_illegal` gemessen statt still
normalisiert.

## Der entscheidende Fund: Verhalten schlägt Selbstauskunft

| Vorgehen | Ergebnis |
|---|---|
| Modell nach einer **Verteilung** fragen | `H_norm = 0.000`, ausnahmslos — One-Hot |
| Modell *n*-mal **eine** Relation wählen lassen, `P_r` = Häufigkeit | echte Verteilung |

Ein LLM nach seinen eigenen Wahrscheinlichkeiten zu fragen liefert einen One-Hot-Vektor: es *wählt*
die beste Antwort, es introspektiert keine Verteilung. Genau daran scheitert `clinical_spl` — nur
auf anderem Weg. Die Verteilung muss aus dem **Stichprobenverhalten** kommen.

## Es funktioniert

| Satz | alpha | beta | JSD | Regel |
|---|---|---|---|---|
| „Smoking is **associated with** lung cancer." | `correlates_with` 1.0, H=0 | dito | 0.000 | **E1** emittiert |
| „A surface-code qubit **needs** many qubits" | `requires` 1.0, H=0 | dito | 0.000 | **E1** emittiert |
| „Vitamin D **may reduce** fracture risk" | causes .57 / prevents .43, H=0.985 | prevents .71 / causes .29 | 0.061 | **E3** blockiert |
| „Regular exercise **is good for** health" | supports .57 / causes .43, H=0.985 | supports 1.0 | 0.257 | **E3** blockiert |

Scharfe Aussagen gehen durch, echt mehrdeutige werden geblockt. Bei „associated with" wählten beide
Builder einstimmig `correlates_with` statt `causes` — die inhaltlich richtige Unterscheidung.

**Korrektur eines eigenen Fehlschlusses:** ein früherer Lauf ergab `H_norm = 0` auf vier Sätzen, und
ich schloss daraus „der Kanal ist tot". Alle vier waren auf Relationsebene *eindeutig* — `H=0` war
dort die **richtige** Antwort. Ich hatte ein korrektes Messergebnis als Defekt gelesen.

## Stabilität: gut ausser im Grenzband

`stability.py`, 4 Wiederholungen je Satz, zwei Stichprobengrößen (`stability_results.txt`):

| Fall | n=7 | n=15 |
|---|---|---|
| beide scharfen Sätze | H=0.000, **E1** 4/4 ✓ | H=0.000, **E1** 4/4 ✓ |
| „is good for cardiovascular health" | **E3** 4/4 ✓ | **E3** 4/4 ✓ |
| „may reduce fracture risk" | **E3** 4/4 ✓ | **E2/E3/E3/E3** ✗ |

Mehr Ziehungen machten es **schlechter**, nicht besser (Spanne 0.12 → 0.62). Bei reinem
Stichprobenrauschen müsste n=15 die Varianz senken. Die Neigung des Modells schwankt also selbst
zwischen Läufen — die Ziehungen sind nicht i.i.d. aus einer festen Verteilung. Der Builder ist
**kein stabiler Schätzer**.

Der Ausfall liegt genau an der Schwelle zwischen E2 (emittieren) und E3 (blockieren).

**Konsequenz:** das Grenzband ist kein Urteils-, sondern ein Prüfbereich. Die Instabilität ist
selbst das Signal — wechselt dieselbe Aussage bei Wiederholung die Regel, ist sie per Definition
ein Grenzfall und gehört zu `HUMAN_REVIEW_REQUIRED`. Praktisch: Hysterese-Band um τ₂/τ₃ oder
Mehrfachmessung mit Mehrheitsentscheid. **Nicht:** die Schwelle feiner justieren.

## Was das für die Ausgangsfrage heisst

Die Lücke war exakt eine Komponente breit, und sie ist in ~150 Zeilen zu schliessen. Der Formalismus
stimmt, die Emissionsregeln greifen, die Kette liefert differenzierte und (ausserhalb des
Grenzbands) reproduzierbare Urteile.

Zwei Einschränkungen bleiben und sind keine Kleinigkeiten:

1. **Reichweite.** Der Relationsraum sieht keine *Frame*-Mehrdeutigkeit. „Entropy increases in the
   system" ist auf Relationsebene eindeutig (`has_property`); die Mehrdeutigkeit sitzt in der
   Entität. DESis Frame-Ebene und der SPL-Relationsraum sind orthogonal — sie messen verschiedene
   Dinge, und keines davon ist für sich Layer 9s Frage.
2. **`H_norm` misst Mehrdeutigkeit, nicht Berechtigung.** „The approach seems promising" bekommt
   H=0 — bestimmt formuliert, epistemisch leer. Wer epistemische Berechtigung will, braucht beides.

## Was als Nächstes zu messen wäre

Nicht Benchmarks. Zuerst: einen Satz **echter** L3-Zeilen aus einem MSCE-Lauf durch C1–C4 schicken
und die eine Frage beantworten, auf die es ankommt — **von den Einträgen, die DESi als unbelegt
markiert: wie viele waren tatsächlich falsch?** Das Ergebnis ist in beide Richtungen brauchbar.

Danach erst: Semantic Layer auf ihre Domäne, Widerspruchserkennung, Gate, Benchmarks.
