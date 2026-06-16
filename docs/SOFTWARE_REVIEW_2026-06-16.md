# Komplettes Software-Review — Joni & Kevin (2026-06-16)

Durchgeführt mit fünf parallelen Review-Agenten, je ein Subsystem, mit der Leitfrage der
wiederkehrenden Fehlerklasse **„nominal path present, functional semantics absent"** (ein Pfad ist
verdrahtet, feuert Calls, besteht Tests — aber seine eigentliche semantische Funktion fehlt) plus
Korrektheit, stille Fehler und Metrik-Theater.

Legende: **[BEHOBEN]** in diesem Durchgang · **[CORE-ASK]** braucht eine human-gated Änderung am
geschützten `desi_layer9`-Kern (nicht still von mir geändert) · **[OFFEN]** sollte gefixt werden ·
**[DOKU]** niedrig/Notiz · **[SOUND]** geprüft und in Ordnung.

---

## A. In diesem Durchgang behoben (kritische Regressionen der Fehlerklasse)

- **[BEHOBEN] Cache-Poisoning leerer Antworten** — `model_call.py`. Ein leerer Live-Output wurde
  content-addressiert gecached und danach **für immer als „erfolgreiche" Leerantwort repliziert**;
  der Empty-Call-Klassifikator läuft nur auf Live-Calls, sah die Wiederholung also nie. Das
  untergrub den gesamten Kevin-Token-Fix. → Leere Antworten werden nicht mehr gecached (Retry beim
  nächsten Zyklus); die Evidenz bleibt im Capture-Record. Test ergänzt.
- **[BEHOBEN] real_trial war Theater** — `kevin/real_trial.py`. Einseitige Metrik (nur Duplikate),
  Strohmann-Baseline (Identität), wirkungslose Negativkontrolle → konstanter, vorbestimmter Pass
  (baseline=1.0/intervention=0.0/passed=True jedes Mal). → Zweiseitige `misclassification_rate`,
  plausible lexikalische Baseline, Methode mit echtem Fehlerfall (doppelte Verneinung),
  strukturlose Hash-Paritäts-Negativkontrolle. Live verdient: 0.50→0.167 vs. Kontrolle 0.417,
  delta 0.333, Pass **verdient**, nicht vorbestimmt.
- **[BEHOBEN] Provider-Response-Parser ungetestet** — `model_call._to_raw` extrahiert + getestet
  (der genaue Ort des Original-Bugs: content=None + finish_reason=length + reasoning_tokens →
  text='' mit erhaltener Evidenz).
