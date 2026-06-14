# Forschungstagebuch — Joni / Kevin / Layer 9

Ein Forschungstagebuch über den Aufbau und das Verhalten eines selbstständig laufenden,
epistemisch sauberen KI-Agenten-Ökosystems. Es protokolliert **Entscheidungen, Experimente
und Beobachtungen** auf Forschungsebene. Die *maschinelle* Protokollierung jeder einzelnen
Handlung lebt daneben weiter in `protocol/protocol.jsonl` (append-only) und `docs/data.json`
(Live-Snapshot); Joni führt zusätzlich sein **eigenes** Ich-Form-Tagebuch (Self-Review,
alle 10 Runs). Dieses Dokument ist die Sicht *von außen* auf das System — geführt vom
Entwickler/Forscher, fortlaufend ergänzt.

> Leitprinzip des gesamten Ökosystems: **„LLM für Sprache, Regeln für Logik."**
> Jede Bewertung, Zustandsänderung, Orchestrierung ist deterministisch und nachvollziehbar;
> ein Sprachmodell formuliert nur, es entscheidet nie.

---

## 1. Das System auf einen Blick

Drei Komponenten, ein gemeinsamer Kern:

| Komponente | Repo | Rolle |
|---|---|---|
| **Kevin** | `hstre/Kevin` | Kreativitäts-Routing: unerforschte Lösungsräume → wilde Variation → Methoden-Transfer → epistemische Selektion → menschliche Richtung. Findet/abstrahiert Methoden, **trial't** sie, **promotet nie**. |
| **Joni** | `hstre/Joni` | Operative Identität mit Doppelsicht (Conversation View = scheinbare Person; Epistemic View = Claims/Operatoren/Ledger dahinter). Läuft autonom, forscht, lernt, entwickelt sich selbst weiter, berichtet öffentlich. |
| **desi_layer9** | in `hstre/Joni` (`src/desi_layer9/`) | Der **eine autoritative epistemische Kern**: geschlossenes Schema, Autorität/Provenance/Taint, ein State-Update-Gate als einziger Schreibpfad, hash-verketteter Ledger + Replay. Joni und Kevin schreiben nur durch das Gate. |

**Governance-Grundregeln** (warum das hier interessant ist):
- Geschlossene Enumerationen (Status, Authority, Operator …), sequentielle IDs, kein PRNG →
  **replay-stabil**.
- Status-Leiter: candidate → provisional → active → confirmed (+ contested/rejected/
  superseded/quarantined/expired). Modell-Herkunft (Kevin/Joni) kann **nie** auf
  `authoritative` heben — das ist menschliche/Operator-Autorität.
