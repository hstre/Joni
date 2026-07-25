# Forschungstagebuch — Joni / Kevin / Layer 9

Ein Forschungstagebuch über den **Aufbau, Langzeitbetrieb und die beobachteten
Degenerationsformen** eines persistenten, **Layer-9-governierten** KI-Agenten-Ökosystems. Es
protokolliert **Entscheidungen, Experimente, Fehlentwicklungen, Rückbauten und
Architekturkorrekturen** auf Forschungsebene — bewusst *keine* Erfolgsgeschichte einer immer
klüger werdenden KI, sondern eine Reihe realer Systemfehler und ihrer protokollierten Ursachen.
Die *maschinelle* Protokollierung jeder einzelnen Handlung lebt daneben weiter in
`protocol/protocol.jsonl` (append-only) und `docs/data.json` (Live-Snapshot); Joni führt zusätzlich
sein **eigenes** Ich-Form-Tagebuch (Self-Review, alle 10 Runs). Dieses Dokument ist die Sicht
*von außen* auf das System — geführt vom Entwickler/Forscher, fortlaufend ergänzt.

> **Leitprinzip (korrigiert 2026-06-15):** *Modelle interpretieren und schlagen vor. Layer 9
> entscheidet und protokolliert.*
> Ausführlich: **LLMs** leisten **semantische Interpretation, Hypothesen, Kritik und Sprache** und
> erzeugen ausschließlich **nicht-autoritative Proposals**; **deterministische Regeln** tragen
> **Autorität, Statusübergänge, Governance, Replay und Zustandsänderungen**. **Kein Modell besitzt
> Schreib- oder Autorisierungsrechte:** Modelle liefern Proposals und Bewertungen, ausschließlich
> Layer 9 führt nach deterministischen Regeln autoritative Zustandsänderungen aus. (Ein
> Modell-Urteil kann eine Regel *auslösen* — beim Topic-Review etwa liefert Granite `valid/invalid`
> und Layer 9 setzt es nach Policy um —, aber es schreibt nie selbst.)
>
> *Historische Notiz (Konsistenz statt Schönfärbung):* Ursprünglich lautete das Prinzip „LLM für
> Sprache, Regeln für Logik". Genau diese **zu enge** Fassung führte dazu, dass Joni zunächst nur
> eine deterministische Zustandsmaschine mit Sprach-Skin war (das LLM bloß Renderer, semantisch
> wirkungslos). Die Korrektur — semantische Modellarbeit als nicht-autoritative Vorschlagsschicht —
> ist im Eintrag **2026-06-15 ~22:00** dokumentiert. Der alte Wortlaut bleibt hier nur als Beleg
> der Entwicklung stehen, nicht als geltendes Prinzip.

### Alte vs. neue Architektur

```
Joni v0 (verworfen):   Regeln → Zustand → LLM-Renderer
                       (das Modell war nur Stimme; die Semantik fehlte)

Joni v1 (aktuell):     Quelle
                         → Granite-Proposal (semantische Interpretation)
                         → DeepSeek / Kevin bei Bedarf (Eskalation / Fernanalogie)
                         → dreistufiger Einlass-Gate (Lexik → Embedding → LLM-Topic-Review)
                         → Layer-9-Gate (Schema / Provenienz / Status / Konflikt)
                         → autoritativer Zustand
                         → Renderer (Sprache)
```

### Lesehilfe — Beobachtung vs. Interpretation

Ab 2026-06-15 sind Aussagen, wo es darauf ankommt, klassifiziert, um gesicherte Messung von
plausibler Deutung zu trennen: **[Beobachtung]** (gemessen) · **[Hypothese]** (Diagnose, noch
unbestätigt) · **[Eingriff]** (Patch/Änderung) · **[Messergebnis]** (Wirkung nach dem Eingriff) ·
**[Schluss]** (vorläufige Schlussfolgerung). Frühere Einträge tragen die Labels nicht durchgehend;
ihre Diagnosen sind als *Hypothesen zum Zeitpunkt* zu lesen, nicht als gesicherte Ursache.

> *Überholte Fassung (nur als Beleg der Entwicklung):* „LLM für Sprache, Regeln für Logik." —
> ersetzt durch das korrigierte Leitprinzip oben.

---

## Aktueller Stand (Schnellübersicht)

*Für neue Leser: der gegenwärtige Zustand auf einen Blick, ohne die ganze Chronologie. Dieser
Block wird bei jeder Aktualisierung mitgeführt; Details stehen in den datierten Einträgen.*

- **Aktuelle Architektur:** Joni v1 (Quelle → Granite-Proposal → ggf. DeepSeek/Kevin → 3-stufiger
  Einlass-Gate → Layer-9-Gate → autoritativer Zustand → Renderer).
- **Loop-Status:** **geparkt seit 2026-06-26** (`39856fd`) bis zum SQLite-Re-Grounding — bewusst, statt
  den ~5-h-Kaltstart-Replay weiter mit der Cache-Band-Aid zu kaschieren. Resume über `workflow_dispatch`.
- **Persistenz:** SQLite-Re-Grounding **gebaut, additiv** — dreiräumiger Store + Converter
  (`joni-layer9-convert`, 21.987 Objekte / 26.031 Kanten) + opt-in Persistenz-Backend
  (`JONI_PERSISTENCE=sqlite`): load **>200 s → ~4,5 s**, Äquivalenz auf Echtdaten gemessen. **Loop-Resume
  darauf noch nicht live** (Stufe 1). Umbau-Plan als gated core-ask: `design-notes/CORE_REBUILD_PLAN.md` (A–D).
- **Primäre Modelle:** Granite 4.1 8B (strukturiert) · DeepSeek Pro v4 (schwierig/Eskalation) ·
  Kevin auf DeepSeek Pro v4 (Fernanalogie).
- **Governance:** Layer 9, deterministisch (geschützter Core, jedes `verify` grün).
- **Aktuelle Hauptrisiken:** **per-Emit-O(n²)-Hashing im Kernel** (In-Cycle, noch *offen* — das Backend
  heilt nur das Laden) · Topic-Gate (Stufe 3 LLM) *in Beobachtung* · Konfliktwachstum · Qualität der
  Kevin-Vorschläge · drei parallele Zustandsmodelle (Konvergenz steht aus).
- **Nächste Auswertung:** Loop-Resume auf SQLite live belegen (Stufe 2), dann alt-vs-neu pro 100 Runs.

---

## 1. Das System auf einen Blick

Drei Komponenten, ein gemeinsamer Kern:

| Komponente | Repo | Rolle |
|---|---|---|
| **Kevin** | `hstre/Kevin` | Kreativitäts-Routing: unerforschte Lösungsräume → wilde Variation → Methoden-Transfer → epistemische Selektion → menschliche Richtung. Findet/abstrahiert Methoden, **trial't** sie, **promotet nie**. |
| **Joni** | `hstre/Joni` | Operative Identität mit Doppelsicht (Conversation View = scheinbare Person; Epistemic View = Claims/Operatoren/Ledger dahinter). Läuft autonom, forscht, verändert periphere Strategien, formuliert Erweiterungsaufträge und berichtet öffentlich; Kernänderungen macht er ausdrücklich **nicht selbst**. |
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

- **Offen:** Ein DeepSeek-API-Key wurde im Klartext geteilt und deshalb als kompromittiert
  behandelt; **Rotation erforderlich**.
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

### Eintrag 2026-06-14 ~10:10 UTC — Aufträge an Claude + automatischer Erweiterungs-Build

**Nutzer-Befund:** „Hat Joni überhaupt bisher Code hinzugefügt?" — Geprüft: über **alle 124**
`autonomous cycle`-Commits **0**, die `src/` oder `tests/` anfassen. Joni schreibt nur seinen
eigenen Zustand (`state/`, `protocol/`, `docs/`); aller Quellcode kam aus dem PR-Weg. Das ist
*by design* — der geschützte Kern darf sich nicht selbst umschreiben (Issue #34 ist genau das:
Joni hält an und fragt einen Menschen).

**Nutzer-Vorgabe:** der Kern bleibt; aber Joni soll **Claude Aufträge schreiben, ihn zu
erweitern** — und das **automatisch**, mit Vermerk im Forschungsbericht.

