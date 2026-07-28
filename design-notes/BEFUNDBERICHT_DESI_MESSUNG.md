# Befundbericht: Was misst DESi eigentlich?

**Stand 2026-07-28 · alle Zahlen aus ausgeführten Läufen, nicht aus Überlegung**

Dieses Dokument ist eigenständig lesbar. Es fasst zusammen, was eine Reihe von Messungen an DESi,
Layer 9 und dem Semantic Projection Layer ergeben hat — ausgelöst durch eine Kooperationsanfrage,
die eine unangenehme Frage erzwungen hat: *Können wir eigentlich, was wir behaupten?*

## Kurzfassung

1. **Die Governance-Architektur hält.** Layer 9 verweigert ohne Messung das Urteil, statt zu raten —
   unter echtem Test bestätigt (§2).
2. **Joni fährt einen Notbetrieb**, der den vorgesehenen SPL-Pfad umgeht. Die dort gefundenen
   Defekte — Frame-Rateversuch, 43 % falsche Widerspruchsurteile — betreffen diese Umgehung, nicht
   die Architektur (§0b, §1, §3).
3. **Dem SPL fehlte der Projektor** π(s): jede `P_r` im Repo ist ein Testliteral, der einzige
   Builder baut die Verteilung aus einem LLM-Skalar (§4).
4. **π(s) wurde gebaut** und funktioniert — aber `H_norm` misst die Entschiedenheit des *Modells*,
   nicht die Mehrdeutigkeit des *Textes*. Zwischen Anbietern kehrt sich das Vorzeichen um (§5, §6b).
   Es ist **kein** Grösseneffekt: ein gleich kleines Modell derselben Familie arbeitet korrekt (§6c).
5. **Die eigentliche Kurskorrektur:** Epistemische Berechtigung ist keine Skalargrösse, sondern eine
   **Ableitungsprüfung**. Der Claim-Evidence-Entailment-Auditor ist gebaut, gemessen und hat eine
   HTTP-API (§7b–§7d).
6. **Gegen MSCE gibt es keinen belastbaren Befund** — ein früherer Fixture-basierter Befund wurde
   am echten Lauf widerlegt (§7).
7. **Neun Fälle desselben lexikalischen Fehlermusters** an einem Tag, zwei davon im Fundament, einer
   im Code, der ausdrücklich dagegen gebaut wurde (§8). Dazu zweimal der Gegenfehler: zu früh
   positiv geurteilt.
8. **Ein zehnter Fund anderer Art (§7f):** Das Normalisierungsschema fasst nur *eine* Proposition
   je Aussage. Bei einer Konjunktion fällt der zweite Konjunkt weg — und damit kann ein Claim, der
   etwas ausdrücklich verneint, als `entailed` durchgehen. Ein falsches `entailed` ist das
   gefährlichste Verdikt des Systems. **Das muss vor jedem Angebot an Dritte behoben sein.**

---

## 0. Die beteiligten Teile

| Name | Was es ist |
|---|---|
| **DESi** | Epistemische Governance-Schicht. Soll entscheiden, welche Behauptungen durch die vorliegende Evidenz gedeckt sind. |
| **Layer 9** (`desi_layer9`) | Der versiegelte Kern. Trifft das *governte* Urteil aus Messwerten, die andere liefern. Eigene Regel: **niemals ein lexikalischer Rückfall für ein Verdikt.** |
| **Semantic Layer** (`desi.frames`, `desi.logic`) | Soll Frames erkennen (in welchem Begriffsrahmen steht eine Aussage) und Logik auditieren. |
| **SPL** (Alexandria Semantic Projection Layer) | Formalismus: Text → Wahrscheinlichkeitsverteilung `P_r` über einen geschlossenen Relationsraum → Entropie `H_norm` und Divergenz `JSD` → Emissionsregeln E0–E4. |
| **AleXiona** | Klinischer Demonstrator, einziger Ort mit einem SPL-„Builder". |
| **Joni** | Autonomer Forschungsagent, der DESi/Layer 9 als Governance nutzt. |
| **MSCE** | Fremdes System (arXiv 2607.16621, Code in `MemTensor/MemOS`). Konsolidiert Agenten-Erfahrung: L1-Traces → L2-Policies → L3-Weltmodell. |

**Der Anlass:** Das MSCE-Team hat schriftlich eingeräumt, dass ihr Verfahren operative Nützlichkeit
mit epistemischer Berechtigung verwechseln kann — *„Cross-episode recurrence can reduce accidental
correlations, but it cannot establish that an inferred environmental fact or regularity is causally
correct"* — und angeboten, DESi als Validierungsschicht an der L2→L3-Grenze zu prototypisieren.
Bevor wir zusagen, wurde gemessen.

---

## 0b. Zwei Wege — und welcher hier gemessen wurde

Diese Unterscheidung ist für alles Folgende entscheidend und war in einer früheren Fassung dieses
Berichts nicht sauber gezogen.

**Vorgesehene Architektur (Alexandria):**

```
Text → LLM-Builder → SPL (P_r → H_norm / JSD → E0-E4) → ClaimCandidate → Protokoll / Layer 9
```

Der SPL ist ausdrücklich die *„Formal Bridge between Natural Language and Epistemic Protocol"*.
**DESi bekommt in diesem Weg gar keinen Rohtext.** Die LLMs speisen den SPL, nicht DESi.

**Was Joni tatsächlich fährt:**

```
Text → desi_semantics (FrameDetector + LogicalAuditor + Embedding) → Layer 9
```

Kein SPL. `analyse_pair(a_text=…, b_text=…)` nimmt Rohtext entgegen.

Und `desi_semantics.py` benennt selbst, dass das ein **Notbetrieb** ist: `_alexandria_jsd()`
versucht `from spl import compute_jsd` zu laden, `_general_projector()` gibt `None` zurück mit dem
Kommentar *„None today, by honest finding … there is no general projector"*. Die Datei **wartet auf
den SPL-Projektor** und läuft in dessen Abwesenheit auf Frames plus Embedding-Kosinus.

> **Konsequenz für die Lektüre:** §1 und §3 messen den **Notbetrieb**, nicht die vorgesehene
> Architektur. §4–§6b messen die vorgesehene Brücke. Das ist unten jeweils gekennzeichnet.

---

## 1. Der Frame-Detector — als Klassifikator getestet, was er nicht ist

> *Gemessen wird hier Jonis Notbetrieb (§0b), nicht die vorgesehene Architektur.*

`desi.frames.detector.FrameDetector` erkennt einen Frame auf genau zwei Wegen:

1. Der Text **deklariert sich selbst**: die wörtliche Zeichenkette `"frame: thermodynamic"` o. ä.
2. Treffer in einer geschlossenen Liste: **10 explizite Marker, 8 Buckets, 69 Schlüsselwörter** —
   `entropy`, `heat`, `kelvin`, `shannon`, `kolmogorov`, `modus ponens`, `syllogism`, `like a`,
   `as if`, `" + "`, `"how many"` …

Der Code benennt seinen Ursprung selbst:

> *„entropy is intentionally listed here too — it is the canonical example of a term that, without
> an explicit frame marker, fires both thermodynamic and information-theoretic buckets
> simultaneously and so triggers FRAME_CONFLICT."*

Das ist ein Vokabular aus **einem** wissenschaftsphilosophischen Beispiel.

