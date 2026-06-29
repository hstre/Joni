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
  darauf noch nicht live** (Stufe 1). Umbau-Plan als gated core-ask: `docs/CORE_REBUILD_PLAN.md` (A–D).
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
des Betreibers, dass Joni *irgendwann* umgebaut werden muss: `docs/CORE_REBUILD_PLAN.md` als gated
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