- **[BEHOBEN] Kevin-Leerantworten** — Token-Budget evidenzbasiert (768→95% leer, 1024→29%),
  Kevin-Profil auf 4096; leere/abgeschnittene Calls als **sichtbare Fehler** behandelt (vorher
  stiller „0-Vorschlag-Erfolg").
- **[BEHOBEN] Sichtbarkeits-Flags nicht persistiert** — `kevin_installed`/`kevin_real_trial` wurden
  nach dem Speichern gesetzt → Reihenfolge korrigiert.
- **[BEHOBEN] Inflationierter Yield** — `accepted_per_live_call` (>1) → echtes per-Call-Yield (≤1).

## B. Governance-Kern — HIGH, aber human-gated (CORE-ASK, nicht still geändert)

Der **Autoritäts**-Teil der Governance ist real durchgesetzt und gut getestet (wer welchen Operator
anfordern darf, Stripping kontrollierter Felder, replaybare Single-Gate-Writes, Aktivierung erst ab
≥3 Trials). Schwach ist der **Kontaminations/Taint**-Teil:

- **[CORE-ASK] Taint wird berechnet/gespeichert, aber nie durchgesetzt** — `desi_layer9/`. Eine
  Claim mit `unverified_model_output`/`adversarial_source` kann zu `CONFIRMED`/`AUTHORITATIVE`
  promoviert werden; `Taint.with_human_validation()` ist toter Code, `human_validated` wird nie
  gesetzt. Die dokumentierte Invariante existiert im Code nicht. → Promotion kontaminierter Objekte
  blocken, außer `human_validated`; einen `HUMAN_VALIDATE`-Operator einführen.
- **[CORE-ASK] `snapshot_operational` umgeht das Gate** — `epistemics.py:103-112` schreibt direkt
  `core.objects[...]` mit `AUTHORITATIVE` (kein submit, kein Ledger-Event) → unsichtbar für Replay
  und `verify_chain`. Der gated Handler `_h_operational_state` ist **toter Code** (kein
  `Operator.OPERATIONAL_STATE`, nicht in `_HANDLERS`). → über das Gate routen, Direkt-Write
  verbieten.
- **[CORE-ASK] `event_canonical` lässt `sampling_provenance` aus dem Ketten-Hash** —
  `hashing.py:48-57` → die Modell/Sampling-Provenienz ist nachträglich fälschbar, ohne die Kette zu
  brechen. → in den kanonischen Hash aufnehmen.
- **[CORE-ASK] `repair()` segnet stillschweigend inkonsistenten State neu** — `persistence.py:79-97`
  fängt jeden `ValueError` und überschreibt den `snapshot_hash`; ein wirklich manipulierter Journal
  würde „repariert". → Trigger auf den spezifischen Hash-only-Mismatch verengen, bei gebrochener
  Kette verweigern.

## C. Honesty & stille Kapazitäts-Abwesenheit — sollte gefixt werden (OFFEN)

- **[OFFEN] Das €20-Wochenbudget steuert die Semantik-Engine NICHT** — `run.py`/`budget.py`. Cap
  wird nur von `frugal`/`experts` konsultiert; `projection`/`escalation`/`kevin_llm`/`topic_review`
  bekommen `budget` gar nicht → Granite/DeepSeek/Kevin-Calls sind ungedeckelt, der Haupt-Kostenpfad.
  Die „harter Wochen-Cap"-Doku ist für den dominanten Pfad falsch. → Budget in die Semantik-Caller
  fädeln **oder** auf der Seite klar sagen, dass der Cap nur Panel/frugal deckt.
- **[OFFEN] Zwei disjunkte Kosten-Ledger, keine Gesamtsumme** — `budget.spent_eur` (nur Panel/frugal)
  vs. `telemetry.est_cost_eur` (nur model_call; Granite-Default €0,0 → zeigt €0). Keine Summe. →
  `total_est_spend` zeigen, Granite-Default-Rate als Schätzung kennzeichnen.
- **[OFFEN] Quell-Ausfälle als „0 Items" geschluckt** — `sources.py` (alle Fetcher fangen Exception
  → `[]`); `run.py` meldet „fetched: 0 item(s)" → ein totaler API-Ausfall ist von „nichts Neues"
  ununterscheidbar. → Fehler als `degraded`-Flag + Zähler auf der Seite.
- **[OFFEN] PDF-Reader / DESi / Embedder-Abwesenheit unsichtbar** — wie der Kevin-Fall (der korrekt
  sichtbar ist), aber für Reader/DESi/Embeddings als bloße Nullen. → analog `pdf_available`,
  DESi/Embedder-Status persistieren + warnen.
- **[OFFEN] Domain-Gate fail-open/inert ohne Embedder** — `quality._contrastive_on_domain` gibt
  `True` zurück, wenn `embeddings.available()` False → emerge-Domain-Filter lässt alles durch,
  obwohl er als aktiv präsentiert wird. → den inerten Zustand protokollieren/anzeigen.
- **[OFFEN] continue-on-error-Installs verstecken Kapazitätsverlust** — `autonomy.yml`. DESi/Embedder
  -Install-Fehler nur als „routing via joni-builtin" bzw. unsichtbar. → Exit-Status je Install in
  ein State-Flag, Install-Health auf der Seite.

## D. Korrektheit (MED/LOW)