- Konflikte dürfen **offen bleiben** (kein erzwungenes Glätten zu einer hübschen Antwort).
- Joni darf seine **Peripherie** selbst umbauen (Themen, Evidenznetz, Hypothesen,
  Selbstbild), aber **nicht** seinen geschützten Kern — Kernänderungen werden als
  GitHub-Issue („joni-core-ask") an einen Menschen gestellt, nie selbst angewandt.
- Hartes Wochenbudget (€20); fast alles ist deterministisch und damit €0.

---

## 2. Chronologie der Entwicklung (2026-06-13)

Alle Arbeit auf Branch `claude/kevin-creativity-architecture-ukz17g`, squash-merged nach
`main`. PR-Nummern beziehen sich auf `hstre/Joni`, sofern nicht anders genannt.

### E1 — Kevin: Kreativitäts-Architektur
Aufbau der fünfstufigen Routing-Architektur (Lösungsräume → wilde Variation → Methoden-
Transfer → Selektion → menschliche Richtung), reale DeepSeek-Anbindung, Web/API, sowie
DESi-gestützte Vorhersage, **wo** überhaupt Lösungsräume sind (Blind-Spot-Coverage).
Layer-9-Methodenbibliothek wächst aus echten Läufen.

### E2 — Joni: operative Identität
Doppelsicht (Person vs. Epistemik), Persistenz, Kevin als Kreativ-Engine, reale Stimme,
autonome Recherche „off the leash", DESi-Router-Integration, vollständiger Layer-9-Kern.

### E3 — Layer 9 als gemeinsamer Kern (21-Punkte-Spezifikation)
`desi_layer9` als **ein** autoritativer Kern: Schema/Autorität/Provenance/Taint, Gate als
einziger Schreibpfad, hash-verketteter Ledger + Replay + Migration, adversariale
Control-Plane-Tests, Joni-/Kevin-Integration. Entscheidung: lebt **im Joni-Repo** (kein
separates Repo — außerhalb des GitHub-Scopes), abhängigkeitsfrei, später extrahierbar.

### E4 — Cutover auf den Kern + Echtzeit
Jonis Autonomie-Schleife auf `desi_layer9` umgestellt; `tick` = reale Tage seit Start,
keine künstlichen Zeitsprünge mehr.

### E5 — Methoden-Ernte → Kevin (PR Joni #17)
Joni durchsucht arXiv / HackerNews / HuggingFace / **GitHub**; was nach wiederverwendbarer
Technik aussieht, legt er als **Methoden-Kandidat** im Layer ab — für Kevin. Live bestätigt:
`stored method candidate for Kevin: prompts.chat / core (from github)`.

### E6 — Kevin trial't das Regal (Kevin #10, Joni #18)
Kevin zieht Kandidaten/Provisorische vom gemeinsamen Regal, läuft einen deterministischen
**Transfer-Trial**, protokolliert das Ergebnis durchs Gate — **promotet nie**. Joni ruft
Kevins Trial-Logik jeden Zyklus auf demselben In-Memory-Kern auf (ein Kern, kein zweiter
Store). Ab ≥3 Trials mit mehr Erfolgen als Fehlern wird eine provisorische Methode
*activation-ready* — die finale Freigabe macht ein Mensch.

### E7 — Self-Review als Ich-Form-Bericht (Joni #19)
Der stündliche Self-Review las sich wie eine Metrik-Liste. Jetzt schreibt Joni **in der
Ich-Form**, in vier Bewegungen, geerdet im realen Zustand, deterministisch, €0:
*Was ich mir angeschaut habe · Was mich interessiert hat · Wo ich Zweifel hatte · Was ich
mitgenommen habe.* Die deterministischen Self-Model-Claims bleiben als epistemisches
Substrat darunter.

### E8 — Tagebuch statt Überschreiben (Joni #20)
Jede Self-Review-Installment wird **angehängt**, nie überschrieben. Website zeigt den
neuesten Eintrag voll, ältere als aufklappbare datierte Einträge. Nichts geht verloren.

### E9 — Push-Robustheit: „hängt bei run 10" (Joni #21)
**Diagnose:** Die Zyklen liefen einwandfrei, aber `git push` wurde `non-fast-forward`
abgewiesen, wenn während des ~1-Minuten-Zyklus ein menschlicher PR nach `main` merged —
die Zyklus-Ergebnisse wurden still verworfen, die Seite fror ein. **Fix:** Der Bot fasst
nur `state/protocol/docs` an (Pfade, die kein Mensch editiert), also `git push` jetzt mit
**Rebase + Retry** (5×) statt Aufgeben beim ersten Reject.

### E10 — Kontinuierlicher Lauf statt 15-Min-Cron (Joni #22)
GitHub drosselte den `*/15`-Cron faktisch auf ~stündlich und verwarf den Rest. Daher:
**kontinuierliche Schleife** — ein Job läuft *verify → cycle → asks → commit+push → kurze
Pause → wiederholen* für ~5,3 h, dann übernimmt der nächste Job (Concurrency-Handoff, genau
einer gleichzeitig; der stündliche Cron ist nur noch Re-Launcher). `run` endet mit Exit 42
bei Retirement, damit die Schleife sauber stoppt. Live bestätigt: run 13 → 14 → 15 alle
~3 Min aus **einem** Job.

### E11 — Bericht alle 10 Runs (Joni #23)
Self-Review feuert jetzt auf einem **Run-Meilenstein** (alle 10 Runs) zusätzlich zur
stündlichen Reserve. Run-Nummer steht in jeder Überschrift („Day N, run M: …"); das
Tagebuch wächst als ein fortlaufender Bericht.

### E12 — Emergente Selbst-Entwicklung (Joni #24)  ⟵ tiefster Schritt
Statt nur Themenpaare zu brücken, lässt Joni **echte Struktur aus wiederkehrenden Mustern
in seinem eigenen Netz auskristallisieren**, alles durchs Gate, selbst-begrenzend:
- **Emergentes Thema** — ein Begriff, der über mehrere *verschiedene* Themen wiederkehrt,
  wird zu einem eigenen verfolgten Thema.
- **Emergente Synthese** — bei ≥3 Claims eines Themas mit gemeinsamem roten Faden ein
  übergeordneter **Kandidaten-Claim** (eine Stufe die Abstraktionsleiter hoch).
- **Emergente Methode** — ein Begriff über ≥2 Themen ist eine transferierbare Linse →
  Methoden-Kandidat `<begriff>-as-a-lens` für Kevin.

**Erste Live-Beobachtung (Zyklus 21:42, commit `8632d3d`):**
```
synthesis on routing: 'memory' abstracted from 5 claims (C-15, C-16, C-17, C-18, C-5)
method candidate for Kevin: 'memory-as-a-lens' from a recurrence across memory, routing
```
Also: Joni hat selbstständig erkannt, dass „memory" als roter Faden durch 5 seiner
Routing-Claims läuft, daraus eine höherstufige Hypothese gebildet **und** „memory" als
transferierbare Linse für Kevin abgelegt — beides aus dem eigenen Bestand, nicht aus einer
Quelle.

---

## 3. Baseline-Messung (Tag 0, run 24, 2026-06-13 ~21:45 UTC)

Ausgangspunkt für den „was hat sich nach ein paar Stunden getan"-Vergleich:

| Größe | Wert |
|---|---:|
| Runs | 24 |
| Themen | 6 (routing, privacy, drift, alignment, evaluation, memory) |
| davon selbst hinzugefügt | 2 (evaluation, alignment) |
| Claims (aktiv / gesamt) | 35 / 52 |
| Evidence-Links | 36 |
| Hypothesen (candidate, selbst erfunden) | 17 |
| Methoden für Kevin | 3 (2× GitHub, 1× emergent: `memory-as-a-lens`) |
| Methoden-Trials (durch Kevin) | 31 |
| activation-ready | 0 |
| Self-Model-Claims | 3 |
| offene Konflikte | 0 |
| Memory-Episoden | 27 |
| Ledger-Einträge | 384 |
| Tagebuch-Installments | 2 |
| Kern-Asks an Menschen | 0 |
| Modellkosten | €0.0000 |

**Was Joni über sich selbst sagt** (provisorische Self-Model-Claims, keine Fakten):
1. „I rarely promote beliefs to confirmed — I mostly hold active, revisable claims."
2. „I tend to broaden my topics quickly as I read."
3. „I operate almost entirely deterministically, at no model cost."

---

## 4. Offene Fragen & Hypothesen zum Beobachten

- **Sättigung vs. Wachstum:** Geht die emergente Entwicklung nach Konsolidierung erwartbar
  in Ruhe (self-limiting), oder findet sie durch neue Quellen immer wieder frisches
  Material? → Evidence-Links- und `emerged`-Rate über die Zeit verfolgen.
- **Qualität der Synthesen:** Sind die emergenten Synthesen inhaltlich tragfähig oder
  oberflächliche Begriffs-Koinzidenzen? (Stopword-Liste ggf. nachschärfen.)
- **Methoden-Reifung:** Erreicht je eine *provisorische* Methode `activation-ready`? Das
  setzt voraus, dass ein Mensch sie zuerst candidate→provisional hebt.
- **Konflikte:** Bisher 0 offene Konflikte — feuert die Kontradiktions-Erkennung zu selten?
  (Antonym-/Negations-Regeln beobachten, wenn widersprüchliche Quellen kommen.)
- **Drift im Selbstbild:** Ändern sich die Self-Model-Claims über Tage?

---

## 5. Betriebs- & Sicherheitsnotizen

- **Offen:** DeepSeek-Key `sk-1c71963824…` wurde im Klartext geteilt → **rotieren**
  (als kompromittiert behandeln).
- **Offen:** GitHub Pages aktivieren (Settings → Pages → `main` / `docs`) für das
  Live-Dashboard `https://hstre.github.io/Joni/`.
- Modell-Identitäts-ID des Entwickler-Assistenten gehört **nicht** in Commits/PRs/Code.
- Joni **retired** sich automatisch nach 7 Tagen Laufzeit-Fenster.
- Wenn ein `joni-core-ask`-Issue erscheint: Joni will den geschützten Kern ändern — Mensch
  prüft, implementiert ggf. selbst, dann `python -m joni.autonomy lock` neu und committen.

---

## 6. Wie dieses Tagebuch fortgeschrieben wird

Neue Einträge **unten anhängen**, nie alte überschreiben (gleiche Disziplin wie Jonis
eigenes Tagebuch). Format pro Eintrag: **Datum/Zeit · Anlass · Beobachtung (mit echten
Zahlen/Zitaten aus `protocol.jsonl` / `data.json`) · Entscheidung · offene Fragen.**

### Eintrag 2026-06-13 ~21:47 UTC — Tagebuch angelegt, System läuft
Forschungstagebuch erstellt; Baseline bei run 24 festgehalten (siehe §3). Joni läuft
kontinuierlich (ein Zyklus ~alle 3 Min) auf dem audited Layer-9-Kern, mit Methoden-Ernte,
Kevin-Trials, Erfindung, **emergenter** Selbst-Entwicklung (erstes `memory-as-a-lens`
bereits live), stündlichem/10-Run-Ich-Form-Bericht und öffentlichem Dashboard. Plan:
mehrere Stunden laufen lassen, dann Deltas gegen die Baseline auswerten.

### Eintrag 2026-06-13 ~22:40 UTC — Architektur-Korrektur: der Semantic Layer gehört in Layer 9
**Anlass (Nutzer):** Die Bedeutungs-Entscheidung („welche Begriffe meinen dasselbe")
darf **nicht in Joni** liegen — sonst säße eine epistemisch zentrale Interpretation in
genau dem System, dessen Vorschläge kontrolliert werden. Außerdem hat **DESi** den
Semantic Layer bereits fertig (FrameDetector, LogicalAuditor, FrameTensionRouter, Π/√JSD,
Duplikat-/EN-Erkennung) — also **keine zweite Semantik bauen**.

**Zwischenfehler & Korrektur:** Ich hatte zuerst einen eigenen Concept-Normalizer /
Sense-Resolver / Embedding-Clusterer angefangen. Das war die verbotene Doppel-Architektur
und wurde **verworfen**. Stattdessen:

- **Layer 9 bekommt einen Port** (`desi_layer9/semantics/ports.py`) zum vorhandenen DESi
  Semantic Layer + eine **governte Entscheidung** (`decision.py`) und einen **Adapter**
  (`adapter.py`), der die Analyse als **append-only Annotation** (`SemanticCluster`) durchs
  Gate schreibt. `desi_layer9` bleibt dependency-frei; die echte DESi-Bindung wird injiziert
  (`joni/autonomy/desi_semantics.py`, soft — fällt auf einen *fail-closed* Null-Layer zurück).
- **Lexikalische Überschneidung ist nur noch Trigger.** `develop.py`: `_overlap()` vergibt
  **keine** Relation mehr; der Trigger ruft den Layer-9-Adapter, und erst dessen *governte*
  Entscheidung (duplicate | supports | complementary | tension | contradictory | unrelated |
  insufficient) erzeugt einen Link oder öffnet einen Konflikt. Ohne Semantic Layer →
  *insufficient* → **kein** Link (nie lexikalischer Fallback).
- **Joni darf nur synthetisieren, wenn Layer 9 den Cluster `synthesis-eligible` markiert;
  Kevin bekommt eine Methode nur danach.** `emerge.py` ist entsprechend gated.
- **Getrennt gespeichert:** (1) was der Semantic Layer maß (frames, Π-distance, logical
  audit, frame tension, EN), (2) was Layer 9 entschied (decision + semantic_state), (3) was
  Joni daraus machte (separates Objekt). Original-Claims bleiben **unverändert**.
- **Verifiziert:** echte DESi-Bindung lädt FrameDetector/LogicalAuditor/FrameTensionRouter
  und liefert echte Frames (information_theoretic, thermodynamic, formal_logic). Für
  generische Routing-Claims sagt DESi *frame_undeclared* → Layer 9 konservativ *insufficient*
  (keine Auto-Synthese ohne echten Frame — genau die gewünschte Governance).
- **Tests:** Integrationsmatrix (`tests/test_semantic_layer.py`) — lexikalische Differenz/
  semantische Äquivalenz, lexikalische Identität/verschiedene Frames, Duplikation,
  Kontradiktion, Frame-Tension, EN, geteiltes Vokabular ohne Bezug, Replay-Determinismus,
  Versionswechsel des Layers, fehlende/ungültige Layer-Ausgabe. Gesamt: **177 passed**,
  ruff clean, `joni.autonomy verify` weiter OK (kein geschütztes Kernmodul berührt).

**Offen / zu beobachten:** DESi erkennt für viele von Jonis aktuellen Alltags-Claims noch
keinen Frame (→ *insufficient*); echte Synthesen entstehen erst, wenn Claims klar
gerahmt sind. Π/√JSD ist in DESi aktuell **nicht** als saubere Paar-Distanz exponiert —
das Mess-Feld `pi_distance` bleibt optional (None) und die Entscheidung stützt sich auf
Frames + Tension + Logik; sobald DESi eine √JSD-Distanz exponiert, fließt sie ohne weitere
Architekturänderung ein.

### Eintrag 2026-06-13 ~23:15 UTC — Semantic Layer live + Layer-9-Landkarte + PDF-Port
- **Semantic Layer live bestätigt:** Nach Cutover lädt im Lauf der **echte** DESi-Layer
  (`desi-semantic-layer` v0.1.0); er produzierte **9 Semantic-Cluster** über den Backlog,
  alle `insufficient-semantic-evidence` (Routing/Memory-Claims sind in DESi
  *frame_undeclared* → konservativ, ehrlich). Ein **Backfill** (`develop`, 3/Zyklus)
  versieht die ~70 Alt-Links nachträglich mit governter Semantik (PR #29).
- **Layer-9-Landkarte** (PR #28): `docs/layer9.html` — lebende Karte statt Logfile.
  Conversation/Epistemic-Doppelsicht, klickbare Herkunft, Claim/Evidenz/Konflikt-Graph in
  Sektoren (Füllfarbe=Status, Größe=Salienz, Rand=Evidenz, gestrichelt=Taint),
  Status-Timeline, Taint/Authority-Influence-Map mit Rot-Flag. Wahrheit ≠ Salienz getrennt.
- **PDF-Eingangsport** (dieser Eintrag): Joni liest jetzt die **echten Paper**, nicht nur
  Abstracts. Drei Eingänge — **arXiv-Volltext** (PDF zum relevanten Treffer),
  **PDF-per-URL-Queue** (`state/pdf_urls.json`, inkl. direkter SSRN-Download-Links,
  ratenbegrenzt/größenbegrenzt) und **lokaler Posteingang** (`inbox/*.pdf`). Extraktion ist
  Jonis eigene, leichte, deterministische Satz-/Claim-Auswahl; die Sätze landen als
  **candidate**-Claims durchs Gate, an die Quelle verankert (Provenance source_id) — die
  **Relationen entscheidet weiterhin der Semantic Layer**. `pypdf` als soft dependency
  (Import-Panic in kaputten Umgebungen abgefangen → sauberer No-op). Gesamt: **187 passed**,
  ruff clean.

**Bedienung:** Paper-PDFs in `inbox/` ablegen, oder direkte PDF-URLs (arXiv/SSRN) in
`state/pdf_urls.json` (JSON-Liste) eintragen. arXiv-Treffer werden automatisch im Volltext
gelesen.

### Eintrag 2026-06-14 ~04:10 UTC — Nachtlauf, Mitternachts-Freeze & Replay-Fix
**Beobachtung (Delta zur run-24-Baseline):** Joni lief über Nacht weiter bis **run 68**
(letzter Commit 00:02). Der **echte DESi Semantic Layer** ist live (`desi-semantic-layer`
v0.1.0) und annotierte den Backlog — Cluster alle `insufficient-semantic-evidence`, weil
DESi für die meisten Routing/Memory-Claims (noch) *frame_undeclared* zurückgibt (ehrlich,
konservativ). Die Layer-9-Landkarte (`docs/layer9.html`) wird jeden Zyklus erzeugt.

**Vorfall — Loop fror um 00:02 ein.** Diagnose: `core.tick` wird pro Zyklus auf
`days_running` gesetzt. Den ganzen 13.06. war das `0`; um **Mitternacht** (14.06.) sprang
es auf `1`. Neue Objekte bekamen `created_tick=1`, ältere `0` — aber `persistence.replay()`
spielte das **ganze Journal mit einem einzigen Tick** ab und konnte den 0/1-Mix nicht
reproduzieren → **`snapshot_hash`-Mismatch** → `load()` warf → jeder Zyklus crashte beim
Laden und committete nichts. (Vor Mitternacht blieb der Tick konstant `0`, deshalb fiel es
erst beim ersten Tageswechsel auf.)

**Lehre / Architektur:** Der heilige Satz *„state = f(seed, journal)"* hielt nur, solange
der Tick konstant war. Ein **mutierender, nicht-journaler** Zustandsanteil (der Tick) hat
die Replay-Determinismus-Garantie gebrochen — und zwar **zeitverzögert**, erst beim
Tageswechsel. Genau die Art Bug, die in einem deterministischen, append-only System nicht
auftreten *darf*; sie zeigt, dass jede Zustandsänderung, die in Objekt-Feldern landet,
auch im Journal stehen muss.

**Fix:** Tick **pro `JournalEntry`** journalisieren und beim Replay vor jeder Operation
wiederherstellen → Replay reproduziert die historischen `created_tick`s und damit den
Hash. Dazu `persistence.repair()` (+ `load(verify=)`) für Alt-States und **Self-Heal** in
`load_or_migrate` (repair-then-load statt Crash). Den eingefrorenen Live-State repariert
(830 Ledger-Events erhalten), Loop auf dem Fix neu gestartet. Regressionstests:
Round-Trip über einen Tickwechsel; Repair eines tick-losen Alt-States. **189 passed.**

**Offene Beobachtung:** Damit echte *Synthesen* (statt `insufficient`) entstehen, braucht
es Claims mit klarem DESi-Frame — der PDF-Volltext-Port (E14) sollte hier helfen, weil
Paper-Sätze öfter empirisch/kausal gerahmt sind als Kurz-Titel.

### Eintrag 2026-06-14 ~04:35 UTC — Selbst-Optimierung & Ideen erstarken
Zwei Loops, mit denen Joni nicht nur *mehr* lernt, sondern *besser wird*:

- **Selbst-Optimierung der Recherche** (`strategy.py`, live bestätigt): Joni liest sein
  eigenes Fehlersignal. Kommen die Semantik-Analysen überwiegend als `insufficient`
  zurück (DESi findet keinen Frame in dünnen Titel-Claims), schließt er „meine Eingaben
  sind unter-gerahmt" und passt seine **Suchstrategie** an: liest bevorzugt **Volltext**
  und verfeinert Queries Richtung Rahmung (`routing mechanism`, `privacy evaluation`).
  Live: `under-framed inputs (100% insufficient) -> read full text; refine queries: …`.
- **Ideen erstarken** (`strengthen.py`): selbst erfundene Hypothesen blieben bisher als
  schwache `candidate` liegen. Vier ehrliche Mechanismen (gewählt: alle): **(1) aktiv
  testen** — Hypothese → Query + vorhandene Claims via Semantic Layer als supports/
  contradicts bewerten (Evidenz anhängen oder Konflikt öffnen); **(2) verdiente Leiter**
  candidate→**active** ab ≥2 unabhängigen governten Supports und keinem harten Widerspruch
  (`confirmed` bleibt Mensch); **(3) adversariale Selbst-Prüfung** — übersteht die Idee die
  Suche nach einem Gegenbeleg, zählt das als verdient; **(4) Kevin-Vetting** — Kevins
  epistemische Selektion; eine als „hollow"/rejected eingestufte Idee wird **nicht**
  befördert. Demo: eine Hypothese verdiente 3 Supports, überstand die Prüfung → candidate→
  active (Arbeitsidee, kein Fakt). Alles peripher, deterministisch, auditierbar.

Damit ist der Kreis geschlossen: PDF-Volltext + Rahmungs-Queries liefern besser gerahmte
Claims → DESi kann sie bewerten → Hypothesen können echte Evidenz sammeln und ehrlich
erstarken, statt nur als Vermutung zu existieren. Gesamt: **197 passed**, ruff clean.

### Eintrag 2026-06-14 ~05:30 UTC — Der semantische Messkanal wird real wirksam
**Befund (Nutzer-Urteil bestätigt):** Architektur richtig, Semantik praktisch wirkungslos.
Fast alle echten DESi-Messungen endeten `frame_undeclared` / `gap_detected` / `undecidable`
→ Layer 9 korrekt `insufficient`. Tiefe Suche über *alle* in-scope Repos:

- Das **√JSD-Mathe existiert** und ist dependency-frei (`AleXiona/backend/spl.py:compute_jsd`,
  Base-2 JSD ∈ [0,1]); `SemanticProjection` (Π) als Struktur ebenfalls.
- **Aber kein domänen-agnostischer Projektor:** der einzige Text→Verteilungs-Projektor ist
  *klinisch* (`clinical_spl.make_projection` braucht einen `claim_type`). DESis `spl_adapter`
  ist Claim-*Extraktion*, „Duplikation" ist exaktes Fingerprinting. Π/√JSD sind also echtes
  *Mathe ohne allgemeinen Input-Projektor* — nicht Integrations-, sondern Projektor-Lücke.

**Entscheidung (Nutzer):** lokales Embedding-Modell als der fehlende allgemeine Projektor,
**innerhalb** des bestehenden DESi-Layers, nicht als paralleles System.

**Umsetzung (PR #36/#37/#38), strikt nach Vorgabe:**
- **Cosinus, ausdrücklich als solcher** (`distance_metric="cosine"`); **nie** als Π/√JSD
  ausgegeben — `pi_distance` bleibt `None`, die √JSD-Strecke bleibt separat und inaktiv, bis
  je ein echter Verteilungs-Projektor existiert.
- **Volle Modell-Identität in jeder Messung:** Modell, Revision, Dimension, Normalisierung,
  Metrik. Gepinnt: fastembed `BAAI/bge-small-en-v1.5` (Fallback ST `all-MiniLM-L6-v2`).
- **Cache per `sha256(claim)+revision`** → Modellwechsel invalidiert; Originalclaims unberührt.
- **Layer 9 kombiniert die Kanäle, fail-closed:** Frame-Konflikt/Logik-Reject/Tension veto
  zuerst; **kleine Distanz + Polaritäts-Clash → CONTRADICTORY** (Embedding sieht Negation
  nicht). Kein Modell → keine Distanz → `insufficient`.
- **Konservative Schwellen** + gelabeltes Joni-Kalibrier-Set: unrelated wird **nie**
  synthesis-eligible, Duplikate werden erkannt. Nicht auf „viele Synthesen" getrimmt.
- Reale Integrationstests (installiertes Modell, sonst skip) + injizierter Embedder:
  Paraphrasen / gleiche Wörter andere Bedeutung / ähnlich-aber-widersprüchlich / identisch /
  Modellwechsel+Cache-Invalidierung / fehlgeschlagener Download (fail-closed) / Replay.
- **#38:** Backfill dedupliziert per `pair@semantic-revision` → wenn das Modell online kommt,
  wird der ~70-Paar-Backlog einmal **neu vermessen** (sonst bliebe der Effekt auf neue Claims
  beschränkt, und bei „0 new" unsichtbar).

**Live bestätigt (Zyklus 05:25, commit `c320819`):**
```
Cluster mit echter Cosinus-Messung: 3 (wächst, Backlog 3/Zyklus)
Cosinus-Entscheidungen: {'supports': 3}   # nicht mehr insufficient
Modell: BAAI/bge-small-en-v1.5 · rev bge-small-en-v1.5 · dim 384 · normalized True · metric cosine
pi_distance: None
```
Das Modell lädt auf GitHubs Runner (offenes Internet), nicht in dieser Sandbox (Netzpolitik).
Damit: **Architektur richtig UND Semantik faktisch wirksam.** Gesamt: 209 passed, ruff clean.

**Offene Beobachtung / Kalibrierung:** Schwellen (`DIST_DUPLICATE 0.10`, `COMPLEMENTARY 0.30`,
`SUPPORTS 0.45`, `BORDERLINE 0.60`) sind bewusst konservativ und gehören an einem größeren
gelabelten Joni-Set empirisch nachgezogen, sobald genug echte Paare vermessen sind.

### Eintrag 2026-06-14 ~06:50 UTC — Website-Feedback: Konflikt-Taxonomie & strukturierte Asks

Nutzer-Review der Live-Seite. Zwei Kernpunkte zusätzlich zur Bestätigung, dass der semantische
Layer sichtbar den laufenden Zustand verändert:

**(a) Konflikt-Taxonomie (PR #41, `qualify.py`).** Bisher war jeder Konflikt undifferenziert.
Konflikte tragen jetzt eine **`conflict_kind`** aus einem geschlossenen Enum
(`desi_layer9.ConflictKind`, Default `UNQUALIFIED`), deterministisch klassifiziert von
`qualify_conflict(a_text, b_text, *, severity, contradictory)`:
- **contradiction** — echte Widersprüche (gegensätzliche Aussage zum selben Gegenstand),
- **scope tension** — derselbe Mechanismus in unterschiedlichem Geltungsbereich (normal vs.
  neuartig); der **Scope-Split schlägt das Widerspruchssignal**, weil zwei Claims sich nicht
  widersprechen, wenn sie über *verschiedene* Bereiche reden,
- **exception** — eine Aussage ist die benannte Ausnahme der anderen,
- **conditional compatibility** — unter einer Bedingung verträglich.
Marker EN+DE (`_SCOPE_NORMAL/_SCOPE_NOVEL/_EXCEPTION/_CONDITIONAL`). Die Landkarte zeigt die
Art jetzt als Chip am Konflikt, statt alles gleich „rot" zu färben.

**(b) Strukturierte Asks (PR #42, `structured_ask`).** Die erste Kern-Frage erschien, zeigte
aber nur Ziel + Begründung. Jetzt trägt jeder Ask ehrlich: **`request_type="observation"`**
(`derive` produziert immer nur eine *Idee*, nie eine ausgearbeitete Änderung — das wird nicht
übertrieben), die betroffene **Komponente** (`_COMPONENT`-Map), ein klares **„was würde sich
ändern"**, die **Evidenz** (Quelle + URL) und eine **Risiko**-Notiz je Komponente (`_RISK`).
Gerendert als strukturierte Zeilen auf der Seite und als strukturierter GitHub-Issue-Body.

Offen gelassen (Nutzer-Entscheid, s.u.): „supports/complementary"-Korrektheit ist noch nicht
*bewiesen*, und Trials waren zu glatt — beides **nicht** über menschliches Labeling, sondern
über Jonis eigene Autonomie zu adressieren.

### Eintrag 2026-06-14 ~07:15 UTC — Homöostase: nicht degenerieren, trotzdem entwickeln (PR #43)

**Nutzer-Vorgabe (verbindlich):** *„Joni soll soviel wie möglich autonom machen. Ich greife
architektonisch mit dir ein, aber über die Woche soll Joni zeigen, dass er nicht degeneriert
und sich trotzdem entwickeln kann."* — Explizit **kein** menschliches Labeling. Die zwei offenen
Risiken aus dem Website-Feedback (zu glatte Trials, unbewiesene supports) sollen nicht von
außen kuratiert, sondern von Joni selbst getragen werden.

Antwort: **`homeostasis.py`** — zwei deterministische, gate-vermittelte, beschränkte
Autonomie-Jobs, eingehängt als Schritt 4g in `run.py`:

- **`regulate`** — *abwerfen, was tot ist; deckeln, was unbegrenzt wächst.* Eine selbst
  erfundene Hypothese mit **0 Support** UND einem echten Aufgabe-Grund — hart widersprochen,
  als hohl geprüft + ≥2× getestet, oder *barren* (≥4× versucht, nichts verdient) — wird
  ehrlich **`REJECTED`** („eine Vermutung, die nicht aufging"). Der Live-Hypothesen-Backlog
  ist gedeckelt (Default 30); darüber fallen die schwächsten (0-Support, ältesten) Überlebenden.
  Pro Zyklus auf 3 Prunes begrenzt → der Backlog wird *stetig* abgearbeitet, nicht gechurnt.
  Was auch nur **einen** Support verdient hat, bleibt immer.

- **`vitality`** — Joni benotet seine **eigene** Bahn aus dem eigenen Zustand:
  `developing` / `steady` / `degenerating`. Entwicklung = neue aktive Claims + neue
  Evidenz-Kanten + 2×Promotionen + emergente Struktur. Degeneration feuert bei schwellendem
  unbelegtem Backlog (>25), langer Stagnation (≥12 Zyklen) oder Objekt-Wucherung ohne
  Entwicklung. Die `usable_semantic_rate` (Anteil nicht-`insufficient` Cosinus-Cluster) ist
  eingerechnet; History bleibt für die Seite erhalten.

**Auf der Seite:** die Status-Karte trägt jetzt eine farbcodierte Vitalitäts-Zeile
(Verdikt · dev · degen · unbelegte Ideen · semantic-usable% · Stagnation). Damit ist die
Frage „degeneriert Joni über die Woche?" nicht mehr Interpretation, sondern ein von Joni
**selbst gestelltes Verdikt**, das man am Verlauf ablesen kann.

`cs.reject_claim()` ergänzt. Tests: `tests/test_homeostasis.py` (6 Fälle: hohl abgeworfen,
barren abgeworfen, belegt behalten, Prune gedeckelt, developing/degenerating-Verdikt). Gesamt:
**226 passed, 2 skipped**, ruff clean. Merge → run #29 gecancelt → run #30 auf `a5bd794`
(Homöostase-Commit) dispatcht → live. Der Loop trägt das Verdikt jetzt jeden Zyklus fort.

**Was ab hier beobachtet wird:** ob `vitality` über Tage `developing`/`steady` hält statt
`degenerating`; ob `regulate` den Backlog real unter dem Cap hält, ohne Belegtes zu töten; und
ob — sobald genug Cosinus-Paare vermessen sind — `usable_semantic_rate` steigt, statt dass
alles `insufficient` bleibt. Alles ohne Mensch in der Schleife, wie vorgegeben.