**Gemessen:** Über drei Domänen — Agenten-Traces, Container-/Tooling-Fakten, klinische Sätze —
liefert der Detektor ausnahmslos `frame_undeclared` (confidence 0.0, *„no marker, no rule bucket
matched"*). Der `LogicalAuditor` liefert ausnahmslos `gap_detected` (*„no 'Therefore' marker
found"*), weil er Argumentketten prüft, nicht freistehende Behauptungen.

Wichtig: Das ist **kein Domänenproblem**. Klinische Sätze („The patient has a fever of 39 degrees
and elevated CRP") liefern dieselben Werte. Der Semantic Layer wurde nie für Klinik gebaut, nur
dort eingebaut.

### Korrektur: Rolle verfehlt

Eine frühere Fassung schloss hieraus, der Detektor „messe nichts". **Das ist ein Urteil über eine
Rolle, die er nicht hat.**

Wenn Frames stromaufwärts vom Protokoll **deklariert** werden — und darauf deutet alles hin: die
expliziten Marker suchen die wörtliche Zeichenkette `"frame: thermodynamic"` —, dann ist der
Detektor ein **Leser von Deklarationen**, kein Rater. Die 69 Stichwörter sind dann ein Rückfall für
undeklarierten Alttext, nicht der Hauptmechanismus. Ich habe ihn als Klassifikator getestet
(Rohtext rein, Frame raus), also in einer Funktion, die im vorgesehenen Weg gar nicht vorkommt.

**Was stehen bleibt:** In Jonis Verdrahtung *wird* er mit Rohtext gespeist, und dort liefert er
konstruktionsbedingt für alles `frame_undeclared`. Das ist ein Befund über den Notbetrieb — nicht
über den Detektor und nicht über DESi.

> **`frame_undeclared` ist im Notbetrieb der Normalfall**, weil dort niemand Frames deklariert.
> Das ist ein Symptom der fehlenden Brücke, nicht eines defekten Bauteils.

---

## 2. Layer 9 verhält sich vorbildlich

Ohne semantischen Projektor gibt Layer 9 zurück:

```
insufficient-semantic-evidence / human-review-required
"frame undeclared / undecidable and no semantic projector - cannot decide"
```

**Es rät nicht.** Es fällt nicht auf eine lexikalische Notlösung zurück. Das ist die zentrale
Governance-Eigenschaft, und sie hat unter echtem Test gehalten.

Die Kehrseite, unbequem formuliert:

> **DESis Ehrlichkeit über Nichtwissen hat verdeckt, dass es meistens nicht wissen kann.**
> `insufficient` zurückzugeben liest sich wie epistemische Tugend. Wenn es das für fast alles
> zurückgibt, regiert die Schicht nichts.

---

## 3. Die Widerspruchsregel im Notbetrieb ist defekt (43 % Falschmeldungen)

> *Gemessen wird hier Jonis Notbetrieb (§0b). Dieser Pfad umgeht den SPL — der Embedding-Kosinus
> steht dort, wo Π/√JSD stehen sollten. Der Befund ist damit **keine** Aussage über die vorgesehene
> Alexandria-Architektur, sondern darüber, was passiert, wenn man sie ohne Brücke betreibt. Er ist
> trotzdem ernst: dieser Pfad läuft in Joni produktiv.*

Sobald ein Embedding-Kanal verfügbar ist (`fastembed`, BAAI/bge-small-en-v1.5), *entscheidet*
Layer 9 — und dann falsch.

**Messung:** 18 Aussagen aus einem Korpus, der fast nur aus einander *stützenden* Sätzen über
dieselbe Umgebung besteht (kein einziges echtes A-und-nicht-A). Alle 153 Paare:

| Urteil | Anzahl |
|---|---|
| `contradictory` | **66 (43 %)** |
| `supports` | 43 |
| `insufficient` | 29 |
| `complementary` | 14 |
| `duplicate` | 1 |

Beispiele für Fehlurteile — alle drei Paare **stimmen inhaltlich überein**:

```
Alpine uses musl libc                 ||  Alpine containers ship musl libc, no glibc
musl no glibc                         ||  shared libs musl-only
Binary wheels fail musl incompatible  ||  pip fails binary wheels mismatch
```

**Ursache, exakt lokalisiert.** `_polarity_clash` ist
`antonym_clash(a,b) or (is_negated(a) != is_negated(b))`. In allen geprüften Fehlurteilen ist
`antonym_clash` **False** — es feuert allein die **Negationswort-Asymmetrie**. Das trifft in
`desi_layer9/semantics/decision.py::_from_distance` auf:

```python
if d <= DIST_SUPPORTS and m.polarity_clash:
    return (CONTRADICTORY, SYNTHESIS_REJECTED, "close in meaning but opposed in polarity")
```

Nah beieinander + ein Negationswort auf *einer* Seite ⇒ Widerspruch **behauptet**. Damit steht an
genau dieser Stelle eine lexikalische Heuristik als semantisches Urteil — die Regel, die das Modul
überall sonst ausdrücklich verbietet.

**Vorgeschlagener Fix (simuliert, nicht angewandt):** Eine lexikalische Polarität darf einen Merge
*verhindern*, aber keinen Widerspruch *behaupten*. Bei undeklarierten Frames also
`insufficient / human-review-required`. **Wirkung: 66 → 0 Falschmeldungen.**

Ehrlicher Preis: Das eine *echte* Gegensatzpaar („ships musl libc, no glibc" vs. „ships glibc")
wird dann ebenfalls nur zur Prüfung geleitet. Mit Embedding + Negationsmarker allein ist es von
einer Übereinstimmung nicht unterscheidbar — beide sind nah und negations-asymmetrisch.

**Nicht angewandt, weil:** die Regel trägt Jonis Konfliktbildung und AleXiona mit. Architektur-
entscheidung, kein Nebenbefund. `decision.py` liegt übrigens **außerhalb** von `joni_core.lock`
(gesperrt sind 17 Module direkt unter `desi_layer9/`, nicht das `semantics/`-Unterpaket) — dass
ausgerechnet dort, wo die epistemischen Urteile fallen, der Schutz endet, ist selbst diskutabel.

### Die naheliegendere Reihenfolge

Alle drei hier gefundenen Defekte — Frame-*Rate*versuch (§1), Negations-Heuristik als
Widerspruchsurteil (§3), Embedding statt Π/√JSD — sind Symptome **derselben** Ursache: der
Notbetrieb tut, was der SPL tun sollte, mit Mitteln, die dafür nicht gedacht sind.

Das legt eine andere Priorität nahe als „Widerspruchsregel patchen": **Joni auf den SPL-Pfad
umstellen**, sobald ein kalibrierter Builder steht. Dann verschwindet die kaputte Regel nicht durch
einen Flicken, sondern weil sie nicht mehr angesteuert wird.

---

## 4. Der SPL hat keinen Projektor

Der SPL enthält den Formalismus **vollständig**: `compute_jsd`, `compute_h_norm`, die
Emissionsregeln E0–E4, das Gateway. Was fehlt, ist π(s) — die Funktion Text → Verteilung.

**Jede `P_r` im gesamten Repo ist ein handgeschriebenes Literal in `test_app.py`:**

```python
P_r={"causes": 0.28, "correlates": 0.27, "inhibits": 0.25, "suggests": 0.20}
```

Der einzige existierende Builder ist AleXionas `clinical_spl._build_P_r`:

```python
primary  = _TYPE_TO_RELATION[claim_type]
residual = (1.0 - ess) / (_N_RELATIONS - 1)
P_r = {r: residual for r in CLINICAL_RELATIONS}
P_r[primary] = ess
```

Die Verteilung wird **deterministisch aus zwei Skalaren** gebaut, die der LLM-Extraktor liefert
(`claim_type`, `ess`). Sie trägt keine Information, die nicht schon in diesen zwei Werten steckt.
Folge, im Docstring selbst dokumentiert: *„ESS ≥ 0.90 → H_norm ≈ 0.22 → E1"* — die „Entropie" ist
eine reine Funktion von `ess` und misst die Selbsteinschätzung des Extraktors, nicht den Text.

Und `JSD` zwischen den Buildern alpha/beta vergleicht zwei so erzeugte Verteilungen: E4 feuert
genau dann, wenn zwei LLM-Aufrufe sich über `claim_type` oder `ess` uneinig waren. Reale
Information — aber **Label-Uneinigkeit**, keine semantische Divergenz.

---

## 5. π(s) gebaut — und es funktioniert

Ein echter Builder wurde implementiert (~150 Zeilen): **LLM für Sprache, Regeln für Logik.** Zwei
*verschiedene* Modelle als unabhängige Builder (`deepseek-v4-pro` / `-flash`), geschlossener
versionierter Relationsraum (12 Relationen), illegale Masse als `p_illegal` gemessen statt still
normalisiert.

### Der entscheidende Fund: Verhalten schlägt Selbstauskunft

| Vorgehen | Ergebnis |
|---|---|
| Modell nach einer **Verteilung** fragen | `H_norm = 0.000`, **ausnahmslos** — One-Hot |
| Modell *n*-mal **eine** Relation wählen lassen, `P_r` = Häufigkeit | echte Verteilung |

> Ein LLM nach seinen eigenen Wahrscheinlichkeiten zu fragen liefert einen One-Hot-Vektor: es
> **wählt** die beste Antwort, es introspektiert keine Verteilung.

Das ist genau der Defekt in `clinical_spl` — nur auf anderem Weg erreicht. Zwei völlig verschiedene
Konstruktionen, dasselbe Scheitern. Die Verteilung muss aus dem **Stichprobenverhalten** kommen.

### Ergebnis

| Satz | alpha | beta | JSD | Regel |
|---|---|---|---|---|
| „Smoking is **associated with** lung cancer." | `correlates_with` 1.0, H=0 | dito | 0.000 | **E1** emittiert |
| „A surface-code qubit **needs** many qubits" | `requires` 1.0, H=0 | dito | 0.000 | **E1** emittiert |
| „Vitamin D **may reduce** fracture risk" | causes .57 / prevents .43, H=0.985 | prevents .71 / causes .29 | 0.061 | **E3** blockiert |
| „Regular exercise **is good for** health" | supports .57 / causes .43, H=0.985 | supports 1.0 | 0.257 | **E3** blockiert |

Scharfe Aussagen gehen durch, echt mehrdeutige werden geblockt. Bei „associated with" wählten beide
Builder einstimmig `correlates_with` statt `causes` — die inhaltlich richtige Unterscheidung.

---

## 6. Stabilität: gut, außer im Grenzband

4 Wiederholungen je Satz, zwei Stichprobengrößen:

| Fall | n=7 | n=15 |
|---|---|---|
| beide scharfen Sätze | H=0.000, **E1** 4/4 ✓ | H=0.000, **E1** 4/4 ✓ |
| „is good for cardiovascular health" | **E3** 4/4 ✓ | **E3** 4/4 ✓ |
| „may reduce fracture risk" | **E3** 4/4 ✓ | **E2/E3/E3/E3** ✗ |

**Mehr Ziehungen machten es schlechter, nicht besser** (H-Spanne 0.12 → 0.62). Bei reinem
Stichprobenrauschen müsste n=15 die Varianz senken. Die Neigung des Modells schwankt also selbst
zwischen Läufen — die Ziehungen sind **nicht i.i.d. aus einer festen Verteilung**. Der Builder ist
kein stabiler Schätzer.

Der Ausfall liegt genau an der Schwelle E2 (emittieren) / E3 (blockieren).

**Vorgeschlagene Konsequenz:** Das Grenzband ist kein Urteils-, sondern ein **Prüfbereich**. Die
Instabilität ist selbst das Signal — wechselt dieselbe Aussage bei Wiederholung die Regel, ist sie
per Definition ein Grenzfall und gehört zu `HUMAN_REVIEW_REQUIRED`. Praktisch: Hysterese-Band um
τ₂/τ₃ oder Mehrfachmessung mit Mehrheitsentscheid. **Nicht:** die Schwelle feiner justieren.

---

## 6b. Zweiter Builder (IBM Granite) — die Messung repliziert **nicht**

Die Ergebnisse aus §5/§6 beruhten auf **einer Modellfamilie** (`deepseek-v4-pro` / `-flash`). Der
Gegentest mit einem unabhängigen Builder — **IBM Granite 4.1-8b via OpenRouter**, anderes Haus,
andere Trainingsdaten — kippt die Schlussfolgerung.

| | Granite Ø | DeepSeek Ø |
|---|---|---|
| `H_norm` bei **scharfen** Aussagen | **0.650** | **0.000** |
| `H_norm` bei **mehrdeutigen** Aussagen | **0.252** | **0.747** |

**Die Entropie ist zwischen den Modellen antikorreliert.** Granite ist unsicher, wo die Aussage klar
ist, und sicher, wo sie mehrdeutig ist. DeepSeek zeigt das umgekehrte — und richtige — Muster.

> **`H_norm` misst nicht die Mehrdeutigkeit der Aussage, sondern die Entschiedenheit des Modells.**
> Bei DeepSeek fiel beides zufällig zusammen. Bei Granite fällt es auseinander.

Folgen:

- **Bei 4 von 7 Sätzen urteilen die Builder verschieden** — `granite=E3` (blockieren) gegen
  `deepseek=E1` (emittieren), am selben Satz. Ein Tor, dessen Verdikt vom eingesetzten Builder
  abhängt, misst nicht die Eingabe.
- **Bedeutungsumkehr:** „Loading a glibc-linked binary wheel **raises** a dynamic-link error" →
  Granite antwortet in ⅔ der Ziehungen `prevents`. Keine Unschärfe, sondern eine Inversion. Wären
  beide Builder gleichermassen sicher und gleichermassen falsch, ginge das als E1 glatt durch —
  nichts in der Kette fängt gemeinsamen Irrtum.
- **Cross-Vendor-JSD Ø 0.508, max 1.000** (innerhalb der DeepSeek-Familie: 0.000–0.257). Bei
  τ₄ = 0.40 würde E4 auf der Mehrheit der Paare feuern. Geschwister-Builder sind also systematisch
  zu blind — aber die Gegenrichtung ist genauso unbrauchbar: verzweigt fast alles, entscheidet
  nichts mehr.

**Was funktioniert hat:**

- **E0 griff sauber.** Bei „Vitamin D may reduce fracture risk" antwortete Granite in **8 von 9**
  Ziehungen ausserhalb des geschlossenen Relationsraums (`p_illegal = 0.889`) → strukturelle
  Zurückweisung. Genau dafür ist die Regel da.
- **Der Idealfall trägt.** „Smoking is associated with lung cancer" → beide Builder
  `correlates_with`, beide H=0, JSD=0.000. Stimmen zwei unabhängige Modelle überein und sind
  sicher, ist die Messung belastbar.

**Zurückgenommen:** Die Formulierung aus §5/§9, die Lücke sei „exakt eine Komponente breit" und der
Builder „funktioniere", beruhte auf einer Modellfamilie und hält dem Gegentest nicht stand.

**Genauere Fassung:** `H_norm` misst **Modellunsicherheit**. Ob die der Textmehrdeutigkeit folgt,
hängt vollständig von der Builderqualität ab — ein starkes Modell approximiert sie, ein schwaches
nicht. Und die Builderqualität wird nirgends gemessen. Die Zwei-Builder-JSD kann das nicht leisten,
weil zwei schwache Builder sich auch einig sein können.

**Ehrliche Asymmetrie:** Granite 4.1-8b (8 Mrd. Parameter) ist deutlich kleiner als
`deepseek-v4-pro`. Der Unterschied könnte Modellgrösse sein statt Anbieter. → **Kontrolliert in
§6c.**

---

## 6c. Kontrollversuch: es ist **kein** Grösseneffekt

Um den Confound aus §6b zu trennen, derselbe Testsatz mit `deepseek-v4-flash` — **klein, aber
dieselbe Familie**. Damit variiert nur die Grösse, nicht der Anbieter.

| | **flash** (klein, DeepSeek) | **granite** (klein, IBM) | **pro** (gross, DeepSeek) |
|---|---|---|---|
| Relation korrekt (scharf) | **4/4** | 3/4 | 4/4 |
| `H_norm` bei **scharf** | **0.000** ✓ | 0.650 ✗ | 0.000 ✓ |
| `H_norm` bei **mehrdeutig** | **0.878** ✓ | 0.252 ✗ | 0.382 ✓ |
| illegale Masse (`p_illegal`) | **0.000** | 0.127 (bis 0.889) | — |
| JSD gegen `pro` | **Ø 0.070** (max 0.269) | Ø 0.508 (max 1.000) | — |

**Die Inversion ist kein Grösseneffekt.** `deepseek-v4-flash` ist ebenfalls klein und verhält sich
vollständig korrekt: null Entropie bei scharfen Aussagen, hohe bei mehrdeutigen, keine einzige
Antwort ausserhalb des Relationsraums — und es trifft auch den Satz, den Granite invertiert hatte
(`causes` statt `prevents`).

Der Confound ist damit aufgelöst, aber anders als vermutet: **es liegt am konkreten Modell, nicht an
der Kapazität.**

### Was daraus für „einfach das bessere Modell nehmen" folgt

Der Vorschlag wird **gestützt**, mit einer präzisen Auflage.

*Gute Nachricht:* Es gibt keine Kapazitätsschwelle, die erst erklommen werden müsste. Ein kleines,
billiges Modell reicht — Flash ist hier so gut wie Pro und in einem Punkt besser: bei „Vitamin D may
reduce fracture risk" ist **Pro fälschlich sicher** (H=0.000 → E1 emittieren), während Flash die
Mehrdeutigkeit korrekt sieht (H=0.991 → E3 blockieren).

*Die Auflage:* **Eignung ist nicht aus Grösse oder Ruf ableitbar.** Granite-8b und Flash sind beide
„klein"; eines funktioniert, das andere invertiert. „Das bessere Modell nehmen" ist richtig — aber
„besser" muss **pro Modell gemessen** werden, nicht geschätzt. Ein Builder-Eignungstest gegen einen
Gold-Standard wird damit ein **Pflichtschritt vor dem Einsatz**, kein optionaler.

### Zwei Bestätigungen nebenbei

- **Die Grenzfall-Instabilität (§6) bleibt.** „Vitamin D may reduce fracture risk" ist derselbe
  Satz, der im Stabilitätslauf zwischen E2 und E3 sprang. Hier gibt Pro H=0.000, in früheren Läufen
  0.35–0.97 — dasselbe Modell, derselbe Satz, verschiedene Ergebnisse.
- **`H_norm` ≠ Berechtigung, jetzt an drei Modellen.** „The approach seems promising" → alle drei
  geben H=0.000 und `has_property`. Alle sind sicher bei einer Aussage ohne Gehalt. **Kein
  Modellwechsel behebt das**, weil es kein Modellproblem ist.

---

## 7. MSCE-seitig: kein belastbarer Befund

Was an ihrer Pipeline gemessen wurde:

- **Ihre Nachprüfung nach dem LLM-Aufruf ist rein strukturell** (`core/memory/l3/abstract.ts`):
  `title` ist ein nicht-leerer String, die drei Facetten sind Arrays. Nicht geprüft wird, ob ein
  Eintrag durch die zitierten Belege gedeckt ist, ob er welche zitiert, oder ob er Gespeichertem
  widerspricht.
- **Ihr Prompt-Ausgabeschema zeigt `evidenceIds: []`** (leer) bei zwei von drei Facetten — der
  Prompt bringt dem Modell also selbst bei, dort keine Belege zu setzen.
- Ihre `confidence` = LLM-Selbsteinschätzung × Embedding-Kohäsion. Keines der Maße ist Evidenz über
  die Welt.

**Aber:** Ein echter End-to-End-Lauf (ihre Prompts *verbatim*, echte Agenten-Traces, echtes LLM)
ergab **18/18 Einträge mit auflösbaren Belegen**. Ein früherer, auf Test-Fixtures gestützter Befund
(„1 von 11 verankert") war ein **Artefakt handgeschriebener Fixtures** und hält auf echter Ausgabe
nicht.

Die übrigen 8 Beanstandungen des Prototyps waren nach Volltextprüfung **Fehler des Prüfers**:
„they *do not have* decision authority" als Handlungsanweisung geurteilt (ist eine Tatsache),
„must conform to recognized prefixes" ebenso (beschreibende Modalität), „causing"/„leading to"
nicht als kausal erkannt (Muster kannte nur `cause`/`lead`).

> **Fazit MSCE-seitig: Wir haben keinen belastbaren Befund gegen ihre Pipeline.**

---

## 7b. Die Kurskorrektur: es ist gar keine Skalarfrage

Bis hierher sucht dieser Bericht eine **einzelne Messgrösse für epistemische Berechtigung** und
stellt fest, dass keine existiert. Das war ein **Kategorienfehler**.

Für den MSCE-Fall lautet die relevante Prüfung nicht *„wie mehrdeutig ist dieser Satz"*, sondern:

```
gegebene Evidenz + zulässige Prämissen   ⟹   L3-Claim ?
```

Das ist **Claim-Evidence-Entailment**, nicht semantische Entropie. Damit ordnen sich die Ebenen:

| Ebene | Frage |
|---|---|
| **Semantic Layer / SPL** | *Was* behauptet der Satz? Relation, Modalität, Reichweite — und wie eindeutig ist diese Lesart? |
| **DESi** | Folgt dieser normalisierte Claim aus den angegebenen Belegen? |
| **Layer 9** | Welches Ergebnis darf persistent werden? |

Der Semantic Layer ist **Zulieferer**. Seine Modellabhängigkeit (§6b/§6c) ist ein Problem der
*Normalisierung* — sie macht die Governance nicht hinfällig. Und `H_norm` sollte epistemische
Berechtigung nie allein leisten; dass es das nicht kann, ist kein Defekt, sondern eine
Zuständigkeitsfrage.

**Damit ist §10 Punkt 2 der früheren Fassung erledigt**, nicht durch eine Antwort, sondern durch
eine bessere Frage.

---

## 7c. Der Entailment-Auditor — gebaut und gemessen

`experiments/msce_bridge/entailment.py`. Eingang: `claim`, `evidence[{text, source_id}]`,
`declared_assumptions`, `context`. Ausgang: Verdikt + Verstösse + Begründung.

**Verdikte:** `entailed` · `partially_entailed` · `compatible_not_entailed` · `contradicted` ·
`insufficient`

**Verstösse:** `missing_premise` · `causal_upgrade` · `modal_strengthening` · `scope_expansion` ·
`unsupported_generalization` · `entity_shift` · `condition_dropped`

### Die Bauweise ist die Lehre aus §8

**Das LLM parst, die Regeln urteilen.** Claim und Belege werden in eine Struktur überführt —
Subjekt, Relation, **Modalität**, **Quantor**, **Reichweitenebene**, Bedingungen — alles aus
geschlossenen Vokabularen:

```
modality    : negated < hypothetical < possible < probable < asserted
quantifier  : singular < existential < generic < universal
scope_level : instance < subclass < class
```

Das Verdikt entsteht dann aus einem **Ordnungsvergleich**. Ein Quantorensprung ist
`QUANT_RANK[claim] > QUANT_RANK[evidence]` — kein Wortfund. Damit ist der Fehlermodus aus §8
konstruktiv ausgeschlossen: es gibt keine lexikalische Regel mehr, die ein semantisches Urteil trägt.

### Das Beispiel aus dem Auftrag

```
Evidence: Alpine uses musl. / A binary wheel failed to load in one Alpine container.
Claim:    Binary wheels are incompatible with musl systems.

⇒ COMPATIBLE_NOT_ENTAILED
   ✗ unsupported_generalization · Claim quantifiziert 'generic', Evidenz nur 'existential'
   ✗ scope_expansion           · Claim spricht auf Ebene 'class', Evidenz nur 'instance'
```

Das Urteil behauptet **nicht**, der Claim sei falsch. Es sagt: die genannten Belege tragen ihn nicht.

### Drei Regelfehler, die der Testsatz gefunden hat

1. **Negation in der Relation statt in der Modalität.** „ships glibc" → `has_property`, „does not
   ship glibc" → `prevents`. Zwei Relationen für dieselbe Proposition — der echte Widerspruch blieb
   unerkannt.
2. **Bedingung in die Relation gefaltet.** „succeeds *when* X" → `requires` mit leerem `conditions`.
3. **Unerlaubte Komposition** — der schwerste, und meiner. Ich nahm das Maximum **pro Dimension
   unabhängig über alle Belege**. Damit konnte ein Claim die Relation aus Beleg A und die Reichweite
   aus Beleg B beziehen, obwohl kein einzelner Beleg die Kombination trägt. Eine MSCE-Kontrolle ging
   dadurch fälschlich als `entailed` durch. Jetzt werden Modalität, Quantor und Reichweite nur gegen
   jene Belege geprüft, die **die behauptete Relation berühren**.

### Der Engpass war wieder die Normalisierung

Identischer Code, identische Eingabe, fünf Läufe mit **einer** Ziehung je Aussage:

```
9/9 · 6/9 · 7/9 · 8/9 · 8/9        (Spanne 3)
```

Der Parser ist trotz `temperature=0.0` nicht deterministisch. **Hätte ich nach dem 9/9-Lauf
aufgehört, wäre ein funktionierender Auditor gemeldet worden — es war der beste von fünf Würfen.**

**Fix: Mehrheitsentscheid pro Feld.** Jedes Strukturfeld wird *k*-mal gezogen und ausgezählt. Fehlt
die **strikte Mehrheit**, gilt das Feld als *unbestimmt*, und die Regeln urteilen nicht mehr darauf,
sondern geben `insufficient` zurück — Uneinigkeit wird vom Fehler zum Signal.

```
k=5, vier Läufe:  9/9 · 8/9 · 8/9 · 8/9     (Spanne 1)
```

Beobachtete Feld-Zustimmung: **0.6 – 1.0**. In den geprüften Läufen blieb **kein** Feld unbestimmt —
die `insufficient`-Notbremse musste nie greifen. Die Streuung bei k=1 kam also von einzelnen
Ausreissern, nicht von echter Unentscheidbarkeit.

### Der verbleibende Fehler ist kein Fehler

Reproduzierbar scheitert **derselbe** Fall, mit Zustimmung **1.0** auf allen Feldern: Das Modell
liest *„The build succeeds **when** the musl headers are pre-installed"* konsistent als `requires` —
als Voraussetzungsrelation. Das ist eine vertretbare Lesart, möglicherweise die bessere. Mein
Testfall hatte die andere als Wahrheit gesetzt, ohne das zu begründen.

> **Nicht der Parser lag falsch, sondern mein Gold-Standard ist an dieser Stelle strittig.**

Dasselbe bei zwei „nicht erkannten" Verstössen: Beim Alpine-Fall ist der Claim `generic` und der
Beleg „Alpine uses musl" ebenfalls — es *gibt* keinen Quantorensprung; die Verallgemeinerung
erscheint korrekt als `scope_expansion`. Meine Erwartung war überspezifiziert.

**Konsequenz für die Kalibrierungsfrage (§10.3b):** Ein Gold-Standard für strukturelles Parsen
enthält genuin strittige Items. Damit ist die **Annotator-Übereinstimmung die Obergrenze** jeder
Builder-Kalibrierung — „das bessere Modell" kann sie nicht überschreiten. Ein Eignungstest braucht
deshalb *zwei* Kategorien: unstrittige Items, an denen ein Builder nicht scheitern darf, und
strittige, bei denen nur **Konsistenz** zählt, nicht Übereinstimmung mit einer Referenz.

---

## 7d. Die API — und der neunte Fehlschlag

`experiments/msce_bridge/api.py` (FastAPI). `POST /v1/audit`, `POST /v1/audit/batch`,
`GET /v1/capabilities`, `GET /v1/health`. Read-only, speichert nichts, hält keine Zugangsdaten.

Zwei Entscheidungen:

- **Die Antwort trennt Modell von Regel.** Jedes Ergebnis trägt
  `determinism: {model_derived: ["structures"], rule_derived: ["verdict","violations",
  "justification"], parser_model, draws_per_statement}`. Der Aufrufer muss nicht glauben, dass die
  Regeln entscheiden — er sieht es.
- **`/v1/capabilities` liefert die gemessenen Grenzen als Teil des Vertrags**: Testsatzgrösse 9
  („a demonstration set, NOT a validation corpus"), die Streuungsbänder, der strittige Gold-Fall,
  die Modellabhängigkeit, die fehlende Kalibrierung, die Kostenformel `k · (n + m)` Aufrufe.

### Der neunte Fall des Musters — in eigenem neuen Code

Der erste HTTP-Aufruf lieferte für den Alpine-Fall `contradicted` statt `compatible_not_entailed`.
Ursache: *„A binary wheel **failed** to load"* wurde als `modality: negated` geparst. Aber „failed"
ist **negative Valenz, keine Verneinung der Proposition** — der Satz behauptet, dass ein Fehlschlag
eintrat, und **stützt** den Claim.

Das ist strukturell exakt `_polarity_clash` aus §3. Zwei Fixes: der Prompt unterscheidet jetzt
„berichtet einen Fehlschlag" von „leugnet die Aussage", und ein Widerspruch verlangt zusätzlich
**Objekt**überlappung, also dieselbe Proposition — nicht bloss Relationsgleichheit plus Subjektnähe.

Gefunden hat das die HTTP-Schnittstelle, **nicht** der Testsatz.

### Ehrlich zum Ergebnis nach dem Fix

Die beiden Fehler sind behoben und direkt verifiziert. **Der Testsatz-Score wurde dadurch aber nicht
besser:**

```
k=5 vor den Fixes:   9/9 · 8/9 · 8/9 · 8/9        (Spanne 8–9)
k=5 nach den Fixes:  8/9 · 8/9 · 7/9 · 8/9        (Spanne 7–9)
```

Bei so wenigen Läufen sind die Bänder nicht unterscheidbar. Die Restvarianz wird von diesen beiden
Fehlern **nicht** erklärt. Verstösse im selben Zeitraum: 4/7 bis 7/7.

---

## 7e. Kohärenz-Sonde: welche Teile sind aneinander anschlussfähig?

Statt einer Kompatibilitätsmatrix eine **Messung**: dieselben Sätze durch mehrere Bauteile schicken
und vergleichen (`coherence.py`, 6 Aussagen, 3 Paare, ein Lauf).

### P1 — Redundanz bestätigt: **6/6**

SPL-Builder (F) und Entailment-Parser (G) bestimmen bei **allen sechs** Sätzen dieselbe Relation.
F ist auf dieser Dimension vollständig in G enthalten. Zwei Modellaufruf-Pfade für dieselbe
Information.

### P2 — meine Synthese-Hypothese: **widerlegt** (r = −0.000)

Ich hatte vermutet, `H_norm` (F) und die Feld-Uneinigkeit des Parsers (G) messen dasselbe. Sie
korrelieren nicht. Aber der Grund ist nicht, dass sie Verschiedenes messen — sondern:

| Satz | `H_norm` (F) | Parser-Uneinigkeit (G) |
|---|---|---|
| „Alpine containers ship musl libc" (scharf) | **0.722** ✗ | **0.000** ✓ |
| „Smoking is associated with…" (scharf) | 0.000 ✓ | 0.000 ✓ |
| „…raises a dynamic-link error" (scharf) | 0.000 ✓ | 0.000 ✓ |
| „Vitamin D **may** reduce…" (mehrdeutig) | **0.000** ✗ | **0.400** ✓ |
| „Regular exercise is good for…" (mehrdeutig) | 0.722 ✓ | 0.200 ✓ |
| „The approach seems promising" (leer) | 0.000 | 0.000 |

**Der Parser trifft in allen sechs Fällen richtig; `H_norm` liegt bei zwei von sechs daneben — und
zwar bei den beiden entscheidenden.** In diesem Lauf hat `H_norm` den scharfen Satz für mehrdeutig
und den mehrdeutigen für scharf gehalten, also genau invertiert gegenüber früheren Läufen (§5).
Die Korrelation lief mithin gegen eine instabile Referenz.

> Die Synthese-Idee überlebt — in der **umgekehrten** Richtung als gedacht: nicht „G validieren an
> F", sondern **F durch G ersetzen**. Die Feld-Uneinigkeit des Parsers ist das stabilere
> Mehrdeutigkeitsmass. (Sechs Sätze, ein Lauf — ein Hinweis, keine Aussage.)

### P3 — nicht vergleichbar, aber ein Fund

Layer 9 gab für alle drei Paare `insufficient-semantic-evidence` zurück: in dieser Umgebung war
`fastembed` deinstalliert, also kein Projektor, also — korrekterweise — kein Urteil (§2). Die
E-Seite war damit dunkel; ein Vergleich E↔H fand nicht statt.

Dafür fiel beim Nachfassen ein **schwerer Fehler im Auditor** auf (siehe §7f).

### P4 — Kante A→E ist tot: **0/6**

Der FrameDetector liefert über alle sechs Sätze `frame_undeclared`. Kein einziger brauchbarer Frame.
Die Kante zu Layer 9 trägt nur, wenn stromaufwärts jemand Frames **deklariert** — und im Notbetrieb
tut das niemand (§0b, §1).

---

## 7f. Der schwerste Fund des Tages: falsches `entailed` bei Konjunktionen

Beim Richtungstest zum Widerspruchsfall:

```
Richtung 1   Claim: "Alpine containers ship glibc."
             Beleg: "Alpine containers do not ship glibc."
             → contradicted                                    ✓

Richtung 2   Claim: "Alpine containers ship musl libc, no glibc."
             Beleg: "Alpine containers ship glibc."
             → ENTAILED                                        ✗✗✗
             geparst als: subj='Alpine containers' obj='musl libc' asserted
```

Der Parser hat **„no glibc" ersatzlos verschluckt.** Die Aussage ist eine **Konjunktion** zweier
Propositionen; das `Structure`-Schema fasst nur *eine* — und die weggefallene war genau die, in der
der Widerspruch sass. Ergebnis: der Auditor bescheinigt einem Claim, der glibc ausdrücklich
verneint, er folge aus einem Beleg, der glibc behauptet.

**Ein falsches `entailed` ist das gefährlichste Verdikt, das dieses System produzieren kann** —
es lässt eine unbegründete Behauptung mit Gütesiegel passieren.

Das ist **kein** lexikalisches Übertriggern wie die Fälle 1–9, sondern eine **repräsentationale**
Lücke: das Normalisierungsschema ist zu dünn für zusammengesetzte Aussagen. Und es trifft echte
Daten — die MSCE-Kontrolle *„…are candidates only; they do not have decision authority…"* ist
genauso gebaut.

### Behoben: Zerlegung, mit Ablehnung als Sicherung

Umgesetzt wurde **beides** — zerlegen wo eindeutig, ablehnen wo nicht:

* `split_propositions()` teilt eine Aussage in atomare Propositionen; die **Anzahl** wird über k
  Ziehungen per strikter Mehrheit bestimmt. Ohne Mehrheit über die Anzahl ist die Zerlegung
  unbestimmt ⇒ `insufficient`, statt auf einem Teilparse zu urteilen.
* Jeder Konjunkt wird **einzeln** geparst und geprüft. `combine()` verknüpft deterministisch in
  Sicherheitsreihenfolge: **ein** widersprochener Konjunkt macht das Ganze `contradicted`, und
  `entailed` verlangt, dass **jeder** Teil trägt.
* Belege werden ebenfalls zerlegt — jeder atomare Teil ist ein eigener Beleg. Das kann Stützung nur
  sichtbarer machen, nie verstecken.

Ergebnis am auslösenden Fall:

```
Claim: "Alpine containers ship musl libc, no glibc."   Beleg: "Alpine containers ship glibc."
  zerlegt in 2 → Teil 1 entailed · Teil 2 contradicted  ⇒  CONTRADICTED   ✓ (vorher ENTAILED)
```

Und an der echten MSCE-Konjunktion („… are candidates only; they do not have decision authority")
wird jetzt korrekt in zwei Propositionen zerlegt und jede einzeln geprüft.

**Der gefährliche Fehler ist weg — das Band wurde dadurch aber NICHT enger:**

| Konfiguration | Verdikte | Verstösse | Läufe |
|---|---|---|---|
| k=5, vor den HTTP-Fixes | 8/9 – 9/9 | 6/7 – 7/7 | 4 |
| k=5, nach den HTTP-Fixes | 7/9 – 9/9 | **4/7** – 7/7 | 4 |
| **k=5 + Zerlegung** | **6/9 – 9/9** | 4/7 – 7/7 | **4** |

Die Antwort trägt jetzt `propositions` und `per_proposition`, sodass sichtbar ist, *wie* zerlegt
wurde und welcher Teil woran scheiterte.

**Preis:** die Kosten steigen. Ein Zerlegungsschritt je Aussage kommt hinzu, bei zwei Konjunkten
also grob das Dreifache. Für ein Gate an einer Konsolidierungsgrenze vertretbar; für Volumen
bräuchte es eine Vorprüfung, die nur zusammengesetzte Aussagen in den vollen Pfad schickt — nicht
gebaut.

---

## 8. Das Meta-Muster — der wichtigste Befund

An **acht** Stellen wurde derselbe Fehlermodus gefunden, an einem Tag:

| # | Ort | Fehlmechanismus |
|---|---|---|
| 1 | Rekurrenz-Hypothesen | lexikalische Wiederholung ⇒ „Hypothese" |
| 2 | Papertitel als Methoden | Titel-String ⇒ „Verfahren" |
| 3 | Refragmentierungs-Schablonen | geteilte Satzform ⇒ „Assoziation" |
| 4 | „npm install" | Verb im Kommandonamen ⇒ „Handlungsanweisung" |
| 5 | `_polarity_clash` | Negationswort-Asymmetrie ⇒ „Widerspruch" |
| 6 | `must` / `do not` / `-ing` | beschreibende Modalität ⇒ „Vorschrift" |
| 7 | Frame-Detector **im Notbetrieb** | 69 Stichwörter ⇒ „Frame" (§1: dort in einer Rolle, die er nicht hat) |
| 8 | `clinical_spl._build_P_r` | ein Skalar ⇒ „Verteilung" |
| 9 | Entailment-Parser (§7d) | „failed" ⇒ „negiert" — negative Valenz als Verneinung gelesen |
| **10** | **Entailment-Schema (§7f)** | **Konjunktion ⇒ erster Konjunkt; der Rest fällt weg — kein lexikalischer, sondern ein REPRÄSENTATIONALER Fehler** |

> **Eine lexikalische Regel kann ein semantisches Urteil nicht tragen.**
> Und: Ein reicher Formalismus über einer dünnen Eingabe misst die Eingabe, nicht die Welt.

Nr. 8 ist die schmerzhafteste — sie steht nicht in der Peripherie, sondern im Fundament der
*vorgesehenen* Architektur. Nr. 7 relativiert sich nach der Korrektur in §1: dort ist die
Stichwortliste ein Rückfall, den erst der Notbetrieb zur Hauptsache macht.

**Nr. 9 ist die lehrreichste**, weil sie in Code entstand, der ausdrücklich gegen dieses Muster
gebaut wurde (§7c: „das LLM parst, die Regeln urteilen"). Die Regelseite war sauber — der Fehler
rutschte über die *Normalisierung* wieder herein, weil ein Modell „failed" für eine Verneinung
hielt. Das Muster lässt sich also nicht an einer Stelle abstellen; es wandert dorthin, wo Sprache
in Struktur übersetzt wird.

Die Nummern 1–6 teilen sich denselben Ursprung: **wo eine semantische Messung fehlt, tritt eine
lexikalische Regel an ihre Stelle** — und niemand merkt es, weil sie plausible Ausgaben liefert.

### Der Gegenfehler, zweimal

Ebenso wichtig: **zweimal wurde in die andere Richtung zu früh geschlossen.**

* Aus vier Sätzen mit `H_norm = 0` wurde „der Kanal ist tot" gefolgert. Alle vier waren auf
  Relationsebene *eindeutig* — Null war die **richtige** Antwort. Ein korrektes Messergebnis wurde
  als Defekt gelesen.
* Nach *einem* 9/9-Lauf des Entailment-Auditors stand „es funktioniert" fest. Es war der beste von
  fünf Würfen (§7c).

Beide Richtungen haben dieselbe Wurzel: **Urteil auf zu wenig Daten.** Deshalb steht in diesem
Bericht zu jeder Zahl die Anzahl der Läufe.

**Und die Gegenrichtung:** Einmal wurde zu früh in die andere Richtung geschlossen — aus vier
Sätzen mit `H_norm = 0` wurde „der Kanal ist tot" gefolgert. Alle vier waren auf Relationsebene
*eindeutig*; Null war die **richtige** Antwort. Ein korrektes Messergebnis wurde als Defekt gelesen.
Beide Fehler haben dieselbe Wurzel: Urteil auf zu wenig Daten.

---

## 9. Gesamturteil

**DESi ist kein Fail. Die Brücke fehlt — und wo sie fehlt, wird improvisiert.**

| Ebene | Weg | Status |
|---|---|---|
| Governance-Architektur (Modelle schlagen vor, Regeln entscheiden, bei Nichtmessbarkeit verweigern) | beide | **funktioniert, unter echtem Test bestätigt** |
| Ledger, Provenienz, Lock, `verify` | beide | funktioniert |
| SPL-Formalismus (JSD, H_norm, E0–E4) | vorgesehen | korrekt und brauchbar |
| E0 (strukturelle Zurückweisung) | vorgesehen | funktioniert, im Gegentest bestätigt |
| π(s) / Projektor | vorgesehen | **fehlte**; gebaut und lauffähig, aber **modellabhängig** (§6b) |
| Frame-Detector als Klassifikator | Notbetrieb | Rolle verfehlt — er liest Deklarationen (§1) |
| Widerspruchsregel (Embedding + Negations-Heuristik) | Notbetrieb | **defekt**, 43 % Falschmeldungen (§3) |

| Entailment-Regeln (Ordnungsvergleich) | DESi | **funktioniert**, deterministisch (§7c) |
| Entailment-Normalisierung | Zulieferer | mit k=5 brauchbar, Restvarianz bleibt (§7c/§7d) |
| API-Schnittstelle | — | lauffähig, Grenzen maschinenlesbar (§7d) |

Die beiden „defekt"-Zeilen betreffen **den Notbetrieb, nicht die vorgesehene Architektur**. Sie sind
trotzdem ernst, weil Joni diesen Pfad produktiv fährt. Und sie haben eine gemeinsame Ursache: ohne
Brücke muss etwas anderes deren Arbeit tun.

### Was sich gegenüber der ersten Fassung geändert hat

Die frühere Fassung schloss: *„es gibt keine gemessene Grösse, die epistemische Berechtigung
abbildet"* — und behandelte das als DESis zentrale Lücke. **Das war die falsche Frage** (§7b).
Berechtigung ist keine Skalargrösse, sondern eine Ableitungsprüfung, und die ist gebaut, läuft und
ist gemessen.

Der Stand ist damit deutlich besser als am Morgen — und die verbleibende Schwäche liegt woanders,
als der Bericht ursprünglich vermutete: **nicht im Urteil, sondern in der Normalisierung.**

**Die entscheidende Einschränkung:** Der Builder liefert ein Ergebnis, aber `H_norm` misst die
Entschiedenheit des Modells, nicht die Mehrdeutigkeit des Textes. Mit zwei unabhängigen Buildern
kehrt sich das Vorzeichen um, und die Emissionsregel wechselt bei 4 von 7 Sätzen. Eine Grösse, die
vom eingesetzten Modell abhängt, ist keine Messung der Eingabe.

Damit steht die Kernfrage offen wie zuvor — nur präziser: **es gibt keine gemessene Grösse, die
epistemische Berechtigung abbildet.** Weder der Frame-Layer, noch `H_norm`, noch die JSD.

---

## 10. Was offen ist — die Fragen für die Diskussion

1. **Frame-Ebene vs. Relations-Ebene sind orthogonal.** „Entropy increases in the system" ist
   relational eindeutig (`has_property`); die Mehrdeutigkeit sitzt in der **Entität**. Der SPL-
   Relationsraum kann Frame-Mehrdeutigkeit prinzipiell nicht sehen, egal wie gut der Builder ist.
   *Braucht DESi beides — und wie sähe ein Entitäts-/Frame-Projektor aus, der nicht wieder eine
   Stichwortliste ist?*

2. ~~**`H_norm` misst Mehrdeutigkeit, nicht Berechtigung** — das ungelöste Kernproblem.~~
   **ERLEDIGT durch §7b/§7c, nicht durch eine Antwort, sondern durch eine bessere Frage.**
   Berechtigung ist keine Skalargrösse. Die Prüfung ist Claim-Evidence-Entailment, sie ist gebaut
   und gemessen. `H_norm` gehört zur *Normalisierung* (was behauptet der Satz, wie eindeutig), nicht
   zum Urteil. Dass „The approach seems promising" H=0 bekommt, ist korrekt: der Satz **ist**
   eindeutig formuliert. Dass er nichts trägt, entscheidet der Auditor — und tut es (`insufficient`
   ohne Evidenz).
   *Neue Restfrage: der Auditor prüft die Ableitung aus den **zitierten** Belegen. Wer prüft, ob die
   zitierten Belege die relevanten sind? Ein Claim mit sorgfältig ausgewählter Teilevidenz besteht
   die Prüfung.*

3. **Der Builder ist kein stabiler Schätzer** (nicht-i.i.d. Ziehungen, mehr Samples ⇒ mehr Varianz)
   **und nicht modellinvariant** (§6b: `H_norm` kehrt zwischen Anbietern das Vorzeichen um).
   *Ist die Sampling-Konstruktion überhaupt legitim? Wären Logprobs der bessere Weg?*

3b. **Die härteste Frage, die aus §6b/§6c folgt:** Die Messung hängt vom Builder ab, und Eignung ist
   **nicht** aus Grösse ableitbar (§6c) — sie muss pro Modell gemessen werden. Also:
   **woran misst man den Builder?** Ein Gold-Standard für Relationszuordnungen ist machbar
   (linguistische Annotationsaufgabe, Menschen können sich einigen) — aber dann ist der
   Gold-Standard das Instrument und der Builder nur seine Näherung. Die Zwei-Builder-JSD löst es
   nicht: zwei schwache Builder können sich einig sein, und gemeinsamer Irrtum (Granites
   `prevents` statt `causes`) passiert die Kette ungebremst.
   *Konkret machbar wäre: 40–60 handannotierte Sätze als Eignungstest, den jeder Builder vor dem
   Einsatz bestehen muss — und dessen Ergebnis mit der Builder-ID versiegelt wird.*

4. **Der `_polarity_clash`-Fix** (66 → 0 Falschmeldungen, aber Verlust des einen echten
   Widerspruchs): *anwenden — oder überspringen?* Da der Defekt im Notbetrieb sitzt (§0b), wäre die
   Alternative, Joni auf den SPL-Pfad umzustellen, statt die Umgehung zu flicken. *Was zuerst?*

5. **Governance-Zuschnitt:** `desi_layer9/semantics/` — wo die epistemischen Urteile fallen — liegt
   außerhalb des Schutz-Locks. *Sollte es hinein?*

6. **Gegenüber MSCE:** Das Angebot ist jetzt ein **laufender Entailment-Auditor mit HTTP-API**
   (§7c/§7d) — genau das Tor, das sie beschrieben haben, und genau der Prototyp, um den Yang
   schriftlich gebeten hat. Ihre eigene Nachprüfung ist rein strukturell (§7); dies prüft die
   Ableitung.
   *Was es **nicht** ist: validiert. 9 Testfälle, unkalibrierter Parser, Score im Band 7–9,
   Modellabhängigkeit nachgewiesen. Als „DESi validiert eure L3-Abstraktionen" verkauft, fliegt es
   beim ersten ernsthaften Lauf auf.*
   Der tragfähige Zuschnitt: **eine Messung**, nicht mehr Features — *von den Einträgen, die das Tor
   als nicht gedeckt markiert: wie viele waren tatsächlich falsch?* In beide Richtungen brauchbar.

7. **Reichweite des Auditors.** Er prüft Modalität, Quantor, Reichweite, Relationsfamilie,
   Bedingungen, Entitätsbezug. Er prüft **nicht**: ob alternative Ursachen ausgeschlossen wurden, ob
   die Stichprobe trägt, ob eine Kausalbehauptung ein plausibles Mechanismus-Modell hat.
   *Reicht die Verstossliste, oder fehlen Kategorien?*

8. **Kosten.** `k · (n + m)` Modellaufrufe je L3-Zeile (k=5). Für eine Zeile mit 18 Einträgen und
   mehreren Belegen sind das schnell mehrere hundert Aufrufe.
   *Ist das für einen Konsolidierungs-Gate tragbar, oder braucht es eine billige Vorfilterung, die
   nur strittige Fälle an den Auditor gibt?*

---

## Reproduzierbarkeit

Alle Zahlen stammen aus ausgeführtem Code im Joni-Repo unter `experiments/msce_bridge/`:

| Datei | Was sie tut |
|---|---|
| `adjudicate.py` | deterministische Prüfungen über einen MSCE-L3-Kandidaten |
| `semantic_probe.py` | DESis Semantic Layer über alle Paare, mit/ohne Embedding |
| `live_run.py` | MSCEs Prompts verbatim auf echten Traces, echtes LLM |
| `spl_builder.py` | π(s) — der LLM-Builder |
| `stability.py` + `stability_results.txt` | Stabilität des Builders |
| `compare_builders.py` + `compare_results*.txt` | Granite vs. DeepSeek, plus Grössen-Kontrolle |
| **`entailment.py`** | **der Claim-Evidence-Auditor** (§7c) |
| `entailment_cases.json` | der Testsatz (9 bewertete Fälle + 2 MSCE-Kontrollen) |
| `run_entailment.py` + `entailment_results.txt` | Auditor gegen den Testsatz |
| `entailment_stability*.txt` | Streuung über Läufe, k=1 und k=5, vor/nach den Fixes |
| **`api.py`** | **HTTP-Schnittstelle** (§7d) |
| `API_README.md` | Übergabe-Dokument für das MSCE-Team |

### Zahlenübersicht (jede Zahl mit Anzahl der Läufe)

| Messung | Ergebnis | Läufe |
|---|---|---|
| Widerspruchsregel im Notbetrieb | 66/153 Paare (43 %) falsch `contradictory` | 1 (alle Paare) |
| … mit simuliertem Fix | 66 → 0 Falschmeldungen | 1 |
| SPL-Builder, scharf vs. mehrdeutig (DeepSeek pro) | H 0.000 vs. 0.382–0.75 | mehrere |
| SPL-Builder, Granite | H **0.650** scharf vs. **0.252** mehrdeutig (invertiert) | 1 |
| SPL-Builder, DeepSeek flash (Grössen-Kontrolle) | H 0.000 vs. 0.878, 4/4 korrekt | 1 |
| Cross-Vendor-JSD vs. Familien-JSD | Ø 0.508 vs. Ø 0.070 | je 1 |
| Builder-Stabilität, Grenzfall | E2/E3-Wechsel bei n=15 | 4 |
| Entailment, k=1 | 6/9 – 9/9 | 5 |
| Entailment, k=5 vor HTTP-Fixes | 8/9 – 9/9 | 4 |
| Entailment, k=5 nach HTTP-Fixes | 7/9 – 9/9, Verstösse 4/7 – 7/7 | 4 |
| MSCE-Ausgabe, Verankerung (echter Lauf) | 18/18 | 1 |

Voraussetzungen: `DESI_ROOT` (hstre/DESi), `SPL_ROOT` (Alexandria-SPL), `pip install fastembed`,
ein LLM-Key in der Umgebung.