- **[OFFEN] `conflict.weaker_claim` Tie-Break widerspricht den Kommentaren** — `conflict.py:91-107`
  (Code verwirft den *neueren*/höhere-id, Kommentar sagt „keep newer / reject lower id"). Code+beide
  Kommentare in Einklang bringen.
- **[DOKU] emerge-Dedup-Sets alphabetisch getrunkiert** — `emerge.py:152,192` (`sorted(...)[-500:]`)
  → bei Wachstum kann ein bereits synthetisierter Key herausfallen und erneut synthetisiert werden.
  Nach Recency cappen oder nicht cappen.
- **[DOKU] Kosten ignorieren Token** — `model_call` flacher Per-Call-Preis trotz erfasster
  completion/reasoning-Tokens; Kevin (4096) und Escalation (2048) gleich tariert.
- **[DOKU] `granite_calls`/`kevin_calls` zählen Replays, `est_cost`/`empty_*` nur Live** —
  unterschiedliche Nenner → Rate-Metriken irreführend.
- **[DOKU] bare `except` kollabiert die vier Fehlerklassen** — `model_call._complete`-Aufrufer +
  `core.py:188`. Auth/4xx von transient ununterscheidbar; Fehlerklasse im Audit taggen.
- **[DOKU] real_trial.record() wird im Zyklus nie aufgerufen** — Docstring suggeriert Gate-Record;
  faktisch nur Artefakt in `extensions` (bewusst, da Methode nicht auf der Shelf). Docstring
  weichzeichnen.

## E. Test-Suite — über dem Durchschnitt für genau diese Fehlerklasse

Beide Suites sind erkennbar *gegen* diese Klasse geschrieben und prüfen Konsequenzen, nicht nur
Struktur (Empty-als-Erfolg, Mock-als-Wirksamkeit, Advisory-als-Entscheidung, unverdiente Promotion
haben je einen semantischen Test). Restliche Lücken:

- **[BEHOBEN] Provider-Parser** (`_to_raw`-Test ergänzt).
- **[OFFEN] Kostenformel nur bounds-checked** — exakten Wert testen (N·d_cost + M·g_cost).
- **[OFFEN] Full-Cycle-Datenfluss** — Tests prüfen „Dateien existieren", nicht „Output von Schritt
  X fließt in Schritt Y / round-trip durch persistierten State". Der Ort, wo Orchestrierungs-„nominal
  path" sich versteckt.
- **[OFFEN] site.build-Zweige** (Kevin-Verdikt-Routing, real_trial-Render) unrendered im Test.
- **[DOKU] zwei tautologische Selector-Tests** (`assert verdict in (alle)`) — löschen oder das Gate
  direkt treiben.

## F. Geprüft & in Ordnung [SOUND]

- Autoritäts/Operator-Grenze des Gates (policy.may_request, Feld-Stripping, Single-Gate-Writes,
  deterministischer Replay, Aktivierung ≥3 Trials).
- `kevin/trial_runner.py` ehrlich als `synthetic_mock`/`epistemic_weight=none` etikettiert; Mathematik
  konsistent; deterministisch.
- `kevin/selector.py` hält das LLM strikt auf Signal-Lesen; Scores/Verdikte deterministisch.
- `conflict.detect_conflicts` deterministisch & idempotent.
- Reproduzierbarkeit/Replay-Stabilität durchgängig positiv getestet; keine Nichtdeterminismus-Funde.

---

### Gesamteinschätzung
Das System ist **bemerkenswert ehrlich an vielen Stellen** (Mock-Trials als Simulation etikettiert,
Kevin-Abwesenheit/Leerantworten sichtbar, echtes per-Call-Yield) — die schlimmsten Theater-Muster
wurden aktiv gejagt. Die verbleibenden Schwächen konzentrieren sich auf **(1)** den
Taint/Kontaminations-Teil der Governance (berechnet, aber nicht durchgesetzt — CORE-ASK) und **(2)**
die **Kosten-Ehrlichkeit** (der prominente €20-Cap deckt den Haupt-Kostenpfad nicht) sowie einige
**stille Kapazitäts-Abwesenheiten** (Quellen/Reader/DESi/Embedder als Nullen). Die in diesem
Durchgang behobenen Punkte (Cache-Poisoning, real_trial-Theater, Kevin) waren echte Regressionen
derselben Klasse — bezeichnenderweise teils in Code, der genau diese Klasse sichtbar machen sollte.
