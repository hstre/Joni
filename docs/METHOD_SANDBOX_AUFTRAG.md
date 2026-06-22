# Auftragsskizze: Method-Sandbox — Joni baut Versuche, lässt sie laufen, misst sie

> **Status:** Skizze. Noch nicht umzusetzen — ein Entwurf, den wir später in echte
> `joni-auftrag`-Schritte zerlegen. Mehrteilig, Auftrag-groß.
> **Component-Key (neu):** `method-sandbox` (non-core, in `commission._EXTENSIBLE` aufzunehmen).
> **Verwandt:** baut direkt auf `kevin.real_trial` (`real_trial_protocol_v1`) und dem Trial-Event-
> Pfad (`kevin_trial_bridge.py`) auf; adressiert die heute strukturelle Lücke `method_trials = 0`.

## 1. Motivation — die Lücke

Joni **erntet Methoden als Text** aus Papers und legt sie als `CANDIDATE`-Methoden ins Regal
(`methods.py`). Trialen kann er sie nicht: ein echter Trial braucht einen *ausführbaren* Baseline-
und Interventions-Solver, ein eingefrorenes Aufgabenset und eine Metrik — das liefert ein Paper-
Snippet nicht mit. Heute existiert genau **ein** handgebauter echter Trial
(`frozen_joni_conflict_cases_v1`, Methode `contradiction-first-review`). Die übrigen ~80 Regal-
Methoden reifen nie; `method_trials` bleibt 0 — ehrlich, aber stagnierend.

Der synthetische Trialer (Keyword-Form-Mock) ist bewusst AUS (`JONI_SYNTHETIC_TRIALS=0`), weil er
epistemisch wertlos ist. Ihn anzuschalten würde nur Schein-Aktivität erzeugen. Der **ehrliche** Weg
nach vorn ist nicht *mehr Mock*, sondern **echtes Ausführen**: aus einer Methode einen lauffähigen
Versuch bauen, ihn in einer abgeschotteten Sandbox laufen lassen, deterministisch messen, ob er
funktioniert.

## 2. Ziel

Ein **non-core Sandbox-Modul**, das eine Regal-Methode in einen echten, gemessenen Trial überführt:

```
Methode (Text)  ──►  ausführbarer Solver  ──►  Sandbox-Lauf (isoliert, gemessen)
                                                      │
                                                      ▼
                              real_trial_protocol_v1  ──►  versiegeltes Trial-Event
                              (Metrik entscheidet)         (provisional, human-gated)
```

Es **verallgemeinert `real_trial`** von einem handgebauten Fall auf vom System gebaute Versuche —
ohne die epistemischen Grenzen aufzuweichen.

## 3. Architektur-Einbettung (die Leitplanken)

- **LLM für Sprache, Regeln für Logik.** Ein LLM darf den *Solver-Code* aus der Methodenbeschreibung
  synthetisieren (Sprache → Code). Das **Verdikt** (Pass/Fail) trifft allein die Metrik + Regel,
  nie das Modell. Genau wie `real_trial` heute.
- **Non-core, gated, budget-metered.** Neues Modul (`sandbox.py` o. ä.), Schalter
  `JONI_METHOD_SANDBOX`, hinter `extension_review.active("method-sandbox")`. Kein Eingriff in den
  Protected Core; der Sandbox-Baustein ist über `commission._EXTENSIBLE` ein non-core-Ziel.