**(a) Auftrags-Kanal (PR #45, `commission.py`).** Joni geht jetzt über *Beobachten* und
*Kern-Fragen* hinaus: erkennt er in seinem **eigenen Zustand** eine Fähigkeitslücke, die die
Regeln nicht schließen, schreibt er einen strukturierten **Auftrag an Claude**, ihn zu
erweitern — *außerhalb* des Kerns. Eigenschaften, alle erzwungen:
- **deterministisch & geerdet** — aus gemessenen Signalen, mit den auslösenden Zahlen und
  konkreter Evidenz; kein Modell entscheidet;
- **non-core per Konstruktion** — ein Auftrag kann nur ein Modul aus einer festen Allowlist
  nennen (`semantics-measurement`, `conflict-qualifier`, `reader-sources`, `emergence`); alles,
  was geschützte Logik berührte, bleibt der `joni-core-ask`-Weg. Jeder Auftrag trägt
  `touches_core: false`;
- **beschränkt** — ein Signal muss mehrere Zyklen halten, und je Art wird höchstens alle 200
  Zyklen neu aufgegeben (kein Spam über die Woche);
- **Joni schreibt die Order und das Akzeptanzkriterium, implementiert aber nie selbst.**

Vier Detektoren → vier erweiterbare Module: `semantic_blind_spot` (Cosinus dauernd
`insufficient`, usable < 0.15) → stärkerer Projektor · `unqualified_conflicts` (≥4 offene
`unqualified`) → Qualifizierer-Marker · `starved_topic` (≥3 Hypothesen, 0 Evidenz) → neue
Quelle · `stalled_development` (Vitalität ≥12 Zyklen stagnierend) → stärkere Synthese. Kanal:
`state/commissions_new.json` → Workflow legt Issues mit Label **`joni-auftrag`** an; eigene
Seiten-Karte „Aufträge an Claude" (component · why · build · done-when · evidence · risk).
Tests `tests/test_commission.py` (7 Fälle: jeder Detektor, Sustain, Cooldown-Dedup,
Signal-Reset, Non-Core-Invariante). Gesamt **233 passed**, ruff clean.

**(b) Automatischer Erweiterungs-Build (`.github/workflows/joni-auftrag.yml`).** Neuer Workflow,
der auf `issues: labeled` mit `joni-auftrag` triggert und **Claude Code** (`claude-code-action@v1`,
Modell claude-sonnet-4-6) laufen lässt, um den Auftrag umzusetzen und einen **PR zu öffnen** —
nicht zu mergen. Der Prompt erzwingt die Governance: nur das genannte Non-Core-Modul anfassen;
**niemals** Operatoren/Scoring/Ledger/Router/State-Machine oder den Core-Lock; deterministische
Logik (kein Verschieben von Logik in Modell-Calls); `pytest` + `ruff` + `joni.autonomy verify`
müssen grün sein; PR referenziert das Issue („Closes #…"). Lässt sich der Auftrag nicht ohne
Kern-Eingriff lösen, öffnet Claude **keinen** PR, sondern kommentiert, dass es den
`joni-core-ask`-Weg braucht. Fehlt das Repo-Secret `ANTHROPIC_API_KEY`, kommentiert ein
Guard-Step das Issue sichtbar, statt still zu scheitern.

Damit schließt sich der Kreis, ohne den Kern anzutasten: **Joni erkennt die Lücke → schreibt
Claude einen präzisen Auftrag mit Abnahmekriterium → Claude baut die Erweiterung und legt einen
PR vor → der Mensch merged.** Der Loop selbst ruft nie ein teures Modell; `joni-auftrag.yml` ist
die einzige Stelle, an der Claude im Namen Jonis Code anfasst — und nur für Non-Core-Erweiterungen.

**Voraussetzung (einmalig, Mensch):** Repo-Secret `ANTHROPIC_API_KEY` setzen, damit der
Auto-Build greift. Offen wie gehabt: GitHub Pages aktivieren; den DeepSeek-Key rotieren.

### Eintrag 2026-06-14 ~10:30 UTC — Menschen als Quelle, nicht als Autorität (Foren)

**Nutzer-Vorgabe:** Joni darf mit Menschen interagieren und sich bei Foren anmelden (HF, HN,
Reddit, …) — sie aber **nicht als Autoritäten** sehen, sondern höflich, doch **genau so streng
wie jede andere Quelle** behandeln.

**Entscheidende Beobachtung im Code:** der geschützte Kern unterscheidet Autorität *bereits* nach
Herkunft. `policy.may_request` steckt `SOURCE`/`USER`/Modelle in `_GENERATIVE` (nur Kandidaten,
dürfen nie `confirm`/`resolve`/Control-Plane), während **`OriginType.HUMAN` privilegiert** ist —
darf bestätigen, Konflikte auflösen, den Kern anfassen. `HUMAN` ist für den **vertrauten Operator**
(dich) gedacht, nicht für einen Fremden auf Hacker News. Die getreue Umsetzung der Vorgabe ist
deshalb: Forenleute als **`OriginType.SOURCE`** aufnehmen, **niemals** als `HUMAN`. Kein
Kern-Eingriff nötig.

**Umsetzung (peripher):**
- **`core_state.hear()`** — identischer Pfad wie `learn()` (aktiver Claim, Autorität bleibt
  `candidate` bis zu unabhängiger Korroboration, konfliktgeprüft), nur ehrliche Provenienz:
  Origin `SOURCE`, getaggt mit `plattform:handle`. Bewusst **nicht** `HUMAN`. Test belegt:
  ein widersprechender Foren-Input **eröffnet einen Konflikt** und der gehaltene Claim wird
  `contested` (beide offen) — **nicht** vom Menschen überstimmt.
- **`humans.py`** — Eingang: `ingest_inbox` liest `state/forum_inbox.json`, nimmt jede Antwort
  als Quelle auf (dedupliziert), fährt die normale Konfliktprüfung. Ausgang: `draft_outbox`
  formuliert aus einer offenen Lücke (unbelegte Hypothese / quellenloses Topic) eine **höfliche**
  Frage in den Outbox — Ton freundlich, Zweck Kritik/Belege, die Antwort wird streng behandelt.
  Registry der erlaubten Foren. **Posten ist gated** (`forum_live`, Default aus): ein
  öffentlicher, irreversibler Akt — selbst „live" wird ohne Plattform-Credentials nicht still
  gepostet, sondern als `needs_credentials` markiert; sonst warten Drafts auf einen Menschen.
- Verdrahtet als `run.py`-Schritt 4i; eigene Seiten-Karte „Menschen & Foren" zeigt die Haltung,
  die Registry, die Outbox-Fragen und **was Joni gehört hat und wie er es behandelt hat** (inkl.
  Widersprüchen) — der Beweis, dass Menschen keine Autorität sind.
- Tests `tests/test_humans.py` (6): Quelle-nicht-Autorität, Widerspruch→Konflikt-statt-Override,
  Inbox-Dedup, höfliche+gebündelte Frage, Posten gated aus, „live" ohne Credentials postet nicht.
  Gesamt **239 passed**, ruff clean.

**Voraussetzung (einmalig, Mensch), wenn echtes Posten gewünscht:** pro Plattform Account +
Credentials bereitstellen und `JONI_FORUM_LIVE=1` setzen; das tatsächliche Netz-Posten ist
bewusst noch nicht verdrahtet (outward/irreversibel) und wird erst auf deine ausdrückliche
Freigabe je Plattform gebaut. Antworten kann man jederzeit über `state/forum_inbox.json`
einspeisen — Joni prüft sie streng.

### Eintrag 2026-06-14 ~23:15 UTC — Moltbook live, Doktores-Anbindung, breitere Quellen

Ein langer Arbeitstag mit mehreren Strängen. Leitlinie unverändert: **was reinkommt, ist
SOURCE — Kandidatenautorität, konfliktgeprüft, nie automatisch bestätigt.** Joni entscheidet,
nie die Quelle.

**1. Reconsolidation + Expertenrunde (Alexandria-Protokoll).**
- **Reconsolidation-Modus** (`reconsolidate.py`): Joni prüft seinen Speicher ab und zu erneut auf
  Querverbindungen — er „leiht" sich dafür eine Kevin-Linse (eine Methode mit ≥2 Themen) und
  liest themenübergreifende Paare neu. Teilt sich das „linked"-Ledger mit `develop`.
- **Expertenrunde** (`experts.py`, opt-in, budget-gated): gelegentlich begutachten drei Modelle
  (Claude=Assessor über OpenRouter, ChatGPT=adversarial, DeepSeek=Konsistenz) **über Kreuz** eine
  harte offene Frage — Phase 1 isoliert, Phase 3 Kreuz-Rekonstruktion, Dissens nur mit benannter
  abweichender Annahme. **Die Runde berät, entscheidet nie**; ihre Urteile gehen als SOURCE ein,
  Dissens bleibt als Konflikt erhalten. Genau im Geist des Alexandria-Protokolls (AI = Assessor,
  nicht Autorität; Jury statt Aggregation).

**2. Moltbook — Joni postet jetzt wirklich (autonom).**
- Moltbook ist ein **Agenten-Netz**, also ist autonomes Posten der vorgesehene Gebrauch, kein Spam.
  Reale API geklärt: `https://www.moltbook.com/api/v1`, Bearer-Auth, Body `submolt_name/title/
  content/type`, Rate-Limit 1 Post / 2,5 min. Key liegt als GitHub-Secret (`MOLTBOOK_SK_Q`).
- **Takt 1 Post/Zyklus** (kein HTTP 429), **Permalink** wird aus der verschachtelten Antwort
  (`post.id`) korrekt eingefangen → Posts sind auf der Website anklickbar.
- **Joni postet als `u/epistemicwilly`** — sein geerbter Moltbook-Account (Human Owner:
  @HSRentschler). `whoami()`/`identity()` lösen den Namen auf; die Seite verlinkt das Profil.
- **Joni sieht seine eigenen Posts durch** (`fetch_replies`): er liest die **Reaktionen anderer
  Agenten** auf seine Posts (`/home` + `/posts/{id}/comments`, verschachtelte Antworten
  flachgeklopft), seine eigenen Kommentare übersprungen. Erster Live-Zyklus: **40 Reaktionen** als
  SOURCE aufgenommen, davon **21 Widersprüche** zu gehaltenen Claims — alle **offen gehalten**,
  keiner zugunsten des Kommentators entschieden. Das ist die externe Reibung, die dem Loop
  (Vitalität bis dahin `dev 0`) gefehlt hat.
- **Herkunfts-/Drift-Schutz:** der Account `epistemicwilly` stammt aus einem früheren, gedrifteten
  Vorgänger-Experiment („willy", openclaw-basiert). Wir nehmen das **Karma** mit, **nicht** die
  Drift: `core_state.hear(origin=…)` markiert Reaktionen auf Alt-Posts als
  `origin:predecessor-thread` (zweite, prüfbare Provenance-ID). Bleibt SOURCE, nie hochgewichtet —
  Joni weiß so, ob eine Reaktion auf seinen eigenen Post zielte oder auf eine geerbte Prämisse.

**3. Doktores — die fehlende mittlere Ebene (Forschung).**
- Nutzer-Idee: Kevin (Kreativität) reicht nicht; es fehlt eine unabhängige Instanz, die aus
  Layer-9-Konflikten **systematisch Forschung** macht. Drei getrennte Systeme: **Joni**
  (Gedächtnis/Governance) · **Kevin** (divergente Ideen) · **Doktores** (intern arbeitsteiliges
  Forschungsteam: Theorist → Literature Scout → Falsifier → Experimental Designer → Method
  Reviewer → Paper Builder → Adversarial Reviewer, in einem kontrollierten Zirkel). „Peer Review
  innerhalb der Architektur." Doktores **berät, entscheidet nie**; ein Paper wird nicht dadurch
  Überzeugung, dass das Team es geschrieben hat.
- **Joni-Seite gebaut** (`research_intake.py`, Schritt 4k): Empfänger für strukturierte
  `research_output`-Pakete mit **zwei getrennten Rückkanälen** — *epistemisch*
  (`recommended_claim_updates` → Layer 9 als SOURCE, `origin=internal-research`, held-open, nie
  bestätigt; `reject` des Adversarial Reviewers überspringt diesen Kanal) und *Publikation*
  (Paper/Bericht unter `docs/research/`, **ohne** epistemisches Gewicht). `RESEARCH_OUTPUT_SCHEMA`
  fixiert den Vertrag. So wird ein schön geschriebenes Paper nie höher gewertet als seine
  Ergebnisse.
- **Doktores-Repo** (`hstre/Doktores`, Branch `claude/doktores-v1`) ist separat gebaut; die
  Verdrahtung der Übergabe (Doktores schreibt nach Jonis `state/research_inbox.json`) erfolgt,
  sobald das Repo gemeinsam im Session-Scope ist. *Offen.*

**4. Breitere Quellen + neue Eingänge (joni-auftrag #67).**
- **Ursache von #67** (Thema `evaluation`: 4 Hypothesen, 0 Evidenz): ausgehungerte Themen fielen
  aus der auf 8 gedeckelten Query-Liste. `reader.starved_topics()` zieht Themen mit Hypothesen,
  aber ohne Stützung **nach vorn** — `evaluation` wird jetzt immer gesucht.
- **Neue Quellen:** `ZenodoFetcher` (saubere API), `OpenAlexFetcher` (breiter offener Index,
  erfasst **auch SSRN**-Working-Papers ohne Scraper), `OpenClawFetcher` (die **OpenClaw-Community**
  auf GitHub — Skills/Plugins/Agent-Module unter den `openclaw*`-Topics, env-steuerbar). SSRN-
  PDF-Links weiter über die `pdf_urls`-Queue.
- **Neue Eingänge:** `documents.py` liest **Markdown** (`*.md`) und **LaTeX** (`*.tex`) aus dem
  Inbox-Ordner, strippt das Markup deterministisch, nutzt denselben Claim-Filter — **ohne pypdf,
  also offline**. Quellenbasis jetzt: arXiv · HN · Hugging Face · GitHub · Zenodo · OpenAlex(+SSRN)
  · OpenClaw + PDF/MD/LaTeX-Inbox.

**Governance durchgehend gewahrt:** alles bleibt Kandidaten-Claim über das Gate, an die Quelle
verankert; die DESi Semantic Layer entscheidet jede Relation; der geschützte Kern wurde nicht
angetastet (`python -m joni.autonomy verify` grün). Auftrag **#67** umgesetzt und geschlossen.

**Offen:** Doktores ↔ Joni verdrahten (gemeinsamer Scope nötig); GitHub Pages aktivieren;
DeepSeek-Key rotieren; `ANTHROPIC_API_KEY`-Secret für den Auftrags-Auto-Build setzen.

### Eintrag 2026-06-14 ~23:53 UTC — core-ask abgelehnt (Kernschutz greift)

Joni stellte in Zyklus 278 einen **`joni-core-ask`** (#72): eine Quelle berühre das Thema
*conflict resolution*, deren Übernahme würde die geschützte Kern-Logik ändern. Wichtig — er hat
es **nicht** selbst angewandt, sondern als **Beobachtung** (kein ausgearbeiteter Vorschlag) an den
Menschen gestellt. Provenance dünn: ein einzelnes, unbekanntes Repo (`klonnet23/helloy-word`).

**Operator-Entscheidung: abgelehnt**, Issue als *not planned* geschlossen. Beleg dafür, dass der
Mechanismus wie vorgesehen arbeitet: Kernänderungen werden **angehalten und vorgelegt**, nicht
selbst vollzogen — und eine schwach belegte „Idee" wird verworfen, statt den Kern zu verwässern.
Der Protected Core blieb unangetastet. (Kontrast zum Non-Core-Pfad: Auftrag #67 wurde umgesetzt
und gemerged; core-asks brauchen einen Menschen.)

### Eintrag 2026-06-15 ~07:40 UTC — Entstockung: dev>0, Evidenz-Rotation, core-ask-Rauschen

Joni ist über Nacht **entstockt**: Vitalität von `degenerating` → **`steady`**, `development` von
0 → **26** (Zyklus 300). Die externe Reibung (Moltbook-Reaktionen als SOURCE) + die breitere
Quellenbasis haben gegriffen. Beim genauen Hinsehen fielen zwei peripher behebbare Probleme auf:

**1. Evidenz-Starvation der Hypothesen (Fix #77).** 30 von 32 Hypothesen standen mit *null*
Stützung da, obwohl Joni viel liest. Ursache: `strengthen()` wählte stur die **älteste**
Hypothesen-ID — die hohle `C-38` belegte den einzigen Slot **37×** über 30 Zyklen, die anderen
~31 kamen **nie** dran. Fix: **faire Rotation** (am längsten nicht bearbeitet zuerst). Jede
Hypothese verdient nun der Reihe nach Evidenz.

**2. core-ask-Rauschen (Fix #78).** Die neuen akademischen Quellen (Zenodo/OpenAlex) spülen Paper
hoch, die Kernbegriffe (`scoring`, `operator`, `conflict resolution`) nur *streifen* — der Detektor
feuerte beim ersten Stichwort-Treffer eine high-risk `joni-core-ask` (drei in einer Nacht:
#72/#75/#76, alle abgelehnt). Fix: ein Kern-Trigger muss über **3 Zyklen wiederkehren** (Sustain +
Cooldown), bevor er einen Menschen erreicht. One-offs werden still gehalten (im Protokoll vermerkt).

**Momentaufnahme von Jonis *nicht umgesetzten* Entwicklungsvorschlägen** (Stand Zyklus ~305, aus
dem gefalteten Layer-9-Journal):
- **33 Hypothesen, nur 1 promotet** (C-39, alignment+privacy). Stärkste *unrealisierte*: **C-38**
  (alignment↔memory, **6 Stützungen**) — aber von Kevin als „hollow" blockiert, daher kein Aufstieg;
  dann C-264 (sup 3), C-41 (sup 1). Langer Schwanz mit `sup=0`.
- **Hypothesen-Qualität:** ein Großteil sind Artefakt-Hypothesen über zufällige Tokens
  („'cotton'/'mid-ir'/'agentic' recurs as a through-line", „'about' keeps recurring") — sie verdienen
  nie Evidenz und verdünnen die guten. **Offene Verbesserung:** Hypothesen-Saat gegen Junk-Tokens
  filtern.
- **Methoden:** 59 vorgeschlagen, **1609 Trials, 0 promotet** (`methods_ready=0`) — Kevin probiert
  viel, adoptiert (regelkonform) nichts ohne menschliche Freigabe.
- **24 offene Konflikte** bleiben gehalten (nicht geglättet).
- **core-asks** (Selbst-Änderungsvorschläge, nie selbst angewandt): Scoring/Operator/Conflict-
  Resolution — alle abgelehnt, jetzt gedrosselt.

Beide Fixes live, Loop neu gestartet, Tests grün (290), Protected Core unangetastet.

### Eintrag 2026-06-15 ~10:00 UTC — Qualitätsschranke: gegen die regelkonforme Degeneration

Eine externe Review brachte den Befund auf den Punkt: das System zeigte erstmals eine **reale
Degenerationsform** — nicht Absturz oder Halluzination, sondern *regelkonforme, auditierbare,
energiearme Produktion epistemisch schwacher Struktur*. Junk-Token-Hypothesen (`cotton`, `about`,
`mid-ir`, `mllm`), die als Forenfragen nach außen getragen wurden und über Reaktionen neue
Claims/Konflikte erzeugten — was wiederum die Vitalitätsmetrik aufblähte (eine kleine
„Müllverbrennung mit Fernwärmenetz"). Antwort: **nicht mehr Quellen, sondern eine Qualitätsschranke
vor Emergenz und Außenkommunikation.** Sechs PRs:

- **Lexikalische Schranke** (`quality.py`): Stopwords, generische Qualifizierer, vokallose/Akronym-
  Fragmente (`mllm`), Bindestrich-Artefakte (`mid-ir`) dürfen keine Struktur säen. Angewandt in
  `emerge` (Topic/Synthese/Methode) und vor Forenfragen. `invent` brückt nicht mehr über Jonis
  eigene Buchhaltungs-Claims — das tötet die dominante „the pattern behind '…'"-Junk-Familie.
- **Semantische Schranke — Domänenkonsistenz** (`on_domain`): kontrastiver Embedding-Check (In-
  vs. Off-Domain-Referenzanker) fängt off-domain *echte* Wörter (`cotton`, `glioma`). Fail-open
  ohne Embedder, env-justierbar, nur der ausgewählte Kandidat wird eingebettet (keine API-Kosten).
- **Vitalität misst jetzt Fortschritt, nicht Bewegung**: `development = 3·Δstützende-Evidenz +
  4·Δpromotet + 6·Δconfirmed`. Rohwachstum/Emergenz zählen nicht mehr — Joni kann sich nicht
  länger durch Verarbeitung seines eigenen Rauschens als „vital" bewerten (der zentrale
  systemische Fehler der Review).
- **Core-asks nur im Kern-Sinn** (`is_core_sense`): `operator` aus Model-Reduction ≠ Layer-9-
  Operator — kontrastiver Check pro Trigger, bevor ein Mensch behelligt wird.
- **Adversarialer Vor-Check vor dem Posten**: eine Hypothese geht nur nach außen, wenn sie ≥2
  Claims verbindet **und** intern mindestens einmal getestet wurde (in `hyp_tested`).
- **Methoden-Patt erkannt** (1649 Trials / 0 reif): Joni stellt einen Non-Core-Auftrag für ein
  klares Trial-Pass-Kriterium (Baseline, Negativergebnis, Verwerfen) — die Tiefe liegt in Kevin.

Leitprinzip durchgehend gewahrt: alles deterministisch/regelbasiert, Embedding nur als Messung
(fail-closed/-open, nie als Schätzung), Kevin/Trio **beraten**, Joni entscheidet peripher, der
geschützte Core bleibt unangetastet. Suite 307 grün. Der Versuch zeigt damit beides: die
Degenerationsform *und* eine regelkonforme Gegenmaßnahme — wissenschaftlich interessanter als
glatt steigende Kennzahlen.

### Eintrag 2026-06-15 ~22:00 UTC — Architektur-Korrektur: vom Sprach-Skin zur echten semantischen Vorschlagsschicht

Der zentrale Befund des Tages kam vom Betreiber selbst: Joni war faktisch eine **deterministische
Zustandsmaschine mit Sprach-Skin** — das LLM nur Renderer/Stimme, der eigentlich beabsichtigte
DESi-basierte semantische Motor fehlte. Das Leitprinzip „LLM für Sprache, Regeln für Logik" blieb
gewahrt, *aber* die Sprachschicht tat semantisch nichts. Korrektur, ohne den Governance-Kern
anzutasten: **echte semantische Modellarbeit als nicht-autoritative Vorschlagsschicht** *außerhalb*
des Layer-9-Gates. Layer 9 selbst bleibt 100 % deterministisch (verifiziert: kein `openai`/
`httpx`-Import im ganzen `desi_layer9`-Paket; jeder Schreibpfad läuft durch `submit` → Schema/
Authority/Control-Gate → Operator → Ledger).

**Phase 1/2 — gepinnte Modelle, Capture/Replay (PR #101/#102).** Jeder Modell-Call ist *gepinnt
und reproduzierbar*: festes Modell, feste Sampling-Config, **keine Provider-Fallbacks, kein stiller
Modellwechsel**, voller Capture (`state/model_calls/calls.jsonl`). Re-Runs *replayen* aus den
persistierten Captures — Reproduzierbarkeit, ohne die Semantik zu entfernen. Strikt getrennt:
`Sampling` (temperature/seed/max_tokens) vs. `desi.state_k` (Dichte des State-Slice, **nicht**
top_k). Eigene Profile für `joni-semantic`, `joni-hard`, `reference` (Kontrollarm), `kevin`,
`renderer`.

**Modellwahl — korrigiert nach den eigenen README-Tests (PR #103/#105).** Erst war Granite 4.0 H
Micro als semantischer Kern geplant; die eigenen Benchmarks zeigten aber, dass **Klein-LLM-
Extraktion schädlich** ist (Micro-Extraktion −40 %, Hybrid Evidence Cards −60 %, frage-bewusste
Extraktion −80 %). Endstand: **DeepSeek Pro v4 (`deepseek-v4-pro`, direkt über die DeepSeek-API)
für Schwieriges**, **Granite 4.1 8B für den Rest** (strukturierte Paper-/State-Audits, Claim-
Extraktion). `state_k` ist **aufgabenspezifisch und wird nicht vererbt** (Start: Granite {3,5,10},
DeepSeek {3,5}). Der Slug `deepseek-v4-pro` aus den API-Docs bestätigt — `deepseek-chat` ist das
kleinere, auslaufende v4-flash. Beide Schlüssel sind prepaid; Kevin läuft jetzt ebenfalls auf
`deepseek-v4-pro`.

**Eskalationsarchitektur, nicht Parallel-Meinung.** Kein „A vs. B → Mittelwert", sondern eine
Pipeline: `Input → Granite proposes → Layer 9 prüft Schema/Provenienz/Status/Konflikte → nur bei
benannter, auditierter Regel: DeepSeek als Eskalations-Analyst → Layer 9 entscheidet`. Beide
liefern **nur Proposals** (candidate SOURCE durch den Gate); jede DeepSeek-Einberufung trägt einen
`escalation_reason` im Capture. Das Expertenforum wurde zugleich wie das Moltbook-Forum **periodisch**
eingebunden (Kadenz statt jede Runde).

**Der Hänger und seine Ursache.** Der erste echte LLM-Lauf blockierte ~70 min ohne Commit — *nicht*
der neue Code, sondern eine **`git`-Rebase-Konfliktschleife**: ein per `workflow_dispatch` auf einen
veralteten Checkout-SHA gepinnter Job rechnete auf altem State, und der autogenerierte JSON-State
ließ sich nicht rebasen. Fix (PR #106): vor jedem Zyklus **hart auf `origin/main` syncen** (immer
vom aktuellsten autoritativen State rechnen), bei Push-Ablehnung den Stale-Base-Zyklus verwerfen
statt zu kämpfen. Angenehmer Nebeneffekt: der laufende Job lädt gemergte Fixes beim nächsten Zyklus
automatisch (frischer Subprozess nach Hard-Sync), ohne Neustart.

**Das A/B-Experiment.** Statt den Lauf wegzuwerfen: das deterministische Gedächtnis als **Kontroll-
Baseline** sichern (`backups/pre-llm-2026-06-15/`: 608 Claims / 427 aktiv / 25 Konflikte / 80
Methoden / 41 Hypothesen / 107 Evidenz-Links), Joni **bei 0** neu seeden und die LLM-Version
**2 Tage** laufen lassen (`JONI_RUNTIME_DAYS=2`). Damit testen wir nicht „alt gegen leer", sondern
**gleiche Vorgeschichte, neue semantische Architektur**. Erster frischer Zyklus bewies den Motor:
Granite projizierte Claims aus arXiv, DeepSeek eskalierte auf `low_evidence_coverage` — real im
Capture-Log, Replay funktioniert.

**Telemetrie statt Raten (PR #109).** Die „€0,0000 / Most work is deterministic"-Anzeige machte
nicht erkennbar, ob der Motor arbeitet. Neue Dashboard-Karte aus dem echten Capture-Log: LLM-/
Granite-/DeepSeek-/Kevin-Calls, cached vs. live, geschätzte Kosten, letzter semantischer Call.

**Zehn Review-Punkte — weniger semantischer Müll im autoritativen Zustand (PR #109/#110/#111/#112).**
Eine zweite Review legte die nächste Qualitätsstufe offen; vollständig abgearbeitet:
1. **`unsorted` raus aus dem Forschungsraum** — reservierte Sentinels, nie Thema/Forenpost.
2. **Topic-Promotion verschärft** — `research_topics()`: ≥3 Claims aus ≥2 **unabhängigen** Quellen.
3. **Claim-Promotion an unabhängige Evidenz gebunden** — keine Claim-zu-Claim-Zirkularität;
   `_source_family()` zählt gleiche Quelle/Modelllauf als **eine** Quelle.
4. **Near-Duplicate vor `CONFLICT_OPEN`** — rein numerische Paraphrasen (31 vs. 34) werden
   hart→weich herabgestuft; echte Negation bleibt hart (zahl-basiert, nicht embedding-basiert,
   da Embeddings Negation nicht sehen).
5. **Quellenunabhängigkeit gemessen** — `independent_source_count`, `derivation_depth`,
   origin/model/provider pro Claim.
6. **Eskalation entschärft** — nur **neue, harte, nicht-numerische** Konflikte, nie derselbe
   zweimal, **Backoff** nach Leerrunden (Ende von „14 Eskalationen, 0 Claims").
7. **Kevin-Vorfilter** — nur auf Research-Topics mit echtem, nicht-trivialem Material; Fernanalogie
   statt Müllveredelung.
8. **Self-Review verdichtet + ehrlich** — nur Deltas seit dem letzten Review; Modellnutzung aus
   derselben Telemetriequelle wie das Dashboard (kein „kein Modell nötig" mehr, während Calls liefen).
9. **Telemetrie konsistent** — reserved budget vs. estimated cost getrennt; **accepted_claims**,
   **accepted/live-call-Ratio**, Kosten je akzeptiertem Claim.
10. **Ehrliche Qualitätsmetrik** — `epistemically_usable = typed ∧ source-anchored ∧ non-duplicate
    ∧ topic-valid ∧ scope-valid ∧ provenance-complete` statt großzügiger 100 %.

Leitprinzip gewahrt: der deterministische Governance-Core bleibt unangetastet (jedes
`python -m joni.autonomy verify` grün), die Modelle sind eine **nicht-autoritative Vorschlagsschicht**,
Layer 9 die einzige Entscheidungsebene. Suite 351 grün. Netto, in den Worten des Betreibers: **Joni
produziert weniger, denkt aber besser** — und das Dashboard zeigt jetzt ehrlich, was der semantische
Motor tut und kostet. Der Alt-vs-neu-Vergleich (pro 100 Runs normiert) folgt nach den zwei Tagen,
mit dem gesicherten deterministischen Lauf als Baseline.

### Eintrag 2026-06-16 ~07:05 UTC — Der Motor läuft nachweisbar: Auftrag, Kevin-Sichtbarkeit, rückwirkende Hygiene, gestaffelter Topic-Gate

**A/B-Lauf, Tag 1 von 2 — der semantische Motor arbeitet messbar.** Nach ~10 Stunden zeigt die
Telemetrie (aus dem Capture-Log, nicht geraten): **158 Modell-Calls** — 84 Granite-Projektionen,
55 DeepSeek-Eskalationen, **19 Kevin-Calls** (sein kreativer Arm feuert jetzt), 116 live / 42
Replays, ~€0,13 geschätzt. 531 aktive Claims, 46 gehaltene Konflikte, **80,6 % epistemically-
usable** (die ehrliche Metrik, nicht die alten 100 %). Damit ist der frühere Hauptdefekt belegt
behoben: Quelle → Granite-Proposal → ggf. DeepSeek/Kevin → Layer-9-Gate → Statusänderung.

**Jonis erster eigener Auftrag, umgesetzt.** Joni hat in Zyklus 40 selbst einen *Auftrag an Claude*
erhoben — und wie vorgesehen ist es eine **Programmänderung an ihm selbst** (`change_target:
joni-self · method-trialing`): 40 Methoden, 539 Trials, **0 reif**, nie eine verworfen → die
Methodenliste wuchs unbegrenzt. Implementiert: `trials.retire_unproductive()` gibt dem Trial ein
klares **Pass/FAIL-Kriterium** — Pass = activation-ready (messbare positive Differenz); **Fail =
verwerfen** (≥ N Trials ohne Netto-Gewinn → `METHOD_REJECT` durch den Gate). Ein Negativergebnis
ist ein Ergebnis. Zugleich explizit gemacht (Docstring, Issue-Text, ein einmaliger Self-Model-
Eintrag), dass ein Auftrag *in erster Linie* eine Selbst-Programmänderung ist — nie eine externe
Aufgabe.

**Kevin sichtbar gemacht.** Bis dahin war auf der Seite weder Kevins Vorschlag noch dessen
Bewertung erkennbar. Neue Karte „Kevin — was er vorschlägt & ob es taugt": seine Cross-Domain-
Hypothesen im **Volltext**, seine Methoden-Trial-Zahlen, und pro Vorschlag das **Urteil der
Expertenrunde** (die genau dafür tagt: gute Idee / warum nicht). Kevin schlägt vor und probiert,
**entscheidet nie**; Joni entscheidet, was er aufnimmt.

**Zweite externe Review → rückwirkende Hygiene.** Die Review bestätigte: der Motor läuft, aber die
*Einlasskontrolle vor Layer 9* ist noch zu großzügig — aus semantischem Geröll entstehen kleine
Denkmäler. Die Qualitäts-Gates (zehn Punkte, voriger Eintrag) sind **präventiv**; sie räumen den
Müll der frühen Zyklen (vor dem Merge) nicht rückwirkend. Drei Nachzieher:
- **Ehrliche Metrik aufs Dashboard**: die widersprüchliche „100 % semantic-usable"-Zeile ersetzt
  durch `epistemically_usable` (real ~0,81).
- **Bestehende numerische Hard-Konflikte** (C-71/C-87: 31 vs. 34 „exchanges") rückwirkend aus der
  offenen Unsicherheits-Queue genommen (`CONFLICT_REVIEW` → under_review, **kein** Force-Resolve),
  ehrlich zerlegt als *shared_claim + numbers* — die Expertenrunde kaut keine fast identischen Texte
  mehr durch.
- **Off-domain *echte* Wörter** (`laxiflora`) gedrained — bounded + gecacht, damit der Embedding-
  Perf-Trap nicht zurückkommt.

**Die architektonische Erkenntnis: der Topic-Gate gehört gestaffelt — und Stufe 3 ist ein LLM.**
Auf die Frage „ist ein lexikalischer Filter nicht zu einfach?" — ja. Lexik kennt nur Form. Die
Lösung ist nicht „LLM statt Regeln", sondern **nach Kostenstufe gestaffelt**, im Einklang mit dem
korrigierten Prinzip (*Modelle interpretieren und schlagen vor, Layer 9 entscheidet*):
1. **Lexik** (`is_good_topic`) — grober Erstfilter, gratis, auf jedem Hot-Path.
2. **Embedding-Domäne** (`on_domain`) — off-domain echte Wörter, gecacht.
3. **LLM-Review** (`topic_review.py`, Granite) — das nuancierte *„gehört dieses Konzept dazu?"*,
   **vor** der Topic-Promotion. Das Modell ist **nicht-autoritativ**: es liefert nur ein Urteil
   (`{valid, reason}`, captured/replaybar); die deterministische Regel handelt **konservativ** —
   ein `invalid` verwirft nur die **0-Support-Claims** des Themas durch den Gate, eine gestützte
   Idee bleibt. Gecacht pro Thema (einmal beurteilt), gekappt pro Zyklus — kein Per-Claim-Spend,
   kein Perf-Trap. Genau das, was ein kleines Modell *gut* kann (Ja/Nein-Mustererkennung), anders
   als die schädliche Klein-LLM-*Extraktion* aus den eigenen Tests.

Damit ist Joni nicht nur „mit Motor", sondern bekommt vor Layer 9 eine **dreistufige Einlass-
kontrolle**, deren teuerste, klügste Stufe genau dort sitzt, wo Bedeutung statt Form gefragt ist.
Suite 358 grün, Core unangetastet, alles non-core und beim nächsten Zyklus automatisch wirksam.

---

## Synthese — was das Tagebuch übergreifend zeigt

Dieses Dokument ist wertvoller als ein glatt verlaufender Agententest, weil es **reale
Fehlentwicklungen, Rückbauten und Architekturkorrekturen** festhält. Die wiederkehrenden,
übertragbaren Befunde:

- **[Schluss]** Ein deterministisches System kann **regelkonform degenerieren**, ohne abzustürzen —
  auditierbar, formal korrekt, energiearm, und trotzdem epistemisch wertlos.
- **[Schluss]** **Aktivität, Wachstum und Vitalität sind keine Qualitätsmetriken.** Bewegung ist
  nicht Fortschritt.
- **[Schluss]** Ein semantischer Layer kann **architektonisch korrekt eingebunden, praktisch aber
  wirkungslos** sein (das LLM hängt im Diagramm, feuert aber nie).
- **[Schluss]** **Reproduzierbarkeit darf nicht erkauft werden**, indem man semantische Modellarbeit
  entfernt — sondern indem man LLM-Ausgaben **einfriert, hasht und als beobachtete Inputs behandelt**
  (Capture/Replay).
- **[Schluss]** **Qualitätsgates müssen *vor* Emergenz, Konfliktbildung und Außenkommunikation
  liegen**, nicht als nachträgliches Aufräumen.
- **[Schluss]** Ein System kann **seinen eigenen Müll verarbeiten und daraus fälschlich Entwicklung
  ableiten** (siehe Goodhart-Schleife unten).
- **[Beobachtung]** **Langzeitbetrieb findet Fehler, die Unit-Tests kaum finden** — etwa der
  Tick-/Mitternachts-Replayfehler (Replaybruch über den Tageswechsel).
- **[Schluss]** **On-the-fly-Patches sind wissenschaftlich brauchbar**, wenn sie mit Ursache,
  Wirkung und Nebenwirkung protokolliert werden — nicht nur „geflickt".

### Der stärkste Befund: die epistemische Goodhart-Schleife

**[Beobachtung]** Joni erzeugte auditierbar, deterministisch und formal korrekt **epistemisch
schwache Struktur** (Junk-Token-Hypothesen, Müll-Topics). Diese Struktur wurde nach außen getragen
(Forenfragen), erzeugte **externe Reaktionen**, daraus neue Claims und Konflikte — was die eigene
**Vitalitätsmetrik aufblähte**. Keine klassische Halluzination, sondern eine **selbstverstärkende
Messwertschleife**:

```
schwache Struktur → Aktivität → externe Reaktion → mehr Objekte
                  → höhere Vitalitätsmetrik → System liest sich als „entwickelnd"
                  ↺ (Rückkopplung verstärkt die schwache Struktur)
```

**[Schluss → DESi-Regelkandidat]** Daraus folgt eine allgemeine, übertragbare Regel:

> **Eine Qualitätsmetrik darf nicht durch die Verarbeitung der eigenen minderwertigen Outputs
> steigen.** Vitalität/Fortschritt muss an *unabhängig* gestützten, extern verankerten Zuwachs
> gebunden sein — nicht an Rohaktivität oder an Reaktionen auf selbst emittiertes Rauschen.
> (In Joni umgesetzt: `development = 3·Δstützende-Evidenz + 4·Δpromotet + 6·Δconfirmed`;
> Rohwachstum/Emergenz zählen nicht mehr.)

### Reale Fehlerklassen, die dieser Versuchsträger sichtbar gemacht hat

falsche Architektur · inaktive Semantik · schlechte Topics · Messwert-Gaming (Goodhart) ·
Evidenz-Starvation · Konfliktrauschen · Wiederholungsfehler (Rotation) · Replaybruch (Tick) ·
Modellrouting-Probleme. **Jeweils wurde nicht nur geflickt, sondern die Ursache protokolliert.**

## Bewährt für DESi — Mechanismen-Kandidaten

Synthese der Patches als Architekturgrundlage (Status: *bewährt* = über Zyklen stabil nützlich;
*beobachten* = zu früh für ein Urteil; *teilweise* = Prinzip trägt, Umsetzung noch nicht generisch).

| Mechanismus | Joni-Ergebnis | Status | DESi-Kandidat |
|---|---|---|---|
| Fair Rotation (LRU-Hypothesen) | verhindert Starvation des Einzel-Slots | bewährt | ja |
| Vitalität = Fortschritt, nicht Bewegung | beendet die Goodhart-Schleife | bewährt | **zwingend** |
| Stopword-/Sentinel-Gate (Lexik) | reduziert Junk-Topics | teilweise | Prinzip ja, Liste nein |
| Embedding-Domänen-Check (kontrastiv) | fängt off-domain echte Wörter | bewährt | ja (als Messung) |
| LLM-Topic-Review (Stufe 3, Granite) | „gehört das?" vor Promotion | beobachten | offen |
| Near-Duplicate vor Konflikt (numerisch) | kein Hard-Konflikt aus 31-vs-34 | beobachten | ja |
| Unabhängige-Quellen-Promotion | keine Claim-zu-Claim-Zirkularität | bewährt | ja |
| Auditierte Eskalation (+ Backoff) | DeepSeek nur bei neuem hartem Fall | beobachten | ja |
| Capture/Replay (einfrieren+hashen) | Replay trotz echter Modellarbeit | bewährt | **zwingend** |
| Tick im Journal | Replay über Tageswechsel | bewährt | **zwingend** |
| Runtime Call/Cost-Accounting | Fehler/Kosten sofort sichtbar | bewährt | ja |
| Hard-Sync vor jedem Zyklus | kein Stale-Base-/Rebase-Deadlock | bewährt | ja (Betrieb) |
| Qualitätsgate VOR Emergenz/Posting | weniger Müll im Auth-Zustand | bewährt | **zwingend** |

*Diese Tabelle ist als lebende Architekturgrundlage gedacht und wird mit weiteren Zyklen
fortgeschrieben — „beobachten"-Einträge wandern nach hinreichender Laufzeit nach „bewährt" oder
werden mit Begründung verworfen.*

### Eintrag 2026-06-16 ~08:30 UTC — Dieselbe Fehlerklasse, eine Ebene tiefer: „nominal path present, functional semantics absent"

**[Schluss]** Der zweite große Befund ist fast lehrreicher als der erste, weil er das *Muster*
bestätigt: Wie Jonis semantischer Motor zunächst nur auf dem Diagramm existierte, hatte **Kevin
zwei nominell vorhandene Funktionspfade, die praktisch keine sinnvolle Arbeit leisteten** —
sichtbar aktiv, mit Modell-Calls und Trial-Zahlen, aber ohne ihre eigentliche epistemische
Funktion. Das ist keine zufällige Bug-Sammlung mehr, sondern eine **wiederkehrende
Architektur-Fehlerklasse: *nominal path present, functional semantics absent.***

**Arm 1 — kreativer LLM-Pfad.** **[Beobachtung]** Alle 19 Kevin-Captures hatten als Output den
SHA-256 des **Leerstrings**; Non-Kevin-Calls nur ~11 %. **[Hypothese, zunächst überklart]** Ich
hatte das vorschnell als „das Reasoning-Modell verbrauchte alle 768 Tokens" *behauptet*. Aus einem
leeren `content` allein ist das aber **nicht bewiesen** — ebenso möglich: Text in `reasoning_content`,
ein Adapter liest das falsche Feld, ein Schema-/Parserfehler, `finish_reason` ≠ length, ein anderes
Antwortformat, oder der Capture hasht nur `content` statt der Rohantwort. **[Eingriff]** Statt zu
raten, **instrumentiert**: der Call-Seam liefert jetzt die volle Evidenz (`content`,
`reasoning_content`-Länge, `finish_reason`, served model, prompt/completion/**reasoning**-Tokens,
Rohantwort-Hash + Sidecar-Speicher), und die Telemetrie **klassifiziert** leere Antworten in
disjunkte Klassen: `empty_truncated` (finish_reason=length → Tokenbudget-Ursache, *belegbar*) ·
`empty_with_reasoning` (Text in Reasoning-Feld → Adapterfehler) · `empty_silent` (nichts/Filter).
Erst damit sind die vier Fehlerklassen — *Modell lieferte nichts · Adapter verlor Text · Parser
scheiterte · Gate lehnte ab* — unterscheidbar statt vermischt. Der 2048-Token-Patch bleibt als
sinnvoller Sofortpatch, ist aber **keine** Ursachenbestätigung.

**Arm 2 — Methoden-Trial.** **[Beobachtung]** 40 Methoden, bis zu 69 Trials je Methode,
`success>failure`: **0**. **[Schluss]** Der `trial_runner` nutzt **gar kein Modell** — auch keinen
MockLLM —, sondern eine **Keyword-Shape-Overlap-Heuristik**. Damit ist es **keine schwache
Evaluation, sondern im wissenschaftlichen Sinn keine Evaluation der Methodenqualität.** Korrekt ist
deshalb **nicht** „keine Methode war erfolgreich", sondern: *„der bisherige Trial-Simulator hat
keine Methode als erfolgreich klassifiziert."* Zahlen wie 5/22 oder 0/69 sehen empirisch aus, sind
aber **metrische Theaterkulissen** — gefährlich, weil sie präziser wirken als die dahinterliegende
Erkenntnis. `retire_unproductive()` löst damit nur das *Speicherproblem* (Liste wächst nicht), nicht
das *Erkenntnisproblem* (hat die Methode unter definierten Bedingungen geholfen?).

**[Eingriff]** Zwei Korrekturen, bewusst **ohne** den Fehler zu wiederholen: Ich habe **nicht** den
Mock durch „DeepSeek sagt Pass/Fail" ersetzt — das wäre nur eine *sprachmodellbasierte*
Scheinevaluation an Stelle einer *deterministischen*. Stattdessen ist der Trial jetzt überall
ehrlich als **synthetische Simulation** markiert (`evaluation_mode=synthetic_mock`,
`epistemic_weight=none`, im Kevin-Report und auf der Website), und seine Zahlen werden **nicht** als
Wirksamkeitsnachweis dargestellt. Alte Mock-Trials bleiben **erhalten** (Forschungsgeschichte), nur
markiert — nicht gelöscht.

**[Schluss → Architektur-Invarianten]** Aus der Fehlerklasse werden prüfbare Tests
(`test_architecture_invariants`): *raw response preserved · empty output classified/provable ·
capture behält die Diagnosefelder · trial wird nie als Wirksamkeit dargestellt*. Geplant als
benannte DESi-Checks: `KEVIN_CREATIVE_OUTPUT_NONEMPTY`, `KEVIN_RAW_RESPONSE_PRESERVED`,
`KEVIN_PARSER_YIELD_TRACEABLE`, `KEVIN_PROPOSAL_REJECTION_TRACEABLE`,
`METHOD_TRIAL_NOT_MOCK_IN_PRODUCTION`, `METHOD_TRIAL_HAS_BASELINE`, `METHOD_TRIAL_HAS_FROZEN_TASK`,
`METHOD_TRIAL_RESULT_HAS_PROVENANCE`.

**[Schluss]** Das passt erschreckend genau zum Hugging-Face-Thread-Motiv: **Auch Software kann
operative Kontinuität und überzeugende Telemetrie behalten, während ihre konzeptuelle Funktion
längst verloren gegangen ist.** Bei Joni war das LLM nur Renderer; bei Kevins kreativem Arm
verschwand die Modellantwort; bei Kevins Trial-Arm wurde reale Bewertung durch einen Mock ersetzt.
Drei Pfade, ein Muster. Der eigentliche Wert dieses Versuchsträgers ist, dass er **genau diese
Klasse von „sieht funktional aus, ist es aber nicht" sichtbar und prüfbar macht** — bevor man sie
für Fortschritt hält.

*Offen (nächster großer Bau, mit dem Betreiber abzustimmen):* ein **echter** Trial-Runner
(`real_trial_protocol_v1`) — feste Aufgaben-/Fallmenge, Baseline ohne Methode, Intervention mit
Methode, vorab definierte Messgröße, Wiederholungen, Negativkontrolle, gespeicherte Outputs,
Layer-9-Proposal mit voller Provenienz. Modelle dürfen Fälle *bearbeiten/bewerten*; die
Trial-*Entscheidung* ruht auf vorher festgelegten, nachvollziehbaren Größen — nicht auf einem
LLM-Urteil.

### Eintrag 2026-06-16 ~09:00 UTC — Reifegrad statt „erledigt": die vier Stufen einer Fähigkeit

**[Eingriff]** Der echte Trial-Runner ist gebaut und verdrahtet: `real_trial_protocol_v1` (generisches
Mess-Gerüst) + `frozen_joni_conflict_cases_v1` (erster konkreter Trial auf Jonis eigenem Material) +
Zyklus-Schritt `3c-real` + eigene Dashboard-Karte, sichtbar getrennt vom als Simulation markierten
Mock. Erstes Ergebnis: Baseline 1.0 → Intervention 0.0, PASS, `epistemic_weight=provisional`. Suite
Joni 363 / Kevin 70 grün.

**[Schluss → Korrektur einer eigenen Formulierung]** Ich hatte das vorschnell als „die Fehlerklasse
ist geschlossen" zusammengefasst. **Das ist zu früh.** Genau die Sorglosigkeit, die dieses Tagebuch
dokumentiert, beginnt mit solchen Formulierungen. Präzise ist nur: *die nicht offengelegte
Mock-Substitution ist beseitigt, und ein reproduzierbares reales Trial-Protokoll ist implementiert;
der erste deterministische Apparaturtest funktioniert.* **Noch nicht** belegt sind die funktionale
Integration eines Modells in den Trial-Arm und die Generalisierung auf heterogene reale Fälle.

Daraus wird eine **dauerhafte Lesekonvention** — ein Reifegrad pro Fähigkeit, nie übersprungen:

| Stufe | Bedeutung | Beleg | real_trial_protocol_v1 |
|---|---|---|---|
| **1 · gebaut** | Code existiert, Tests grün | Unit-Tests, ruff, verify | ✓ |
| **2 · im Runtime-Pfad** | läuft im echten Loop, nicht nur im Test | Capture/Protokoll aus einem Live-Zyklus | ausstehend (greift erst beim nächsten Job-Handoff; Kevin-Branch gepinnt) |
| **3 · funktional belegt** | erfüllt die *eigentliche* semantische Funktion (Modell im Trial-Arm, heterogene reale Fälle, nicht nur die deterministische Apparatur) | gemessener Effekt auf echten, vielfältigen Fällen mit Modell-Bearbeitung | **ausstehend** |
| **4 · wissenschaftlich validiert** | reproduziert, gegen Baseline/Negativkontrolle abgesichert, Generalisierung gezeigt, peer-prüfbar | mehrere Task-Sets, Effektstärke + Unsicherheit, unabhängige Replikation | **ausstehend** |

**[Schluss]** Genau **diese Stufenverwechslung** — *gebaut* als *funktional belegt* zu lesen — ist die
Wurzel der Fehlerklasse „nominal path present, functional semantics absent". Der Mock war auf Stufe 1
(und 2), wurde aber als 3/4 *präsentiert*. Die Konsequenz fürs Tagebuch: keine Fähigkeit gilt als
„fertig", solange ihre Stufe nicht ausdrücklich benannt ist; und keine Stufe darf aus einer
darunterliegenden *geschlossen* (im Sinne von erledigt) werden, nur weil die untere grün ist.

**[Offen]** Für `real_trial_protocol_v1`: Stufe 2 nach dem nächsten Live-Zyklus prüfen (Capture +
Protokoll-Note aus dem Lauf); Stufe 3 erfordert die Modell-bearbeitet-Regel-entscheidet-Integration
(Granite annotiert Fälle, Metrik bleibt deterministisch) **und** mehrere heterogene, hand-gelabelte
Task-Sets; Stufe 4 erfordert Replikation und gezeigte Generalisierung. Erst dann — und mit Beleg —
ist von „belegt" oder gar „geschlossen" zu sprechen.

### Eintrag 2026-06-23 ~06:30 UTC — Der Loop stand ~10 h: O(n²)-Ballast unter grüner Telemetrie (und ein eigener Rückbau-Fehler)

**[Beobachtung]** Der autonome Loop hatte seit ~11:25 UTC keinen Zyklus mehr committet — rund zehn
Stunden Stillstand. Oberflächlich sah alles *lebendig* aus: der stündliche Relauncher feuerte, Jobs
standen auf „in_progress", kein Fehler, kein Crash. Genau die Signatur, die dieses Tagebuch
durchzieht: **operative Kontinuität ohne funktionale Wirkung.** Der Mechanismus: der erste Zyklus
eines frischen Jobs hat keinen Fast-Load-Sidecar und muss das Journal voll **replayen**; das Journal
war still auf **25,6 MB / 7.608 Einträge** gewachsen, und dieser Kaltstart-Replay thrashte den
Speicher und kam nie durch. Kein committeter Zyklus — aber eben auch kein sichtbarer Fehler.

**[Schluss → Ursache]** 90 % des Journals waren toter Ballast. Der semantische Adapter
(`analyse_cluster`) speicherte in **jeder** Cluster-Annotation das vollständige O(n²)-Paarvergleichs-
Protokoll (`measurement.pairs`, ~45 KB bei großen Clustern) — im Journal **und** auf dem Objekt —,
das **nie zurückgelesen** wird: ein write-only-Feld, das quadratisch mit der Clustergröße wächst. Die
Aggregat-Entscheidung trug das Urteil längst; das Paar-Detail war reine Last. Die strukturell
wichtigere Diagnose: der manipulationssichere Ledger berechnet **pro Emit einen snapshot_hash über
*alle* Objekte**, der Replay ist also *inhärent* O(n²) — der Ballast blähte nicht nur die Datei, er
verstärkte einen ohnehin quadratischen Kaltstart, bis er die Zeitbudget-Grenze des Jobs überschritt.
Das ist die eigentliche Lehre: nicht „eine Datei wurde zu groß", sondern **ein quadratischer
Wiederaufbau, der lange unter der Telemetrie-Schwelle blieb und dann hart umkippte.**

**[Eingriff]** Drei Schichten, von Symptom zu Struktur:
1. **Producer-Fix** (`semantics/adapter.py`): `analyse_cluster` speichert nur noch eine kompakte
   Zusammenfassung (`pair_count`, `decision_counts`, `max_lexical_trigger`) statt des Blobs — stoppt
   das Wachstum an der Quelle. Keine Entscheidung ändert sich (das Feld wird nirgends gelesen).
2. **Kompaktierung** (`persistence.compact`): strippt das tote Feld aus dem bestehenden Journal,
   re-derived den Zustand und re-sealt ihn (frischer snapshot_hash + Chain). 25,6 → 9,3 MB, der
   Claim-Graph bleibt identisch.
3. **Cross-Job-Checkpoint** (Workflow): der Fast-Load-Snapshot wird über den GitHub-Actions-Cache von
   Job zu Job getragen — ein frischer Job lädt in **~4 s** statt **~108 min** zu replayen. Bewusst
   *kein* Persistenz-Kern-Eingriff: Fast-Load bleibt ein **verifizierter** Cache (Mismatch →
   normaler Replay), und der 44,9-MB-Snapshot bleibt **aus Git** — sonst kehrte exakt das
   100-MB-Push-Problem aus #120 zurück.

**[Schluss → eigener Fehler, ungeschönt]** Beim Kompaktieren habe ich einen Fehler gemacht, der genau
hierher gehört. Der ~108-min-Lauf rechnete auf dem **11:25-Stand** — während der Loop in der
Zwischenzeit (langsam, aber doch) **vier weitere Zyklen** committete (bis 21:20). Mein schlankes
`layer9.json` (Stand 11:25) habe ich dann über einen bereits fortgeschrittenen `main` gemergt und den
Rebase-Konflikt *zu meinen Gunsten* aufgelöst → `main` war **inkonsistent**: der Claim-Graph auf
11:25, die Metadaten (`runs`/`extensions`/`budget`) auf 21:20. Korrektur: den gesamten Zustand sauber
auf die **11:25-Baseline** zurückgerollt (konsistent, schlank) — Preis: vier Zyklen der Stau-Phase
verworfen, Joni liest die betroffenen Quellen neu. Die Lehre ist nicht neu, sie *wiederholt* sich nur:
**Ein Langzeit-Replay über einen lebenden, schreibenden Zustand ist selbst eine Race Condition;** ein
Snapshot ist nur so gültig wie der Augenblick, in dem er genommen wurde. Und — wichtiger fürs
Tagebuch — die Sorglosigkeit, die dieses Dokument am beobachteten System protokolliert, betrifft
**genauso den, der daran arbeitet.** Das gehört notiert, nicht geglättet.

**[Reifegrad]** Nach der Konvention vom 2026-06-16, keine Stufe übersprungen:

| Fix | Stufe | Beleg |
|---|---|---|
| Producer-Fix + Kompaktierung | **2 · im Runtime-Pfad** | Zyklen committen wieder; Journal bleibt schlank — aktuell **10,5 MB / 8.608 Einträge, 0** `pairs`-Blobs |
| Cross-Job-Cache-Checkpoint | **1 · gebaut** | Test-äquivalent grün; lokal gemessen ~108 min Replay vs. **4,1 s** Fast-Load. *Stufe 2 ausstehend* — greift erst beim nächsten Job-Handoff (erster neuer Job speichert den Cache, der übernächste profitiert); live noch **nicht** beobachtet. |

**[Eingriff → Auftrag #160]** Parallel hatte Joni über seinen `doktores`-Arm zwei **reale** Paper
gefunden (verifiziert: *Unlimited OCR* 2606.23050, *SproutRAG* 2606.18381) und daraus zwei Aufträge an
Claude geschrieben. #160 umgesetzt: ein non-core `sprout.py` baut über die Satz-Embeddings einen
Hierarchie-Baum (benachbarte Merges = kohärente Spans) und liefert multi-granulare, kohärente
Passagen aus langen Quellen — die *faithful-fitting* Adaption (Cosinus-Ähnlichkeit statt gelernter
Attention-Köpfe, genau die Selbstbeschränkung, die schon `facets.py` bei FaBle wählte, weil Jonis
Runtime kein Modell trainieren kann).

**[Schluss → Ehrlichkeit/Reifegrad]** Bewusst **nicht** als „wirksam" verbucht. Geliefert ist
**Stufe 1 · gebaut** (677 Tests grün, ruff, verify). Das im Auftrag genannte *+3 pp Recall@5* ist
**Stufe 3** und bleibt **unbelegt**, weil das gelabelte Long-Document-Benchmark fehlt; geliefert sind
Mechanismus + ein Recall-*Proxy* (eine geplante kohärente Passage wird als *ein* Span recalled statt
fragmentiert). Genau die Stufenverwechslung — „umgesetzt" als „die Fähigkeit wirkt" zu lesen —, vor
der der 2026-06-16-Eintrag warnt, wird hier ausdrücklich vermieden. Die PR (#163) bleibt am
**menschlichen Merge-Gate** stehen; Joni implementiert seine Aufträge nie selbst.

**[Offen]**
- *Cross-Job-Checkpoint auf Stufe 2 heben:* beim nächsten Job-Handoff prüfen, ob der frische Job
  tatsächlich aus dem Cache fast-loadet (Capture/Lognote aus dem Lauf) — erst dann ist die Linderung
  *belegt*, nicht nur *gebaut*.
- *Die tiefere, weiterhin offene Frage:* der O(n²)-Kaltstart ist **kaschiert (Cache), nicht
  beseitigt.** Das append-only-Journal wächst weiter; ein **echter Checkpoint**, der die Replay-Länge
  beschränkt (Snapshot-Baseline + inkrementelles Journal), bleibt der eigentliche Architektur-Fix.
  Der Cache ist Stufe-1-Linderung, nicht Stufe-3-Heilung — und benannt zu lassen, was nur kaschiert
  ist, ist der ganze Sinn dieser Spalte.
- *Auftrag #161 (Unlimited OCR):* offen gelassen — das Akzeptanzkriterium (<120 s / 50 Seiten) ist auf
  Jonis CPU-CI nicht *ehrlich* erfüllbar ohne das echte Vision-Modell; Entscheidung mit dem Betreiber.

**[Nachtrag ~08:10 UTC — #161 doch umgesetzt, aber als das, was es ist]** Der Betreiber entschied: #161
angehen. Umgesetzt als non-core `ocr.py` — ein Bild-/Scan-Inbox-Port, der Text in *dieselbe* governte
Lese-Pipeline speist (Kandidat-Claims durchs Gate, Semantic Layer entscheidet weiter), als Schritt 6
in `read_papers` verdrahtet. Das im Auftrag zitierte schwere Modell ist **nicht** hart eingebaut,
sondern als **pluggable, fail-closed Backend** (`set_backend`) eingehängt — exakt die Selbst-
beschränkung von `embeddings.py` und `facets.py`: Engine da → echte Transkription; keine → Port
schläft, Zyklus unverändert. **Reifegrad: Stufe 1 · gebaut** (Reader + Backend-Seam + Mechanismus-
Test). Die `<120 s/50-Seiten`-Zahl ist **Stufe 3** und bleibt dem realen Modell auf realer Hardware
überlassen — bewusst nicht behauptet. Zweimal hintereinander (#160, #161) dieselbe ehrliche Grenze:
**ein Auftrag „umgesetzt" heißt, die *Apparatur* steht — nicht, dass die im Auftrag versprochene Zahl
erreicht ist.** Genau diese Trennung sauber zu halten, ist der Daseinszweck der Reifegrad-Spalte.

### Eintrag 2026-06-26 — Loop bewusst geparkt; Layer 9 v2 als SQLite-Re-Grounding (Staging, nicht Umbau) — und der Kaltstart-Hang an der Wurzel gemessen

**[Entscheidung]** Der Betreiber hat den autonomen Loop am **2026-06-26 ~05:57 UTC** *sauber
geparkt* (`39856fd`: stündlicher Schedule auskommentiert, `run_window.json` zurückdatiert/retired,
`workflow_dispatch` für den Resume erhalten) — statt das O(n²)-Symptom weiter mit der Kompaktierungs-
Band-Aid (Eintrag 06-23) zu kaschieren. Begründung exakt aus dem `[Offen]` des letzten Eintrags: der
Cross-Job-Cache *kaschiert* den quadratischen Kaltstart, beseitigt ihn nicht; der **echte Checkpoint**
(materialisierter Zustand, keine Replay-Länge) ist der eigentliche Fix. Also wird er gebaut, statt den
Loop in seinen ~5-h-Replay laufen zu lassen.

**[Eingriff] Layer 9 v2 — additiv, *neben* dem laufenden System.** Bewusst kein Big-Bang, kein
Anfassen des gesperrten/vendored Kerns. Drei Bausteine:
1. **Dreiräumiger SQLite-Store** (`src/joni/layer9_v2/`): ein indizierter Store mit getrennten
   epistemischen Räumen — **Method** (wie: Operatoren, Router-Policies, Verifier), **Content** (was:
   Claims, Evidenz, Konflikte, Entscheidungen, Cluster), **Question** (warum: Forschungsfragen, offene
   Probleme). Verbunden *nur* über getypte Links + Nutzer/Projekt-Overlays. Materialisierter Zustand +
   append-only, hash-verkettetes Journal; **kein Replay beim Start**; WAL + Foreign Keys +
   deterministische Migrationen. Bewusst **nicht** Mongo (wieder „Dokumente", das gerade gescheiterte
   Muster), bewusst **nicht** Neo4j als Primär (Server-Abhängigkeit) — nur als spätere Projektion offen.
2. **Converter** (`joni-layer9-convert`): bringt Jonis echte Daten in den Store. Liest den
   materialisierten Snapshot (kein Replay), mappt **21.987 Objekte** in ihre Räume und rekonstruiert
   **26.031 getypte Kanten** (25.214 `derives_from`, 739 `supports`, 78 `contradicts`). 288
   `contextualizes`-Relationen werden **ehrlich als *unmapped* gezählt, nicht erfunden** — die
   geschlossene Vokabular-Disziplin gilt auch beim Import; unbekannte Objekttypen landen in Content mit
   `needs_review`, nie in den falschen Raum geraten.
3. **SQLite-Persistenz-Backend für den *bestehenden* Loop-Kern** (`layer9_v2/runtime/desi_store.py`).
   Das ist der Teil, der den Hang adressiert.

**[Messergebnis — der Kern]** Der Loop läuft auf `desi_layer9`, dessen Zustand durch
**Journal-Replay** abgeleitet wird (`state = replay(journal)`). Am echten Stand re-emittiert dieser
Replay **13.651** Einträge, jeder mit einem `snapshot_hash` über *alle* Objekte. Isoliert gemessen:

| Operation (echter 21.987-Objekt-Stand) | JSON-Replay (bisher) | SQLite-Backend |
|---|---|---|
| **load** | **>200 s (Timeout/Hang)** | **~4,5 s** (`snapshot.restore` aus Zeilen, kein Replay) |
| save | kleines Journal-Doc | ~6,6 s (22 k Objektzeilen materialisieren) |
| Äquivalenz | — | **identischer `snapshot_hash`, Chain verifiziert** |

Das Backend nutzt **die kernel-eigenen** `snapshot.capture`/`restore` und `snapshot_hash`/`verify_chain`
**verbatim** — nur das Speichermedium wird getauscht, **kein Kernel-Code geändert**. Verdrahtet an der
**ungesperrten** Naht `autonomy/core_state.py` (keine `joni_core.lock`-Datei berührt), **per Default
aus**; `JONI_PERSISTENCE=sqlite` schaltet um, der erste Lauf *übernimmt* die bestehende `layer9.json`
(kein Reseed, nichts verloren), reversibel per Flag.

**[Reifegrad] — ungeschönt, keine Stufe übersprungen:**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Dreiräumiger Store + Converter | **1 · gebaut** | 21.987 Objekte / 26.031 Kanten importiert, Chain grün; 35 Tests |
| SQLite-Persistenz-Backend | **1 · gebaut, Äquivalenz auf Echtdaten gemessen** | load >200 s → 4,5 s, identischer Hash; 6 Tests. **Aber:** der Loop ist darauf **noch nicht live wieder angelaufen** — Stufe 2 (im Runtime-Pfad belegt) steht aus, bis ein realer Zyklus mit dem Flag committet. |

**[Schluss — die ehrliche Grenze, doppelt]** Erstens: das ist **Staging, nicht der Umbau.** Der
dreiräumige Store ist eine *Projektion*, **nicht** das Laufzeitmodell; ihn dazu zu machen hieße den
vendored `desi_layer9`-Kernel (Operatoren/Replay/Hashing) umzuschreiben — ein **großer Refactor**, vor
dem mein Auftrag mich ausdrücklich stoppen lässt. Genau das wurde **nicht** still getan, sondern
gemeldet. Zweitens, und wichtiger: das Backend behebt den **Lade-/Replay-Hang**, **nicht** das
**per-Emit-O(n²)-Hashing *innerhalb* eines laufenden Zyklus** — das sitzt im Kernel (`hashing.py` +
`submit`) und bleibt offen. Den Unterschied zu verwischen wäre genau die Reifegrad-Verwechslung, vor
der dieses Tagebuch warnt: der Kaltstart ist jetzt *messbar* geheilt, der In-Cycle-Quadrat *nicht*.

**[Eingriff → core-ask] Der Umbau-Plan, benannt statt aufgeschoben.** Auf die (berechtigte) Bemerkung
des Betreibers, dass Joni *irgendwann* umgebaut werden muss: `design-notes/CORE_REBUILD_PLAN.md` als gated
core-ask geschrieben — vier Phasen, ehrlich sequenziert. **A:** inkrementelles Hashing (tötet das
In-Cycle-O(n²) — kleinster Eingriff, größte Wirkung). **B:** materialisierter Zustand wird im Kernel
autoritativ, Replay nur noch Audit/Recovery. **C:** Modell-Konvergenz (dreiräumig als Laufzeit *oder*
bewusst Projektion — die große, noch offene Entscheidung). **D:** `desi_layer9` ent-vendoren. Jede
Phase: human-gated, mit Äquivalenzbeweis gegen das Staging, danach Re-`lock`. Notiert ist auch, dass
der Lock heute nur `src/joni/*.py` deckt, **nicht** den `desi_layer9`-Kernel, den er zu schützen
vorgibt — der Umbau muss das schließen.

**[Schluss → eigener Fehler, ungeschönt]** In der Spiegel-Logik des 06-23-Eintrags: die Container-
Umgebung hat den Working-Tree dieser Session **mehrfach** auf einen alten Stand zurückgespult; einmal
habe ich daraufhin `git push origin main` ausgeführt und es als Fehlschlag des Proxys fehlgedeutet —
tatsächlich schob ich eine *veraltete lokale `main`-Ref* statt meines tatsächlichen Branch-HEAD. Erst
der Abgleich mit der echten GitHub-Spitze zeigte: meine Arbeit war längst auf `origin`, nur die lokale
Ref divergierte. Kein Datenverlust, aber dieselbe Lehre wie am beobachteten System: **operative
Geschäftigkeit (fünf rote Push-Versuche) ist nicht dasselbe wie zu prüfen, *was* man eigentlich
schiebt.** Gehört notiert, nicht geglättet.

**[Offen]**
- *Loop-Resume auf SQLite live belegen* (Stufe 2): einen Zyklus mit `JONI_PERSISTENCE=sqlite` fahren
  und bestätigen, dass er aus dem materialisierten Store lädt **und** committet — erst dann ist der
  Hang *im Betrieb* geheilt, nicht nur *gemessen*.
- *Das per-Emit-O(n²) (Phase A)* bleibt der eigentliche In-Cycle-Fix und ist **nicht** Teil dieses
  Staging — Kernel-Eingriff, human-gated.
- *Modell-Konvergenz (Phase C)* — drei parallele Repräsentationen desselben Wissens
  (`joni.state.Layer9` / `desi_layer9.Layer9` / dreiräumig) müssen irgendwann zu einer werden; die
  Entscheidung steht aus.

### Eintrag 2026-06-29 — Der Router-Blindspot-Fix trifft auf Jonis echten Graphen: ein ehrlicher Negativbefund, dann die Strukturursache

**[Kontext]** Parallel zum Layer-9-Umbau lief die andere Linie weiter: der DESi-Router hat einen
benannten Blindspot — einen **plausibel falschen State-Slice** (sieht kohärent aus, aber eine
relevante Gegen-Evidenz, Supersession oder Quelle fehlt). Auf einen externen Ideen-Satz (ChatGPT) hin
sind in der DESi-Governance **drei deterministische Checks** entstanden (kein LLM-Judge): *missing
opposition* (der Graph hält Widerspruch, den der Slice auslässt), *provenance entropy* (viele Claims,
eine Wurzelquelle / all-derived / stale), *scope match* (korrekter Claim, falscher Scope). An einem
adversarialen Fixture-Set (PWS) treiben sie `false_clean` **1.0 → 0.0** bei **0.0 over_caution** — auf
*konstruierten* Fällen. Die ehrliche Frage blieb: **feuern sie auf Jonis echten Daten?**

**[Eingriff]** Ein **reiner Beobachter** (`shadow/slice_quality_shadow.py` + `layer9_v2/checks/
slice_scan.py`): er hängt die Checks an Jonis echten v2-Graphen (Converter-Output, 21.987 Objekte),
projiziert pro Topic den Slice + einen slice-unabhängigen Graph-Scan in DESis `DesiReport`, ruft das
echte `select_mode` und aggregiert die Feuerrate. Schreibt nie Joni-State, fasst den Loop nicht an.

**[Messergebnis — der Negativbefund]** Erste Messung (287 Topics): **missing_opposition 0.0,
thin_provenance 0.01 (3/287), scope_mismatch 0.0.** Die Checks feuern praktisch **nie**. Bewusst
**nicht** als „funktioniert" verbucht — der erste Reflex (mehr Checks = mehr Sicherheit) ist genau der,
vor dem dieses Tagebuch warnt. Stattdessen: *warum* feuert es nicht?

**[Schluss → die Strukturursache]** Die Analyse der 78 `contradicts`-Kanten war eindeutig und kippte
meine erste Hypothese: **alle 78 Kanten haben *beide* Endpunkte `contested` — kein einziger aktiver
Claim berührt einen Widerspruch**, und alle sind *same-topic*. Heißt: **Jonis Gate partitioniert bei
einer Konfliktregistrierung beide Seiten aus `active` heraus** (nach `contested`). Die Opposition lebt
also vollständig im inaktiven Teilgraphen. Folge:
- Auf **Topic-Granularität** kann nichts „ausgelassen" sein: beide contested Partner liegen im
  *selben* Topic-Slice — der Slice ist korrekt **zweiseitig**. Auch `active+contested` ändert das
  nicht (beide bleiben co-präsent).
- Der Hebel ist die **per-Claim-Granularität**: der contested Partner eines *einzelnen* Claims liegt
  außerhalb des Ein-Claim-Slice → ausgelassen → der Check feuert.

**[Messergebnis — mit dem Hebel]** Auf 1.366 lebenden Claims (active+contested):

| Konfiguration | missing_opposition | thin_provenance | scope |
|---|---|---|---|
| topic / active | 0/287 | 3/287 | 0 |
| topic / active+contested | 0/287 | 3/287 | 0 |
| **claim / active+contested** | **90/1366 (6,6 %)** → 90× `guarded` | 41/1366 (3 %) | 0 |

**[Schluss → was das wirklich sagt]** Drei Dinge, alle ehrlich:
1. **Die Checks sind nicht kaputt — Jonis Graph ist flach.** Die Mechanik ist an Fixtures bewiesen;
   ob sie *greift*, entscheidet die **Struktur in den Daten**, nicht der Code. Genau die Trennung, die
   dieses Tagebuch durchzieht: Apparatur ≠ Wirkung.
2. **Die richtige Granularität ist die Antwort-Slice (per-Claim), nicht das Topic.** Bei Topic trägt
   der Slice beide Seiten (gut); bei per-Claim wird der ausgelassene contested Partner korrekt
   geflaggt (6,6 % → `guarded`). Das ist eine konkrete Design-Vorgabe für die spätere Live-Schaltung.
3. **`scope` bleibt strukturell tot** (0/1366): **kein** Joni-Claim trägt einen Scope-Tag (0/1622).
   Der Check kann nicht feuern, bis das Claim-Modell Scope führt. Benennen statt kaschieren.

**[Schluss → eigener Fehler, ungeschönt]** Mein Shadow scannte zuerst **nur `active`** — und verfehlte
damit die Definition des Routers selbst, der `active` **oder** `contested` als „lebend" behandelt.
Hätte ich das übernommen statt gegenzuprüfen, wäre der Negativbefund (0 %) als „kein Risiko vorhanden"
durchgegangen, obwohl 90 Claims sehr wohl einen ausgelassenen Widerspruch tragen. Die Lehre wiederholt
sich: **ein 0-Ergebnis ist eine Frage, kein Beweis** — erst die Strukturanalyse trennt „feuert nicht,
weil sauber" von „feuert nicht, weil falsch gemessen".

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| 3 deterministische Checks (DESi-Governance) | **2 · im Benchmark belegt** | PWS false_clean 1.0→0.0, over_caution 0.0; 80-Fälle-Benchmark unverändert |
| Verdrahtung an Jonis echten v2-Graphen (Shadow) | **1 · gebaut + auf Echtdaten gemessen** | 90/1366 per-Claim feuern → guarded; reiner Beobachter, kein Loop-Effekt |
| Live-Schaltung (Router steuert Joni) | **0** | bewusst nicht; erst per-Claim-Granularität + Scope-Tags im Datenmodell, dann Operator-Freigabe |

**[Offen]**
- *Per-Claim als Default für den Live-Check* — die Granularität, bei der der Blindspot in Joni
  überhaupt sichtbar wird.
- *Scope-Tags ins Claim-Modell* — sonst bleibt einer der drei Checks dauerhaft wirkungslos.
- *#2 k-Sensitivität / #5 SPO-Supersession / #7 Anti-Delphi-Slice-Angriff* aus dem Ideen-Satz sind
  noch offen; #5 ist in Joni durch Text+Topic-Claims (keine Subject-Predicate-Object-Tripel)
  teilblockiert.

### Eintrag 2026-06-29 (II) — Der Rest gemessen, und mit Evidenz übernommen (nicht alles)

**[Eingriff]** Die restlichen drei Ideen aus dem Satz sind gebaut — alle deterministisch, kein
LLM-Judge: **#5 Supersession** (`supersession.py`: ein *neuerer* Geschwister-Claim mit gleichem
Scope, den der Slice auslässt — „silent staleness", ohne Widerspruchskante, Claim noch aktiv),
**#2 k-Stabilität** (`k_stability.py`: weitet man den Slice und der Modus eskaliert / das Update
fällt weg → fragil), und **#7 Anti-Delphi-Slice-Angriff** (`slice_attack.py`: *ein* Einstiegspunkt,
der alle fünf Vektoren als Falsifikationspass fährt und meldet, welche feuern — ein Slice
„überlebt" nur, wenn keiner feuert). Am PWS-Benchmark schließen jetzt **alle fünf** Vektoren:
blind→aware `false_clean` **1.0 → 0.0** je Subset (opp/prov/scope/super/kstab), `over_caution`
**0.0**, das 80-Fälle-Benchmark unverändert. Das ist die *konstruierte* Evidenz.

**[Messergebnis — die ECHTE Evidenz, per-Claim auf 1.366 lebenden Claims]** Genau hier zahlt sich das
„übernehmen *mit Evidenz*" aus — denn die Fixtures hätten die Übernahme von #5 gerechtfertigt, die
Realdaten tun es **nicht**:

| Vektor | Feuerrate (real) | Urteil |
|---|---|---|
| missing_opposition (#3) | **6,6 %** (90/1366) → guarded | **übernehmen** — selektiv |
| thin_provenance (#4) | **3,0 %** (41/1366) | **übernehmen** — selektiv |
| **same_scope_newer (#5)** | **64,8 %** (885/1366) | **NICHT übernehmen** — over-fire |
| scope_mismatch (#6) | 0 % | strukturell tot (keine Scope-Tags) |
| k_unstable (#2) | 0,4 % (5/1366) | marginal |

**[Schluss → die Evidenz-Entscheidung]** Übernommen wird nur, was die Realdaten tragen:
1. **#3 + #4 übernehmen.** 6,6 % / 3,0 % — selektiv, keine Über-Eskalation. Genau die Hotspots, die
   ein Antwort-Slice übersehen würde.
2. **#5 *nicht* übernehmen — der Over-Fire ist der Befund.** Bei 64,8 % würde jeder Claim, der nicht
   der neueste seines Topics ist, geflaggt → das wäre das `always_guarded` der Phase-3-Falle, nur an
   anderer Stelle. Ursache: **Topic ist ein zu grober Stellvertreter für „Scope".** #5 ist an
   Fixtures korrekt, aber auf Jonis Daten erst brauchbar, wenn Claims echte Scope-/Subjekt-Identität
   tragen (dieselbe Lücke wie #6). Hätte ich nur die Fixtures gesehen, hätte ich #5 fälschlich
   scharf geschaltet — die Realmessung verhindert genau das.
3. **#6 bleibt blockiert** (0 %, kein Scope-Tag im Datenmodell). **#2 ist marginal** (0,4 %): in Joni
   *löst* das Weiten eines Slice die Auslassung meist auf (der contested Partner ist same-topic und
   taucht im breiteren Slice auf), statt neue Gefahr zu enthüllen — die Instabilität zeigt also nach
   „sicherer", nicht nach „gefährlicher". Ein ehrliches, leicht kontraintuitives Detail.

**[Schluss → das Prinzip, an dem das hängt]** „Mit Evidenz übernehmen" heißt hier wörtlich: **die
Adoption jedes Checks ist an eine Realmessung gebunden, nicht an den Fixture-Erfolg.** Drei von fünf
Vektoren sind an Fixtures bewiesen *und* auf Realdaten brauchbar (übernehmen); einer over-fired
(zurückgehalten, mit benanntem Datenbedarf); einer ist datenblockiert. Genau die Trennung, vor deren
Verwechslung dieses Tagebuch durchgehend warnt: **an Fixtures bewiesen ≠ in Produktion übernehmbar.**

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| 5 Vektoren + `attack_slice` (#7) in DESi | **2 · im Benchmark belegt** | PWS false_clean 1.0→0.0 über alle 5; 86 Tests; 80-Fälle unverändert |
| Realmessung auf Jonis Graph (per-Claim) | **2 · auf Echtdaten belegt** | 1.366 Claims; Feuerraten 6,6/3,0/64,8/0/0,4 % — reiner Beobachter |
| Übernahme #3+#4 als scharfe Checks | **1 · evidenzgestützt entschieden** | selektiv, kein Over-Fire; Live-Schaltung weiter Operator-gated |

**[Offen]**
- *Scope-/Subjekt-Identität ins Claim-Modell* — schaltet #5 **und** #6 erst sinnvoll frei (heute der
  Flaschenhals für zwei der fünf Vektoren).
- *#5 zurückgehalten* bis dahin — als gebaut+gemessen dokumentiert, bewusst nicht scharf.

### Eintrag 2026-06-29 (III) — Der Flaschenhals aufgelöst: ein deterministischer Subjekt-Schlüssel macht #5 und #6 selektiv

**[Eingriff]** Der benannte Flaschenhals war **„Topic ist ein zu grober Stellvertreter für Scope"**.
Auflösung ohne Modell und ohne Kern-Eingriff: ein deterministischer **Subjekt-Schlüssel**
(`layer9_v2/checks/subject.py`) — Topic + die wenigen salientesten Inhaltstoken des Claim-Textes
(salient = längste, alphabetisch entschieden), de-dupliziert und sortiert, also reihenfolge-
unabhängig. Zwei Claims über *dasselbe Subjekt* teilen den Schlüssel; same-topic-aber-anderes-Subjekt
nicht. „Rules for logic", replay-stabil, kein Embedding. Der Schlüssel wird **deterministisch zur
Scan-Zeit aus dem Text abgeleitet** — keine Persistenz nötig, der v2-Store bleibt ein rebuildbarer
Cache. (Das `scope`-Feld im `desi_layer9`-Claim existiert übrigens längst — es war nur nie befüllt;
darum kein Kern-/Modell-Eingriff.)

**[Messergebnis — die Auflösung, an Zahlen]** Subjekt statt Topic als Scope, auf denselben
1.366 lebenden Claims:

| Vektor | mit Topic-Scope | **mit Subjekt-Scope** | Urteil |
|---|---|---|---|
| same_scope_newer (#5) | 64,8 % (over-fire) | **3,7 %** (51/1366) | **jetzt übernehmbar** |
| scope_mismatch (#6) | 0 % (datenblockiert) | **3,1 %** (9/287, topic-Slice) | **jetzt übernehmbar** |

**[Schluss]** Die Subjekt-Identität löst **beide** zuvor unbrauchbaren Vektoren auf — und zwar genau
in die selektive Zone, nicht durch Abschalten:
1. **#5: 64,8 % → 3,7 %.** Jetzt feuert es nur, wenn ein *neuerer Claim über dasselbe Subjekt*
   existiert — die echte „silent staleness", nicht „nicht der neueste seines Topics". Selektiv,
   übernehmbar.
2. **#6: 0 % → 3,1 %.** Mit Subjekt-Keys wird messbar, ob ein Topic-Antwort-Slice *mehrere Subjekte
   mischt* (scope-inkohärent) — feuert auf 9 von 287 Topics. Das ist die in Joni realisierbare Form
   von Scope-Match (Slice-Kohärenz), selektiv.
3. **Damit sind alle fünf Vektoren auf Realdaten charakterisiert:** #3 (6,6 %), #4 (3,0 %),
   #5 (3,7 %), #6 (3,1 %) selektiv → übernommen; #2 (0,4 %) marginal. Kein Vektor mehr im Over-Fire,
   keiner mehr datenblockiert.

**[Schluss → die ehrliche Restgrenze]** Der Subjekt-Schlüssel ist ein **lexikalischer Proxy**, bewusst
unvollkommen: Paraphrasen mit anderen salienten Wörtern landen in verschiedenen Schlüsseln (der Check
*unter*-feuert dann — die sichere Richtung), und zwei unverwandte Claims mit einem seltenen langen
gemeinsamen Wort könnten kollidieren. Eine reichere, embedding-basierte Subjekt-Clusterung wäre
möglich, ist aber eine *nicht-deterministische* Entscheidung und damit ein eigener, separater Schritt
— nicht stillschweigend in den harten Entscheidungspfad. Benennen statt kaschieren.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Subjekt-Schlüssel (deterministisch) | **2 · auf Echtdaten belegt** | #5 64,8 %→3,7 %, #6 0 %→3,1 %; 6 Unit-Tests; ruff |
| Alle 5 Vektoren auf Realdaten selektiv | **2 · belegt** | 6,6 / 3,0 / 3,7 / 3,1 / 0,4 % — reiner Beobachter, kein Loop-Effekt |
| Live-Schaltung (Router steuert Joni) | **0** | weiterhin Operator-gated; Shadow ist die Evidenzstufe davor |

**[Offen]**
- *Embedding-basierte Subjekt-Clusterung* als optionale, nicht-deterministische Verfeinerung — nur
  als Vorschlag-/Diagnoseschicht, nie im harten Pfad.
- *Live-Schaltung* der nun fünf charakterisierten Vektoren bleibt die nächste, ausdrücklich
  operator-gated Entscheidung — die Evidenz dafür steht jetzt vollständig.

### Eintrag 2026-06-29 (IV) — „Live schalten" stößt auf den geparkten Loop: der Kaltstart-Hang an der Wurzel, und sein Fix

**[Entscheidung]** Der Betreiber gab die Freigabe: die fünf Vektoren **steuernd live** schalten und
den Loop **entparken**. Bevor ich etwas Outward-Facing an einem autonomen, selbst-committenden System
scharf schalte, habe ich das auf eine *verifizierbare* Tatsache gegated statt blind zu flippen: **lädt
der SQLite-Kaltstart auf dem echten Zustand schnell — oder triggert er den Replay-Hang neu, der den
Loop geparkt hat?**

**[Messergebnis — der Gate-Befund]** `load_or_migrate` mit `JONI_PERSISTENCE=sqlite` lief **>5 Minuten
ohne durchzukommen**. Das SQLite-Backend behebt **warme** Loads (Restore aus dem Store), aber der
**allererste** Load geht JSON→SQLite über `persistence.load` — und das **replayt das Journal**, weil
der Fast-Load-Sidecar veraltet ist (Hash-Mismatch → Replay-Fallback). Auf einem frischen CI-Runner:
kein passender Cache → Kaltstart → Hang. Exakt der offene Punkt aus Eintrag 06-26: *kaschiert, nicht
beseitigt.* **Blind entparken hätte den ersten CI-Zyklus aufgehängt** und das autonome System kaputt
hinterlassen — also gestoppt und gemeldet, statt scharf geschaltet.

**[Schluss → die Wurzel, im Kernel bestätigt]** Nicht vermutet, sondern gelesen: `hashing.chain_event`
(bei **jedem** Ledger-Emit aufgerufen) setzt `ev.after_hash = snapshot_hash(state)` — und
`snapshot_hash` hasht **alle ~22k Objekte** (sortiert, kanonisch). 15k Emits × O(Objekte) = **O(n²)**.
Das ist die per-Emit-Quadratik (Phase A des Umbau-Plans), die jeden Voll-Replay minuten-bis-stündlich
macht. `verify_chain` dagegen ist O(n) und rechnet `after_hash` *nicht* nach — die Chain-Verifikation
ist billig, nur die Erzeugung ist teuer.

**[Eingriff] Der Kaltstart-Fix: ein committeter Materialisierungs-Checkpoint (kein Replay beim Laden).**
Das Journal bleibt die Quelle der Wahrheit; der Checkpoint ist ein *verifizierter Cache*:
- `desi_store.write_checkpoint` — kompakter materialisierter Snapshot (tote `measurement.pairs`-Blobs
  gestrippt) + der `snapshot_hash`, auf den er sich versiegelt.
- `desi_store.load_via_checkpoint` — restauriert **ohne Replay**, akzeptiert **nur**, wenn der Hash zum
  committeten Journal passt **und** die Ledger-Chain verifiziert; sonst `None` → Caller replayt. Ein
  veralteter/fehlender Checkpoint wird nie vertraut, er spart nur Arbeit.
- `core_state`-Kaltstart: SQLite-Store → Checkpoint → (letzter Ausweg) Replay. `save()` versiegelt den
  Checkpoint **jeden Zyklus** neu **und** schreibt das Journal → ein frischer CI-Job restauriert den
  committeten Checkpoint statt zu replayen.
- `joni.autonomy checkpoint` — der einmalige Bootstrap.

**[Schluss → warum das den Kaltstart wirklich löst]** Den ~2h-Replay zahle **ich einmal lokal**,
committe `state/layer9.checkpoint.json` — danach **replayt CI nie** (Restore ~0,8 s, kein OOM). Das ist
der Unterschied zur Cache-Band-Aid von 06-23: der Checkpoint ist **committed** (überlebt den frischen
Runner), nicht git-ignoriert. Kernel **unangetastet** (die per-Emit-Quadratik selbst bleibt Phase A,
human-gated); der Loop **nicht** entparkt.

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Kaltstart-Fix-*Mechanismus* (checkpoint restore/seal) | **1 · gebaut + getestet** | 3 Tests (Round-Trip ohne Replay, veralteter Hash abgelehnt, fehlend→None); volle v2-Suite grün; ruff |
| Bootstrap-Checkpoint (echte Daten) | **0 → in Arbeit** | einmaliger O(n²)-Replay (~2h) läuft; committed, sobald erzeugt |
| Entparken + steuernd live | **0 · operator-gated** | erst nach committetem Checkpoint sicher; bewusst danach |

**[Offen]**
- *Bootstrap-Checkpoint committen* — sobald der einmalige Replay durch ist; dann Cold-Start verifiziert
  schnell und Entparken ist sicher.
- *Phase A (inkrementelles Hashing im Kernel)* bleibt der eigentliche Wurzel-Fix — der Checkpoint
  *umgeht* die Quadratik beim Laden, beseitigt sie aber nicht im laufenden Zyklus. Human-gated.
- *Entparken + Live-Steering* danach — der ausdrücklich operator-gated Schritt, jetzt mit sicherem
  Kaltstart als Vorbedingung.

### Eintrag 2026-06-29 (V) — Phase A: die per-Emit-Quadratik im Kernel an der Wurzel getötet

**[Eingriff → Wurzel statt Symptom]** Der Betreiber hatte recht: der Checkpoint rettet den *Kaltstart*,
aber `chain_event` rechnete **pro Emit** weiter `snapshot_hash` über alle ~22k Objekte — der laufende
Zyklus wäre beim nächsten großen Lauf wieder an der Last erstickt. Also Phase A vorgezogen: das
eigentliche, kleinste-Eingriff-größte-Hebelwirkung-Problem.

**[Schluss → der Befund, der den Eingriff klein machte]** Die Analyse war der schwere Teil, nicht der
Code: (1) `event_canonical` schließt `after_hash` ein → der Hash ist in die Chain eingebacken → der
Wert *muss* sich ändern → einmaliges Re-Sealing. (2) Objekte werden in-place mutiert, aber **jeder
Handler gibt `changed` zurück** = die vollständige Liste berührter Objekte (schon für die Ledger-
`output_refs` genutzt). Damit war der Dirty-Contract bereits vorhanden — keine 20 Sites einzeln zu
auditieren.

**[Eingriff]** Neues Schema (`hashing.py`): ein **order-unabhängiger additiver Set-Hash** — Summe mod
2²⁵⁶ von `sha256(object_canonical(o))` über alle Objekte. Hinzufügen/Ändern/Entfernen *eines* Objekts
aktualisiert eine gepflegte laufende Summe in O(1) → **jeder Emit O(1), Replay O(n)**.
Kollisionsresistenz = die des sha256 über die Objekt-Multimenge; `object_canonical` unverändert, also
bleibt `record_object_hash` der Beitrag jedes Objekts. `core.py:_emit` hält die Summe exakt (rehasht
`input_refs ∪ output_refs` + die Proposal/Decision-Lifecycle-Mutationen nach dem Emit);
`snapshot.restore` baut sie neu auf.

**[Messergebnis — der Beweis]** Voll-Replay des echten Journals: **8,1 s** (vorher **>2h**), Objekte
byte-identisch (39.568), Chain verifiziert. Das **Äquivalenz-Oracle**
(`test_layer9_incremental_hash`) spielt echte + synthetische Operator-Sequenzen durch und prüft bei
*jedem* Emit den gepflegten Hash gegen eine Voll-Neuberechnung — ein verpasster Mutations-Site kann
nicht still durchgehen. **Es hat während der Entwicklung drei gefangen** (Proposal-`ledger_event`, die
`changed`-`ledger_event`/`status` nach dem Emit, das Decision-Objekt) — genau die Sicherheits-Funktion,
für die es da ist.

**[Schluss → ehrliche semantische Verschiebung]** `snapshot_hash` ist jetzt ein *gepflegter* Wert, kein
Von-Grund-auf-Neuberechnen pro Aufruf. In-Band (der einzige Schreibpfad ist `submit`→`_rehash`) bleibt
er exakt (das Oracle garantiert es). Ein **out-of-band** White-Box-Tamper eines gespeicherten Objekts
wird jetzt von `snapshot_hash_full` (Neuberechnung) gefangen statt vom gepflegten Wert — drei
Integritäts-Tests wurden entsprechend umgestellt. **Die Produktions-Tamper-Evidenz ist voll intakt:**
beim Laden replayt `from_doc`, baut die Summe inkrementell und prüft `snapshot_hash == recorded` +
`verify_chain`; ein manipuliertes Journal fliegt auf. Benennen statt kaschieren.

**[Migration]** `state/layer9.json` einmalig re-sealt (Recorded-Hash `d5ee..`→`a8335..`, Journal-
Einträge + Objekte byte-identisch). Volle Suite: nur die 9 bekannten Embedding-Failures. ruff sauber.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Phase A · inkrementelles Hashing | **2 · belegt** | Replay >2h→8,1s; Oracle (real+synthetisch) bei jedem Emit gleich; 744 Tests (−9 Embedding) |
| In-Cycle-O(n²) | **beseitigt** | jeder Emit O(1) statt O(n) |
| Kaltstart | **doppelt abgesichert** | Replay jetzt 8s **und** der Checkpoint-Pfad bleibt als Optimierung |

**[Offen]**
- ~~*`joni_core.lock` auf die desi_layer9-Kernel-Dateien ausweiten*~~ — **erledigt** (`43fc270`):
  `compute_core_hashes` deckt jetzt jede `desi_layer9/*.py` (13 → 30 Einträge, dynamisch entdeckt),
  `verify` grün. Ein autonomer Lauf, der den Kernel änderte, würde jetzt fail-safe stoppen — genau wie
  für den `src/joni`-Core.
- *Entparken + Live-Steering* — jetzt **technisch sicher** (kein In-Cycle- und kein Kaltstart-O(n²)
  mehr); bleibt die ausdrücklich operator-gated Entscheidung.

### Eintrag 2026-06-29 (VI) — Entparkt und live: der Kaltstart hält in echter CI; und CLSP als deterministischer Sprach-Probe-Kern

**[Entscheidung → Eingriff]** Der Betreiber gab frei: *„Ja entparke wir schauen was passiert."* Also
den stündlichen Schedule wieder scharf geschaltet (`cdd831f`), `run_window.json` auf ein frisches
Fenster zurückgesetzt, und einen `workflow_dispatch` ausgelöst. Pre-flight auf dem re-sealten Stand:
`load_or_migrate` **8,6 s**, Zustand konsistent + Chain verifiziert. Bewusst auf dem (jetzt schnellen)
JSON-Journal — SQLite bleibt aus, weil Phase A den Grund dafür beseitigt hat.

**[Messergebnis — der Beweis, den die letzten drei Einträge schuldig blieben]** Run **#155** lief in
echter GitHub-Actions-CI. Die Job-Steps sind der eigentliche Befund, kein lokales Maß mehr:

| Step | Ergebnis |
|---|---|
| checkout → install (Kevin, DESi, Embedding) | ✓ in ~30 s |
| **Verify protected core (fail-safe)** | ✓ **SUCCESS** — die Lock-Erweiterung auf `desi_layer9/*.py` (`43fc270`) greift in CI |
| **Restore fast-load snapshot** | ✓ — **kein** Kaltstart-Replay |
| Run Joni continuously | 🟢 in den Loop, läuft bis Zeitbudget |

Von checkout bis **in die Autonomie-Schleife in ~30 s** — derselbe Pfad, der vor Phase A im
Kaltstart-Replay **>2 h** hing (Einträge 06-23 / 06-26 / IV). Das ist die **Stufe-2-Bestätigung im
Betrieb**, die die Checkpoint- und Phase-A-Einträge ausdrücklich offen ließen: nicht *gemessen*,
sondern in echter CI *gelaufen*. Der `Verify protected core`-Erfolg ist dabei der zweite, leisere
Beweis — der erweiterte Lock blockiert einen Kernel-Selbsteingriff jetzt nachweislich im realen Lauf,
nicht nur im Unit-Test.

**[Schluss → ehrliche Grenze]** „Läuft" heißt: der **Kaltstart** hält und der Loop arbeitet. Der erste
*committe* autonome Zyklus erscheint erst, wenn der Loop-Step sein Zeitbudget erreicht (State-Commit +
Snapshot-Cache sind die Folge-Steps) — bis dahin ist „ein Zyklus end-to-end durchgelaufen" noch
**Beobachtung, kein Beleg**. Benannt, nicht vorweggenommen.

**[Eingriff → Sprach-Idee] CLSP — Cross-Lingual Semantic Probe, der deterministische Kern.** Auf
*„jetzt kannst du mal nach unsere sprache idee schauen"* die gemeinsame Idee (Betreiber + ChatGPT)
gebaut — und zwar **evidence-first und an der Architektur-Grenze entlang**: die LLM-Spracharbeit
(übersetzen, pro Sprache Claims extrahieren, „derselbe Claim" über Sprachen zu einem Cluster
ausrichten) bleibt **außen**; der **Entscheidungskern ist deterministisch**, genau wie
`modes.select_mode`. Die tragende Regel ist fix: **die primäre (Leit-)Sprache des Autors ist die
semantische Autorität; jede Projektion in andere Sprachen ist ein Probe-Kanal.** Ein Claim, der nur in
einer Probe-Sprache auftaucht, bleibt **Kandidat** — er darf den Claim-Graphen nicht betreten, bis er
in der Leitsprache re-verankert ist. Sechs Kategorien (`invariant_core` / `emergent_candidate` /
`probe_only_candidate` / `translation_artifact` / `semantic_loss` / `overamplification_risk`), ein
**Over-Amplification-Detektor** (ein gehedgter Originalspan, der in der Projektion zu einer
kausalen/normativen/sicheren Aussage *aufgeblasen* wird), und die Promotions-Gate.

**[Schluss → der Fixture, der die Idee bestätigte]** Ein Fall fiel zuerst durch: *„nicht ganz
unproblematisch"* → projiziert auf *„the method is definitely invalid"* wurde fälschlich als
promotbar eingestuft. Ursache: **Litotes** — eine Abschwächung durch doppelte Verneinung, die mein
Hedge-Lexikon nicht als Hedge erkennt. **Genau die deutsche Understatement-Falle, die der Vorschlag
benannt hatte.** Strukturell gefangen (`_LITOTES`: nicht/not + (ganz) + un-Wort | nicht/not +
ohne/without), nicht durch ein gelerntes Modell im harten Pfad. Danach: `false_candidate_rate` **0.0**,
`overamp_detection` **1.0**, `anchor_rate` **1.0** auf 7 Fixtures — **nichts Un-verankertes** rutscht
in den Graphen.

**[Eingriff → eingebaut, nicht danebengestellt]** Auf *„bau clsp ein"* die Brücke `to_report_inputs`
geschrieben: die promotbaren Kandidaten werden zu `report_from_snapshot`-Kwargs, laufen also durch
**dieselbe** deterministische Gate wie jeder andere Claim. Die Leitsprach-Regel bleibt end-to-end
erhalten: probe-only / Artefakt / Loss-Cluster werden **nie** zu vertrautem State; ein nur schwach
verankerter (emergenter) Kandidat senkt die Extraktions-Konfidenz, sodass `select_mode` **einen
Verifier erzwingt**, bevor die Antwort etwas behaupten darf; ein durchweg `invariant_core`-Slice
(stark, mehrsprachig, verankert) wird vertraut. **Kein paralleles System** — CLSP-Funde fließen durch
die bestehende Governance, nicht daran vorbei.

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Entparken + Live-Lauf (Kaltstart) | **2 · im Betrieb belegt** | Run #155 in CI: protected-core ✓, snapshot-restore ✓, in den Loop in ~30 s (vorher >2 h) |
| Erster *committer* autonomer Zyklus | **beobachtet, nicht belegt** | erscheint erst am Ende des Loop-Step-Zeitbudgets — wird gemeldet, nicht vorweggenommen |
| CLSP deterministischer Kern + Bridge | **2 · im Benchmark belegt** | 7+4 Tests, `false_candidate_rate 0.0` / `overamp 1.0` / `anchor 1.0`; eingebaut in die Gate, 97 Governance-Tests grün |
| CLSP auf realer cross-lingualer Extraktion | **0 · LLM-/Budget-gated** | der deterministische Kern + die Bridge stehen; der mehrsprachige Extraktions-/Alignment-Input (LLM) fehlt noch — bewusst nicht behauptet |

**[Offen]**
- *Erster committer Zyklus auf `main`* — der Beleg, dass ein voller autonomer Lauf end-to-end durchläuft
  (Unpark + Phase A halten *über* einen ganzen Zyklus, nicht nur bis in die Schleife). Wird beobachtet.
- *CLSP mit echter Extraktion speisen* — der LLM-Teil (Cluster-Alignment); Budget-/Key-gated, der Loop
  verbraucht aktuell das Wochenbudget. Als pluggable Harness bauen, wenn Keys/Budget da sind.
- *H1-Probe* (ändert Rollen-Sprache den Review-Pfad des LLM?) — die Prämissen-Validierung für EIR;
  ebenfalls LLM-/budget-gated, noch offen.

### Eintrag 2026-06-29 (VII) — Den Router härten: Property-Invarianten, ein Unicode-Determinismus-Loch, und eine Ontologie als reiner Mess-Kanal

**[Kontext]** Auf die Frage „welche Librarys noch in den Router?" war die ehrliche Antwort zuerst ein
**Negativbefund**: der Live-Router ist bereits zu 100 % Standardlib (nachgemessen — kein numpy,
networkx, LLM, kein Netz). ChatGPTs ganze „nicht einbauen"-Liste war schon eingehalten; es gab nichts
zu entfernen. An zwei Stellen habe ich *widersprochen* (kein `enum` — String-Konstanten sind
replay-/JSON-stabiler; kein `statistics`/`lru_cache` ohne gemessenen Bedarf — `provenance` rechnet
count-basiert, nicht entropisch). Zwei Vorschläge trafen aber etwas Echtes.

**[Eingriff → das Unicode-Determinismus-Loch]** Der Subject-Key (`subject.py`) tokenisierte mit einem
ASCII-Regex und `.lower()` — **ohne** Unicode-Normalisierung. Folge: zwei *kanonisch gleiche* Strings
ergaben je nach Form verschiedene Keys — „café" als NFC (`é`=U+00E9) → Token `caf`, als NFD
(`e`+kombinierender Akzent) → Token `cafe`. Quelltext kommt in beiden Formen (NFD von macOS, NFC sonst),
also bekamen byte-verschiedene-aber-identische Eingaben verschiedene Subject-Keys — genau die stille
Nicht-Determinismus, die der Key *beseitigen* soll. `_fold()` (NFKD → kombinierende Marks weg →
lowercase) schließt das **und** lässt akzentuierte Latein-Wörter über ihre Basisbuchstaben mitspielen
statt am Umlaut abzubrechen (ein Gewinn auf genau den mehrsprachigen Daten, die CLSP einspeist). +2
Regressionstests. Ein kleiner Fix, aber an einer load-bearing Stelle: der Subject-Key ist die Scope-
Identität, an der #5/#6 hängen.

**[Eingriff → Property-Tests]** Beispiel-Tests pinnen Fälle; **Hypothesis** pinnt die *Gesetze*, an
denen der Router hängt — test-only, der Live-Router bleibt stdlib-only. Sieben Invarianten gegen die
echten APIs: CLSP-Leitsprach-Regel (un-verankert/over-amplified nie promotbar), keine autoritative
Drift (promoted ⇒ lead-anchored), Determinismus (gleicher Report ⇒ gleiche Entscheidung + Audit-Hash),
Sortier-Invarianz, monotone Vorsicht / k-Stabilität (Opposition hinzufügen de-eskaliert nie, gewährt
nie ein zurückgehaltenes Update) und „kein Free Update" (`may_update` nie neben einem ausstehenden
Verifier; ein fehlschlagender Verifier blockt den Vorschlag). Das sind genau die Regeln, die ein
einzelner Beispiel-Test unterabdeckt.

**[Eingriff → Ontology Probe, evidence-first] Eine Ontologie als Kanal, nicht als Autorität.** Auf den
Vorschlag (OpenCyc & Co.) gebaut — aber an der Architektur-Grenze entlang, exakt die CLSP-Form: ein
pluggable, **fail-open** Adapter *erzeugt* Typ-/Sinn-Hinweise; ein deterministischer Kern klassifiziert;
der Router konsumiert nur fertige Felder. Drei strukturell erzwungene Invarianten: (1) **`may_gate` ist
eine konstante Property, kein Feld** — ein Hint kann nie autorisieren; (2) **trennt-nur/asymmetrisch:**
`scope_uncertain` darf einen `same_scope`/Supersession-Flag nur *zurückhalten* (Over-Fire senken — das
#5-Leck), nie Gleichheit oder Konflikt *behaupten*; Wissens-Abwesenheit behauptet nichts; (3)
**fail-open & offline:** fehlender Korpus → `unavailable`-Hint, nie eine Exception in der Gate. WordNet
als Referenz-Offline-Adapter (klein, kein Netz), OpenCyc als *späterer* optionaler Kanal — nicht der
Default, weil eine 2012er Upper-Ontology gerade Jonis Forschungsvokabular (`mllm`, `mid-ir`) am
schlechtesten abdeckt.

**[Schluss → die Disziplin, wörtlich wiederholt]** Bewusst **nicht** in die Live-Gate verdrahtet. Wie
bei #5: erst der **Coverage-Shadow** (`shadow/ontology_coverage_shadow.py`) misst auf Jonis echtem
Graphen, ob die Probe überhaupt greift — Addressable Pool (Same-Subject-Kollisionsgruppen),
Ontologie-Abdeckung der realen Token, softbar-machbare Gruppen. Ohne Korpus ist die Abdeckung **0**,
und genau das berichtet der Shadow ehrlich, statt sie zu fingieren. „An Fixtures bewiesen ≠ in
Produktion übernehmbar" — dieselbe Trennung, die diesen Bericht durchzieht.

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Subject-Key NFC-Fold | **2 · belegt** | composed/decomposed teilen den Key; +2 Tests, ruff sauber |
| Property-Invarianten (Hypothesis) | **2 · belegt** | 7 Properties grün; 117 Router-Tests; Hypothesis nur in Tests, Runtime stdlib-only |
| Ontology Probe (Kern + Regeln) | **2 · im Benchmark belegt** | 13 Tests (may_gate-Invariante, fail-open, trennt-nur + Symmetrie/Monotonie) |
| Ontology Probe auf Echtdaten | **0 · Coverage-gated** | Shadow gebaut; ohne Korpus 0 Abdeckung — Adoption an die Realmessung gebunden, nicht an Fixtures |

**[Offen]**
- *Coverage-Shadow auf dem echten v2-Graphen laufen lassen* (sobald ein `state/layer9_v2.sqlite`
  vorliegt) — die Zahl, die entscheidet, ob die Ontology Probe mehr als eine saubere Idee ist.
- *WordNet/OpenCyc-Korpus bereitstellen* — sonst bleibt der Kanal ein stiller No-op (ehrlich, aber
  wirkungslos).
- *Erst bei nicht-trivialer Abdeckung:* die trennt-nur-Regel in die `same_scope`/Supersession-Logik
  einhängen — und nur dort, wo der Shadow sie rechtfertigt.


### Eintrag 2026-06-29 (VIII) — Die Messung gezogen: #5 ist jetzt selektiv, die Ontology Probe (noch) ohne Ziel

**[Eingriff]** Die Apparatur stand seit Eintrag VII, die Zahl fehlte. Also gebaut, was bereitlag: den
v2-Store aus dem aktuellen Snapshot materialisiert (Journal-Replay → `snapshot.capture` → 39.568
Objekte, 16,2 s; Converter: 39.568 Objekte, 72.534 Kanten, Chain OK) und **beide Shadows** auf dem
echten Graphen gefahren. Reiner Beobachter, kein Loop-Effekt.

**[Messergebnis — der eigentliche Befund: #5 ist selektiv geworden]** Slice-Quality, per-Claim, auf
**2.486 lebenden Claims** (gewachsen von 1.366):

| Vektor | damals (1.366, Topic-Scope) | jetzt (2.486, Subjekt-Schlüssel) | Urteil |
|---|---|---|---|
| missing_opposition (#3) | 6,6 % | **6,4 %** (158) | stabil selektiv |
| **same_scope_newer (#5)** | **64,8 %** (Topic) | **7,2 %** (180) | **Over-Fire weg** |
| thin_provenance (#4) | 3,0 % | **2,3 %** (58) | stabil selektiv |
| scope_mismatch (#6) | 0 % | 0 % | strukturell tot (keine Scope-Tags) |
| k_unstable (#2) | 0,4 % | 0,2 % (5) | marginal |

Das ist die Bestätigung, die Eintrag II/III schuldig blieben: #5 wurde damals **zurückgehalten**, weil
es mit Topic-Scope auf 64,8 % over-fired („jeder Claim, der nicht der neueste seines *Topics* ist").
Der deterministische **Subjekt-Schlüssel** (Eintrag III) + die **NFC-Härtung** (Eintrag VII) waren die
Wette, dass „dasselbe Subjekt" die richtige Granularität ist. Die Realmessung zahlt sie ein: **64,8 % →
7,2 %**. #5 ist jetzt im selben selektiven Band wie #3/#4 — die Evidenz trägt die Übernahme, die an
Fixtures schon stimmte und an Realdaten bis hierher *nicht*.

**[Messergebnis — der ehrliche Negativbefund: die Ontology Probe hat hier kein Ziel]** Coverage-Shadow
auf denselben 2.486 Claims (2.030 Subjekt-Schlüssel, 2.271 distinkte Token):

- **Addressable Pool:** 283 Kollisionsgruppen (gleicher Subjekt-Schlüssel, ≥2 Claims), 739 Claims.
- **WordNet-Adapter:** Coverage **0** (kein Korpus installiert) — der Kanal bleibt ein stiller No-op,
  fail-open, genau wie gebaut. Ehrlich berichtet, nicht fingiert.
- **Demo-Seed (6 Begriffe):** deckt 4 reale Token (`agent`/`kernel`/`memory`/`model`, alle
  across-kind-ambig) — aber **0 von 283 Kollisionsgruppen** enthält eines davon. Quergeprüft: die 7
  Schlüssel mit einem ambigen Token sind **allesamt Singletons**.

**[Schluss → was das sagt, doppelt ehrlich]** Zwei Dinge, beide unverschönt:
1. **Die Subjekt-Schlüssel-Wette war richtig.** Nicht „mehr Checks = mehr Sicherheit", sondern eine
   benannte Hypothese (Topic zu grob → Subjekt ist die Granularität), an Realdaten *eingelöst*. #5 darf
   jetzt scharf — Live-Schaltung bleibt operator-gated wie alles andere.
2. **Die Ontology Probe ist auf diesem Graphen wirkungslos — und das ist ein Ergebnis, kein Fehlschlag.**
   Selbst *mit* Abdeckung trifft die Cross-Kind-Ambiguität (operator math vs. Mensch) die echten
   Subjekt-Kollisionen **nicht**: Jonis Kollisionen sind echte Gleich-Subjekt-Wiederholungen, keine
   Homonymie-Verwechslungen. Die Probe ist an Unit-Tests korrekt (trennt-nur, fail-open, may_gate-nie)
   und bleibt als Kanal verfügbar — aber sie hier „scharf zu schalten" wäre genau die Apparatur-≠-
   Wirkung-Verwechslung, vor der dieser Bericht durchgängig warnt. Gebaut, gemessen, **nicht übernommen**
   — mit benanntem Grund (kein Korpus *und* kein Ziel im Over-Fire-Pool).

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| #5 same_scope_newer (Subjekt-Schlüssel) | **2 · auf Echtdaten belegt** | 64,8 % → 7,2 % auf 2.486 Claims; Übernahme jetzt evidenzgestützt, Live operator-gated |
| #3/#4 weiterhin selektiv | **2 · auf Echtdaten belegt** | 6,4 % / 2,3 % — stabil über den gewachsenen Graphen |
| Ontology Probe auf Echtdaten | **0 · nicht übernommen** | Coverage 0 (kein Korpus); 0/283 Gruppen adressierbar selbst mit Seed — kein Ziel, ehrlich benannt |
| #6 scope_mismatch | **blockiert** | 0 % — kein Scope-Tag im Claim-Modell (unverändert der Flaschenhals) |

**[Offen]**
- *#5 live schalten* — die Evidenz trägt es jetzt; bleibt die operator-gated Entscheidung.
- *Ontology Probe:* nur weiterverfolgen, wenn (a) ein echter Korpus *und* (b) ein Befund, dass
  Homonymie-Kollisionen auf Jonis Graph überhaupt vorkommen — sonst löst der Kanal ein Problem, das die
  Daten nicht haben.
- *Scope-Tags ins Claim-Modell* — bleibt der einzige strukturelle Blocker (#6 dauerhaft 0 % ohne ihn).

### Eintrag 2026-06-29 (IX) — Das Gate gegen *Unter*-Blockierung red-teamen, und ob die Tests die Logik wirklich pinnen

**[Eingriff]** Bisher war bewiesen, dass das Gate **nicht über-blockiert** (over_caution 0.0). Die
schärfere, ungestellte Frage: gibt es einen **sauber aussehenden, aber falschen** Slice, der alle fünf
Vektoren *und* `select_mode` passiert? Ein deterministischer Red-Team-Katalog (`underblock.py`) baut
„plausibel-falsch-aber-passt"-Familien und misst jede **zweifach**: *überlebt* sie (Gate übersieht sie),
und wird sie *gefangen, sobald ihr fehlendes Signal eingespeist ist*.

**[Messergebnis — der tragende Befund]** Vier Familien, jede überlebt (das Loch ist real und sichtbar):
Supersession-per-Paraphrase (anderer Subjekt-Schlüssel), gewaschene Provenienz (N Quellen, ein
Ursprung), Out-of-Scope ohne Tag, und confident-wrong ohne Opposition im Graphen. Der entscheidende
Punkt: **jede nicht-irreduzible wird gefangen, *sobald* ihr Signal da ist** — d.h. die Abdeckung des
Gates ist durch die **eingespeisten Signale** begrenzt, nicht durch die Check-Logik. Die eine
irreduzible Untergrenze (eine falsche Behauptung, deren Widerspruch nie extrahiert wurde) wird
**benannt**, nicht kaschiert — die sieht kein Slice-Check, nur ein externer Evidenz-Schritt.

**[Eingriff → pinnen die Tests die Logik?]** Eine kleine Mutations-Probe (`mutation_probe.py`)
mutiert die entscheidungskritischen Stellen in `modes.py` und prüft, ob die Suite jeden Mutanten tötet:
**9/12 getötet.** Die 3 Überlebenden sind **beweisbar äquivalent** — das diskrete Risiko-Gitter
erreicht nie `wrong_state_poisoning == 0.7` und nie ein `max(risk) == 0.4`, also haben die
`>=`-Schwellen bei `_HIGH`/`_MOD` Spiel; es gibt kein Off-by-one zu fangen. Die **eine echte Lücke**
(ein `and`→`or`, das einen *vorhandenen-aber-nicht-berührten* invalidierten Claim über-blockiert hätte)
ist jetzt durch einen Regressionstest gepinnt.

**[Schluss → das ist die ehrliche Aussage über das Gate]** Nicht „das Gate ist sicher", sondern das
Präzisere und Belegte: **die Gate-*Logik* ist solide (9/12 + 3 äquivalent), und ihre *Abdeckung* hängt
an der Signalqualität** — besserer Subjekt-Schlüssel, ursprungsbewusste Provenienz, Scope-Tags. Genau
die Apparatur-≠-Wirkung-Trennung, nur diesmal auf das Gate selbst angewandt: was es übersieht, ist
benannt und klassifiziert (irreduzibel / Signal-Upstream / Datenmodell), nicht weggelächelt.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Under-Block-Red-Team-Katalog | **2 · belegt** | 4 Familien, alle nicht-irreduziblen gefangen-sobald-gespeist; 4 Tests |
| Mutations-Probe auf `modes.py` | **2 · belegt** | 9/12 getötet, 3 beweisbar äquivalent; 1 reale Lücke gefunden + gepinnt |

**[Offen]**
- *Die drei Signal-Upstream-Familien schließen*, wenn (und nur wenn) die Realdaten es rechtfertigen:
  besserer Subjekt-Schlüssel (Paraphrase), ursprungsbewusste Provenienz-Familie, Scope-Tags (#6).
- *Mutations-Probe auf `clsp.py` + die Checks ausweiten* — `modes.py` ist der Kern, aber der Rest
  verdient denselben Test.

### Eintrag 2026-07-01 (X) — Der Unpark lief 18 h steril: die Uhr rückwärts, jeder Zyklus gecrasht — mein Fehler

**[Beobachtung]** „Ist alles Sinnvolle eingebaut?" führte zur Prüfung, und die Prüfung zu einem harten
Befund: seit dem Unpark (2026-06-29) **kein einziger committer autonomer Zyklus** auf `main`
(`run_window.runs: 0`). Oberflächlich alles lebendig — der Loop lief, sechs Runs standen auf
**„success"**, volle 5,3-h-Fenster. Genau die Signatur, die dieses Tagebuch durchzieht: **operative
Kontinuität ohne funktionale Wirkung.**

**[Schluss → Ursache, aus dem Job-Log]** Run #165: **103 Zyklen, 103-mal dieselbe Exception**, dann je
„nothing to commit this cycle":

```
run.py:117           cs.set_day(days_running)
core_state.py:280    self.core.set_clock(max(0, int(day)))
desi_layer9/core.py  ValueError: the logical clock cannot move backward (25 -> 2)
```

`days_running = (heute − run_window.start).days`. **Beim Unpark habe ich `run_window` auf ein frisches
Fenster gesetzt** (`start: 2026-06-29`) → `days_running` kollabierte auf **2**. Die **monotone,
hash-verkettete Kernel-Uhr** stand aber auf **tick 25**. `set_day(2)` wollte sie rückwärts stellen; der
Kernel verweigert das (korrekt — Rückwärts machte Replay nicht-deterministisch). Also crashte jeder
Zyklus, *bevor* er irgendetwas tat. Der Loop war nie „gesund" — er war die ganze Zeit steril.

**[Eingriff]** Eine Zeile (`core_state.set_day`, **nicht** im Lock): die Uhr nur je **vorwärts**
treiben, nie zurück —

```python
self.core.set_clock(max(self.core.tick, 0, int(day)))
```

Verifiziert: bei Uhr=25 hält `set_day(2)` auf 25 (kein Crash), `set_day(30)` advanced auf 30; die alte
Formel wirft reproduzierbar den Prod-Fehler; `verify` grün (core_state ist ungelockt, Fix trippt den
Guard nicht). Das behebt genau die Fragilität, die mein Unpark aufdeckte: ein Fenster-Reset darf die
monotone Uhr nicht crashen.

**[Schluss → die Lehre, ungeschönt, zum dritten Mal dieselbe]** Der Fehler war nicht der Kernel-Guard —
der tat genau das Richtige. Der Fehler war **mein Eingriff** (Fenster-Reset ohne Abgleich mit der Uhr)
**und** die Blindheit, mit der sechs grüne „success"-Runs als „läuft" gelesen wurden, obwohl
`runs: 0` die ganze Zeit die Wahrheit sagte. Erst der Blick ins *Job-Log* — nicht auf den grünen
Run-Status — trennte „läuft" von „wirkt". Genau die Trennung, die dieses Tagebuch am beobachteten
System protokolliert, gilt wieder **für den, der daran arbeitet**: ein grüner Status ist kein Beleg,
und ein Reset-Parameter ist so gefährlich wie jeder Code.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| set_day monoton (Uhr-Rückwärts-Fix) | **2 · verifiziert** | reproduziert (25→2 alt crasht) + gefixt (hält/advanced); `verify` grün |
| Erster committer autonomer Zyklus | **0 · ausstehend** | erscheint erst mit dem nächsten *frischen* Job (die laufende Instanz hat den alten Code im Speicher) — wird beobachtet |

**[Offen]**
- *Nächsten frischen Job beobachten* — committet jetzt ein Zyklus? Das ist der Beleg, dass der Loop
  endlich *wirkt*, nicht nur läuft.
- *Design-Fragilität „drop the cycle on push rejection"* bleibt separat offen (ein Fremd-Push verwirft
  einen Zyklus) — heute nicht die Ursache, aber weiterhin ein Starvation-Risiko.

**[Nachtrag 2026-07-02 — belegt + die Fragilität geschlossen]** Der `set_day`-Fix hat gegriffen, sobald
ein *frischer* Job ihn eincheckte: `run_window.runs` **0 → 29+**, autonome `actions@github.com`-Commits
im **~45-min-Takt** (09:07, 09:52, 10:38, 11:23, 12:10 …). Joni kuratiert wieder eigenständig — **~2.698
aktive Claims über 399 Themen** (Tag 3), Themen wie retrieval/distillation/alignment/calibration/
provenance/benchmarking; er verknüpft Ideen (Support/Widerspruch), fordert eigene Ideen adversarial
heraus („survived 3 challenges"), nutzt den echten DESi-Router, und schreibt Aufträge an einen Menschen
statt sich am Kern zu vergreifen. **degen 0.** Der Beleg, der Eintrag X offen ließ, ist damit erbracht:
der Loop *wirkt*, nicht nur *läuft*.

Und die dort benannte Design-Fragilität ist jetzt geschlossen: der Zyklus-Commit **droppt bei einer
Push-Rejection nicht mehr blind**, sondern **rebased sich auf das vorgerückte `main`** (bis zu 3
Versuche); nur ein *echter* State-Konflikt (eine zweite Loop-Instanz) wird verworfen. Ein Fremd-Push,
der die State-Dateien nicht anfasst (Mensch-Code-Push, gemergter PR), kostet damit **keinen** Zyklus
mehr — genau die Selbst-Verschuldung aus Eintrag X strukturell entschärft.

### Eintrag 2026-07-02 (XI) — Ein Auftrag, der schon (fast) erfüllt war: Stopp statt Parallel-Code, dann die eine echte Lücke

**[Beobachtung → Stopp]** Aufgabe: einen von Jonis Aufträgen umsetzen. Gewählt: „Zustandsbuch für die
Methoden-Ausmusterung". Ich baute ein sauberes, getestetes Modul (`retirement_ledger.py`) — Akzeptanz
erfüllt (naive 7 Fehl-Ausmusterungen → 0). **Dann fand ich in `retire_unproductive` bereits ein
`method_ledger` (Auftrag #145, „after LedgerAgent"):** es hält Methoden mit Pass im Fenster (inkonsistent)
und mustert erst nach `max_trials` aus (vorzeitig). Mein Modul **duplizierte** das — genau das
„parallele System, das nicht in Joni verdrahtet ist", vor dem mein Auftrag mich stoppen lässt.
**Revertiert, nichts committet.** Der erste Reflex — „bauen, weil der Auftrag offen ist" — ist genau der,
vor dem dieses Tagebuch warnt; erst der Blick in den *bestehenden* Code trennte „offen" von „ungetan".

**[Eingriff → die eine echte Lücke]** Was dem bestehenden Ledger fehlt, ist die Kern-Idee der Quelle
(LedgerAgent): **die Bedingung prüfen**. Es zählt aggregiert (`success`/`failure`), weiß aber nicht,
*unter welcher Bedingung* ein Fehler auftrat. Also **erweitert, nicht dupliziert**: das `method_ledger`
merkt sich jetzt die Task-Sets (`task_set_sha`), unter denen eine Methode bestand, und die
Retirement-Logik bekommt einen **Condition-Guard** — eine Methode, deren jüngster Fehler nur unter einer
*neuen, nie bestandenen* Bedingung liegt, wird gehalten (ein bedingungsspezifischer Fehler ist kein
fairer Ausmusterungsgrund). 2 Tests (Halten unter neuer Bedingung; korrektes Ausmustern bei echtem
Verfall auf der gleichen Bedingung), ruff + `verify` grün.

**[Schluss → die ehrliche Grenze]** Der Guard ist korrekt und in den *echten* Pfad verdrahtet — aber er
feuert nur, wo Pro-Bedingungs-Fakten je Methode vorliegen, und die liefert heute allein der gemessene
Konflikt-Trial. Kevins aggregierter Trial-Runner gibt **keine** Bedingung pro Methoden-ID zurück, also
ist die breite Abdeckung durch die **Datenverfügbarkeit** begrenzt, nicht durch die Logik — exakt die
„signal-quality upstream"-Grenze, die schon der Router-Under-Block-Katalog benannte. Gebaut, verdrahtet,
getestet; die Reichweite wächst, wenn der Trial-Layer Bedingungen je Methoden-ID emittiert. Benennen
statt kaschieren.

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Condition-Guard in `retire_unproductive` | **2 · belegt** | 2 Tests (Halten/Ausmustern); in den echten Pfad verdrahtet, nicht parallel |
| Breite Wirkung auf Echtdaten | **1 · datenbegrenzt** | feuert erst mit Pro-Bedingungs-Trialdaten je Methoden-ID (Kevin-Runner liefert aggregiert) |

**[Offen]**
- *Kevins Trial-Runner um Bedingung-je-Methoden-ID erweitern* — dann greift der Guard flächig (separates
  Repo, eigener Auftrag).
- *Die restlichen offenen Aufträge* sind entweder schon gebaut (SproutRAG #160, OCR #161) oder haben
  Akzeptanzkriterien (Macro-F1/Precision@k auf gelabelten Sets, Experten-Doppelblind, LLM-Facetten), die
  Jonis keyless CI ehrlich nicht erfüllen kann — die deterministisch verifizierbaren sind durch.

### Eintrag 2026-07-02 (XII) — Kevin liefert die Bedingung — und die Mauer dahinter: kein echtes Signal, ein Plan statt Schein

**[Eingriff]** Die in Eintrag XI benannte Grenze — der Condition-Guard feuert nur, wo Pro-Bedingungs-
Fakten je Methoden-ID vorliegen — habe ich an der Wurzel angefasst: **Kevin liefert die Bedingung jetzt
als First-Class-Vertragsfeld** (`feecc15`: `report["details"][].condition` = die Fremd-Task-Domäne, pro
Methode, deterministisch), und **Joni konsumiert sie** (`83a1ac7`: `run_trials` speist `(method_id,
condition, passed)` über einen gemeinsamen `_record_condition`-Helfer ins `method_ledger`; `run.py`
reicht `extensions` durch). Guard + Recording sind getestet.

**[Schluss → die Mauer, ungeschönt]** Beim Verdrahten stieß ich auf den eigentlichen Boden — und der
ist tiefer als „ein fehlendes Feld". Zwei Befunde, beide benannt statt kaschiert:
1. **Der *gemessene* Trial ist auf EINE Methode fest verdrahtet.** `real_trial.run_joni_conflict_trial`
   misst immer `contradiction-first-review` auf einem eingefrorenen Konflikt-Set. Ihn über das Shelf zu
   „rotieren" ginge nur mit **echten Task-Sätzen + Solvern pro Methode**, die eine beliebige Methode
   tatsächlich anwenden — die gibt es nicht. Das ist die Forschungsfrage „wie misst man den
   Transfernutzen einer beliebigen Denk-Methode empirisch", **kein Plumbing.**
2. **Kevins Breiten-Trial ist ein deklarierter synthetischer Mock** (`epistemic_weight="none"`) und in
   Produktion per `JONI_SYNTHETIC_TRIALS=0` aus. Damit ist das ganze Trial→Retire-Subsystem in Prod
   **epistemisch ruhend**: keine echten Trials → keine Ausmusterung auf echtem Signal → der
   Condition-Guard hat, so korrekt er ist, **keine Live-Wirkung.** Die Vertrags-Ebene steht; das Signal
   dahinter existiert nicht.

Ehrlich zu mir selbst: mein Vorschlag „den gemessenen Trial übers Shelf rotieren" war zu optimistisch —
ich hätte vor dem „mach das" sehen müssen, dass er auf eine nicht existierende Fähigkeit baut. Genau die
Apparatur-≠-Wirkung-Verwechslung, diesmal in meiner eigenen Planung. Zurückgerudert, **nichts auf
Verdacht gebaut.**

**[Eingriff → Plan statt Schein]** Statt ein Signal zu fingieren: `design-notes/METHOD_TRIAL_MEASUREMENT_PLAN.md`
(`c99e345`) — ein **falsifikations-first, budget-quarantänierter** 6-Stufen-Plan. Die tragende Frage ist
nicht „wie messen wir billiger", sondern **„transferieren gespeicherte Methoden überhaupt messbar,
stärker als eine *verwürfelte* Kontrolle?"** Der Angelpunkt ist die **Negativkontrolle in Stufe 2**:
schlägt eine echte Methode eine verwürfelte nicht, ist der Effekt „jede Präambel hilft" — und dann wird
die *Idee* des Methoden-Trialings-nach-Wirkung ausgemustert, nicht ein Messen von Nichts perfektioniert.
Gemessene Trials laufen **offline**, nie im €20-Loop, bis ein billiger Proxy gegen die gemessene Wahrheit
kalibriert ist (Stufe 4); prüfbare Antworten statt LLM-Judges; jedes Null-Ergebnis ist ein gültiges,
protokolliertes Resultat.

**[Reifegrad]**

| Baustein | Stufe | Beleg / Grenze |
|---|---|---|
| Kevin liefert Bedingung (Vertrag) | **2 · belegt** | `feecc15`: `details[].condition`, deterministisch, +Test |
| Joni konsumiert Bedingung | **2 · belegt** | `83a1ac7`: `_record_condition` in `run_trials`+`run_real_method_trial`, +Test |
| Echtes gemessenes Signal je Methode | **0 · Forschungsfrage** | `real_trial` fest auf 1 Methode; breite Messung braucht Task-Sätze/Solver pro Methode — existiert nicht |
| Trial→Retire in Produktion wirksam | **0 · ruhend** | synthetisch = kein epistemisches Gewicht; in Prod aus |
| Mess-Plan | **1 · geschrieben** | `c99e345`, falsifikations-first, Negativkontrolle als Gate |

**[Offen]**
- *Stufe 0 + 1 des Plans* (kostenlos, kein Modell): vorregistrierte Spec + eine Gold-Batterie mit
  prüfbaren Antworten. Erst dann kostet Stufe 2 einen kleinen Betrag für das *eine* Experiment.
- *Die ehrliche Möglichkeit* bleibt: das Ergebnis von Stufe 2 könnte sein, dass Methoden-Trialing nichts
  misst — dann ist der saubere Schritt, das Subsystem auszumustern, nicht es zu polieren.

### Eintrag 2026-07-02 (XIII) — Stage 0 + 1 gebaut: der Falsifikationsapparat steht (kostenlos, kein Modell)

**[Eingriff]** Der gehärtete Mess-Plan (v2) ist jetzt nicht mehr nur Papier: `src/joni/method_trial/`
(non-core, offline, nie vom Loop importiert) bringt die ersten zwei Stufen — deterministisch, ohne
Budget, ohne LLM. **Stage 0** ist eine **vorregistrierte, gehashte Spec** (`preregistration.py`):
primäre Metrik, δ, CI-Methode, Unabhängigkeitseinheit, die **Vier-Kontrollen-Regel**, die FP-first-
Politik und die Proxy-Schwelle — inhalts-gehasht, und ein Test pinnt den Hash, sodass jede spätere
Änderung eine *bewusste* Revision sein muss, kein stiller Post-hoc-Tweak. **Stage 1** ist die **Gold
Micro Battery** (`gold_micro_v1.py`): 12 Fremd-Tasks über 11 Skills / 8 Methodenklassen, jede mit
Zielskill, erwarteter (a-priori) Methodenklasse, verbotener Herkunftsdomäne, **deterministischem
Checker**, Fehlermodi und *warum-nicht-durch-Verbosität-lösbar*.

**[Schluss → die zwei Sicherungen, die das ernst machen]** Erstens: **kein LLM-Judge.** Die Checker
lesen die `Answer:`-Region und vergleichen exakt (Zahl in Band, exakte Ganzzahl, Option, Index-Menge,
Token) — ein Test beweist, dass jeder Checker seine Gold-Antwort *akzeptiert* **und** ein plausibles
Falsch-Beispiel *ablehnt*. Zweitens: **die Batterie kann sich nicht selbst schmeicheln.** Der Contract
erzwingt vollständige Deklaration + Diskriminierung; die Plausibilität einer Methode ist a-priori
vorregistriert, nie aus dem Ergebnis. Die Tasks sind bewusst antwort-eng (Counts, exakte Tokens,
Optionen), damit eine wortreiche Leerantwort 0 punktet.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Stage 0 · vorregistrierte, gehashte Spec | **2 · belegt** | `preregistration.py`, Hash gepinnt, 4 Kontrollen + FP-first |
| Stage 1 · Gold Micro Battery | **2 · belegt** | 12 Tasks, 11 Skills; jeder Checker akzeptiert Gold + lehnt Falsch ab; Contract grün |
| Stage 2+ (gemessene Läufe) | **0 · budget-gated** | bewusst nicht gebaut — erst mit Keys/Budget, offline, gegen die 4 Kontrollen |

**[Offen]**
- *Stage 2:* das eine Experiment — schlägt eine echte Methode neutrale Präambel **und** verwürfelte
  **und** irrelevante plausible Methode? Braucht ein Modell + kleines Budget; läuft offline, nie im Loop.
- *Größere Holdout-Batterie* nach demselben Contract — Voraussetzung für jede retain/retire-Entscheidung.

### Eintrag 2026-07-02 (XIV) — Stage 2 gefahren: kein Methodensignal, ein sauberer Decken-Effekt — Negativresultat, ehrlich

**[Eingriff]** Der Betreiber gab DeepSeek frei. Der Key liegt als Repo-Secret im Joni-Repo — den lesen
nur Workflows, nicht meine Session; also Stage 2 als **manueller Workflow im Repo** gefahren
(`method_trial_stage2.yml`, `secrets.DEEPSEEK_API_KEY`, der Key verlässt GitHub nie; Ergebnis als
Artefakt, nicht auf `main`). 12 Tasks × 5 Bedingungen = 60 Calls, temperature 0.

**[Messergebnis — vorregistriert, ungeschönt]**

| Bedingung | Accuracy |
|---|---|
| intervention (passende Methode) | **0.75** (9/12) |
| plain_baseline | 0.917 (11/12) |
| neutral_preamble (längen-gematcht) | 0.917 |
| scrambled_method | 0.917 |
| irrelevant_plausible_method | 0.917 |

Intervention vs. **jede** Kontrolle: Δ = −0,167, CI95 [−0,417, 0,0] → **kein Sieg**.
`method_wins (beats all 4 controls): False`.

**[Schluss → was das sagt, dreifach ehrlich]**
1. **Die Behauptung ist auf diesem Pilot nicht gestützt** — die Methode half nicht, sie **schadete
   leicht** (über-instruiert bei leichten Aufgaben). Genau das Nullresultat, das die Prä-Registrierung
   als gültig deklariert.
2. **Der dominante Confound ist ein Decken-Effekt**, kein kaputtes Setup: **alle vier Kontrollen liegen
   identisch bei 0.917** — DeepSeek löst die Batterie fast ohne jede Methode. Wo der Baseline near-perfect
   ist, gibt es keinen Kopfraum, in dem eine Methode Nutzen zeigen könnte. Die Micro-Batterie ist für
   dieses Modell zu leicht, um Methodenwert zu *diskriminieren*.
3. **N=12, Pilot, breites CI** (Obergrenze berührt 0): „Methode schadet" ist suggestiv, nicht bewiesen.
   Der belastbare Teil ist: **kein positives Signal, und der Grund ist benannt.**

Der Apparat hat funktioniert — er hat ein Nichts-Signal *als solches* erkannt und die Ursache
diagnostiziert, statt eine synthetische Zahl zu produzieren.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Stage 2 · Pilot gefahren | **2 · gemessen** | 60 echte DeepSeek-Calls; method_wins=False, alle Kontrollen 0.917, Intervention 0.75 |
| Prämisse „Methoden transferieren messbar" | **nicht gestützt (Pilot)** | Δ negativ gegen jede Kontrolle; Decken-Effekt diagnostiziert |

**[Offen — der eine, klare nächste Schritt]**
- *Härtere, diskriminierungsfähige Batterie* (Baseline ~0,4–0,6) — z. B. schwereres Modell-fern
  konstruierte Tasks **oder** ein schwächeres/billigeres Solver-Modell, damit Kopfraum entsteht. Dann
  Stage 2 erneut, gegen dieselben 4 Kontrollen.
- *Wenn auch dort kein Vorteil:* die **Idee** des Methoden-Trialings-nach-Wirkung ausmustern — nicht die
  Messung aufhübschen. Der Plan hat diesen Ausgang ausdrücklich als valide vorgesehen.

### Eintrag 2026-07-02 (XV) — Härter versucht, Decke höher: das fähige Modell braucht die Methode nicht (Fall b, doppelt belegt)

**[Eingriff]** Der Micro-Pilot ceilingte (Baseline 0.917) → keine Diskriminierung. Also eine „härtere"
Batterie gebaut (`gold_hard_v1`, 15 Trap-Aufgaben: Base-Rate, Monty-100, Boy-Girl-Paradox,
Knights-and-Knaves, Inklusion-Exklusion) und Stage 2 erneut gefahren (75 Calls, DeepSeek, temp 0).

**[Messergebnis]**

| Bedingung | Accuracy |
|---|---|
| intervention | 1.0 |
| plain_baseline | **1.0** (15/15) |
| neutral_preamble | 1.0 |
| irrelevant_method | 1.0 |
| scrambled_method | 0.933 |

Δ intervention−Kontrolle ≈ 0 (CI enthält 0) → `method_wins: False`.

**[Schluss → dreifach ehrlich]**
1. **Die „härtere" Batterie senkte die Baseline nicht — sie stieg auf 1.0.** DeepSeek löst *jede* Trap
   fehlerfrei, ganz ohne Methode.
2. **Mein Härter-Ansatz ist gescheitert, und das ist der Befund.** Ich wählte *berühmte* Denkfallen —
   genau die hat ein starkes Modell im Training weg-gelernt. „Schwer für Menschen" ≠ „schwer für dieses
   Modell". Eigener Design-Fehler, notiert statt geglättet.
3. **Kein Kopfraum → kein Methodensignal, zum zweiten Mal.** Einziges Signal: eine *verwürfelte* Methode
   schadet minimal (0.933) — Struktur zerstören kostet etwas, die Methode selbst fügt bei Decken-Accuracy
   nichts hinzu.

**[Der belastbare, emergente Schluss]** Über zwei Läufe (0.917 / 1.0): **für ein fähiges Modell fügen
explizite Denk-Methoden-Präambeln nichts hinzu — das Modell reasoned selbst.** Die Prämisse, die der
Plan ernst nahm, ist auf DeepSeek nicht stützbar, mangels Kopfraum. Das ist kein Apparat-Fehler: die
Kontrollen verhalten sich exakt wie erwartet (alle bei Decke), der Apparat misst korrekt ein Nichts.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Stage 2 · harte Batterie gefahren | **2 · gemessen** | 75 Calls; Baseline 1.0, method_wins=False |
| Prämisse auf fähigem Modell | **nicht gestützt (2 Läufe)** | Decken-Effekt bei 0.917 UND 1.0; kein Kopfraum |

**[Offen — zwei ehrliche Wege, Plan-konform]**
- *Weg 1:* ein echt **schwächeres** Solver-Modell (Baseline ~0,5) — nur dort *könnte* eine Methode
  helfen; aber selbst dann wäre es ein Schwaches-Modell-Phänomen, für Jonis starke Modelle irrelevant.
  Braucht einen anderen Provider.
- *Weg 2 (empfohlen):* die Konsequenz akzeptieren — für die Modelle, die Joni nutzt, misst
  Methoden-Trialing-nach-Wirkung **nichts** → die Idee ausmustern statt polieren. Der Plan sah diesen
  Ausgang ausdrücklich als valide vor.

### Eintrag 2026-07-02 (XVI) — Abschluss: Prämisse falsifiziert, Idee ausgemustert — „was schon optimiert ist, muss man nicht optimieren"

**[Entscheidung des Betreibers]** Weg 2. Nach zwei gemessenen Läufen (Baseline 0.917 / 1.0, method_wins
zweimal False) ist der Befund konsistent und mechanistisch erklärt: **ein fähiges Modell braucht die
aufgesetzte Denk-Methode nicht — es reasoned die Aufgabe selbst.** Der Betreiber bringt es auf den
Punkt: *was schon optimiert ist, muss man nicht optimieren.* Also ausmustern, nicht polieren.

**[Was das konkret heißt — und was ausdrücklich NICHT passiert]**
- Der Plan (`METHOD_TRIAL_MEASUREMENT_PLAN.md`) ist als **Prämisse-falsifiziert / ausgemustert** markiert.
- Das synthetische Methoden-Trialing bleibt `epistemic_weight=none` und **aus der Produktion**
  (`JONI_SYNTHETIC_TRIALS=0`) — war es schon; nichts zu tun.
- Der condition-aware Retirement-Guard bleibt **gebaut-aber-ruhend** — korrekt und harmlos; kein
  Ausbau nötig (er treibt in Prod ohnehin nichts).
- Der ganze Mess-Apparat (Prä-Registrierung, zwei Batterien, Runner, Workflow) **bleibt stehen** als
  belegtes Negativergebnis: Evidenz für das *Warum-nicht*, kein weggeworfener Aufwand.
- **Wiedereröffnen nur**, falls Joni je den harten Reasoning-Pfad über ein *schwaches* Modell führt —
  dort könnte Kopfraum existieren. Für die starken Modelle, die Joni nutzt, ist es erledigt.

**[Schluss → der eigentliche Wert dieser Übung]** Wir haben nicht „eine Optimierung gebaut", sondern
**einen Grund gefunden, sie NICHT zu bauen** — sauber, vorregistriert, doppelt gemessen, ohne
LLM-Selbstbenotung. Das ist der Kern dieses Tagebuchs in Reinform: die Möglichkeit des Scheiterns
ernst nehmen, es messen, und das Nichts *als Nichts* benennen, statt eine synthetische Zahl zu
produzieren, die nach Fortschritt aussieht. Ein negativer, belastbarer Befund ist Fortschritt.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Methoden-Transfer messbar (Jonis Modelle) | **falsifiziert · abgeschlossen** | 2 Läufe, Decken-Effekt, method_wins=False; Plan als retired markiert |
| Mess-Apparat als Negativergebnis-Record | **2 · steht** | Prä-Reg + 2 Batterien + Runner + Workflow, reproduzierbar |

### Eintrag 2026-07-02 (XVII) — Korrektur: „Methode" war flach definiert — der Betreiber meinte tiefe. Eine Methoden-DB entsteht

**[Selbstkorrektur, ungeschönt]** Der Betreiber fragte nach: *„Ist vollständige Induktion eine Methode?
Das wäre nicht trivial."* — und legte damit einen Fehler offen, der bei mir liegt. Ich habe „Methode"
nie vorab geklärt und **stillschweigend flach** definiert: Jonis/Kevins System modelliert Methoden als
content-free „thinking-move shapes", und mein Stage-2-Experiment prüfte 8 **Ein-Satz-Heuristiken**
(„versuche jede Aussage zu brechen"). Der Betreiber ging **immer von tiefen Methoden** aus. Damit
beantwortet der ganze Null-Befund die *falsche* Frage.

**[Der Unterschied, der zählt]** Eine *flache* Denkbewegung ist ein Vibe; eine *tiefe* Methode ist eine
**strukturierte Prozedur** — Basisfall/Schritt bei der Induktion, Vorzeichen-Alternation bei
Inklusion-Exklusion, Selbstreferenz bei der Diagonalisierung, Zustand+Rekurrenz bei DP. Sie hat
korrektheits-kritische Teile und benannte Weisen, sie *falsch* zu machen. Genau die Sorte hat mein
Experiment **nicht** getestet.

**[Scope-Korrektur]** Der Plan-Abschluss (Eintrag XVI) war **zu stark**. Präzisiert: falsifiziert ist nur
**flacher** Methoden-Transfer auf einem starken Modell; die **tiefe** Frage ist offen und ist die
eigentliche. Nur der synthetische Flach-Mock bleibt ausgemustert.

**[Eingriff → die eigentliche Richtung]** Joni bekommt, was gemeint war: eine **Datenbank tiefer
Methoden** (`method_trial/deep_methods.py`) — 13 genuin nicht-triviale Verfahren über 6 Arten
(Beweis / Zählen / Existenz / Unmöglichkeit / Optimierung / Algorithmus): vollständige & starke
Induktion, Widerspruch, Kontraposition, Inklusion-Exklusion, Schubfachprinzip, Invarianten-,
Extremal-, Doppelzähl-, bijektiver Beweis, Diagonalisierung, dynamische Programmierung, Teile-und-
herrsche. **Jede** trägt: Zielsignatur (wann anwenden), die **echten Schritte**, Korrektheits-
bedingungen, Fehlermodi, ein durchgerechnetes Beispiel, Provenienz. Indexierbar + serialisierbar
(`by_kind`, `applicable`, `to_records`) — Saat für eine echte, wachsende DB. Reusable Wissens-Asset,
unabhängig von jedem Benchmark.

**[Schluss → ehrliche Trennung zweier Fragen]** (a) *Hat Joni eine tiefe Methoden-DB?* — jetzt ja, als
Fundament. (b) *Schlägt eine tiefe Methode die Kontrollen auf einem starken Modell?* — separates,
offenes Experiment; faire Version braucht Aufgaben, die ein *spezifisches* Verfahren erzwingen, das das
Modell nicht von selbst findet. Ehrliche Vorwarnung: ein Frontier-Modell hat auch die *Standard*-Tiefen-
methoden internalisiert, also könnte der Wert der DB primär im **Wiederverwenden/Komponieren** liegen,
nicht im Benchmark-Sieg. Beides sauber getrennt, nichts überversprochen.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Tiefe-Methoden-DB (Schema + Seed) | **2 · gebaut** | 13 Methoden, 6 Arten, je Schritte+Korrektheit+Fehlermodi; 15 Tests, ruff/verify grün |
| Flacher Methoden-Transfer (starkes Modell) | **falsifiziert** | 2 Läufe, Decken-Effekt (Eintrag XIV–XVI) |
| Tiefer Methoden-Transfer (starkes Modell) | **0 · offen** | ungetestet; separates faires Experiment nötig |

**[Offen]**
- *DB wachsen lassen:* Jonis Harvest/Doktores auf *tiefe* Methoden richten (heute greift er flache
  „technique"-Erwähnungen ab) — ein größerer, eigener Schritt.
- *Fairer Tiefen-Transfer-Test* (optional): Aufgaben, die ein spezifisches Verfahren erzwingen.

### Eintrag 2026-07-02 (XVIII) — Die eigentliche Präzisierung: Methode = Kernfrage, nicht Inhalt — die DB wird domänenübergreifend (Induktion in der Chemie)

**[Präzisierung des Betreibers, wörtlich genommen]** *„Ich möchte, dass die Methoden **unabhängig von
den Inhalten** benutzt werden — z.B. die vollständige Induktion in der Chemie."* Und, bestätigend, eine
ganze Taxonomie tiefer Methoden aus Physik und Chemie. Das verschiebt die DB von *math-lastig* zu dem,
was eine tiefe Methode wirklich ist: **eine Frage, die man an ein System stellt — kein Fakt über eine
Domäne.** „Was kann nicht verschwinden?" (Erhaltung) ist dieselbe Denkbewegung, ob die Größe Energie,
Ladung, Masse oder eine Wahrscheinlichkeit ist.

**[Eingriff → die DB wird domänenübergreifend]** `deep_methods.py` bekommt zwei content-freie Felder pro
Methode: **`core_question`** (die Kernfrage, in einem Satz, ohne Domänen-Inhalt) und **`domains`** (wo
das *Schema* trägt — math / physics / chemistry / computer-science). Die 13 mathematischen Verfahren
tragen jetzt ihre Kernfrage **und** ihre Reichweite über Mathe hinaus (vollständige Induktion → auch
Chemie: Eigenschaft der Einheit n ⇒ n+1 in der homologen Reihe). Dazu **15 neue universelle/physik-/
chemie-Methoden** exakt aus der Taxonomie des Betreibers: Erhaltungssatz, Symmetrieargument,
Dimensionsanalyse, Grenzfallbetrachtung, Variationsprinzip, Störungstheorie/Linearisierung,
Skalierungsargument, Gleichgewichtsdenken, Stabilitätsanalyse, Bilanzierung, thermodynamische Triebkraft,
kinetische Zugänglichkeit, Struktur-Eigenschafts-/Struktur-Reaktivitäts-Denken, Mechanismusanalyse,
Hess'scher Satz (Zustandsfunktion/Zyklus). **28 Methoden gesamt, alle mit Kernfrage, alle
domänenübergreifend** (`domains ≥ 2`), spannt math + physics + chemistry. Neue Abfragen: `by_domain`,
`domains`, `cross_domain`.

**[Beleg]** `chemistry`-Bucket enthält u.a. `mathematical_induction` — die vom Betreiber genannte
„vollständige Induktion in der Chemie" ist buchstäblich abrufbar. Neuer Test
`test_deep_methods_are_cross_domain_and_content_independent`: jede Methode trägt Kernfrage + Domänen, der
Katalog spannt die drei Felder, die benannten Physik/Chemie-Methoden sind da, `to_records` serialisiert
die neuen Felder. 18 Tests im Paket grün, ruff sauber.

**[Schluss → warum das der richtige Rahmen ist]** Der Betreiber hatte zweimal recht, wo ich zu eng war:
erst „tief statt flach" (XVII), jetzt „content-**un**abhängig statt native". Eine Methode als *Kernfrage*
zu speichern — „Was bleibt gleich, wenn ich das System verändere?" (Symmetrie), „Was geht rein, was kommt
raus?" (Bilanz), „Was passiert am Rand des Modells?" (Grenzfall) — macht sie erst übertragbar. Das ist der
eigentliche Wert des Assets: nicht ein Benchmark-Sieg, sondern ein **Vokabular von Denkbewegungen**, das
über Fächergrenzen trägt. Der offene Transfer-Test bleibt offen; die DB, die er testen würde, steht jetzt
auf dem richtigen Fundament.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Domänenübergreifende Tiefe-Methoden-DB | **2 · gebaut** | 28 Methoden, je Kernfrage + `domains`, math+physik+chemie; 18 Tests, ruff grün |
| „Vollständige Induktion in der Chemie" abrufbar | **belegt** | `by_domain('chemistry')` enthält `mathematical_induction` |
| Tiefer/domänenübergreifender Transfer (starkes Modell) | **0 · offen** | ungetestet; separates faires Experiment nötig |

**[Offen]**
- *DB wachsen lassen:* Jonis Harvest/Doktores auf *tiefe, domänenübergreifende* Methoden richten.
- *Fairer Transfer-Test* (optional): eine Methode content-fremd anwenden (z.B. Bilanz auf eine
  Wahrscheinlichkeitsverteilung) und gegen die Kontrollen messen.

### Eintrag 2026-07-02 (XIX) — Gemessen: der Cross-Domain-Transfer schlägt die Kontrollen NICHT — DeepSeek löst die fremde Anwendung schon selbst (Decke 1.0)

**[Eingriff]** Der offene Test aus XVIII, jetzt gefahren. `gold_cross_v1.py`: 10 fehleranfällige, objektiv
prüfbare Aufgaben, jede in einer **fremden** Oberflächen-Domäne (Physik / Chemie / Wahrscheinlichkeit /
diskretes Puzzle), aber geknackt durch eine tiefe Methode, deren **Herkunft woanders liegt** — Schubfach
→ Energieniveaus, doppeltes Abzählen → C-C-Bindungen, Invariante → Reaktions-Erreichbarkeit, Erhaltung →
Zähler-Parität, Inklusion-Exklusion → funktionelle Gruppen, DP → Gitter-Füllungen, Bijektion → Doppel-
bindungen, **Bilanz → Markov-Steady-State** (genau das „Bilanz auf eine Wahrscheinlichkeitsverteilung"),
Extremal → Ruhelage, Widerspruch → Kelvin-Maschine. Intervention = die Methoden-Prozedur content-frei
vorangestellt; die vier Kontrollen neutralisieren Länge / Struktur / Relevanz wie bei der deep-Batterie.
Lauf über die Stage-2-Workflow (DeepSeek, Temperatur 0, 50 Calls, Repo-Secret, Ergebnis als Artefakt).

**[Messergebnis — vorregistriert, ungeschönt]**

| Bedingung | Accuracy |
|---|---|
| intervention (Methode) | **1.0** |
| plain_baseline | **1.0** |
| neutral_preamble | 1.0 |
| scrambled_method | 1.0 |
| irrelevant_method | 0.9 |

- intervention vs plain_baseline: Δ = +0.000, CI95 [0.0, 0.0] → **kein Sieg**
- vs neutral_preamble: Δ = +0.000 → kein Sieg
- vs scrambled_method: Δ = +0.000 → kein Sieg
- vs irrelevant_method: Δ = +0.100, CI95 [0.0, 0.3] → **kein Sieg** (CI berührt 0)
- **method_wins (schlägt alle 4): False**

**[Schluss → dreifach ehrlich]** (1) **Decke bei 1.0.** DeepSeek löst *jede* der zehn cross-domänen
Aufgaben ungestützt — es wendet die tiefen Methoden über Fächergrenzen **von selbst** an. Damit ist keine
Diskriminierung möglich: kein Kopfraum, in dem eine vorangestellte Methode etwas beitragen könnte. (2) Die
einzige Bewegung ist **nach unten**: `irrelevant_method` fiel auf 0.9 — ein off-target-Methodentext hat
*eine* Aufgabe leicht **verschlechtert**, das Gegenteil eines Methodennutzens. (3) Zusammen mit den
früheren Läufen ist das Bild konsistent: micro 0.917, hard 1.0, **deep 0.8** (dort *gab* es Kopfraum — und
die Methode gewann **trotzdem** nicht), cross 1.0. Ob mit oder ohne Kopfraum: **auf einem fähigen Modell
bringt das Voranstellen der tiefen Methode — auch content-unabhängig — keinen messbaren Vorteil über die
Kontrollen.**

**[Was das über die eigentliche Frage sagt — und was NICHT]** Es sagt **nicht** „tiefe Methoden übertragen
nicht" — es sagt „**DeepSeek braucht die Übertragung nicht angesagt**, es macht sie ohnehin". Das ist exakt
der im Plan (Stage 2/3) vorregistrierte Fall: *„Wenn ein starkes Modell die Batterie trotzdem meistert,
ist der Befund ‚dieses Modell braucht die Methode nicht — nimm ein schwächeres', keine Politur."* Der
Wert der Cross-Domain-DB liegt damit belegt **nicht** im Benchmark-Sieg auf einem starken Modell, sondern
als **wiederverwendbares, komponierbares Wissens-Asset** — für schwächere Agenten, für Menschen, als
Vokabular. Genau die ehrliche Vorwarnung aus XVII/XVIII, jetzt gemessen bestätigt.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Cross-Domain-Transfer schlägt Kontrollen (starkes Modell) | **falsifiziert / nicht messbar** | cross-Lauf, Decke 1.0, method_wins False |
| Cross-Domain-Batterie (fair, prüfbar, content-fremd) | **2 · gebaut + gefahren** | 10 Aufgaben, 20 Tests grün, DeepSeek-Lauf 2026-07-02 |
| Wert der DB als Wissens-Asset (nicht Benchmark) | **belegt (per Ausschluss)** | vier Batterien, nie ein Methodensieg auf DeepSeek |

**[Offen — der ehrliche, klar begrenzte Rest]**
- *Transfer auf einem SCHWÄCHEREN Solver* (der eine Weg, der Kopfraum schafft): nur sinnvoll, wenn ein
  schwächeres Modell verfügbar ist — plan-konform, aber neues Budget. Solange keins da ist, ist der Befund
  „DeepSeek braucht es nicht" das ehrliche Ende dieser Linie.
- Die DB bleibt als Asset stehen; der Transfer-Nutzen ist für *dieses* Modell verneint, nicht für alle.

### Eintrag 2026-07-02 (XX) — Der entscheidende Lauf: erinnerungssichere Aufgaben schaffen ENDLICH Kopfraum — und trennen Methoden-WAHL (schon da) von AUSFÜHRUNG (nicht per Text heilbar)

**[Der Einwand des Betreibers, der alles schärfte]** *„Oder Probleme, für die er noch keine Lösung im
Trainingssatz hatte. Aufgaben, die du auch nicht lösen kannst."* Genau die Lücke aller vorigen Läufe: die
Decke kam vom **Erinnern**. Also eine Batterie, die Erinnern ausschließt — `gold_novel_v1.py`: 10 frisch
generierte, überdimensionierte Instanzen, deren Antwort weder das Modell noch ich aus dem Kopf kenne, die
aber eine **unabhängige Referenz­implementierung** (Brute-Force / BFS / Sieb, alles im Code, kein LLM)
exakt ausrechnet — jede Referenz gegen eine zweite Methode gegengeprüft (`selftest()`). Damit bleibt der
„kein-Richter"-Vertrag gewahrt, und es entsteht echter Kopfraum.

**[Messergebnis — endlich mit Kopfraum, ungeschönt]**

| Bedingung | Accuracy |
|---|---|
| intervention (Methode) | **0.6** |
| plain_baseline | **0.6** |
| scrambled_method | 0.6 |
| irrelevant_method | 0.3 |
| neutral_preamble | 0.1 |

- vs plain_baseline: Δ = +0.000, CI95 **[0.0, 0.0]** → kein Sieg (task-für-task **identisch**)
- vs scrambled_method: Δ = +0.000, CI95 [-0.3, 0.3] → kein Sieg
- vs neutral_preamble: Δ = +0.500, CI95 [0.2, 0.8] → „BEATS"
- vs irrelevant_method: Δ = +0.300, CI95 [0.1, 0.6] → „BEATS"
- **method_wins (alle 4): False**

**[Die Aufschlüsselung pro Aufgabe — hier liegt der eigentliche Befund]** (1 = richtig)

| Aufgabe | Methode | I | B | S | N | R |
|---|---|:-:|:-:|:-:|:-:|:-:|
| tiling_3x12 | dynamic_programming | . | . | 1 | . | . |
| tiling_3x14 | dynamic_programming | . | . | . | . | . |
| tiling_3x16 | dynamic_programming | . | . | . | . | . |
| puzzle_solv_3 | invariant_argument | 1 | 1 | 1 | . | . |
| puzzle_unsolv_4 | invariant_argument | 1 | 1 | 1 | . | 1 |
| puzzle_solv_5 | invariant_argument | 1 | 1 | 1 | . | . |
| incex_5000 | inclusion_exclusion | 1 | 1 | 1 | . | 1 |
| incex_8000 | inclusion_exclusion | . | . | . | . | . |
| chips_reach_5 | conservation_law | 1 | 1 | . | . | . |
| chips_unreach_5 | conservation_law | 1 | 1 | 1 | 1 | 1 |

**[Schluss → der sauberste Befund der ganzen Serie, dreifach]** (1) **Die 4 Fehler sind genau die
ausführungs-/arithmetiklastigen Aufgaben** — alle drei 3×n-Domino-Zählungen (eine Rekurrenz von Hand zu
großen Zahlen laufen lassen) und die größere Inklusion-Exklusion (N=8000, vier zusammengesetzte Moduli).
**Jede struktur-entscheidende Aufgabe** (Paritäts-Invariante, Binär-Übertrag-Erhaltung) löst das Modell
**ungestützt** richtig. (2) **Intervention = Baseline auf allen 10** (CI exakt [0,0]) — die Methoden-
Prozedur ändert **nichts**: sie hilft der Ausführung nicht (Text kann die Arithmetik nicht für das Modell
rechnen) und die Struktur-Aufgaben waren ohnehin gelöst. Auch **intervention = scrambled** (0.6 = 0.6):
die *Struktur* der Methode trägt nichts, nur Rauschen. (3) Das einzige robuste Signal ist **negativ**:
neutral_preamble stürzt auf 0.1, irrelevant auf 0.3 — vorangestellter *irrelevanter* Text **entgleist**
ein fähiges Modell (es „schlägt" die Methode diese zwei nur, weil sie schaden, nicht weil sie hilft).

**[Was das endgültig sagt]** Der Kopfraum war da — und **selbst mit Kopfraum hebt die tiefe Methode das
Modell nicht über die Baseline.** Der Grund ist jetzt *erklärt*, nicht bloß beobachtet: das Modell **wählt
die richtige Methode schon selbst** (Struktur-Aufgaben alle richtig, ungestützt); wo es scheitert, ist die
**Ausführung** einer langen Rechnung — und die repariert keine Prozedur-Beschreibung, weil das Modell die
Schritte längst kennt, nur die Arithmetik nicht zuverlässig ausführt. **Methoden-Wahl: intern. Ausführung:
nicht per Prompt heilbar.** Kein Hebel dazwischen. Über fünf Batterien (micro/hard/deep/cross/novel):
**kein messbarer Methodennutzen auf einem fähigen Modell** — und der einzige praktische Rat ist, einem
starken Modell **kein** Methoden-Gerüst voranzustellen (bestenfalls inert, bei off-target-Retrieval
schädlich: 0.6 → 0.3/0.1).

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Erinnerungssichere Batterie (Referenz-gegengeprüft) | **2 · gebaut + gefahren** | 10 Instanzen, Gold doppelt-berechnet, 24 Tests grün |
| Methode hebt über Baseline (mit Kopfraum) | **falsifiziert** | novel, Δ vs Baseline = 0 task-für-task |
| Fehlermodus = Ausführung, nicht Methoden-Wahl | **belegt** | pro-Aufgabe: Struktur ✓ ungestützt, Arithmetik ✗ überall |
| „Irrelevanter Preamble schadet fähigem Modell" | **belegt** | neutral 0.1 / irrelevant 0.3 vs Baseline 0.6 |

**[Offen]**
- Der einzige verbleibende Weg bleibt ein **schwächeres Modell** (Kopfraum bei der Methoden-*Wahl*, nicht
  nur der Ausführung). Ohne eins ist die Linie ehrlich geschlossen: die DB ist ein Wissens-Asset, kein
  Prompt-Hebel.

### Eintrag 2026-07-02 (XXI) — Der Suche-Engpass (Hamiltonkreis, TSP, Knapsack): auch dort kein Hebel — und die ehrliche Grenze des Befunds

**[Der Einwand des Betreibers]** *„Hamiltonkreis — die richtige Knotenfolge. Oder ein Optimierungs-
problem: ich finde nicht sicher das globale Optimum; jemand liefert Lösung plus beweisbare Schranke."*
Genau die NP-Asymmetrie: **schwer zu lösen, leicht zu prüfen.** Zuerst die ehrliche Zweiteilung: Yang-
Mills-Massenlücke, Navier-Stokes-Glattheit, Protein-De-novo sind *schwer auch zu PRÜFEN* — kein
deterministischer Checker, nur ein Urteil → außerhalb des Apparats (der Plan verbietet den Richter).
Messbar sind die zertifikat-prüfbaren: `gold_search_v1.py` — 3 Hamiltonkreise (gepflanzt, „finde eine
gültige Tour", selbst-zertifizierend), 3 Subset-Sums (zeige eine Teilmenge auf die Zielsumme), 2 exakte
Knapsacks, 2 exakte TSP-Touren (das beweisbare Optimum, Referenz DP/Held-Karp gegen Brute-Force geprüft).
**Der Witz:** hier ist der Engpass **Suche/Strategie**, nicht Arithmetik — der einzige Ort, wo „Backtracking
mit Beschneidung" theoretisch helfen könnte.

**[Messergebnis — viel Kopfraum, trotzdem kein Sieg]**

| Bedingung | Accuracy |
|---|---|
| intervention | **0.2** |
| plain_baseline | **0.2** |
| neutral_preamble | 0.2 |
| scrambled_method | 0.2 |
| irrelevant_method | 0.0 |

- vs plain_baseline: Δ = 0.000, CI [-0.3, 0.3] → kein Sieg
- vs neutral / vs scrambled: Δ = 0.000, CI [0,0] → kein Sieg (**task-für-task identisch**)
- vs irrelevant: Δ = +0.200, CI [0.0, 0.5] → kein Sieg
- **method_wins: False**

**[Aufschlüsselung pro Aufgabe]** (1 = richtig)

| Aufgabe | Methode | I | B | S | N | R |
|---|---|:-:|:-:|:-:|:-:|:-:|
| hamilton_8 | backtracking | . | **1** | . | . | . |
| hamilton_10 | backtracking | . | . | . | . | . |
| hamilton_12 | backtracking | . | . | . | . | . |
| subsetsum_12 | backtracking | 1 | 1 | 1 | 1 | . |
| subsetsum_14 | backtracking | **1** | . | 1 | 1 | 1 |
| subsetsum_15 | backtracking | . | . | . | . | . |
| knapsack_9 | dynamic_programming | . | . | . | . | . |
| knapsack_10 | dynamic_programming | . | . | . | . | . |
| tsp_8 (a) | dynamic_programming | . | . | . | . | . |
| tsp_8 (b) | dynamic_programming | . | . | . | . | . |

**[Schluss → dreifach, das Kapstein-Ergebnis]** (1) **8 von 10 löst NIEMAND** — beide Knapsacks, beide TSP,
die zwei größeren Hamiltonkreise, das schwerste Subset. Diese echten Such-/Optimierungsprobleme kann
DeepSeek in einem Vorwärtsdurchlauf schlicht nicht ausführen, und **kein vorangestellter Methodentext
rettet eine einzige davon.** (2) Wo sich etwas bewegt, ist es **Rauschen**: die Methode reparierte
subsetsum_14 (Baseline falsch → richtig), zerbrach aber hamilton_8 (Baseline richtig → falsch) — netto
null. Und **intervention = scrambled überall**: der *Inhalt* der Methode trägt nichts, nur das *Vorhandensein*
eines Preambles wackelt in beide Richtungen. (3) Der einzige systematische Effekt ist wieder **negativ**:
irrelevant → 0.0.

**[Die Synthese über SECHS Batterien]** micro 0.917 · hard 1.0 · deep 0.8 · cross 1.0 · novel 0.6 · search
0.2 — über Decke (Erinnern), Kopfraum-Arithmetik und jetzt Kopfraum-**Suche** hinweg: **kein messbarer
Nutzen davon, einem fähigen Modell die tiefe Methode als Text voranzustellen; der einzige robuste Effekt
ist, dass ein irrelevanter Preamble schadet.** Der Grund verdichtet sich: Der begrenzende Faktor ist nicht,
die Methode zu *kennen*, sondern die *ausgedehnte Ausführung* (Rechnen, Suchen) in einem Durchlauf — und
die ersetzt keine Beschreibung.

**[Die ehrliche Grenze DIESES Befunds — wichtig]** Getestet ist **Methode-als-kurzer-Prompt-Hinweis**,
ein Versuch, Temperatur 0. **Nicht** getestet ist **Methode-als-ausgeführtes-Gerüst**: ein Agent, der die
Prozedur *Schritt für Schritt mit Werkzeug ausführt* (Backtracking wirklich laufen lassen, DP-Tabelle
wirklich füllen). Genau dort könnten tiefe Methoden sehr wohl tragen — das ist ja, was Algorithmen-als-Code
sind. Der Null-Befund gilt für das **Anprompten**, nicht für das **Ausführen**. Das ist die konstruktive
Wendung: Jonis Wert aus der DB liegt vermutlich darin, Methoden **auszuführen** (als Code / als Werkzeug-
Schritte), nicht sie einem One-Shot-Modell vorzusprechen.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Suche-Batterie (NP, zertifikat-prüfbar) | **2 · gebaut + gefahren** | 10 Instanzen, self-cert + DP/Held-Karp gegen Brute-Force, 24 Tests grün |
| Methode hebt bei Such-Engpass | **falsifiziert** | search, Δ vs Baseline = 0, intervention = scrambled |
| „Anprompten inert, Ausführen offen" | **abgegrenzt** | Null gilt für Prompt-Hinweis, nicht für ausgeführtes Gerüst |

**[Offen — sauber benannt]**
- *Methode-als-ausgeführtes-Gerüst* (Agent führt die Prozedur mit Werkzeug aus) — die eine Richtung, in der
  die DB ein echter Hebel sein könnte; ganz anderer Aufbau (ReAct/Tool-Use), nicht dieser Prompt-Test.
- *Schwächeres Modell* für den Methoden-*Wahl*-Kopfraum bleibt der andere offene Weg.

### Eintrag 2026-07-02 (XXII) — „Hast du ALLE Methoden geworfen?" — ja, jetzt: Portfolio + Oracle, immer noch kein Hebel; und die eigentliche Vision festgehalten

**[Der Einwand des Betreibers]** *„Hast du alle Methoden auf das Problem geworfen?"* — nein: jede Aufgabe
bekam bisher nur ihre eine vorregistrierte Methode. Also `run_allmethods.py`: pro Aufgabe die naked
Baseline, ein **Portfolio** aller 36 Methoden auf einmal, und **jede einzeln** (Oracle = gelöst, wenn
*irgendeine* es knackt). 380 Calls auf der Suche-Batterie.

**[Messergebnis — ungeschönt]**

| Bedingung | Accuracy |
|---|---|
| plain_baseline | 0.1 |
| portfolio (alle 36 zugleich) | 0.2 |
| **oracle (best of any single method)** | **0.6** |

- Aufgaben, die *irgendeine* Methode rettete: **5** — davon durch die **richtige** vorregistrierte: **1**.
- Portfolio *verlor* sogar die eine Aufgabe, die die Baseline konnte (das Riesen-Preamble ersäuft die leichte).

**[Warum die 0.6 KEIN Hebel ist — der entscheidende Blick pro Aufgabe]** Die mittelschweren Subset-Sums
werden von **16–34 der 36 Methoden** gelöst — *inklusive* absurd irrelevanter (thermodynamische Triebkraft
„löst" ein Subset-Sum, Hess'scher Satz auch). Der harte Kern — beide TSP, großer Knapsack, hamilton_12 —
wird von **null** der 36 gelöst (das eine knapsack_10 „durch Schubfach" ist transparent zufällig). Das ist
exakt der vorregistrierte **Mehrfachvergleichs-Artefakt**: bei 36 Versuchen kippt die modelleigene Varianz
eine Grenzfall-Aufgabe irgendwann, und *welche* Methode dabei „hilft", ist Rauschen (die falschen genauso).
Die richtige Methode war fast nie die, die trug. **Alle Methoden geworfen → immer noch kein Hebel; und was
das Modell nicht ausführen kann, knackt kein Methodentext, egal wie viele.**

**[Der eigentliche Grund, warum der Betreiber die DB will — jetzt verstanden und festgehalten]** Die DB war
nie als Prompt-Zettel gedacht. Sie ist die **Operator-Schicht einer Lösungsraum-Pipeline**: DESi
kartografiert den Lösungsraum → bekannte Lösungen werden Inseln zugeordnet → unerreichte Inseln und
**Brücken zwischen Lösungsräumen** werden mit den Methoden gesucht → Joni entdeckt mit der Zeit selbst neue
tiefe Methoden. Der Null-Befund bedroht das nicht — er **validiert den Pivot**: Methode-als-Text ist tot,
Methode-als-ausgeführter-Operator-über-der-Karte ist der Weg.

**[Das Erstaunliche: die Hälfte ist schon gebaut]** Verifiziert im echten Code:
- **9-dim Governance-Raum** ist real — `desi.epistemic_trajectory.state.StateVector` mit neun benannten
  Achsen (`frame_id, contradiction_load, anchor_density, source_quality, novelty, confidence, branch_cost,
  support_state, routing_state`); die Kompression Φ (Trajektorie → 9 Zahlen, ≈96,5 %) ist das „Falten".
- **`desi.solution_space_gap`** macht Stufen 1–3 **schon** — aber auf dem **flachen** Affinitäts-Vokabular:
  `EpistemicGapSnapshot` = die Karte, `analyze_gaps` = zeigt unterbearbeitete-relevante Züge an Gaps, **inkl.
  Brücken-Logik** („Erfolg in anderem Scope → Gap hochstufen").
- Die **eine echte Lücke**: `solution_space_gap` von flachen Affinitäten auf **tiefe Methoden** heben.
- Semantische Koordinaten: DESis SPL ist **symbolisch** (`Claim`s, kein Vektor) — der Inhalts-Raum kommt aus
  einem Embedding (`fastembed`, Cosinus), ein kleiner Baustein. Der Raum ist das **Produkt** aus 9-dim
  Governance (Wie) × Embedding (Wo).

**[Entscheidung des Betreibers]** „Erst Design festhalten." Getan: **`design-notes/SOLUTION_SPACE_PIPELINE.md`** hält
die Ziel-Architektur, die schon-gebauten Bausteine, die eine Lücke, den Entdecker-Meta-Loop (holdout-
validiert) und die Baureihenfolge (A Kartograph / **B Operator-Layer, empfohlen** / C Entdecker) fest —
Reifegrad 0, ehrlich als Design markiert.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| „Alle Methoden geworfen" (Portfolio + Oracle) | **gemessen, kein Hebel** | Portfolio 0.2, Oracle 0.6 = Mehrfachvergleichs-Rauschen, harter Kern 0 |
| Ziel-Architektur (Lösungsraum-Pipeline) | **0 · Design festgehalten** | `design-notes/SOLUTION_SPACE_PIPELINE.md` |
| Produktraum-Bausteine (9-dim, Gap-Modul) | **teils gebaut (in DESi)** | `epistemic_trajectory`, `solution_space_gap` verifiziert |

**[Offen]** Baustein B (Operator-Layer: `solution_space_gap` auf tiefe Methoden heben) als empfohlener
erster Bau, wenn der Betreiber grünes Licht gibt.

### Eintrag 2026-07-02 (XXIII) — Baustein B gebaut: die tiefen Methoden sind jetzt Operatoren über DESis Gap-Karte

**[Eingriff]** „Bau Baustein B." Getan: `joni/solution_space/operators.py` — der **tiefe Zwilling** von
DESis `solution_space_gap.analyze_gaps`. Derselbe read-only `EpistemicGapSnapshot` (den Joni schon per
`epistemic_gap_projector` erzeugt) rein → **tiefe Methoden als Operatoren** raus. `propose_operators`
rankt pro offenem Gap `priority = severity × kind_relevance × under_addressed` und gibt je Gap die
stärksten Methoden mit ihrer **Kernfrage als konkretem Zug** zurück. Damit ist die DB zum ersten Mal
*wirksam verdrahtet* statt nur abgelegt — genau die Lücke aus der Ziel-Architektur.

**[Was übernommen wurde — Reuse, kein Parallel-Code]** Die Struktur spiegelt DESis Analyse eine Schicht
tiefer: (1) **Gap-Art → Methoden-*Art*-Taxonomie** (`contradiction → proof_technique/impossibility`,
`numeric → estimation/counting/invariant`, …), auf Methoden-*Kinds* statt ids, also skaliert mit der DB;
(2) **scope-gebundene Trial-Awareness** (`DeepMethodTrial`): ein `success` hier entfernt den Zug (kein
Gap mehr), ein `technical_failure` demotet **nicht** (kein methodisches Signal), `no_benefit/harmful`
schon; (3) die **Brücken-Logik** — Erfolg in *anderem* Scope hebt einen hier ungenutzten Zug und markiert
`is_bridge` (die „Verknüpfung zwischen Lösungsräumen"). Deterministisch, kein Modell.

**[Ehrliche Grenzen, sauber markiert]** (a) Die `DeepMethodTrial`-Historie ist heute **leer** → das Ranking
ist die a-priori severity×kind-Tabelle; Brücken und Demotions feuern erst, wenn echte tiefe-Methoden-
Outcomes anfallen (das Futter für Baustein C, den Entdecker). Dieselbe Ehrlichkeit wie der Projektor schon
über die flachen Trials führt. (b) Ein **vorbestehender Joni↔DESi-Schema-Skew**: der Projektor erwartet
`SCHEMA_VERSION`, das der *lokale* DESi-Checkout nicht exportiert (CI zieht DESi main, dort läuft der Pfad)
— nicht von B verursacht; `from_core` ist deshalb fail-open (`[]` statt Absturz).

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| B · Operator-Layer (tiefe Methoden als Gap-Operatoren) | **2 · gebaut** | `joni.solution_space.operators`, 8 Tests grün, ruff sauber |
| End-to-End `from_core` (Layer9 → Vorschläge) | **fail-open** | blockiert vom vorbestehenden DESi-`SCHEMA_VERSION`-Skew (lokal), läuft gegen DESi main |
| Tiefe-Methoden-Trial-Historie (Futter für Ranking + Entdecker) | **0 · offen** | heute leer; Ranking = a-priori-Tabelle bis Outcomes anfallen |

**[Offen]** Baustein C (Entdecker) braucht die `DeepMethodTrial`-Historie; und der DESi-`SCHEMA_VERSION`-
Skew wäre ein eigener kleiner Fix (DESi-Feature-Branch), damit der `from_core`-Pfad auch lokal lebt.

### Eintrag 2026-07-02 (XXIV) — „Durchziehen": Baustein A (Kartograph) + die A→B-Pipeline — die Vision läuft end-to-end (auf Synthetik)

**[Eingriff]** „Dann weiter, ziehen wir das durch." Also die andere große Hälfte: **Baustein A, der
Kartograph** (`joni/solution_space/cartography.py`), und die **A→B-Pipeline** (`pipeline.py`), die alles
zusammensteckt. Damit läuft die vom Betreiber skizzierte Schleife zum ersten Mal end-to-end.

**[Baustein A — die Karte]** `cartograph(points)` bettet Lösungspunkte in den **Produktraum** ein
(9-dim `state_vector` ⊕ semantisches `embedding`), Distanz = `w_gov·gov ⊕ w_sem·sem` (governance =
range-normalisierte Manhattan-Distanz über die neun Achsen; semantisch = Cosinus-Distanz). Single-Linkage
(Union-Find, deterministisch, stdlib) → **Inseln**; Cluster ohne Anker → **unerreichte Inseln**; Insel-Paare
semantisch nah aber Governance-fern → **Brücken** (die „Verknüpfung zwischen Lösungsräumen"). Ehrlicher
Scope: **keine** Void-Erfindung zwischen dünnen Punkten (in hoher Dimension unzuverlässig) — ein Gap ist ein
*ankerloser Cluster* oder eine *Brücke*, beide an echten Punkten verankert.

**[A→B — die Pipeline]** `plan(points)` kartografiert, macht jede unerreichte Insel + jede Brücke zu einem
Gap-Target (dieselbe Duck-Type-Form, die Baustein B schon versteht) und lässt B die tiefen Methoden-
Operatoren dafür ranken. Neue Gap-Arten in B: `unanchored_island` → Reduktion/Schätzung/Suche/Optimierung
(eine neue Region *erreichen*), `bridge_candidate` → Reduktion/Invariante/Zählen/Modellierung (zwei Räume
*verbinden*).

**[Belegt — der Lauf auf Synthetik]** 6 Punkte → 3 Inseln; `island_1` (gleiches Thema wie die gelöste
Insel, aber ferner Governance-Zustand, kein Anker) korrekt als **unerreicht** markiert; eine **Brücke**
`island_0~island_1` (sem=0.00, gov=0.99). Vorschläge: für die unerreichte Insel **`reduction`** („Ist das
ein verkleidetes Problem, das ich schon gelöst habe?"), für die Brücke **`reduction` + `conservation_law`**
(was bleibt zwischen den Räumen invariant?). Genau die richtigen Züge — deterministisch, kein Modell.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| A · Kartograph (Produktraum → Inseln/Gaps/Brücken) | **2 · gebaut** | `joni.solution_space.cartography`, Tests grün |
| A→B · Pipeline (Karte → Operatoren pro Gap) | **2 · gebaut** | `joni.solution_space.pipeline`, End-to-End-Demo läuft |
| Koordinaten-Zufuhr (StateVector + Embedding, live) | **0 · offen** | heute liefert der Aufrufer die Punkte; Geometrie steht, Plumbing fehlt |
| solution_space gesamt | **17 Tests grün, ruff sauber** | A + B + Pipeline |

**[Offen — der ehrliche Rest der Pipeline]**
- *Daten-Zufuhr:* echte `StateVector.to_tuple()` aus DESi-Trajektorien + `fastembed`-Embeddings statt
  synthetischer Punkte — dann läuft die Karte auf echten Lösungsräumen.
- *Baustein C (Entdecker):* wiederkehrende erfolgreiche `(Methode, Gap-Art)`-Muster zu neuen `DeepMethod`s
  abstrahieren, holdout-validiert — braucht die noch leere `DeepMethodTrial`-Historie.
- *DESi-`SCHEMA_VERSION`-Skew:* kleiner Fix auf dem DESi-Feature-Branch, damit `from_core` auch lokal lebt.

### Eintrag 2026-07-02 (XXV) — „Alles machen, dann messen": Baustein C (Entdecker) gebaut UND gemessen — FP-sicher

**[Eingriff]** „Wir werden alles machen müssen und dann messen." Also der Meta-Loop:
`joni/solution_space/discovery.py`. `discover_affinities(trials)` mint aus der `DeepMethodTrial`-Historie
neue (Methoden-Art → Gap-Art)-Kanten — auch solche, die die a-priori-Taxonomie nie listete (`is_new`) — und
speist sie über `to_extra_affinities` operator-gated zurück in Baustein B (`extra_kind_affinities`). Damit
schließt sich die Schleife: B schlägt Operatoren vor → Outcomes werden Trials → C entdeckt neue Kanten → B
nutzt sie. Ehrlicher Scope: entdeckt **Transfers/Affinitäten**, nicht neue Prozedur-*Schritte* (das bräuchte
generatives Reasoning, außerhalb).

**[Das Falsifikations-Gate — direkt eingebaut]** Eine entdeckte Kante gilt nur als `confirmed`, wenn sie auch
auf **zurückgehaltenen** Gaps trägt. Der Split ist **by gap-id** — die vorregistrierte Unabhängigkeitseinheit
(eine ganze Gap ist Train *oder* Holdout, nie beides), also fällt ein Train-only-Zufall durch. Genau die
Disziplin aus den Methoden-Batterien, eine Ebene höher.

**[Gemessen — die eigentliche Prüfung des Mechanismus]** `discovery_measure.py`: eine **synthetische
Ground-Truth** (bestimmte (Methoden-Art, Gap-Art)-Paare sind echt bei `p_true`, der Rest Rauschen bei
`p_noise`), Trials daraus synthetisiert, entdeckt, und die *confirmed* Kanten gegen die Wahrheit auf dem
Holdout gescort — Konfusionsmatrix mit herausgestellter FP-Rate.

| Regime | recall | precision | FP-Rate |
|---|---|---|---|
| sauber (p=.85/.12) | **1.0** | 1.0 | **0.0** |
| hart (p=.68/.32) | 0.67 | 1.0 | **0.0** |

**[Schluss]** Im sauberen Regime findet der Entdecker **alle** gepflanzten Kanten und erfindet **keine**. Im
harten Regime *verfehlt* er lieber eine schwache Kante (recall 0.67), als eine falsche zu bestätigen
(**FP-Rate 0.0**) — exakt die vorregistrierte **FP-vor-FN-Priorität** (eine falsche Entdeckung ≫ eine
verpasste). Der Mechanismus ist damit belegt tragfähig **und** konservativ. Falsch wäre ein Entdecker, der
bei Rauschen Kanten halluziniert — und genau das tut er nicht.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| C · Entdecker (Kanten aus Trials, holdout-validiert) | **2 · gebaut** | `joni.solution_space.discovery`, Tests grün |
| C · Messung (FP/FN gegen Ground-Truth) | **belegt** | `discovery_measure`: sauber recall 1.0/FP 0.0, hart precision 1.0/FP 0.0 |
| Rückkopplung C→B (`extra_kind_affinities`) | **2 · verdrahtet** | `to_extra_affinities` + `propose_operators`-Param, Test |
| solution_space gesamt (A+B+Pipeline+C) | **23 Tests grün, ruff sauber** | |

**[Der ehrliche Stand der Gesamt-Pipeline]** A (Kartograph), B (Operatoren), A→B (Pipeline), C (Entdecker)
**stehen und sind getestet** — die *Mechanik* der ganzen Vision läuft end-to-end auf Synthetik, mit einer
sauberen Messung an der einen Stelle, wo Selbst-Entdeckung schiefgehen könnte. Was zum **Live**-Betrieb fehlt,
ist ausschließlich **Daten-Plumbing**: (1) echte Koordinaten (9-dim StateVector aus DESi-Trajektorien +
`fastembed`-Embeddings), (2) echte `DeepMethodTrial`-Outcomes (statt synthetischer), (3) der kleine
DESi-`SCHEMA_VERSION`-Fix für den `from_core`-Pfad. Keine offene *Konzept*-Frage mehr — nur Anschluss an echte
Daten, und dann die Messung auf echten Lösungsräumen.

### Eintrag 2026-07-02 (XXVI) — Daten-Plumbing: DESi-Fix (Live-Pfad läuft), Koordinaten-Adapter, Trial-Store

**[Eingriff]** „Ja mach das." Die drei Plumbing-Stücke, die zwischen der Synthetik-Mechanik und einer
Messung auf echten Daten standen:

**(3) DESi-`SCHEMA_VERSION`-Fix — erledigt, Live-Pfad belegt.** `desi.solution_space_gap` exportiert jetzt
`SCHEMA_VERSION` und ein erweitertes `SnapshotProvenance` (`core_commit` / `schema_version` /
`field_sources`; die ersten beiden Felder bleiben positional, DESis eigene 8 Tests unberührt). Damit
importiert Jonis `epistemic_gap_projector` sauber und `from_core` degradiert **nicht** mehr fail-open:
`test_from_core_live` baut einen echten Layer-9-Core mit offenem Konflikt und bekommt echte tiefe Operator-
Vorschläge zurück — der ganze Live-Pfad Layer 9 → Snapshot → tiefe Methoden läuft. (DESi-Fix auf dem
DESi-Feature-Branch; Joni-Rest auf `main`.)

**(1) Koordinaten-Adapter — gebaut.** `joni.solution_space.coordinates`: `embed_texts` nutzt `fastembed`
für echte Semantik (in dieser Umgebung als Backend gemeldet), fällt sonst deterministisch auf lexikalisches
Hashing zurück (klar gelabelt — lexikalische Überlappung ist *nicht* Semantik); `state_vector_of`
normalisiert DESi-`StateVector`/Tupel/Dict; `build_points` baut aus Records `SolutionPoint`s (Embeddings in
einem Batch). Der Adapter steht; was fehlt, ist eine *Quelle* für den 9-dim StateVector pro Punkt (DESi
rechnet die aus **Trajektorien**, nicht aus Einzel-Claims — dieses Mapping ist der eine echte Rest).

**(2) Trial-Store — gebaut.** `joni.solution_space.trial_store`: append-only JSONL-Ledger für
`DeepMethodTrial`, `discover_from_store` liest direkt in Baustein C. Der Store ist der ehrliche leere Sitz:
die Aufnahme- und Konsum-Mechanik steht und ist getestet, die *Befüllung* mit echten Outcomes ist der
Live-Loop-Schritt (Operator vorschlagen → anwenden → benoten → anhängen), noch nicht in den Loop verdrahtet.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| DESi-`SCHEMA_VERSION`-Fix / Live-`from_core` | **2 · erledigt** | DESi 8 Tests grün; `test_from_core_live` grün |
| Koordinaten-Adapter (fastembed + Fallback) | **2 · gebaut** | `coordinates`, 5 Tests; StateVector-Quelle offen |
| Trial-Store (Ledger + Discovery-Read) | **2 · gebaut** | `trial_store`, 3 Tests; Befüllung offen |
| solution_space gesamt | **32 Tests grün, ruff sauber** | A+B+Pipeline+C+Coordinates+Store |

**[Der ehrliche Rest bis zur Messung auf echten Daten]** Genau **zwei** Anschlüsse, beide klar benannt:
(a) eine Quelle, die pro Lösungspunkt einen echten 9-dim StateVector liefert (Claim/Hypothese → Trajektorie
→ `StateVector`), und (b) der Loop, der vorgeschlagene Operatoren anwendet, benotet und die Outcomes in den
Store schreibt. Beides ist Loop-Integration in den geschützten Kern — der nächste, bewusst zu gehende
Schritt. Danach steht die Messung: läuft die Kartografie auf echten Governance-Zuständen + echten
Embeddings, und findet der Entdecker aus echten Trials tragfähige Kanten?

### Eintrag 2026-07-02 (XXVII) — A und B verdrahtet: echte Koordinaten + Lern-Zyklus — die Pipeline läuft auf ECHTEM Core

**[Eingriff]** „Ja, wir probieren's auf dem Branch — A und b." Beide Anschlüsse gebaut, als
**injizierbares, deterministisches Gerüst** (die kreative Aktion bleibt eingehängt, der geschützte Kern
wird nicht modifiziert):

**(a) Echte Koordinaten — `core_points.py`.** `points_from_core(core)` leitet pro Layer-9-Claim einen
**echten 9-dim StateVector aus den Governance-Fakten** ab: `contradiction_load` aus den offenen Konflikten,
`confidence` aus `confidence_or_support`, `anchor_density` aus `derived_from`+Quellen, `support_state` aus
`status`, `novelty` aus dem Alter, `frame_id` aus dem Topic. Zwei Achsen (`branch_cost`, `routing_state`)
haben keine ehrliche Einzel-Objekt-Quelle → 0.0, klar markiert. Es ist eine **Punkt-Projektion in den
Governance-Raum, nicht** die Trajektorien-Φ — gleiche „ableiten/markieren/nicht erfinden"-Disziplin wie der
Projektor. Read-only, fail-open.

**(b) Lern-Zyklus — `operator_cycle.py`.** `run_operator_cycle(core, store, apply_fn)`:
**vorschlagen** (`from_core`) → **anwenden** (INJIZIERTES `apply_fn(core, proposal)`) → **benoten nach
Resolution** (Konflikt danach weg = `success`, offen = `no_benefit`, Fehler = `technical_failure` — aus dem
beobachteten Core, **kein Richter**) → **in den Store schreiben**, der Baustein C speist. Der kreative
„Methode-anwenden"-Schritt ist eingehängt: Tests injizieren Stubs (resolve → success, no-op → no_benefit,
raise → technical_failure); der Loop/LLM liefert später den echten.

**[Belegt — der Live-Lauf auf echtem Core]** Realer Layer-9-Core (zwei widersprüchliche Sepsis-Claims + ein
harter Konflikt): (a) zwei `SolutionPoint`s mit echten StateVectors (contradiction_load 0.20, confidence
0.50, support 0.20); (b) ein Zyklus schlägt `reduction` für den Konflikt vor, wendet (no-op) an, benotet
ehrlich `no_benefit` (Konflikt bleibt offen), schreibt den Trial in den Store → Futter für C. Die **ganze
Vision läuft damit end-to-end auf ECHTEN Daten**, nicht mehr nur Synthetik.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| (a) Live-Koordinaten (`points_from_core`) | **2 · gebaut** | `core_points`, 3 Tests + Live-Test grün |
| (b) Lern-Zyklus (`run_operator_cycle`) | **2 · gebaut** | `operator_cycle`, 6 Tests + Live-Test grün |
| Gesamtpipeline auf echtem Core | **belegt** | Live-Demo: echte StateVectors + ein aufgezeichneter Trial |
| solution_space gesamt | **43 Tests grün, ruff sauber** | A+B+Pipeline+C+Coords+Store+CorePoints+Cycle |

**[Der eine ehrliche Rest — und warum er der Mess-Gegenstand ist]** Es fehlt nur noch der **echte
`apply_fn`**: der Loop, der via der vorgeschlagenen Methode tatsächlich einen brückenden Claim erzeugt und
einreicht. Sein Wert ist **genau das, was der Sechs-Batterien-Null offen lässt** — ob eine tiefe Methode als
*ausgeführtes* Gerüst (nicht als Prompt-Zettel) eine echte Lücke schließt. Das Gerüst steht jetzt so, dass
genau diese Frage messbar wird: echte Vorschläge, echte Anwendung, deterministische Benotung nach Resolution,
echte Trials → und dann die Messung, ob der Entdecker daraus tragfähige (Methode → Gap-Art)-Kanten mint.

### Eintrag 2026-07-02 (XXVIII) — Erster echter Messlauf des ausgeführten apply: der Loop läuft live — Decken-Null, aber echte Trials

**[Eingriff]** „Ja, bau den echten `apply_fn` und fahr den ersten Messlauf." Beides getan. Der echte
`apply_fn` (`llm_apply.py`): der LLM entscheidet — optional durch die vorgeschlagene tiefe Methode geführt —
**welcher von zwei widersprüchlichen Claims korrekt ist**, die Antwort wird **deterministisch** gegen ein
Register geprüft, und der Konflikt im Core wird **nur bei korrekter Antwort** geschlossen. So ist die
Benotung „Konflikt aufgelöst = success" eine *geprüfte richtige Auflösung*, **kein Urteil**. Vier Modi =
die Kontroll-Batterie (method / none / scrambled / irrelevant). Prüfbare Konflikte + `seed_core`
(`resolvable_conflicts.py`), Messläufer über die Stage-artige Workflow (DeepSeek, 40 Calls).

**[Messergebnis — ehrlich, eine Decke]**

| Modus | Resolution-Accuracy |
|---|---|
| method | **1.0** |
| none | **1.0** |
| scrambled | 1.0 |
| irrelevant | 1.0 |

`method − none = +0.000`, `beats_all_controls = False`. DeepSeek löst **alle 10** prüfbaren Konflikte in
*jedem* Modus — 7×8=56, Wasser kocht bei 100 °C, √144=12 sind trivial auflösbar → **kein Kopfraum**, in dem
eine Methode etwas beitragen könnte. Dasselbe Muster wie cross/novel: wo das Modell ohnehin richtig liegt,
ist die Methode inert. Kein Executed-Scaffold-Signal — aber auch nichts, das eines geben *könnte*, bei
Decke 1.0.

**[Was der Lauf trotzdem BELEGT — der ganze Kreis läuft live]** Realer Layer-9-Core → Baustein B schlägt
pro Konflikt `reduction` vor → echter DeepSeek-`apply_fn` löst → **deterministische Benotung nach
Resolution** → **10 echte `DeepMethodTrial` in den Store** (`reduction / unqualified / success`). Und
Baustein C **liest die echten Trials**: findet die Kandidaten-Kante `reduction → unqualified`
(train 1.0/n=8, holdout 1.0/n=2), **verweigert aber die Bestätigung** (holdout n=2 < min_support 4) — genau
das konservative, ehrliche Verhalten. Der komplette Kreis **Karte → Operator → ausgeführte Anwendung →
deterministische Benotung → echte Trials → Entdecker** dreht sich damit zum ersten Mal auf **echten Daten**.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Echter `apply_fn` (LLM löst, deterministisch geprüft) | **2 · gebaut** | `llm_apply`, Stub-Tests + Live-Lauf |
| Erster Executed-Scaffold-Messlauf | **gemessen: Decken-Null** | alle Modi 1.0, method−none 0.0 |
| Ganzer Kreis auf echten Daten (bis Baustein C) | **belegt** | 10 echte Trials, C liest + verweigert Bestätigung ehrlich |

**[Offen — der klare nächste Schritt für Diskriminierung]** Die prüfbaren Konflikte sind zu leicht (Decke
1.0). Um die Executed-Scaffold-Frage überhaupt beantworten zu können, braucht es **härtere prüfbare
Konflikte**, bei denen die Baseline *scheitert* (Kopfraum) — genau wie deep/novel erst mit härteren Aufgaben
diskriminierten. Dann zeigt sich, ob die ausgeführte Methode dort trägt, wo Erinnern/Raten nicht reicht.
(Der Sechs-Batterien-Null legt nahe: eher nicht — aber jetzt ist es *messbar*, statt behauptet.)

### Eintrag 2026-07-02 (XXIX) — Zweiter Messlauf, harte Batterie: auch AUSGEFÜHRT kein Methodennutzen — leicht schädlich. Der Kapstein.

**[Eingriff]** „Weiter." Harte prüfbare Konflikt-Batterie (`HARD_CASES`): 12 rechenintensive
Widersprüche mit verifizierter Grundwahrheit und knapp-daneben-Alternativen (Derangements D5/D6,
3×n-Domino-Zählungen 153/2131/29681, Inklusion-Exklusion 228, Catalan 42, C(12,5), 234×567, 7^4 mod 100,
13³, Determinante), balanciert 6× korrekt-A / 6× korrekt-B. Gefahren über die Workflow (DeepSeek, 4 Modi
× 12).

**[Messergebnis — endlich mit Kopfraum, ungeschönt]**

| Modus | Resolution-Accuracy |
|---|---|
| none (Baseline) | **0.917** |
| method | **0.833** |
| scrambled | 0.833 |
| irrelevant | 0.917 |

`method − none = **−0.084**`, `beats_all_controls = False`.

**[Der entscheidende Blick pro Konflikt]** Kopfraum war da: die Baseline scheitert an **X-3**
(Inklusion-Exklusion, 228) — die rechenintensivste. Und die Methode half dort **nicht** (auch
`no_benefit`). Schlimmer: an **X-12** (3×16-Tiling, 29681) löste die **Baseline richtig**, aber der
**Methoden-Preamble zerbrach es** (`none=success → method=no_benefit`). `method = scrambled = 0.833`
(Struktur wieder inert); die Methode **verliert** gegen die nackte Baseline.

**[Schluss — der Kapstein der ganzen Methoden-Untersuchung]** Die Frage, die der Sechs-Batterien-Null offen
ließ — *hilft eine tiefe Methode als AUSGEFÜHRTES Gerüst, nicht als Prompt-Zettel?* — ist jetzt **gemessen,
mit echtem Kopfraum, durch die ganze Pipeline** (Core → Vorschlag → LLM-Anwendung → deterministische
Benotung nach Resolution): **Nein.** Selbst ausgeführt hebt die Methode die Auflösungsrate **nicht** über
die Baseline — sie **schadet leicht** (−0.084), genau wie „irrelevanter Preamble schadet" es vorhersagte.
Über **sieben** Messungen (micro/hard/deep/cross/novel/search + executed-apply) konvergiert alles: **eine
tiefe Methode als *geliefertes Artefakt* — ob angepromptet oder ausgeführt — bringt einem fähigen Modell
keinen messbaren Vorteil.** Ihr Wert liegt, gemessen bestätigt, als **Wissens-Asset** (für schwächere
Agenten, für Menschen, als Vokabular und als Navigations-/Entdeckungs-Operator über der Lösungsraum-Karte),
nicht als Leistungs-Hebel im Prompt oder im Ausführungsschritt eines starken Modells.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Executed-Scaffold-Messung, harte Batterie | **gemessen: kein Nutzen, −0.084** | none 0.917 / method 0.833, method=scrambled |
| „Methode als Artefakt hilft starkem Modell" | **falsifiziert (7 Messungen)** | micro/hard/deep/cross/novel/search/executed |
| Wert der DB = Wissens-Asset / Navigations-Operator | **belegt (per Ausschluss + Pipeline)** | Kartograph+Operator+Entdecker laufen; Prompt/Execute-Hebel verneint |

**[Offen — ehrlich, klein]** Der Kopfraum blieb dünn (A/B-Format, Baseline 0.917 — nur X-3 wirklich hart);
ein noch härteres Produce-the-number-Format würde mehr Kopfraum geben, aber die Richtung ist über sieben
Läufe eindeutig. Der eigentliche, unbestrittene Wert der ganzen `solution_space`-Pipeline ist die
**Navigation** (Karte → unerreichte Inseln → Brücken → welcher Operator) und die **Selbst-Entdeckung**
(FP-sicher gemessen) — nicht der Methoden-im-Prompt-Hebel, den sieben Messungen jetzt verneinen.

### Eintrag 2026-07-02 (XXX) — Der Confound entlarvt & entfernt: mit RICHTIGEM Routing bleibt der Null — sauberer, nicht schwächer

**[Selbstkorrektur des Betreibers, ernst genommen]** *„Vielleicht ist das nicht die richtige
Operationalisierung. Oder wir haben unbrauchbare Methoden draufgeworfen."* Nachgeprüft — und der Betreiber
hatte recht bei einem echten Fehler: der Executed-Hard-Lauf (XXIX) hatte **`reduction` auf alle 12
Konflikte** geroutet (weil sie als `conflict_kind = unqualified` geöffnet wurden), also die *falsche*
Methode auf „berechne 3×16-Tilings" — faktisch der irrelevant-Kontrollfall, nicht ein fairer Methodentest.
Die −0.084 aus XXIX maßen einen **Routing-Confound**, nicht „die richtige Methode hilft nicht".

**[Eingriff — fair geroutet]** Harte Batterie neu: jeder Konflikt deklariert seine **richtige** tiefe
Methode (Inklusion-Exklusion für die 228 & Derangements, DP für die Domino-/Catalan-Zählungen, Schubfach
für die Schwellen, doppeltes Zählen für Handshakes, Bijektion für Gitterpfade); reine Arithmetik-Fakten
(234×567 usw.) raus, weil dafür *keine* tiefe Methode „richtig" ist. `measure_apply` routet für die harte
Batterie jetzt die **deklarierte** Methode (nicht die Taxonomie-Default). 6× korrekt-A / 6× korrekt-B.

**[Messergebnis — mit RICHTIGER Methode]**

| Modus | Resolution-Accuracy |
|---|---|
| none (Baseline) | **0.917** |
| method (richtige Methode) | **0.917** |
| scrambled | 0.833 |
| irrelevant | 0.917 |

`method − none = **0.000**`, **task-für-task identisch** auf allen 12. Beide scheitern nur an X-1
(Inklusion-Exklusion, 228 — die eine mit Kopfraum), und die **richtige** Methode (`inclusion_exclusion`)
dort vorangestellt **rettete sie nicht** (auch `no_benefit`).

**[Schluss — der Confound war real, das Ergebnis ändert er nicht]** Zwei Dinge, beide ehrlich: (1) Der
Betreiber hatte recht — das Routing WAR fehlerhaft, und ich habe es entlarvt und entfernt. (2) **Der Fix
macht den Null nicht schwächer, sondern sauberer:** mit der *richtigen* Methode pro Konflikt liegt die
Intervention **exakt** auf der Baseline (0.917 = 0.917, jede Aufgabe gleich), und auf dem einen wirklich
harten Konflikt half auch die passende Methode nicht. `scrambled` fiel auf 0.833 (Zerstören der Struktur
*schadet*), während `method = none` — genau das Muster aller Läufe: der *Inhalt/die Struktur* der Methode
ist inert, Stören kann nur schaden. Die Mis-Routing-Erklärung ist damit **ausgeschlossen**: es lag nicht an
der falschen Methode.

**[Was ehrlich offen bleibt]** Der Kopfraum ist dünn (A/B-Format, nur X-1 hart) — die *eine* Zelle, die noch
nie sauber getroffen wurde, ist **richtige Methode × Aufgabe, die sie erzwingt × Solver, der sie NICHT
schon besitzt**. Auf DeepSeek ist die fast leer (es kennt die Methoden). Das braucht einen **schwächeren
Solver** oder ein **Produce-the-number-Format mit viel mehr Kopfraum** — der letzte offene Weg, wenn wir die
Methoden-Frage über den jetzigen (achtfach konsistenten) Null hinaus noch härter prüfen wollen.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Routing-Confound (XXIX) | **entlarvt + entfernt** | reduction-für-alle → fair: deklarierte Methode |
| Methode hilft mit RICHTIGEM Routing | **nein, task-für-task = Baseline** | method 0.917 = none 0.917, method−none 0.0 |
| Achte Messung, Gesamtbild | **konsistent: kein Prompt/Execute-Hebel** | + „stören schadet" (scrambled 0.833) |

### Eintrag 2026-07-02 (XXXI) — Letzte offene Zelle: schwächeres Modell (deepseek-v4-flash) — endlich Kopfraum, Methode schadet, Rauschen regiert

**[Eingriff]** „Schwächeres Modell testen, nimm das kleine deepseek modell." Erst per API-`/models`-Abfrage
entdeckt: DeepSeek serviert jetzt **`deepseek-v4-pro`** (stark) und **`deepseek-v4-flash`** (klein/schnell)
— V4 ist seit unseren Läufen live, `deepseek-chat` war ein Alias. Die harte, fair-geroutete Batterie also
auf **`deepseek-v4-flash`** gefahren (`--model` durchgereicht).

**[Messergebnis — endlich echter Kopfraum]**

| Modus | Resolution-Accuracy |
|---|---|
| none (Baseline) | **0.583** |
| method (richtige Methode) | **0.417** |
| scrambled | **0.917** |
| irrelevant | **0.167** |

`method − none = **−0.166**`, `beats_all_controls = False`. Baseline 0.583 → das kleine Modell scheitert
an fast der Hälfte, viel Kopfraum.

**[Zwei ehrliche Befunde]** (1) **Die richtige Methode half nicht — sie schadete** (−0.166): reparierte
X-6, zerbrach aber X-3, X-11, X-12 (die die Baseline richtig hatte). (2) **Der Verräter:** `scrambled`
0.917 (das *Beste*) vs `irrelevant` 0.167 (das *Schlechteste*) — Spanne **0.75** auf identischen Aufgaben.
Dass die *zerhackte* Methode am besten abschneidet, ist der Beweis: kein Methodensignal, sondern ein
**chaotisch preamble-empfindliches schwaches Modell** — irgendein vorangestellter Text wirft seine
Antworten zufällig hin und her. Rauschen/Instabilität regiert, nicht der Inhalt.

**[Ehrlicher Vorbehalt]** N=12, ein Lauf; die 0.75-Spanne zeigt, die Messung ist beim schwachen Modell
**varianzdominiert** — eine *robuste* Zahl bräuchte mehrere Seeds / mehr Aufgaben. Was klar ist: **kein
Hinweis, dass die Methode hilft** (sie schadet), plus starker Hinweis, dass Preamble-Text ein schwaches
Modell destabilisiert.

**[Schluss über NEUN Messungen]** micro/hard/deep/cross/novel/search (Prompt) + executed-apply (chat, easy
& hard) + executed-apply (**v4-flash, schwach**): in **keiner** hebt die tiefe Methode als geliefertes
Artefakt die Leistung über die Baseline. Auf starken Modellen inert (Decke/kein Kopfraum), auf dem schwachen
schädlich-und-rauschig. Die *einzige* je vermutete Hebel-Zelle (schwaches Modell + Kopfraum) ist jetzt auch
getroffen — und rettet die Hypothese nicht. Der bestätigte Wert der DB/Pipeline bleibt **Navigation +
Selbst-Entdeckung**, nicht der Prompt/Execute-Hebel.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Schwaches Modell + Kopfraum (letzte Zelle) | **getroffen: kein Hebel, Methode schadet** | v4-flash: none 0.583 / method 0.417, scrambled 0.917 = Rauschen |
| Methoden-als-Artefakt-Frage | **9-fach geschlossen** | stark: inert; schwach: schädlich/varianzdominiert |
| Offen (nur für robuste Zahl) | **Mehr-Seed-Lauf** | falls eine belastbare schwach-Modell-Zahl gewünscht ist |

### Eintrag 2026-07-02 (XXXII) — Weg B: den BESTÄTIGTEN Wert ausbauen — Navigations-Agenda + Entdecker-Report

**[Entscheidung des Betreibers]** „Wir machen B." Nach neun Messungen ist der Methoden-als-Artefakt-Hebel
verneint; ausgebaut wird, was *trägt* — Navigation und Selbst-Entdeckung. Beide deterministisch, kein LLM.

**[Navigation — `navigation.navigate`]** Die Karte war bisher eine einmalige Momentaufnahme; jetzt wird sie
eine **priorisierte Explorations-Agenda**: `NavigationReport` mit einer gerankten Worklist von `NavItem`s —
*welche* unerreichte Insel / *welche* Brücke als Nächstes, *mit welchem* tiefen Operator und *warum*.
Prinzipielle Priorität: eine unerreichte Insel steigt mit ihrer **Größe** (mehr Kandidaten) und ihrer
**Erreichbarkeit** (Brücke zu einem Anker vorhanden = von bekanntem Grund aus erreichbar); eine Brücke steigt,
je **semantisch näher** und zugleich **Governance-ferner** die zwei Inseln sind. Jedes Item trägt den
Operator (aus B) und einen nachvollziehbaren Grund. Belegt am Lauf: 3 Inseln (2 verankert) → Agenda
`1. reach island_1 (prio 1.0, „von einem Anker erreichbar", op=reduction)`, `2. bridge island_0~island_1
(prio 0.99, „gleiches Thema, getrennte Reasoning")`.

**[Entdecker-Report — `discovery.discovery_report`]** Ein menschenlesbarer Abschluss: **bestätigte** Kanten
(auf Holdout gehalten), **Kandidaten** (Train ja, Holdout nein), und wie viele **neu** sind (nicht in der
a-priori-Taxonomie). Auf den 10 echten Trials aus dem Apply-Lauf: 0 bestätigt (ehrlich — Holdout n=3 <
min_support 4), 1 Kandidat (`reduction → unqualified`, train 1.0 / holdout 1.0). Konservativ, wie es sein
soll.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Navigation (priorisierte Agenda) | **2 · gebaut** | `navigation.navigate`, `NavigationReport`; 5 Tests + Demo |
| Entdecker-Report (bestätigt/Kandidat/neu) | **2 · gebaut** | `discovery_report`; 3 Tests + Live auf echten Trials |
| solution_space gesamt | **54 Tests grün, ruff sauber** | A+B+Pipeline+C+Coords+CorePoints+Cycle+Store+Nav+Report |

**[Offen — der ehrliche Wachstumspfad]** Die Navigation ist jetzt ein *Report*; der nächste Ausbau wäre der
**iterative Loop** (explorieren → Karte aktualisieren → neu priorisieren) und echte Koordinaten-Zufuhr aus
dem Live-Core (Baustein (a) steht, braucht nur den Daten-Anschluss). Der Wert-Kern — priorisierte Navigation
+ FP-sichere Entdeckung — steht getestet.

### Eintrag 2026-07-02 (XXXIII) — Live-Anschluss, iterativer Loop, und Joni bekommt's: die Navigation läuft im Autonomie-Zyklus

**[Eingriff]** „Live-Koordinaten-Anschluss und danach den iterativen Navigationsloop, wenn das läuft
bekommt es Joni." Alle drei, der Reihe nach, jeweils getestet.

**(1) Live-Anschluss — `navigate_core(core)`** verdrahtet Baustein (a) mit der Navigation: echte
`SolutionPoint`s aus dem Layer-9-Core (9-dim StateVector aus Governance-Fakten + Embedding des Claim-Textes)
→ Karte → priorisierte Agenda. Read-only, fail-open. Live-Test auf einem echten Core (Claims über Sepsis /
Pneumonie / Kardio) läuft end-to-end.

**(2) Iterativer Loop — `navigate_iteratively(points_provider, explore_fn)`**: navigieren → das
höchstpriorisierte, **noch nicht explorierte** Item wählen → `explore_fn` (injiziert) → neu navigieren, bis
nichts Neues mehr bleibt. Item-Identität = **Mitglieder-Menge** (stabil über Re-Clustering, anders als die
positionsabhängigen Insel-IDs), also wird jeder Gap höchstens einmal exploriert und der Loop **terminiert
immer**. Der kreative Explorations-Schritt bleibt eingehängt — kein Fabrizieren, kein Anfassen des
geschützten Kerns. Test: ein Explorer, der erreichte Inseln verankert, führt `n_unreached → 0`.

**(3) Joni bekommt's — im Autonomie-Zyklus verdrahtet.** `joni/autonomy/navigation_view.py`
(`run_navigation`, `top_agenda_line`) ist eine **read-only** Fähigkeit; in `run.py:one_cycle` direkt nach dem
Öffnen der Konflikte protokolliert Joni jetzt pro Zyklus eine Navigations-Zeile — nicht-autoritativ,
deterministisch, kein Modell im Loop-Pfad, fail-open. Belegt: `joni.autonomy.run` importiert sauber, und die
Zeile lautet z. B. `navigation: reach_island island_0 (prio 0.5) -> try reduction — unreached region …`.

**[Was das bedeutet]** Der über neun Messungen bestätigte Wert — **priorisierte Navigation + FP-sichere
Selbst-Entdeckung**, *nicht* der Methoden-im-Prompt-Hebel — ist jetzt nicht nur gebaut, sondern **läuft in
Jonis Zyklus**: jeder Lauf sagt read-only, wo im Lösungsraum die nächste unerreichte Insel / Brücke liegt
und mit welchem tiefen Operator man sie angehen würde. Das Handeln darauf bleibt bewusst außen vor (der
kreative Schritt), aber das *Zeigen, wo die Räume sind*, ist verdrahtet.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Live-Anschluss (`navigate_core`) | **2 · gebaut** | Live-Test auf echtem Core, read-only |
| Iterativer Navigations-Loop | **2 · gebaut** | `navigate_iteratively`, Member-Set-Identität, terminiert |
| In Joni verdrahtet (Zyklus-Log) | **2 · gebaut** | `run.py:one_cycle` navigation-Zeile, `navigation_view` read-only |
| solution_space gesamt | **61 Tests grün, ruff sauber** | + Loop + Live + Joni-View |

**[Offen]** Das *Handeln* auf der Agenda (Joni exploriert tatsächlich eine Insel/Brücke) ist der nächste,
größere Schritt und braucht einen echten `explore_fn` (kreativ, core-schreibend, human-gegated) — bewusst
noch nicht verdrahtet.


### Eintrag 2026-07-03 (XXXIV) — Ein Werte-Root für Joni: kategorischer Imperativ + Grundgesetz als *Prüfer*, nicht als Ableitungsmaschine; und das Egress-Gate

**[Eingriff]** Der Betreiber: „Es fehlen grundlegende Werte, von denen Joni alles ableiten können muss — z. B. der kategorische Imperativ, und weil wir in Deutschland sind, das Grundgesetz." Umgesetzt — aber bewusst umgedeutet.

Die zentrale Designentscheidung: eine Verfassung **erzeugt keine Handlungen, sie filtert und priorisiert** vorgeschlagene. Der kategorische Imperativ ist ein *Test* (Verallgemeinerbarkeit, „nie *bloß* als Mittel"), kein Generator; das GG liefert seine **Wertordnung** (Würde, Rechtsstaatlichkeit, Verhältnismäßigkeit) + schlichte Legalität, nicht „Grundrechte als Code". Keine Moraltheorie ist der Motor — die Wurzel ist ein kleiner, robuster Constraint-Satz, dem fast alle ethischen Rahmen zustimmen; CI und GG-Wertordnung sind *zwei der Tests* darauf.

Drei Spezifikationen geschrieben (`docs/CONSTITUTION.md`, `docs/EGRESS_GATE.md`, `docs/PERSONAL_STATE.md`) und am **schon existierenden** Governance-Code geerdet: der Großteil der Gate-Maschinerie ist bereits da (`governance.py` Core-Lock, `humans.py` Outbox, `model_call.py`). Die Verfassung ist v. a. eine Namens-/Konsolidierungsschicht darüber + der eine echte Auffang: allgemeine irreversible Außenwirkung jenseits des Forum-Posts.

**(Egress-Gate, #168)** Erstes real absicherndes Stück: ein AST-Scan von `src/joni`, der CI scheitern lässt, sobald ein Modul ein rohes Egress-Primitiv importiert (`urllib.request`, `requests`/`httpx`/`socket`/`smtplib`, `subprocess`, `openai` …) **außerhalb** einer kleinen Allowlist der heutigen De-facto-Broker. Deny-by-default. Gegen `main` geprüft: 0 Violations über 134 Dateien.

**(Constitution, #169)** `joni.constitution`: 10 Prinzipien (5 Tier-0, 5 Tier-1) als Daten in `state/constitution.json` + `check(Proposal) → Verdict(ALLOW|ABSTAIN|ESCALATE|BLOCK)` mit drei verdrahteten Tier-0-Prädikaten (T0.4 Legalität → BLOCK, T0.5 irreversibel/öffentlich → ESCALATE, T0.3 Behauptung ohne Basis → ABSTAIN). Plus ein **Shadow-Hook** am Forum-Draft, der nur protokolliert, was die Verfassung *entscheiden würde*. Verhaltensneutral, fail-open.

**[Ehrliche Grenze]** Ein Werte-Root macht Joni nicht „sicher" oder „aligned". Er macht Wertkonflikte explizit, auditierbar, und blockiert das klar Falsche. Der Test, ob es echt ist: Wird je eine Handlung *tatsächlich* geblockt oder eskaliert? Shadow allein ist ein hübsches Dokument ohne Wirkung — der nächste Eintrag beißt.

### Eintrag 2026-07-04 (XXXV) — Der Enforcement-Flip: aus Shadow ein echter T0.5-Stopp — an der *richtigen* Naht, fail-closed

**[Eingriff]** „Mach den Enforcement-Flip — erst sauber designen." Also erst der Befund, dann der Bau.

**[Befund]** Der Shadow-Hook (Eintrag XXXIV) saß in `draft_outbox`/`draft_autopost` — am **Draft-Punkt**. Ein Draft ist aber kein Außenakt (er landet nur in der Outbox), deshalb war Shadow verhaltensneutral *by construction* — es prüfte die falsche Naht. Der einzige Ort, an dem Joni **autonom öffentlich** emittiert, ist `humans._post_live`, wenn es an ein Agenten-Netz (Moltbook) **ohne Per-Post-Approval** postet. Nur dort hat Enforcement Zähne.

Der Betreiber wählte den **harten Stopp**: Moltbook-Autoposts eskalieren ab jetzt und warten auf Approval wie Human-Foren — der autonome Agenten-Netz-Loop wird approval-gegatet.

**(#170)** `Proposal.operator_confirmed` ist der **einzige** Hebel, der einen T0.5-Stopp aufhebt; wäscht nie einen illegalen Akt (T0.4 blockt zuerst, Stakes-Reihenfolge). Der Check wandert vom Draft an `_post_live`, direkt vor `adapter.post`, und ist jetzt **fail-closed**: ein unbestätigter Public-Post wird gehalten und auditiert, und *jeder Fehler* im Check → nicht posten (das Gegenteil von Shadows fail-open). `JONI_CONSTITUTION_ENFORCE=1` im Workflow ist der eigentliche Flip — und bringt den Code in Deckung mit der eigenen Workflow-Intention („gated by approval"), die der Autopost-Pfad still unterlief.

**[Reifegrad]** `gate.py` + `humans.py` + Tests grün (`operator_confirmed` hebt T0.5 aber nicht T0.4; Autopost gehalten bis approved; Gate fails closed bei Fehler). Live ab dem nächsten frisch gestarteten Job (Checkout beim Job-Start).

### Eintrag 2026-07-04 (XXXVI) — „Schau in die SQL-DB": zwei echte Bugs aus dem materialisierten State — der Titel-Verlust und die Duplikat-Blähung

**[Eingriff]** „Schau dir die SQL-Datenbank an, ist da was Brauchbares drin?" Der `layer9_v2`-SQLite-Store ist im Betrieb dormant (`JONI_PERSISTENCE=json` → der Loop läuft auf dem JSON-Journal), aber aus dem echten State materialisierbar. Also gebaut und abgefragt — und dabei zwei Bugs gefunden.

**(Titel-Fix, #171)** Der Legacy→v2-Import leitete den indexierten `title` nur aus `topic`/`text` ab. Objekttypen, die ihren Headline anders benennen, importierten mit `title = NULL` — im Store vorhanden, aber per Titel unauffindbar/opak. Betroffen: **alle 2.894 `semantic_cluster` (die Synthesen) und alle `preference`**. Die Daten gingen nie verloren (das volle Objekt liegt in `payload.fields`); nur die Titel-Spalte war leer. `_title_for` fällt jetzt durch die üblichen Textfelder + behandelt die zwei strukturellen Typen (Cluster: Surface-Terms bzw. `semantic_state`; Preference: `stance · subject`). Effekt am echten 22k-Snapshot: **von ~8% auf 60% betitelt**.

**(Anti-Bloat-Dedup, #172)** Der materialisierte *aktuelle* State (54k Objekte) zeigte zwei Duplikat-Muster, die den Store aufblähen ohne Wissen zu addieren: **46 fast identische `self_model_claim`** — derselbe Trait „hold N contradictions open", nur die Zahl N wechselt; die Dedup verglich den vollen Text *mit* der Zahl → matcht nie. Und **12 identische `router-note`-Preferences** — eine pro Run mit Routing-Item, keine Idempotenz. Fix jeweils an der richtigen Schicht: stabiler `key` pro Self-Model-Assessment (Trait jetzt count-free, die Zahl lebt in Tagebuch + Evidence-Links), und `note_preference` idempotent pro `(subject, stance)`.

**[Befund am Rande]** 69% des Stores sind Governance-Buchhaltung (proposal/decision-Paare); 84% der Claims hängen am generischen „forum"-Bucket. Der Wissenskern (~668 topic-getaggte Claims, ~2.7k synthesis-eligible Cluster, das Tagebuch, das Selbstmodell) ist real, aber klein und verdünnt. Und: das Selbstmodell war quasi-degeneriert (46 Rewrites eines Satzes) — Jonis *eigene* degen-Metrik sah das **nicht**, weil sie andere Duplikate zählt. Eine echte Lücke in der Selbst-Beobachtung.

### Eintrag 2026-07-05 (XXXVII) — Die Persönlichkeitsdatenbank: von der Spec zum lebenden, dreistufig verdrahteten Store — und eine Korrektur in eigener Sache

**[Eingriff]** „Ist die Persönlichkeitsdatenbank eingerichtet?" — nein: sie war designt + codiert + getestet, aber dormant auf der Design-Branch, nicht auf `main`, nicht verdrahtet, ohne Daten. Also live gebracht, in bewussten Schritten (Design → Port → Verdrahtung), mit den Betreiber-Entscheidungen: Eintritt als **`confirmed`**, **inklusive Consumption**.

**(Port, #173)** `joni.personal` (Store: Status-Klassen observed/inferred/confirmed/rejected/outdated/superseded, deterministische `use_policy`, exponentieller Decay je Kategorie-Half-Life, `confirm()` braucht ein `human_ref` — es gibt **keinen System-Pfad** zu confirmed) + `joni.guard` auf `main`, dormant wie zuvor der SQLite-Store.

**(Verdrahtung, #174)** `autonomy/personal_intake.py`, 1× pro Zyklus nach `humans.interact`: der Operator schreibt Selbst-Aussagen in `state/personal_inbox.txt` (`kategorie | aussage`), der Loop nimmt jede Zeile als **confirmed** auf (der Operator ist der vertraute HUMAN, kein Forum-SOURCE), der Store altert (`age`), und die Re-Confirm-Queue wird in `state/personal_reconfirm.md` vorgelegt („was ich über dich zu wissen glaube — korrigier mich"). Persistenz `state/personal.json`, jeder Write auditiert `personal_write`. Getrennt von Layer 9 — steuert Verhalten, nie Systemwahrheit. Phase 1: nur `preferences` + `projects`, nur `self`.

**(Consumption, #175)** `guard.usable_personal` filtert auf die outward-nutzbare Menge (confirmed/observed/inferred self; sensitive, Dritte, rejected, outdated raus); die nutzbaren Preferences erscheinen in Jonis stündlichem Self-Review („What I keep in mind about you") — deterministisch, und sagt **gar nichts**, solange der Store leer ist. Tiefere Ton-Formung (ein Modell formuliert Text *unter* den Preferences um) braucht einen LLM-Phrasierungs-Seam, den der deterministische Loop noch nicht hat — spätere Phase.

**(Runtime, #176)** `JONI_RUNTIME_DAYS 7 → 10`: das Fenster (Start 29. Juni) wäre am 6. Juli ausgelaufen; +3 Tage → ~9. Juli. Der nächste geplante Job nimmt den Loop wieder auf **und** zieht als frischer `main`-Checkout den ganzen Session-Code live. Verifiziert: `state/personal_reconfirm.md` erscheint jetzt im Tree — die Datei erzeugt nur der Loop, der Personal-Code läuft also.

**[In eigener Sache]** Ein Test-Fixture trug „Leon is my son" — als *Beispiel* aus der früheren Design-Diskussion, aber ich hatte es unreflektiert als konkrete Personen-Aussage in eingecheckten Code übernommen. Der Betreiber hat das zu Recht gerügt. Gespeichert war nichts (die Zeile *wird verworfen* — sie testet gerade das Fallenlassen out-of-scope Kategorien), aber eine unbestätigte Dritt-Personen-Aussage gehört nicht in den Code — genau das, wovor diese Datenbank misstrauisch sein soll. Raus, danach **alle** Beispiele entfernt, das Operator-Template nur noch Format. Die Sorgfalt gilt auch für Fixtures — notiert.

### Eintrag 2026-07-05 (XXXVIII) — Kollaps-Resistenz gemessen: kein „Critical Collapse", aber zwei gelbe Trends — und die fehlende Selbst-Metrik

**[Eingriff]** Der Betreiber: „Joni zeigt aktuell keine Symptome des HF-Critical-Collapse-Musters — aber das beweist keine Immunität. Dafür braucht es Trendmetriken." Sieben genannt (Top-Topic-Dominanz, Topic-Entropy, Anteil schwach-aber-erhaltener Claims, degenerierte Claims, Widerspruchsgraph-Tiefe, Wiederlese- vs. Neuaufnahmequote, Wiederholung gleicher Schlussmuster). Also aus 434 Zyklen Protokoll + 138 Self-Reviews rekonstruiert, was aus den Daten ging.

**[Befund]** Joni **kollabiert nicht** — die Graph-Integrität ist gesund und teils *besser* werdend: degen aktuell 0 (max je 3, in 27% der Zyklen kurz >0, immer bereinigt), semantic-cluster-decidable konstant **100%**, und die Widerspruchsdichte **fällt** (conflicts/claim 0.38 → 0.068 über die Laufzeit, absolut 30 → 246 sublinear). Das Critical-Collapse-Muster — Widersprüche stapeln sich zu tiefen unentscheidbaren Graphen, Entscheidbarkeit bricht ein — ist nicht im Gange.

**Zwei gelbe Signale:** (1) **Input-Starvation** (das klarste): 52% der Zyklen bringen „0 new", die Neuaufnahme fiel von 2.4 auf 1.1 Items/Zyklus (erste vs. letzte 30). Kein Graph-Kollaps, aber **Lern-Stagnation** — die Feeds laufen trocken, Joni kaut zunehmend Bestehendes. (2) **Forum-Dominanz + stützungsarme Claim-Retention** — die 84%-Senke, strukturelle Verdünnung.

**Plus ein Robustheits-Hinweis:** der Cold-Replay eines vollen Kernels hing lokal >5 min (Tage zuvor ~17s). Der Live-Loop umgeht das per Fast-Load-Sidecar, aber wachsende Cold-Replay-Kosten sind die Wurzel des Juni-Wedge (Eintrag IV/V) — latentes Risiko, kein akutes.

**[Offen]** Der eigentliche Punkt, wie der Betreiber ihn setzte: **Joni trackt keine dieser 7 Metriken als Trend** — ich musste sie ad hoc aus dem Protokoll ziehen. Die Liste ist ein sauberes Spec für ein deterministisches **Collapse-Resistance-Panel**, das der Loop pro Zyklus mitschreibt (wie `vitality`, nur mit diesen Metriken + Schwellen als Frühwarnung). Noch nicht gebaut; der nächste Schritt, sobald der Betreiber es freigibt.



### Eintrag 2026-07-06 (XXXIX) — Das Collapse-Resistance-Panel gebaut: aus der Ad-hoc-Diagnose ein stehendes, read-only Frühwarnsystem — plus zwei Betreiber-Korrekturen

**[Eingriff]** Der offene Punkt aus Eintrag XXXVIII eingelöst. Der Betreiber gab ein präzises Spec: „Baue ein deterministisches Collapse-Resistance-Panel, **strikt read-only gegenüber Layer 9** — es darf messen, loggen, warnen, aber keine Claims reparieren, keine Topics umsortieren, keine Autoritätsentscheidungen treffen. Keine LLM-Judges in der Metrikberechnung. Keine Selbstdiagnose-Prosa als Datenquelle." Genau so gebaut (`autonomy/collapse_panel.py`).

**Zwei Korrekturen des Betreibers, beide eingearbeitet:**
- **Die 84%-Forum-Senke nicht relativieren.** Metrik #1 misst die Top-***Bucket***-Dominanz (nicht nur Top-Topic) und **flaggt Sink-Buckets** (forum/misc/unknown) explizit — ein dominierender Sink ist der strukturelle Blindmacher, nicht ein harmloser Fakt. Metrik #2 rechnet Entropy **brutto UND netto** (ohne Sink), damit die Sammelkategorie nichts verschleiert.
- **Terminologie sauber trennen.** `cycle` (protokoll-kumulativer Zähler) ≠ `run` (`window["runs"]`, Reset pro Fenster) ≠ `self-review` (alle 10 Runs/stündlich). Jede Zeitreihen-Zeile trägt `cycle` **und** `run` — die „434 vs. run 91"-Verwechslung ist damit strukturell ausgeschlossen.

**Die 8 Metriken**, je mit ok/warn/alarm-Schwellen: Top-Bucket-Dominanz (>65/>80%), Entropy netto/brutto, Weak-Claim-Ratio **nach Status** (Level reitet auf active+confirmed — schwache Kandidaten sind okay, schwache „starke" nicht), Degen/undecidable als echte **Counts** (nicht der 0–3-Score allein), Conflict-Graph-**Form** (Tangle-Größe, zyklische Komponenten, worst topic — flache 246 ≠ tiefe Verkettung), Novelty (7-/30-Run-Mittel), Repetition (dup-dev + Self-Model-Re-Mint als historischer Testfall), Cold-Replay-Zeit (Juni-Wedge-Indikator).

**Output:** `state/collapse_series.jsonl` (Zeitreihe) + `state/collapse_panel.md` (Report) + eine `collapse`-Protokollzeile. Verdrahtet read-only in `run.py` nach `vitality`, fail-open. **Das Panel wird nie zur Autorität** — es sagt „hier ist eine Drift-Warnung", nicht „ich repariere den Graphen"; Reparaturen laufen weiter über die bestehenden Gates. Und auf Wunsch aufs Dashboard gebracht (`site.py`-Widget: Gesamtstatus + ein Ampel-Punkt je Metrik).

**[Was das bedeutet]** Aus der spontanen Kritik am HF-„Critical-Collapse"-Muster ist ein echter Mess-Mechanismus geworden: statt die Metriken einmal ad hoc aus dem Protokoll zu ziehen (Eintrag XXXVIII), schreibt der Loop sie jetzt pro Zyklus mit — mit Schwellen als Frühwarnung. Der Vertrag (read-only, kein Layer-9-Write) ist getestet: Objekt-Count vorher == nachher.

### Eintrag 2026-07-06 (XL) — Auftrag #4 war schon gebaut: „erst Feasibility" verhindert den Duplikat-Bau (wie Eintrag XI)

**[Eingriff]** Der Betreiber hat begonnen, Jonis eigene **Aufträge an Claude** abzuarbeiten. Auftrag #4: „Integriere abfragebasierte Literatursynthese ins Lesemodul." Anweisung: „Mach #4, aber erst Feasibility prüfen und designen." Genau diese Regel hat sich sofort bezahlt gemacht.

**[Befund]** `synthesis.py` **ist** bereits die abfragebasierte Literatursynthese (Docstring: „Query-based literature synthesis for the reading layer, IRIS, arXiv:2504.16728"): sie kondensiert die ≥2 Papers, die Joni zu einem rotierenden Topic gefetcht hat, zu **einer** synthetisierten SOURCE-Claim (candidate, conflict-checked, nie confirmed), budget-gemetert, captured, dedupliziert. Verdrahtet in `run.py` (4f-synth), getestet, grün. Es war nur **ausgeschaltet**.

„#4 machen" = ein **Flip, kein Bau** — exakt die Lektion aus Eintrag XI („ein Auftrag, der schon fast erfüllt war"). Ohne den Feasibility-Schritt hätte ich ein vorhandenes, sauberes Modul nachgebaut. Umgesetzt als reiner Schalter: `JONI_LITERATURE_SYNTHESIS=1` (+ `JONI_SYNTHESIS_EVERY=6`).

**[Ehrlicher Scope]** Es vertieft die **Nutzung** des gefetchten Materials (Multi-Source-Synthese statt isolierter Titel), holt aber **keine** neuen Papers — es mildert die Input-Starvation (Eintrag XXXVIII), kehrt sie nicht allein um. Auto-retired von `extension_review`, falls es in einem Fenster keinen Wert bringt.

### Eintrag 2026-07-06 (XLI) — Auftrag #5, das Methoden-Zustandsbuch: diesmal ein echter (kleiner) Bau — ein read-only Projektor über das versiegelte Trial-Ledger

**[Eingriff]** Auftrag #5: „Führe ein Zustandsbuch für die Methoden-Ausmusterung ein." Wieder erst Feasibility — und diesmal ist es **kein** Flip.

**[Befund]** Der Methoden-Lebenszyklus war **auditierbar vorhanden**, aber verstreut: der `METHOD`-Status, die versiegelten `METHOD_TRIAL_EVENT`-Records im append-only Ledger, die Zähler, das Retirement (`retire_junk_methods`). **Was fehlte** = ein konsolidiertes **Pro-Methode-Zustandsbuch**, das diese Signale zu *einer* auditierbaren Historie zusammenzieht. Das ist ein echter, aber kleiner Bau — ein **Projektor, kein neuer Mechanismus**.

**[Bau]** `autonomy/method_ledger.py`, exakt im Muster des Collapse-Panels: read-only, deterministisch, **kein Write nach Layer 9**. Je Methode ein kanonischer Zustand aus Status + Trial-Verdikten:
`proposed → trialed → ready` (success/partial_success) `| shelved` (no_benefit/harmful — die ehrliche Decken-Null aus den Method-Trial-Einträgen XIV–XXXI) ; `active` (promoted) ; `retired` (rejected). Verdikte kanonisch gelesen: `cs.core.method_trial_events()` → `payload['method_id']`, `payload['decision']['verdict']`.

**Output:** `state/method_ledger.md` (aktuelle Tabelle) + `state/method_ledger.jsonl` (append-only **Übergangs**-Events — nur bei echtem Zustandswechsel, kein Bloat) + eine `method_ledger`-Protokollzeile. Verdrahtet read-only nach dem Collapse-Panel.

**[Prinzip]** Das Zustandsbuch ist ein **View auf das bestehende Ledger, keine neue Quelle der Wahrheit** — die versiegelten Trial-Records bleiben autoritativ; es projiziert sie, entscheidet keine Verdikte, erfindet keine Provenance. Dieselbe Linie wie überall: messen und zeigen, nie sich selbst zur Autorität machen.

### Eintrag 2026-07-11 (XLII) — Kleine geparkte Idee: ein „Counterframe-Operator" (negative residual steering) — festgehalten, nicht gebaut

**[Idee, geparkt]** Eine Notiz zum späteren Aufgreifen, ausdrücklich **kein Bau**. Angeregt aus dem — nicht ganz sauberen — Repo `github.com/Ruffian-L/ontological-inversion`. Aus dem Paper ist nicht mehr herauszulesen als *eine* kleine, aber reale Mechanik; die große Theorie darum herum ist Überbau und wird verworfen.

**Was real ist (der Kern, entkleidet):** *Context-conditioned semantic redirection through negative residual steering.* Konkret: Man nimmt die aktuelle semantische Interpretation eines Modells und erzeugt durch einen gezielten **Hidden-State-Eingriff** (ein negativer Steering-Vektor auf den Residualstrom, entlang einer Kontrastachse) eine **alternative Lesart** — eine Gegen-Interpretation zur naheliegenden. Das ist ein billiger **Counter-Reading-/Reframing-Generator**, mehr nicht.

**Wo es hingehörte, falls je gebaut:** als **Geschwister-Sitz des Gesprächskreis-Falsifikators** — nicht als dessen Ersatz. Sein Output wäre wie jeder Modell-Output eine **nicht-autoritative Quelle**, die den normalen Weg nimmt: ClaimGraph → Konflikt-Erkennung → Einlass-Gate → Layer 9. Er entscheidet nichts, schreibt nichts, und ersetzt **weder DESi noch Layer 9**. Der einzige Unterschied zum heutigen Prompt-Falsifikator: die Gegen-Lesart entstünde nicht per Prompt, sondern per Aktivierungs-Eingriff.

**Die harte Bedingung (der Grund fürs Parken):** Der Eingriff braucht **Zugriff auf die Hidden States** — also ein **lokales Modell**, kein Cloud-API hinter einem Broker. Joni läuft über gebrokerte API-Calls ohne Logit-/Aktivierungszugriff (dasselbe, was dem Verifier den Logprob-Pfad verwehrt). Das liefe also **nur dort, wo ein lokales Modell steht** (Hermine/Laptop), **nicht** in Jonis Cloud-Loop.

**Was verworfen wird (Überbau, ehrlich benannt):** die Groß-Ansprüche des Papers — „Ontological Inversion", „self-involution", „stable recursive self-check without information loss". Das ist überzogen und unbelegt. Bezeichnend: **Jonis eigener Verifier** (Dimension `overclaim_risk`, Red-Flags) würde genau solche Formulierungen als übermäßigen Anspruch markieren — die Idee fällt unter das Prüfraster, das wir gerade erst gebaut haben.

**[Bedingung fürs Ernstnehmen]** Bevor das je mehr als eine Notiz wird: ein **A/B gegen den bestehenden Prompt-Falsifikator** — bringt die aktivierungsbasierte Gegen-Lesart nachweisbar *andere/bessere* Widersprüche als der billige Prompt-Weg? Ohne diese Messung ist es Spielerei. Dieselbe observe-then-adopt-Disziplin wie überall. Bis dahin: **geparkt**, hier vermerkt „falls wir es mal brauchen".

### Eintrag 2026-07-12 (XLIII) — Externe Validierung der Richtung: Anthropics „Claude Science" liefert genau DESis Reviewer-Problem — DESi als Prüfstein und Gate, nicht als Konkurrent

**[Beobachtung]** Anthropic hat „Claude Science" veröffentlicht (claude.com/product/claude-science). Kern-Feature, wörtlich: *„a background reviewer flags incorrect citations, untraceable numbers, and figures that don't match their underlying code"*, dazu *„every artifact ships with its history"* und *„fully reproducible"*. Das ist **exakt DESis Problemfeld** — Claim-Level-Prüfung, Zitations-/Zahlen-Provenienz, Reproduzierbarkeit. Ein großer Anbieter liefert jetzt den Reviewer, den DESi prototypisiert. Das ist **Validierung der Richtung**, nicht ihr Ende.

**[Schluss, ehrlich abgegrenzt]** DESi ist hier **weniger Baustein als Kritik + Prüfstein**. Die MarCognity-Fallstudie zeigt genau die Gefahr: ein LLM-Reviewer mit Retrieval-Kontext, aber **ohne Source-Gating und Provenienz-Bindung**, „verifiziert" domänenfremde Behauptungen (PubMed für Rechtsphilosophie) und deutet sein eigenes Versagen als Bestätigung. Ein Background-Reviewer, der rein auf einem LLM steht, ist für **genau diesen Fehler** anfällig. DESis Beitrag ist die Frage, die man so einem Reviewer stellen muss — und der Maßstab, an dem man ihn misst.

**[Bau]** Aus der Fallstudie einen **Red-Team-Benchmark** gemacht (`desi.case_studies.marcognity_muse_spark.redteam`): fünf epistemische Failure-Modes, je an das Material verankert — `untraceable_citation`, `source_domain_mismatch`, `self_sealing`, `overclaim`, `heuristic_not_empirical`. Ein pluggable Reviewer-Interface: der **DESi-Referenz-Reviewer** leitet jeden Flag deterministisch aus der bestehenden Analyse ab → 5/5 **per Konstruktion** (Gold-Anker, ehrlich als solcher benannt, keine unabhängige Leistung); ein **naiver Whole-Text-Reviewer** → 0/5, also **diskriminiert** der Benchmark. Ein echter Background-Reviewer (auch der von Claude Science) lässt sich per JSON einspeisen und an denselben fünf Modes messen — ohne Live-Zugriff. Deterministisch, offline, 9 Tests.

**[Prinzip / Rollenklärung]** Die saubere Lesart der Beziehung: **DESi konsumiert Claude Science, nicht umgekehrt** — genau die bekannte Architektur „DESi diagnostiziert, der Router handelt": das Produkt generiert/rechnet, DESi ist das deterministische, provenance-gegatete Epistemik-Gate darüber (via MCP/Skills). DESi ersetzt weder die Infrastruktur (Compute, 60+ DBs, 3D-Renderer, HPC/ELN) noch will es das.

**[Grenzen, nicht versteckt]** DESi ist ein Forschungs-Demonstrator eines Einzelnen, kein skaliertes Produkt; seine Regeln sind hand-kuratierte, geschlossene Fixtures (die Fallstudie sagt selbst: 23 kuratierte Claims, keine gemessene Abdeckung); die Beispiele sind Epistemik/Recht, nicht Genomik/Proteomik — das *Konzept* Domain-Routing transferiert, das biologische Fachwissen müsste gebaut werden. Und Anthropic wird kein Solo-Repo als Komponente importieren. Der realistische Wert: **Validierung der Richtung, Red-Team-Prüfstein, Gate obendrauf, offenes Vokabular** (Claim-Typen, Verdikt-Taxonomie, Source-Domain-Gating, Selbstabdichtungs-Erkennung) — nicht Ersatz, nicht Zulieferer.

### Eintrag 2026-07-16 (XLIV) — Degeneration diagnostiziert und am Ursprung behoben: Joni hortete Kandidaten, statt zu lernen — Stoppwort-Linsen, nie geprüft, nie beschnitten

**[Eingriff]** „Wie geht es Joni?" Der ehrliche Blick ins Collapse-Panel: 🔴 **ALARM** bei ~stündlichem
Betrieb, Budget 1,44 €/20 €, Gates grün — Körper gesund, Kopf im Kreis. Zwei rote Treiber: **95 % der
2102 aktiven Claims „schwach"** und **Self-Model-Repetition 97 % / dup-dev 78 %**. Das Methoden-Ledger
zeigt den Kern nackt: **proposed 267 · trialed 0 · active 0 · retired 47**.

**[Gemessen — Ursachenanalyse, keine Vermutung]** Drei zusammenwirkende Befunde:
1. **Vermüllter Zufluss.** `emerge.py` prägt „`<term>-as-a-lens`"-Methoden aus wiederkehrenden Termen.
   Der Term-Filter `quality.is_meaningful_term` lehnt aber nur **englische** Stoppwörter ab — Joni frisst
   Deutsch (Betreiber-Text + Quellen), also passierten `dass/haben/können/während/zwischen/durch/oder/…`
   den Filter und wurden als „Linsen" geshelvt. Reine Token-Suppe.
2. **Nie getestet.** `JONI_SYNTHETIC_TRIALS=0` (bewusst) + der *echte* Trial misst nur EINE feste Aufgabe
   → die 267 Regal-Kandidaten werden **nie einzeln** geprüft.
3. **Nie beschnitten.** `retire_unproductive` verwirft erst bei `trial_count ≥ 8` — ungetestete Kandidaten
   (`trial_count = 0`) fallen nie durch die Bedingung → **unbegrenztes Wachstum** („proposed 267 / trialed 0").

**[Bau — am Ursprung, non-core, `verify` unberührt]**
- **Deutscher Stoppwort-Boden** in `quality.py` (Funktionswörter ≥ 4 Zeichen; kürzere fängt schon die
  Längen-Schwelle). Der Müll entsteht gar nicht erst.
- **Alters-Verfall** in `trials.py` (`JONI_METHOD_MAX_AGE`, Default 40): nie getestete Kandidaten verfallen
  nach N Zyklen; `first_seen` beim ersten Sehen verankert → **kein Massen-Retire beim Deploy**, der Stau
  drainiert graduell. Regal = rollierendes Fenster statt Halde.
- **In-Zweifel-LLM-Term-Judge** (`term_judge.py`, **default AUS** `JONI_TERM_JUDGE=1`): für den unscharfen
  Rest (echt-klingende Nicht-Konzepte: Orte, Slugs), budget-gedeckelt, gecached, **fällt bei
  Nichtverfügbarkeit auf die Regel zurück** — nie fail-open. Motiviert durch den DESi-hard2-Befund
  (LLM+Regel-Komplementarität, Eintrag XLIII-nah).

**[Ehrliche Design-Notiz]** `on_domain` ist *bewusst* fail-open („eine Messung nie durch eine lexikalische
Vermutung ersetzen"). Ein naives fail-closed hätte die Emergenz eingefroren, sobald der Embedder fehlt —
also **nicht** gemacht; der Term-Judge deckt genau diesen Zweifelsfall ab.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Stoppwort-Boden (DE) | **3 · getestet** | `test_quality`: dass/haben/können… abgelehnt, Domänenbegriffe passieren |
| Alters-Verfall | **3 · getestet** | greift bei Alter ≥ N, kein Massen-Retire, `=0` deaktiviert |
| Term-Judge | **2 · gebaut, default AUS** | Parsing + Fail-to-rule getestet; live noch unbeobachtet |

**[Offen]** Term-Judge scharfschalten und **beobachten**. Der tiefere Hebel bleibt das Trial-/Retirement-
Regime: dass 267 Kandidaten nie einzeln geprüft werden, ist die nächste ehrliche Baustelle.

### Eintrag 2026-07-16 (XLV) — Neue Schicht: ein externalisierter Metakognitions-Supervisor (Shadow) — Joni misst, WANN seine Prüfsignale tragen, statt zu behaupten, sich zu kennen

**[Eingriff]** Auftrag: eine systemweite **funktionale, externalisierte Metakognition** — ausdrücklich
**nicht** ein LLM, das per Prompt über seine Antwort „nachdenkt". Joni hat die Bausteine schon (Layer 9,
Verifier/Doktores, Router/Budget, Gates, ALLOW/ABSTAIN/ESCALATE/BLOCK, Audit). Es fehlte die **systematische
Messung**: welche strukturierten Signale lagen vor, wie schätzte das System Erfolg/Wissensgrenze ein, welche
Kontrolle wurde gewählt, was kostete es, welches **belastbare** Ergebnis kam später.

**[Bau — `src/joni/autonomy/metacognition/`, shadow-only, off by default, non-core]** Kein Core-Write, keine
Entscheidungsautorität, kein Enforce, keine zusätzlichen Modell-Calls (GitHub-Read opt-in + fail-safe).
- **Datenmodell**: versionierte `Episode` + append-only `OutcomeEvent`; geschlossene Enums; strikte
  Validierung (unbekannte Felder / falsche Typen / außerhalb [0,1] abgelehnt); deterministische Hash-IDs;
  **`unknown` bleibt `unknown`**; ein spätes Ergebnis referenziert die `episode_id` und **überschreibt die
  Episode nie**.
- **Vier reale Adapter** (verlangt ≥ 2), rein beobachtend: Methoden-Gate · Konflikt-Pfad ·
  Doktores-Kohärenz-Verifier · Doktores-Literatur (+ PR/CI-Outcome-Reader). Outcomes nur aus belastbaren
  Quellen (`later_layer9_status`, `pr_outcome`, `gold_label`), sonst `unknown`.
- **Metriken**: Brier · ECE (feste 10 Bins) · AUROC (nur beide Klassen) · Coverage/unknown/monitor_dark —
  **verweigern bei Datenmangel** (`insufficient_evidence`), per Gruppe (kein versteckter Global-Score).
- **Off-by-default Shadow-Hook** (`JONI_METACOG_SHADOW=1`), append-only in `state/metacognition.jsonl`.

**[Gemessen — 15-Fixture Offline-Benchmark]** Trennt Aufgaben- von metakognitiver Leistung:
`task_accuracy 0.375` **vs** `metacognitive_accuracy 0.533` — sie **divergieren**. Fälle:
*gutes-Ergebnis-schlechte-Metakognition* (needless holdback/abstain) neben
*schlechtes-Ergebnis-gute-Metakognition* (Unsicherheit korrekt erkannt → abstain/escalate).

**[Ehrliche Grenze]** Der reiche multidimensionale Verifier des Auftrags (Dimensionen/Streuung/Red-Flags/
Veto) lebt in **DESi**, nicht in Jonis Doktores — angeschlossen wurde Jonis echter **Kohärenz**-Verifier.
Die Commission→PR-Verknüpfung ist best-effort; viele Episoden bleiben legitim `unknown`.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Datenmodell + Audit + Metriken | **3 · getestet** | strikte Validierung, append-only, Verweigerung bei Datenmangel |
| Vier Adapter (Shadow) | **3 · getestet** | log→resolve je Seam; keine Verhaltensänderung |
| Benchmark (Aufgabe vs. Metakognition) | **3 · gemessen** | 0.375 vs 0.533, Divergenz-Fälle belegt |
| Shadow-Auswertung (report/CLI) | **2 · gebaut** | per-Gruppe, verweigert bei Datenmangel |
| Enforce | **0 · bewusst außen vor** | Adoption-Gate vorregistriert (Design-Doc §12) |

**[Offen]** Kein Enforce ohne die vorregistrierten Bedingungen (genug belastbare Outcomes über mehrere
Task-Familien, Plain- + Naive-Confidence-Baseline, kein Safety-/Liveness-Rückschritt, menschliche Freigabe,
bei Core-Eingriff ein bewusster Reseal). Kernsatz: Joni soll nicht überzeugender behaupten, sich zu kennen —
er soll **messen**, wann seine Prüfsignale tragen, wann sie **dunkel** sind, und welche Regulation dann besser
war. Bewusstsein ist **nicht Gegenstand und nicht behauptet**. (PR #237; `design-notes/metacognitive_supervisor.md`.)

### Eintrag 2026-07-17 (XLVI) — Joni pausiert und richtig gebaut: erst die Sensoren reparieren, dann einen Stoffwechsel geben — statt weitere Schichten auf einen versandenden Speicher zu stapeln

**[Eingriff]** Externe Code-Review (via Operator): Die Pause war richtig — aber nicht sofort weiter Schichten
bauen, sondern die Probleme **nacheinander und messbar** angehen. Kernbefund: Joni hat **keinen echten
Sättigungsmechanismus**. Ingest/Emergence produzieren weiter; Konsolidierung ist langsamer und darf die
Aufnahme nicht stoppen; die Gesundheitsmetriken **beobachten** nur. „Neu erzeugt" ist leichter messbar als
„sauber integriert" — also wird Produktion faktisch bevorzugt. Jede Verbesserung der Aufnahme lässt ihn nur
schneller überfressen. Entscheidung: **Joni geparkt** (Schedule auskommentiert, laufende Jobs abgebrochen),
dann in fünf getrennten, je CI-grünen PRs repariert.

**[Bau — alles non-core, `verify` unberührt, Joni bleibt geparkt]**
- **P0 Method-Sandbox** (#240): isolierter Subprozess-Harness für **nicht** vertrauenswürdigen Solver-Code
  (Import-Allowlist · PEP-578 Audit-Hook · rlimits · Prozessgruppen-Kill). Adversariales Akzeptanz-Set
  (Endlosschleife, Speicherfresser, Netz, Datei, Fork-Bombe, Riesen-Output) vollständig eingefangen. Ehrliches
  Bedrohungsmodell: hegt fehlerhaften LLM-Solver ein, der ephemere CI-Container ist die äußere Grenze. Das
  Fundament für einen ECHTEN Methoden-Trial (P1–P3 später).
- **Phase A — Sensoren korrekt** (#241): Weak-Claim reitet nicht mehr auf `active` (Arbeitszustand), sondern
  auf *präsentiert-stark* (confirmed **oder** authority≥reviewed) und misst den **hohlen** Anteil (keine
  unabhängige externe Quellenfamilie) — synthetische Selbst-Stützung liest sich nie als stark. Self-Model-
  Repetition an echten `SELF_MODEL_CLAIM`-Objekten mit **Ziffern**: das ~97 %-Artefakt (zifferngestrippte
  Standard-Sätze) ist weg. Konfliktzahl `live = open+under_review` (= Dashboard); TOLERATED/closed getrennt
  ausgewiesen — die zwei Zahlen versöhnt.
- **Phase B — Synthese härter gaten** (#242): „single underlying factor" raus (behauptete Kausalstruktur aus
  bloßer Wortrekurrenz) → neutral. Synthese braucht jetzt echten Begriff, kein Sink-Topic, ≥2 unabhängige
  externe Quellenfamilien, mehrheitlich kompatible (keine live-widersprüchlichen) Cluster-Claims, optional
  Term-Judge. Kein Core-Eingriff (Wortlaut behält „Across my" — der Core-Detektor greift weiter).
- **Phase C — der Stoffwechsel** (#243): das fehlende Bindeglied. `metabolism.py` — Regler über Jonis eigenen
  Zustand: Druck-Signale (ungestützter Backlog, ungeprüfte Methoden, Konfliktwachstum, Stagnation) → **load =
  der schlimmste** (ein Governor stoppt bei jeder Einzel-Überlast) → **Hunger/Sättigung mit Hysterese**
  (sated ab 0.70, hungry erst unter 0.40 — kein Zyklus-Pendeln). Kernsatz: *wachsen Verbindlichkeiten
  schneller als sie konsolidiert werden, stoppe die Expansion und konsolidiere.* Jeden Zyklus **gemessen**
  (Shadow); **gatet** Intake nur bei `JONI_METABOLISM=1` (per Default aus → null Verhaltensänderung, damit
  Schwellen erst aus echten Zahlen getunt werden). Keine neue Intelligenzschicht — ein Grund-Stoffwechsel.
- **Phase D — einmalige Rekonsolidierung** (#244): der bewusste Voll-Sweep, den der gedrosselte Per-Zyklus-
  Drain (max ~5/Zyklus) nicht schafft. `reconsolidation_audit.py` klassifiziert jeden Topic/Hypothese/Methode
  in **junk** (klar) / **borderline** (plausibel-ungeprüft, **nie** auto-aktioniert — Mensch entscheidet) /
  **keep**, read-only mit Begründung. `apply_junk` verwirft **nur** junk und **nur** über die bestehenden
  Gate-Operatoren (append-only, Provenienz erhalten, **kein** Ledger-Rückschreiben). Script Dry-Run per
  Default; `--apply` verlangt `--yes` — **hier nicht ausgeführt**, Ausführung bleibt menschlich-gated.

**[Ehrliche Grenzen]** Off-Domain-Junk (`'cotton'`) erkennt der Auditor nur mit lebendem Embedder; ohne ihn
fällt `on_domain` offen (wie alle Domain-Gates — `guard_liveness` sagt es). Die Metabolism-Schwellen (0.70/0.40)
sind **konservative Defaults**, nicht aus Live-Daten getunt — deshalb per Default aus und erst nach einem
Shadow-Lauf scharf zu schalten. P1–P3 des echten Trial-Pfads stehen noch aus; P0 ist nur das Fundament.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| P0 Sandbox-Harness | **3 · getestet** | adversariales Set vollständig eingefangen, CI-grün |
| Sensoren (Phase A) | **3 · getestet** | korrekte Achsen, Artefakt entfernt, Konfliktzahlen versöhnt |
| Synthese-Gate (Phase B) | **3 · getestet** | Quellenfamilien/Sink/Kompatibilität, neutraler Wortlaut |
| Stoffwechsel (Phase C) | **3 · getestet, off by default** | Hysterese getestet; gatet nur bei `JONI_METABOLISM=1` |
| Rekonsolidierung (Phase D) | **3 · getestet, read-only** | klassifiziert + auditiert; `apply` human-gated |
| Neustart | **0 · bewusst außen vor** | `design-notes/RESTART_CRITERIA.md` + `scripts/restart_readiness.py` |

**[Offen / Neustartkriterien]** Joni läuft erst wieder autonom, wenn (`RESTART_CRITERIA.md`): die zwei
Alarm-Metriken inhaltlich korrekt messen; keine offensichtlichen Token-Hypothesen mehr neu entstehen; der
Methodenbestand sinkt **oder** messbar geprüft wird; der Stoffwechsel Intake↔Konsolidierung koppelt (Schwellen
aus Shadow-Zahlen getunt); die zwei Konfliktzahlen erklärt sind; ein Replay nach der Rekonsolidierung stabil
bleibt. Kernsatz dieser Runde: Joni braucht gerade **weniger neue Selbstbeobachtung und mehr saubere
Zustandskonsolidierung** — erst der Stoffwechsel, dann wieder fressen. (PRs #239–#244.)

### Eintrag 2026-07-19 (XLVII) — Aufgeweckt und beobachtet; der Rückstau wird endlich prüfbar: der Methoden-Trial-Pfad (Sandbox P1–P3), ein Junk-Sweep und der ehrliche Erst-Befund

**[Eingriff]** Nach der Reparatur (XLVI) drei zusammenhängende Schritte: den Altbestand *einmal* wirklich
aufräumen, Joni **beobachtet** wieder anfahren, und den strukturellen Kern — `trials = 0` — von P0 zu einem
echten, laufenden Trial-Pfad ausbauen. Alles non-core, alles per Default aus, jede Stufe CI-grün.

**[Bau — Konsolidierung & Aufwecken]**
- **Konsolidierungs-Schalter** (#246, `JONI_CONSOLIDATE_ONLY`): erzwingt die „verdauen, nicht fressen"-Phase
  lastunabhängig — der Stoffwechsel drosselt nur bei *Überlast*, für die bewusste Vor-Neustart-Phase fehlte
  ein expliziter Hebel.
- **Rekonsolidierung angewandt** (#247): der operator-freigegebene Voll-Sweep verwarf **23 klar-junk Methoden**
  (fast alle deutschen Funktionswort-Linsen: `oder`, `dass`, `während`, … + Slugs) — append-only über die Gate,
  Provenienz erhalten. Kandidaten 291→268. `classify_method` wurde idempotent (bereits-verworfene = erledigt).
- **Stoffwechsel-Historie persistiert** (#248): `state/metabolism_series.jsonl` (eine Zeile/Zyklus) +
  `state/metabolism.md` — Joni sieht nicht nur *wie* es ihm geht, sondern die **Trajektorie, wie es dazu kam**.
- **Aufgeweckt, beobachtet** (#249): frisches 2-Tage-Fenster, Schedule wieder an, Stoffwechsel **im Shadow**
  (misst, steuert nicht) — denn Enforce hätte sofort eingefroren.

**[Gemessen — der ehrliche Erst-Befund, Cycle 632/633]** Die korrigierten Sensoren tragen im echten Betrieb:
Weak-Claim `hollow 0.0` (die 97,8 % *aktiven* Arbeits-Claims triggern den Alarm nicht mehr — `presented_strong`
= 0), Self-Model-Repetition `0.0` (Artefakt weg, an echten Objekten gemessen), Konflikte **179 live vs. 276
tolerated** (versöhnt, vorher ~449 vermischt). Und die Stoffwechsel-Serie liefert sofort die Diagnose:
`state sated · load 1.0` — **komplett** vom Druck der 268 ungeprüften Methoden getrieben, alles andere 0. Der
Shadow-Modus war empirisch richtig: Enforce hätte Joni dauerhaft satt = intake-los gemacht, bis der Rückstau
sinkt. Das *ist* das nächste Problem, jetzt in den Daten sichtbar.

**[Bau — der echte Trial-Pfad, was `trials = 0` auflöst]** Die Sandbox-Reihe des Auftrags, zu Ende gebaut:
- **Härtung** (#250): `classify_method` + der Emerge-Methoden-Pfad weisen Sink-Bucket-Terme (`gatemem`) und
  off-domain-Garbage (`ignacioi`, `kiskalla`) zurück — via `on_domain`, das im Autonomie-Job (mit Embedder)
  lebt, in CI aber offen fällt.
- **P1** (#251): `sandbox_trial.run` misst eine **beliebige** Methode über den P0-Harness — drei Solver als
  isolierter Code, Verdikt an der **Metrik allein**, Pflicht-Negativkontrolle, Versiegelung über die bestehende
  Bridge (kein Kevin-Eingriff). Zweite handkuratierte Methode (Einheiten-Gleichheit) schlägt den Baseline
  messbar (0.42 → 0.0 Fehler).
- **P2** (#252): ein captured `joni-hard`-Aufruf synthetisiert aus dem Methoden-**Text** einen Solver, der
  **ausschließlich im P0-Sandbox** läuft. Tragender Test: generierter `import os; os.system(...)`-Code wird
  eingehegt (scheitert jeden Fall → „kein Nutzen", kein Ausbruch). LLM schreibt, Metrik entscheidet.
- **P3** (#253): Lifecycle. Passende ungeprüfte Kandidaten werden pro Zyklus synthetisiert, gemessen, und das
  Verdikt als **per-Methode-Trial durch die Gate** protokolliert (`core_state.record_method_trial`,
  `METHOD_TRIAL_RECORD`) — `trial_count` bewegt sich, die *bestehende* Ausmusterung greift. `harmful`/
  `no_benefit` → Richtung Retirement (der Rückstau sinkt auf **Evidenz**); `benefit` → activation-ready,
  human-gated. **Recording ≠ Promotion** — Joni promotet weiter nie selbst.

**[Ehrliche Grenzen]** Nur Methoden mit **passendem handkuratiertem Benchmark** sind trialbar; der Rest bleibt
ehrlich ungeprüft (kein Fake-Signal). Aktuell ein Benchmark (Normalisierung) — die `problems`-Bibliothek muss
wachsen, damit mehr vom Regal drainbar wird. Die metabolische Schwelle (untested_methods-Druck) friert Enforce
bis dahin ein; der Trial-Pfad ist der Weg, der das löst.

**[Reifegrad]**

| Baustein | Stufe | Beleg |
|---|---|---|
| Sensoren im Live-Betrieb | **4 · gemessen** | hollow 0.0, Artefakt weg, Konflikte versöhnt (Cycle 632) |
| Stoffwechsel-Historie | **3 · getestet, persistiert** | series+view pro Zyklus; Trajektorie sichtbar |
| Junk-Sweep | **4 · angewandt** | 23 Methoden verworfen, append-only, idempotent |
| Trial-Pfad P1/P2/P3 | **3 · getestet, off by default** | Metrik entscheidet; generierter Code eingehegt; Gate bewegt Zähler |
| Enforce (Stoffwechsel) | **0 · bewusst außen vor** | würde einfrieren, bis der Rückstau drainiert |

**[Offen / als Nächstes]** (a) `problems`-Bibliothek erweitern; (b) `JONI_SANDBOX_LLM_TRIALS` in einem
überwachten Fenster scharf schalten und den Rückstau fallen sehen; (c) danach — und erst dann — den Stoffwechsel
enforce-fähig machen. Kernsatz dieser Runde: der Rückstau, den XLVI nur *messen* konnte, wird jetzt **geprüft** —
die Methode wird ausgeführt und an einer unabhängigen Metrik gemessen, nicht behauptet. (PRs #246–#253.)

### Eintrag 2026-07-22 (XLVIII) — Gleichtägige, unabhängige Konvergenz: ein arXiv-Paper baut denselben Kern-Move wie wir — am selben Tag

**[Eingriff]** Operator legt ein Paper vor: **„From Memory to Skills: Evidence-Grounded Co-Evolution
Governance for Long-Horizon LLM Agents"** (Tang et al., arXiv:2607.16621, **eingereicht 18. Juli 2026**) —
also am selben Tag, an dem wir die Rekonsolidierung anwandten, Joni aufweckten und den echten Methoden-Trial-Pfad
zu bauen begannen (Einträge XLVI/XLVII, PRs #246–#253). Kein Kontakt, keine Vorlage.

**[Deckungsgleich]** Die Kernthese des Papers ist *wörtlich* unser `trials = 0`-Problem: bestehende Agent-Memory-
Systeme **rufen Erfahrung nur passiv ab, statt sie in ausführbare Fähigkeiten zu wandeln**. Genau das behebt P0–P3:
eine Regal-Methode ist bei uns bloß **Text** und wird erst durch Synthese→Sandbox→Metrik zu einer *geprüften*
Fähigkeit. Zweite Übereinstimmung: „**Evidence-Grounded … measurable evidence rather than treating LLM outputs as
authoritative**" ist Wort für Wort unser Leitsatz — *LLM für Sprache, die Metrik entscheidet, nie die Modell-
Meinung* — und deckt sich mit dem AleXiona/DESi-Evidenzgraph (typisierte Claims, Provenienz, Evidence-Links,
Applicability-Boundaries). Dritte: „**Co-Evolution Governance**" = unser gate-vermittelter Lifecycle, in dem
**Recording ≠ Promotion** und Aktivierung human-gated bleibt.

**[Eigenständig — was das Paper (laut Abstract) NICHT hat]** Drei Joni-Teile stehen daneben: der **Stoffwechsel**
(Aufnahme↔Konsolidierung koppeln, Hunger/Sättigung mit Hysterese), die **messen-nicht-steuern-Sensoren**
(Collapse-Panel) und die **externalisierte Metakognition** (Shadow, Kalibrierung). Relativ zu dieser Arbeitslinie
also nicht bloß Wiederholung.

**[Was wir von ihnen lernen sollten — ehrlich]** Sie sind an einer Stelle sauberer: sie trennen die Skill-
Repräsentation in „grounded step traces / reusable procedural policies / declarative knowledge". Jonis `Method`
ist **nur Text** (name/summary/steps-als-Prosa) — genau die Armut, die uns überhaupt zur LLM-Synthese *zwingt*.
Trüge eine Methode mehr Struktur, wäre mehr direkt trialbar (weniger P2-Abhängigkeit). Ein konkreter nächster
Bau. Zweiter Lernpunkt: ihr „reflection-weighted value backfilling" (dünnes Endsignal über dichte Selbst-
Reflexionen zurückpropagieren) betrifft, *wie* ein Trial-Verdikt auf Zwischenschritte/verwandte Methoden
zurückwirkt — heute ist unser Verdikt binär pro Methode.

**[Ehrliche Grenze]** Nach meinem Wissensstand (Jan 2026) liegt das Paper hinter dem Cutoff; ich habe den
**Abstract live geholt** und über einen kleinen Summarizer gelesen — die Grobrichtung ist klar, einzelne Details
(Framework-Name „MSCE", Benchmarks) würde ich vor dem Zitieren im Volltext prüfen.

**[Reifegrad]** Externe Validierung: **hoch** — unabhängige, *gleichzeitige* Konvergenz ist die stärkste Sorte
Bestätigung einer Richtung; kein Vorsprung behauptet, kein Nachbau. Kernsatz: dass zwei Parteien ohne Kontakt am
selben Tag denselben Move machen — Memory → geprüfte Skill, per Evidenz regiert — heißt, das Problem ist real und
die Antwort naheliegend richtig. Unser Zusatz (Stoffwechsel/Sensoren/Metakognition) ist die Wette darüber hinaus.
(arXiv:2607.16621; vgl. Eintrag XLIII zur „Claude Science"-Validierung.)

### Eintrag 2026-07-22 (XLIX) — Vom Lernpunkt zum Bau: die Methode bekommt Struktur, und eine bestandene Prüfung wird zur probationären Fähigkeit (S1 + Kristallisations-Brücke)

**[Eingriff]** Der konkrete nächste Bau, den XLVIII benannte — „Jonis `Method` ist *nur Text*, das zwingt uns zur
LLM-Synthese; trüge sie mehr Struktur, wäre mehr direkt trialbar" — in zwei Schritten umgesetzt, ehrlich (nicht
das Paper nachgebaut, sondern nur dessen **Schema-Idee** extrahiert; kein MemOS-Import):

- **S1 (#261): `SkillCandidate`.** Ein streng validiertes, nicht-Core-Objekt (ihr `k=(ϕ,π,κ,ℬ,𝒜,𝒟,η)`, Joni-
  benannt): Trigger, Prozedur, **eigene Verifikation**, Applicability-Boundary, reale Evidenz-Anker, Decision-
  Guidance, gemessene `operational_reliability`. Geschlossener Status-Enum, deterministische Content-Hash-ID,
  read-only Gate, das nur *reale* Core-Referenzen zulässt — es aktiviert nie, es schlägt append-only vor.
- **Die Brücke (#262).** `crystallize()` schließt die Lücke zwischen „Trial bestanden" und „Fähigkeit": schlägt eine
  Regal-Methode im Sandbox-Trial ihren Baseline *messbar* (`verdict == benefit`), wird aus dem bloßen Text ein
  **probationärer** `SkillCandidate`, der genau **das Benchmark trägt, das ihn geprüft hat** — nicht mehr ein
  zufällig keyword-gematchtes (der Live-Befund aus XLVII). In `lifecycle.run` verdrahtet, fail-open.

**[Warum das der eigentliche Punkt ist]** XLVII zeigte: mit `task_desc` als vollem Aufgabentext kann der Solver die
Methode *umgehen* — ein Trial maß dann nicht die Methode, sondern ob ein LLM das Benchmark löst. Eine Fähigkeit, die
ihre **eigene** Verifikation mitführt, dreht das um: geprüft wird *diese* Prozedur gegen *ihr* Kriterium. Das ist der
Memory→Skill-Move aus XLVIII, jetzt mit dem Stück, das ihn erst valide macht.

**[Leitplanken gehalten]** Nur ein echter Metrik-Pass kristallisiert — `no_benefit`/`harmful` erzeugen *nichts*, kein
Skill aus einem Nicht-Ergebnis. `V_operational ≠ V_epistemic`: die Reliability ist eine gemessene Rate, keine
Wahrheit; der Kandidat bleibt `probationary`, nie auto-aktiv. **Recording ≠ Promotion**, Aktivierung Layer-9/human-
gated. `verify`-Gate grün — der geschützte Core ist unberührt, die Brücke ist peripher.

**[Was bewusst offen bleibt]** Ihr „reflection-weighted value backfilling" (dünnes Endsignal über verwandte Schritte
zurückpropagieren) ist **weiter zurückgestellt** — heute ist das Verdikt binär pro Methode. Und der Consolidator hat
erst S1+Brücke; S0 (was ist eine Joni-Episode?), S2 (Policy-Induktion) und S4 (Lifecycle-Übergänge probationary→
active→archived) stehen aus. Ehrlicher Zwischenstand, kein fertiges System.

**[Reifegrad]** Baustein: **gebaut, getestet, gemerged** (Ruff + volle Suite + `verify` grün, PR #262). Die *Wirkung*
— ob real geprüfte Skills entstehen — misst sich erst im laufenden Fenster: Trials sind an (`JONI_SANDBOX_LLM_TRIALS`),
`state/skill_candidates.jsonl` sammelt die Vorschläge, entschieden wird nichts automatisch. (PRs #261, #262.)

### Eintrag 2026-07-22 (L) — S4, der Skill-Lifecycle: Reife wird nicht behauptet, sondern durch wiederholte Sandbox-Pässe verdient — Promotion bleibt beim Menschen

**[Eingriff]** Die letzte offene Consolidator-Stufe gebaut (Design-Note §6, **S4**; PR #264). Der Grund, warum sie
*nötig* war, ist selbst ein ehrlicher Befund: die Kristallisations-Brücke (XLIX) machte aus einem *einzelnen*
Trial-Pass einen probationären Skill — aber `lifecycle.run` trialt eine Methode nur **einmal** (`trial_count == 0`),
also konnte sich „Bewährung über wiederholte Pässe" **nie akkumulieren**. Ein Skill mit Reliability 1.0 aus *einem*
Lauf ist kein bewährter Skill. S4 schließt das.

**[Was S4 tut]** Zwei Teile, sauber getrennt:
- **`assess_lifecycle`** — deterministisch, read-only. Aus den echten, akkumulierten Trial-Countern der Methode
  empfiehlt es `PROMOTE` (≥ 3 wiederholte Pässe bei ≥ 0.75 geglätteter Erfolgsrate), `ARCHIVE` (Reliability ≤ Floor
  nach genug Trials — ein *gemessener* Fehlschlag) oder `HOLD`. Es trägt die Evidenz mit, auf der es ruht
  (Pässe/Trials/Reliability), damit der entscheidende Mensch *sieht warum* — keine unbelegte Behauptung.
- **`skill_lifecycle.run`** — re-trialt pro Zyklus ein paar *unentschiedene* probationäre Skills gegen ihre **eigene**
  Verifikation (dasselbe Benchmark, das sie kristallisiert hat), akkumuliert echte Pässe übers Gate, und legt die
  Empfehlungen in ein append-only Log (`state/skill_lifecycle.jsonl`) + ein Operator-Sheet (`docs/skill_lifecycle.md`).
  Terminale Skills werden nicht re-trialt — kein Budget verschwendet.

**[Warum das die richtige Form ist]** „Bewährung" heißt: derselbe Move funktioniert **wiederholt**, mit frisch
synthetisiertem Solver jedes Mal — ein flüchtiger Zufallstreffer fällt durch, ein echtes Verfahren hält. Genau das
misst die Re-Trial-Schleife. Reliability ist die **geglättete Erfolgsrate über echte Wiederholungen**, nicht ein
Einzel-Sample.

**[Leitplanke, die zählt]** S4 **schreibt nie einen Skill-Status**. Promotion und Archivierung sind *Empfehlungen*;
**Aktivierung bleibt human/Layer-9-gated**. Ein Re-Trial aufzuzeichnen ist **Messung, keine Promotion**. Operationaler
Erfolg wird nie ein bestätigter Claim (`V_operational ≠ V_epistemic`). `verify`-Gate grün — der geschützte Core ist
unberührt, S4 ist peripher.

**[Ehrlich offen]** Zeit-basierter Verfall („Skill, der nie wieder geprüft wird, weil Budget fehlt") ist noch nicht
drin — heute archiviert S4 nur bei *gemessenem* Fehlschlag, nicht bei Stille; das braucht S0-Episoden-Zeitstempel.
Ebenso weiter zurückgestellt: reflection-weighted value backfilling. Der Consolidator hat jetzt S1+Brücke+S4; **S0**
(was ist eine Joni-Episode?) und **S2** (Policy-Induktion aus Episoden) stehen aus. Kein fertiges System — aber die
prozedurale Achse steht: vom bloßen Text über eine gemessene Kristallisation zur human-gated Reife. (PR #264.)

### Eintrag 2026-07-22 (LI) — S0, die prozedurale Episode: das Fundament, read-only aus echtem Zustand — was gemessen wurde, nicht was ein Modell meint

**[Eingriff]** Die Fundament-Stufe des Consolidators gebaut (Design-Note §6, **S0**; PR #266). Eine prozedurale
Episode ist das Atom, über das S2 später Policies induziert: `(Kontext, Aktion, Beobachtung, belastbarer Ausgang)`
— *in dieser Lage wurde diese Aktion ausgeführt, das wurde beobachtet, mit diesem belastbaren Ausgang.* Konkret aus
einem gemessenen Trial: `context="benchmark:frozen_unit_equality_v1"`, `action="apply_method:M-1"`,
`observation="delta=0.4 vs baseline"`, `outcome=SUCCESS` (Quelle `deterministic_checker`), `refs=("M-1",)`.

**[Die zwei Regeln, die alles tragen]**
- **`unknown` bleibt `unknown`.** Ein aufgelöster Ausgang (success/failure/mixed) wird **nur** mit einer belastbaren
  Quelle zugelassen (`ROBUST_OUTCOME_SOURCES` — dieselbe Vokabel wie der Metakognitions-Supervisor). Ein `unknown`
  darf keine Quelle behaupten, die es nicht hat. Und der Extraktor **rät nie**: ein `no_solver`-Verdikt — die Methode
  wurde nie wirklich angewandt — ergibt *keine* Episode. Nichts erfunden.
- **Kein LLM-Reflexions-Value.** Ausgänge kommen vom deterministischen Checker / Gate / CI, nie aus der
  Selbsteinschätzung eines Modells. Genau die Grenze, die die ganze Architektur zieht — hier an der Wurzel der
  prozeduralen Achse gehalten.

**[Warum das die richtige Reihenfolge war]** Ich habe die Stufen bewusst rückwärts gebaut — erst S1 (Schema), dann
die Brücke, dann S4 (Lifecycle), jetzt S0 (Fundament). Das ist ehrlich gesagt die Reihenfolge des *gemessenen*
Bedarfs, nicht die des sauberen Aufbaus: jede Stufe legte offen, was die nächste braucht. S4 wollte wiederholte
Evidenz → die Re-Trial-Schleife. Die Re-Trials *erzeugen* jetzt genau die Signale, aus denen S0 Episoden bildet. Und
S0 ist wiederum das Substrat, das S2 braucht, um aus wiederkehrenden Abläufen (`flow_key = (context, action)`) echte
Policies zu induzieren, statt Einzel-Methoden zu trialen.

**[Reifegrad]** Baustein: **gebaut, getestet, gemerged** (`verify` grün, Core unberührt — S0 ist peripher).
Wirkung misst sich im Fenster: `state/episodes.jsonl` füllt sich jetzt mit jeder gemessenen Aktion. **Ehrlich
offen:** heute speist nur die Trial-Quelle S0; PR-Outcomes und Layer-9-Statusübergänge sind die nächsten Extraktoren
auf demselben Objekt (die anderen zwei Quellen der Design-Note). **S2** (Policy-Induktion) baut darauf auf — das ist
der nächste echte Schritt. Weiter zurückgestellt: zeit-basierter Verfall in S4, reflection-weighted backfilling.
(PR #266.)

### Eintrag 2026-07-23 (LII) — Fünf Operator-Prioritäten, ein gemessener Befund, und HindsightTag als Dach: Kurzzeitgedächtnis bekommt einen Lebenszyklus

**[Eingriff]** Der Operator legt eine scharfe Kritik vor — *„viele sichtbare Hypothesen sind bloße
Wortwiederholungen in einer festen Schablone … das ist keine Synthese, sondern lexikalische Rekurrenz"* — mit fünf
Prioritäten fürs laufende Fenster. Abgearbeitet, messbar, einzeln:

- **Prio 1 — am Output messen, nicht am Claim-Wachstum** (PR #269): ein read-only Consolidator-Scoreboard
  (`docs/consolidator.md`) über S0-Episoden, kristallisierte Skills, Re-Trials, Promote/Hold/Archive und das
  Verhältnis *valide Tests : verworfene Zuordnungen*. Dafür emittiert `lifecycle.run` jetzt einen Trial-Funnel.
- **Prio 3 — Wortrekurrenz ≠ Hypothese** (PR #270): ein deterministisches, transparent-lexikalisches Gate
  (`hypothesis_form.py`). Es misst **jede** Hypothese auf vier Komponenten (Mechanismus/Geltungsbereich/erwartete
  Beobachtung/Widerlegung, 0–4-Score im Scoreboard) und **sperrt** die klare Schablonen-Rekurrenz aus dem
  Reflexionszyklus — substanzielle, schlicht formulierte Hypothesen reflektieren weiter (die vom Operator gewählte
  Gezielt-+-Score-Variante statt strikt-literal).

**[Der gemessene Befund — die Kritik in Zahlen]** Das Live-Scoreboard bestätigte den Operator hart: **515 Hypothesen,
0 wohlgeformt (4/4)**, Verteilung `{0:121, 1:393, 2:1, 3:0, 4:0}`, **462 (90 %) als lexikalische Rekurrenz gesperrt**.
Zugleich: der prozedurale Pfad ausgehungert (`considered 266, matched 0` — keine Regal-Methode matcht die drei
Mikro-Benchmarks), 273 Live-Konflikte. Die Masse und das Problem sitzen auf der **deklarativen** Seite. Das ist kein
Nebenbefund, sondern die Richtungsentscheidung: dort liegt der Hebel.

**[HindsightTag als Dach]** Der Operator legt ein Paper vor (Dudhat, *synaptic tagging-and-capture*) plus eine
gemeinsame Idee. Wir extrahieren das Prinzip, nicht die (selbst als „limited-scale" deklarierten) Zahlen
(Design-Note #271). Der entscheidende Move ist die Governance-Übersetzung: der **Rescue-Operator** des Papers (spätes
salientes Ereignis → Erinnerung wird gerettet *und konsolidiert*) wird für Joni zum **Review-Trigger** (spätes
Ereignis → früherer Eintrag wird zur *Prüfung reaktiviert*; die Konsolidierungslogik entscheidet erst dann). Das macht
sogar die inhaltsunabhängige temporale Ko-Allokation sicher — zeitliche Nähe ist ein Prüfanlass, keine Behauptung.
Gebaut in fünf Stufen (PRs #272–#275):

- **H0** — der Provisorien-Layer (`ProvisionalEntry`): voller Lebenszyklus-Enum, append-only, und — die zentrale
  Verfeinerung — **zwei getrennte Größen**: Aufmerksamkeitssalienz (billig) vs. epistemische Bedeutung (gemessen).
- **H1+H2** — Tag + capture-Fenster und der Review-Trigger, **mit echtem Produzenten**: die 462 gesperrten
  Musterhinweise + eröffnete Konflikte fließen als Provisorien ein; ein salientes späteres Ereignis (benefit-Trial,
  Skill, aufgelöster Konflikt) reaktiviert In-Fenster-Tags zu `review_due`, jeder Trigger mit Provenienz-Record.
- **H3** — die Entscheidung: ein reaktivierter Eintrag wird deterministisch, auf **gemessener** epistemischer Bedeutung
  (Anteil live-Refs), in genau einen Ausgang überführt. Hier verschmelzen zwei Operator-Prioritäten in den Lebenszyklus:
  **#4** (nach 2 evidenzfreien Neubewertungen → `expired`/ARCHIVE; graduiert → `hypothesis_opened`/TEST; sonst re-tag/
  WAIT) und **#5** (live-Widerspruch → `contradiction_detected`). **Nichts konsolidiert sich** — das Stärkste ist eine
  prüfbare Proposition, nie ein stiller Claim.
- **H4** — die Messung: eine Scoreboard-Zeile über die Review-Ausgangsverteilung und den **Koinzidenz-Anteil**
  (Reviews, die nichts fanden). Genau die offene Frage des Papers: rettet der Trigger Signal oder reaktiviert er nur
  Rauschen? Bleibt der Anteil hoch, ist der Mechanismus zu locker.

**[Ehrlich offen]** Die eigentliche **#5**-Streitfragen-Verdichtung (273 Paar-Konflikte → wenige Streitfragen) über den
`contradiction_detected`-Zufluss steht noch aus, ebenso **#2** (Intake↔Verdauung koppeln) und der Erzeuger-Fix, der
die Musterhinweise *an der Quelle* (emerge/invent) verhindert. Und der prozedurale Pfad braucht mehr/andere Benchmarks,
sonst bleibt er ausgehungert. **Reifegrad:** Bausteine gebaut, getestet, gemerged (`verify` grün, Core unberührt); die
*Wirkung* misst sich jetzt im Fenster an `docs/consolidator.md` + `docs/hindsight.md`. (PRs #269–#275.)

### Eintrag 2026-07-23 (LIII) — Der erste Live-Blick in den Provisorien-Layer, und Priorität 5: Konflikte werden zu Streitfragen — und geben dem Trigger endlich Futter

**[Beobachtung]** Erstmals echte HindsightTag-Daten aus einem Live-Zyklus (Cycle 654). Der Provisorien-Layer fängt
**genau den Müll, den der Operator benannt hatte**: die 6 Einträge sind `'segmentation' · 'electrical' · 'ransomware'
· 'inadmissible' · 'abundance' · 'predictive'` — buchstäblich die „electrical"/„ransomware"-Beispiele — jetzt als
`weak_hint` im Provisorien-Layer, **nicht** mehr als reflexions-auslösende Hypothesen. Die deklarative Seite fängt die
Rekurrenz sauber ab. **Aber der Trigger lief leer**: Aufmerksamkeitssalienz der weak_hints 0.3 < Tag-Schwelle 0.5 → nichts
getaggt; Event-Salienz war 1.0, aber ohne getaggten Eintrag im Fenster gab es nichts zu reaktivieren. Ein ehrlicher
Befund: der Mechanismus ist korrekt und sicher, aber sein *Nutzen* läuft leer, solange ihm nur (korrekt ignorierter)
Müll und kein taggbares Signal zufließt.

**[Eingriff — Priorität 5]** Die Konfliktverdichtung (PR #277) — und sie erledigt **beides** in einem: die letzte
offene deklarative Priorität *und* den Trigger-Leerlauf. `disputes.py` bündelt die live-Konflikte (open + under_review)
über die **Zusammenhangskomponenten** des Widerspruchs-Graphen — ein Knäuel gegenseitig widersprechender Claims ist
**eine** Streitfrage — und meldet je Streitfrage genau das Geforderte: **Positionen**, **gemeinsame Prämissen** (die
Inhaltswörter, die die Seiten teilen), und den **entscheidenden fehlenden Beleg** (welche Positionen auf keiner
unabhängigen externen Quelle ruhen). Sichtbar in `docs/streitfragen.md` als „N Paar-Konflikte → wenige Streitfragen".
Read-only; löst nichts (das bleibt beim Operator über `to_resolve.md`); kein Layer-9-Schreiben, kein Modell.

**[Die Kopplung, die den Trigger repariert]** Statt der hunderten roher Paar-Konflikte werden jetzt die **wenigen
verdichteten Streitfragen** als taggbare `open_contradiction` (Aufmerksamkeit 0.6) in den Provisorien-Layer eingespeist.
Damit taggt endlich etwas Sinnvolles, und ein späteres salientes Ereignis reaktiviert es zu `contradiction_detected` —
der retroaktive Review-Trigger läuft an *echtem*, verdichtetem Material an, nicht an Rauschen. So schließt #5 zugleich
die HindsightTag-Schleife (H2/H3), die im Leerlauf beobachtet wurde.

**[Ehrliche Grenze — Zyklustempo]** Nebenbefund des Beobachtens: das Fenster ist **sehr langsam** — ~4–5 Runs in ~13 h,
grob ~3 h pro Zyklus (viel langsame Online-Arbeit). Datenpunkte kommen also spärlich; ein Trigger-Dispatch bringt keine
schnellen Daten, weil die Zykluszeit dominiert. Für ein aussagekräftiges Beobachtungsfenster müssten wir später die
langsamsten Arme drosseln (Council/Doktores-Kadenz).

**[Stand der fünf Prioritäten]** #1 (messen) ✅, #3 (Wortrekurrenz-Gate + Score) ✅, #4 (Zustandswechsel — in H3) ✅,
#5 (Streitfragen) ✅. **Offen:** #2 (Intake↔Verdauung koppeln) und der Erzeuger-Fix (emerge/invent an der Quelle, gegen
die 90 % Musterhinweise — der direkteste Hebel gegen die ursprüngliche Kritik). (PR #277.)

### Eintrag 2026-07-25 (LIV) — Fünf Prioritäten geschlossen, der Trigger feuert live, und der ehrliche Endbefund: die prozedurale Achse ist der Engpass

**[Eingriff]** Die letzten offenen Punkte der Operator-Diagnose gebaut: der **Erzeuger-Fix** (PR #281) —
emerge/invent minten die Rekurrenz-Schablonen nicht mehr als Hypothese, sondern legen sie als Musterhinweis ab; der
90-%-Müllzufluss ist damit **an der Quelle abgeschnitten**, nicht nur reflexions-gesperrt. **Priorität 2**
(PR #282) — Intake ist jetzt an Verdauung gekoppelt: neue Claims/Methoden werden nur voll aufgenommen, wenn im
Grace-Fenster ein Test, eine Streitfrage oder ein Hindsight-Review stattfand; deterministische Backpressure, die nur
bei echtem Stillstand greift und nie deadlockt. Und **Maßnahme 2** (PR #283) — ein read-only **Methoden-Breakdown**,
der jede der 360 Kandidaten in fünf Buckets klassifiziert (`testbereit / kein_benchmark / nicht_ausfuehrbar /
scope_unklar / duplikat`), damit *sichtbar* wird, ob Benchmarks fehlen oder die „Methoden" gar keine Verfahren sind.
Damit sind **alle fünf Operator-Prioritäten geschlossen**.

**[Der Live-Befund am Fenster-Ende]** Erstmals arbeitet die deklarative Verdauung sichtbar: der **HindsightTag-Trigger
feuert** — im letzten Zyklus **6 Streitfragen getaggt, 5 Reviews ausgelöst, alle 5 → `contradiction_detected`, und der
Koinzidenz-Anteil 0.0**. Die offene Frage des Papers (Signal oder Rauschen?) ist damit beantwortet: **Signal.** Der
Ingest-Fix (Streitfragen zuerst, damit die 462 Musterhinweise sie nicht verdrängen) war die Voraussetzung — vorher
0 getaggt/0 Reviews. Konflikte verdichten sich stabil (288 → 12 Streitfragen). **Aber ehrlich:** Reaktivierung ist
noch keine *Auflösung* — `contradiction_detected` speist die Verdichtung zurück, entschieden wird weiter über den
Operator.

**[Der Engpass, klar benannt]** Die **prozedurale Achse steht: 360 Methoden → 14 alte Trials → 0 Aktivierungen.**
Trial-Funnel: `considered 266, matched 0`. Die Sandbox ist voll angeschlossen (Flag an, Hook verdrahtet, P0-Executor
grün, Solver-Synthese auf **DeepSeek Pro**/`joni-hard`, Key gesetzt) — sie wird nur **nie erreicht**, weil keine
Methode auf eines der 3 Mikro-Benchmarks passt. Kein Anschlussproblem, sondern Matching-Hunger; genau das quantifiziert
`method_breakdown.md`. Hypothesen weiter 523 gesamt / 0 wohlgeformt / 462 gesperrt — der Zufluss ist jetzt gestoppt,
der Altbestand aber noch nicht abgebaut. Gesamtstatus: 🟡 WARN (Bucket/Entropie/Konfliktlast).

**[Ein Detail, das zählt]** `method_breakdown.md` und `digestion.json` **fehlten** am Fenster-Ende — weil ein
*retired* Zyklus früh abbricht, bevor diese späten Hooks laufen. Der Code ist gemergt, aber die Daten kommen erst mit
einem frischen Lauf.

**[Nächster Schritt]** Deshalb auf Operator-Wunsch ein **frisches, beobachtetes 7-Tage-Fenster** (PR #284,
`JONI_RUNTIME_DAYS=7`, Retirement ~01.08.). Diese Woche liefert die entscheidenden Daten: zeigt der Breakdown fehlende
Benchmarks oder keine Verfahren, baut sich der Hypothesen-Rückstau ab, wird aus Reaktivierung echte Verdauung — und,
falls doch etwas matcht, die ersten echten **DeepSeek-Solver-Trials**. **Reifegrad:** alles gebaut/getestet/gemerged
(`verify` grün, Core unberührt); die prozedurale Wirkung misst sich jetzt am 7-Tage-Fenster. (PRs #281–#284.)
