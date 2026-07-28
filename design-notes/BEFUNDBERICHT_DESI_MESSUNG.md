# Befundbericht: Was misst DESi eigentlich?

**Stand 2026-07-28 · alle Zahlen aus ausgeführten Läufen, nicht aus Überlegung**

Dieses Dokument ist eigenständig lesbar. Es fasst zusammen, was eine Reihe von Messungen an DESi,
Layer 9 und dem Semantic Projection Layer ergeben hat — ausgelöst durch eine Kooperationsanfrage,
die eine unangenehme Frage erzwungen hat: *Können wir eigentlich, was wir behaupten?*

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

## 1. Der Frame-Detector ist eine Stichwortliste

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

> **`frame_undeclared` ist nicht das Versagen des Detektors, sondern sein Normalfall.**
> Für jeden Text außerhalb dieser 69 Wörter ist „unbekannt" die konstruktionsbedingte Antwort.

Wichtig: Das ist **kein Domänenproblem**. Klinische Sätze („The patient has a fever of 39 degrees
and elevated CRP") liefern dieselben Werte. Der Semantic Layer wurde nie für Klinik gebaut, nur
dort eingebaut.

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

## 3. Die Widerspruchsregel ist defekt (43 % Falschmeldungen)

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
`deepseek-v4-pro`. Der Unterschied kann Modellgrösse sein statt Anbieter — das ist kein
grössenkontrollierter Vergleich. Grössere Granite-Versionen bietet OpenRouter nicht an
(verfügbar sind nur `granite-4.0-h-micro` und `granite-4.1-8b`). Aber genau das ist der Punkt: wenn
die Messung von der Modellgüte abhängt, ist sie keine Eigenschaft des Textes.

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
| 7 | Frame-Detector | 69 Stichwörter ⇒ „Frame" |
| 8 | `clinical_spl._build_P_r` | ein Skalar ⇒ „Verteilung" |

> **Eine lexikalische Regel kann ein semantisches Urteil nicht tragen.**
> Und: Ein reicher Formalismus über einer dünnen Eingabe misst die Eingabe, nicht die Welt.

Nr. 7 und 8 sind die eigentlich schmerzhaften — sie stehen nicht in der Peripherie, sondern im
Fundament. Was sechsmal an den Rändern gefunden wurde, ist die Bauweise des Kerns.

**Und die Gegenrichtung:** Einmal wurde zu früh in die andere Richtung geschlossen — aus vier
Sätzen mit `H_norm = 0` wurde „der Kanal ist tot" gefolgert. Alle vier waren auf Relationsebene
*eindeutig*; Null war die **richtige** Antwort. Ein korrektes Messergebnis wurde als Defekt gelesen.
Beide Fehler haben dieselbe Wurzel: Urteil auf zu wenig Daten.

---

## 9. Gesamturteil

**DESi ist kein Fail — aber es war bis heute kein Messinstrument.**

| Ebene | Status |
|---|---|
| Governance-Architektur (Modelle schlagen vor, Regeln entscheiden, bei Nichtmessbarkeit verweigern) | **funktioniert, unter echtem Test bestätigt** |
| Ledger, Provenienz, Lock, `verify` | funktioniert |
| SPL-Formalismus (JSD, H_norm, E0–E4) | korrekt und brauchbar |
| Frame-/Logic-Layer | **misst nichts** auf freistehenden Behauptungen |
| Widerspruchsregel | **defekt** (43 % Falschmeldungen) |
| π(s) / Projektor | gebaut und lauffähig — aber **modellabhängig, nicht textabhängig** (§6b) |
| E0 (strukturelle Zurückweisung) | funktioniert, im Gegentest bestätigt |

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

2. **`H_norm` misst Mehrdeutigkeit, nicht Berechtigung.** „The approach seems promising" bekommt
   H=0: bestimmt formuliert, epistemisch leer. Für Layer 9s eigentliche Frage („ist diese
   Behauptung durch die Evidenz gedeckt?") fehlt die zweite Größe komplett.
   *Was misst epistemische Berechtigung? Das ist das ungelöste Kernproblem.*

3. **Der Builder ist kein stabiler Schätzer** (nicht-i.i.d. Ziehungen, mehr Samples ⇒ mehr Varianz)
   **und nicht modellinvariant** (§6b: `H_norm` kehrt zwischen Anbietern das Vorzeichen um).
   *Ist die Sampling-Konstruktion überhaupt legitim? Wären Logprobs der bessere Weg?*

3b. **Die härteste Frage, die aus §6b folgt:** Wenn die Messung von der Builderqualität abhängt —
   **woran misst man den Builder?** Ein Gold-Standard für Relationszuordnungen wäre nötig, aber
   dann ist der Gold-Standard das Instrument und der Builder nur seine Näherung. Die
   Zwei-Builder-JSD löst es nicht: zwei schwache Builder können sich einig sein, und gemeinsamer
   Irrtum (Granites `prevents` statt `causes`) passiert die Kette ungebremst.

4. **Der `_polarity_clash`-Fix** (66 → 0 Falschmeldungen, aber Verlust des einen echten
   Widerspruchs): *anwenden? Er betrifft Jonis Konfliktbildung und AleXiona mit.*

5. **Governance-Zuschnitt:** `desi_layer9/semantics/` — wo die epistemischen Urteile fallen — liegt
   außerhalb des Schutz-Locks. *Sollte es hinein?*

6. **Gegenüber MSCE:** Ein Provenienz-/Typisierungsangebot ist dünn und hat sich in der Messung
   nicht bewährt. Ein **funktionierender Projektor mit Mehrdeutigkeits-Messung an der L2→L3-Grenze**
   ist dagegen etwas, das ihr Tor nicht hat — jetzt vorführbar statt behauptet.
   *Mit welchen Einschränkungen wird das ehrlich kommuniziert?*

---

## Reproduzierbarkeit

Alle Zahlen stammen aus ausgeführtem Code im Joni-Repo unter `experiments/msce_bridge/`:

| Datei | Was sie tut |
|---|---|
| `adjudicate.py` | deterministische Prüfungen über einen MSCE-L3-Kandidaten |
| `semantic_probe.py` | DESis Semantic Layer über alle Paare, mit/ohne Embedding |
| `live_run.py` | MSCEs Prompts verbatim auf echten Traces, echtes LLM |
| `spl_builder.py` | π(s) — der LLM-Builder |
| `stability.py` + `stability_results.txt` | die Stabilitätsmessung |

Voraussetzungen: `DESI_ROOT` (hstre/DESi), `SPL_ROOT` (Alexandria-SPL), `pip install fastembed`,
ein LLM-Key in der Umgebung.