- **Captured & replay-stabil.** Codeausführung ist nicht deterministisch reproduzierbar beim Replay.
  Deshalb muss ein Sandbox-Lauf wie ein `model_call` behandelt werden: **einmal ausführen, das
  gemessene Ergebnis als Artefakt capturen**, als versiegeltes Trial-Event **idempotent** aufzeichnen
  (genau der Pfad, den #155 gerade idempotent gemacht hat) — der Replay liest das gecapturte Ergebnis,
  führt nichts erneut aus.
- **Provisional, human-gated.** Ein Sandbox-Ergebnis ist `epistemic_weight = provisional`,
  `epistemic_authority = none`. Kein Auto-Confirm, keine Selbst-Aktivierung — die Statusleiter bleibt.

## 4. Der Knackpunkt: sichere Ausführung von generiertem Code

Das ist der Teil, an dem das Ganze steht oder fällt — daher **zuerst** zu lösen, vor jeder LLM-
Synthese:

- **Eigener Subprozess**, kein In-Process-`exec`.
- **Kein Netz** (Sockets blockiert), **kein Dateisystem** außer einem Wegwerf-Scratch-Verzeichnis.
- **Harte Limits:** CPU-Zeit, Wall-Clock-Timeout, Speicher (`resource.setrlimit`), Prozess-/Thread-
  Anzahl, Output-Größe.
- **Reine Berechnung:** der Solver bekommt einen Case-Payload (dict) rein, gibt eine Antwort (dict)
  raus — keine I/O, keine Imports außer einer kleinen Allowlist (stdlib-Teilmenge).
- **Crash/Timeout = sauberer Fail**, nie ein Cycle-Abbruch (wie alle Joni-Arme: fail quietly).
- Der GitHub-Actions-Job ist der äußere, ephemere Rahmen — die Sandbox ist der **innere** kontrollierte
  Harness pro Cycle.

> **Akzeptanz Phase 0 (Sicherheit, eigenständig testbar):** ein adversariales Test-Set
> (Endlosschleife, Speicherfresser, Netz-/Datei-Zugriff, Fork-Bombe, riesiger Output) wird
> **vollständig eingefangen** — jeder Fall endet als sauberer Fail, der Cycle läuft weiter, nichts
> entkommt der Sandbox.

## 5. Woher die Gold-Wahrheit kommt (Anti-Zirkularität)

Auch mit Sandbox braucht ein Trial **Fälle mit unabhängigen Gold-Labels**. Sonst misst sich Joni
selbst.

- **Phase 1:** ausschließlich **handkuratierte** Aufgabensets (wie `frozen_joni_conflict_cases_v1`),
  content-gehasht/eingefroren. Klein, aber ehrlich.
- **Später:** generierte Fälle nur, wenn die Gold-Labels aus einer **vom Solver unabhängigen** Quelle
  stammen (anderes Modell/Verfahren, oder eine Eigenschaft, die ohne die Methode prüfbar ist). Das
  LLM, das den Solver baut, darf **nie** auch dessen Testfälle labeln.
- Der **Negativ-Kontroll-Solver** (Sham) aus `real_trial` bleibt Pflicht: schlägt er gleich gut an,
  misst die Apparatur Rauschen → inconclusive, kein Pass.

## 6. Stufenplan (jede Stufe einzeln umsetzbar & prüfbar)

| Stufe | Inhalt | Akzeptanz |
|---|---|---|
| **P0 — Sandbox-Harness** | Isolierter Subprozess-Runner (netzlos, Limits, Scratch-only), Solver-Signatur `dict→dict`. Noch **kein** generierter Code — nur der sichere Ausführungsrahmen. | Adversariales Set vollständig eingefangen (§4); ein bekannter Python-Solver läuft korrekt und deterministisch. |
| **P1 — Generalisierter Real-Trial** | `real_trial` so öffnen, dass es **beliebige** (Methode, Aufgabenset, Baseline, Intervention, Metrik) annimmt und über den Harness misst. Erstes Set handkuratiert. | Ein zweiter echter Trial (andere Methode, neues Set) läuft end-to-end, wird als versiegeltes Event idempotent aufgezeichnet, fließt in die DESi-Projektion. |
| **P2 — Methode → Solver (LLM-Synthese)** | Captured `joni-hard`-Aufruf erzeugt aus einer Regal-Methodenbeschreibung einen Solver-Kandidaten; läuft in P0; Verdikt via P1-Metrik. Budget-metered, captured. | Mindestens eine **geerntete** Methode wird real getrialt; `method_trials`/eine echte Trial-Zahl bewegt sich; ein Fehlschlag wird als ehrliches `no_benefit`/`harmful` aufgezeichnet (nicht versteckt). |
| **P3 — Lifecycle-Anschluss** | Sandbox-Ergebnisse speisen die Reife-/Ausmusterungs-Logik (`trials.py retire_unproductive`, method_ledger) und die Website. | Eine Methode reift über **echte** Sandbox-Pässe Richtung activation-ready (weiterhin human-gated); eine real durchgefallene wird über das Gate ausgemustert. |

## 7. Was es ausdrücklich NICHT tut

- Kein Eingriff in den Protected Core; keine neuen Operatoren im Kernel.
- Kein Auto-Confirm, keine Selbst-Aktivierung von Methoden — Promotion bleibt human-gated.
- Kein Netz-/Dateizugriff aus generiertem Code.
- Keine generierten Testfälle mit selbst-gelabelter Gold-Wahrheit.
- Kein Wiederbeleben des synthetischen Keyword-Mocks — die Sandbox **ersetzt** die Mock-Idee durch
  echtes Messen.

## 8. Risiken

- **Codeausführung (hoch)** — durch P0-zuerst und das adversariale Akzeptanz-Gate eingehegt; ohne
  bestandenes P0 geht keine spätere Stufe live.
- **Solver-Synthese-Qualität (mittel)** — das LLM baut evtl. unbrauchbare Solver; das ist
  unproblematisch, weil die Metrik sie sauber als `no_benefit` aussortiert (ein negatives Ergebnis ist
  ein Ergebnis).
- **Budget (niedrig–mittel)** — P2 kostet je Trial einen `joni-hard`-Aufruf + Rechenzeit; über die
  Cadence und das Wochenbudget gedeckelt.
- **Zirkularität (mittel)** — durch §5 (unabhängige Gold-Labels, Pflicht-Negativkontrolle) adressiert.

## 9. Offene Fragen (vor P2 zu klären)

1. Sandbox-Tech: reicht `subprocess` + `resource`-Limits + seccomp-artige Restriktion, oder wollen wir
   einen Container/`nsjail`-Ansatz? (Abhängig davon, was der Actions-Runner erlaubt.)
2. Solver-Sprache: nur Python-Teilmenge, oder auch deklarative Mini-DSL für die ganz einfachen Fälle?
3. Aufgabenset-Herkunft langfristig: rein handkuratiert, oder ein geprüfter halb-automatischer Weg mit
   unabhängiger Labelquelle?

---

*Diese Skizze ist bewusst sicherheits-zuerst und stufig: jeder Schritt ist für sich lauffähig und
prüfbar, der riskante Teil (P0) ist die Voraussetzung für alles Weitere. Umsetzung später, in
einzelnen `joni-auftrag`-Schritten.*
