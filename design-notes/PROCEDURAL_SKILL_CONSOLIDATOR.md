# Auftragsskizze: Procedural Skill Consolidator — Jonis prozedurales Kleinhirn

> **Status:** Skizze. Noch nicht umzusetzen — ein Entwurf, den wir später in `joni-auftrag`-Schritte
> zerlegen. Mehrteilig.
> **Component-Key (neu):** `skill-consolidator` (non-core, in `commission._EXTENSIBLE`).
> **Verwandt:** baut direkt auf dem Method-Sandbox-Pfad (P0–P3: `method_trial/sandbox*.py`,
> `solver_synth.py`, `lifecycle.py`) auf — der ist das Ausführungs- und Mess-Rückgrat.
> **Anlass:** Tang et al., „From Memory to Skills: Evidence-Grounded Co-Evolution Governance for
> Long-Horizon LLM Agents" (arXiv:2607.16621, eingereicht 18. Juli 2026; Code: MemTensor/MemOS,
> Apache-2.0). Gleichtägige unabhängige Konvergenz mit unserem Trial-Pfad (Tagebuch XLVIII).

## 1. Was wir aus ihrem Repo/Paper übernehmen — und was nicht

**MemOS als Ganzes ist ein konkurrierender Gedächtniskern.** Es hält einen eigenen Langzeit-Zustand
(SQLite `memos.db`: L1-Traces / L2-Policies / L3-World-Model / Skills / **Episodes** / Feedback, plus
Neo4j+Qdrant und ein eigener Reward/Value-Layer). Es zu integrieren hieße, **zwei Autoritäten** für
Jonis langfristigen Zustand zu schaffen — genau das, was Layer 9 verbietet. Also **keine
MemOS-Abhängigkeit**.

**Herausgelöst übernehmen** wir die rechte Seite ihrer Architektur — die als agent-agnostischer
Skill-Teil (JSON-RPC-Contract) ohnehin trennbar gedacht ist — und bauen sie Joni-nativ nach:

| MemOS | Übernehmen? | Verhältnis zu Joni |
|---|---|---|
| L1 Trace Memory | nur das **Konzept** | konkurriert mit Protokoll/Provenienz — nicht als Speicher, aber wir brauchen strukturierte Episoden (§4) |
| L2 Policy Memory | ja, als **Induktion** | „Verfahren aus vielen Traces" — heute fehlt Joni |
| L3 Environmental Cognition | **nein** | konkurriert mit DESi/semantischem Layer |
| Skill Library + Schema | **ja** | echte Erweiterung: das reiche, versionierte Skill-Objekt |
| Skill-Lifecycle | ja | probationary → active → archived (haben wir in P3 als candidate→provisional→active→rejected) |
| Reflection-weighted Value Backfilling | **vorerst nein** (§6) | LLM-geschätztes Credit-Assignment — Rausch-Quelle |

## 2. Die Leitplanke: V_operational ≠ V_epistemic

Der wichtigste Satz des ganzen Vorhabens. **„Hat funktioniert" ≠ „ist wahr".** Eine Prozedur kann
klappen und auf falscher Annahme beruhen; eine Antwort kann gefallen und sachlich falsch sein; eine
korrekte Warnung kann negatives Feedback bekommen. Deshalb führt Joni zwei **strikt getrennte**
Bewertungen:

- **V_operational** — „hat die Prozedur unter diesen Bedingungen zuverlässig funktioniert?" Das misst
  der Skill-Consolidator, ausschließlich über die **deterministische Sandbox-Metrik** (P1). Es ist eine
  *Zuverlässigkeit einer Prozedur*, kein Wahrheitswert.
- **V_epistemic** — „waren Annahmen, Belege und Schlüsse legitim?" Das bleibt bei **Layer 9 / DESi**.

Der Consolidator darf **nur V_operational** erzeugen. Ein Skill-Erfolg wird **nie** zu einem
bestätigten Claim. (Das ist heute schon so: ein Sandbox-Trial erzeugt einen *Methoden*-Trial, nie eine
Confirmation — dieser Auftrag macht die Regel explizit und benennt sie.)

## 3. Der Consolidator als non-core Modul (liest, schreibt nie den Zustand)

```
Joni / Layer 9  (die eine Autorität: was Joni weiß, warum, woran gebunden)
│  episodische + epistemische Aufzeichnungen · Claims/Gründe/Zweifel/Constraints ·
│  semantisches Modell · Identität, Ziele, Selbstbindungen
│
└── Procedural Skill Consolidator  (non-core, gated, budget-metered)
    ├─ liest wiederkehrende erfolgreiche Abläufe (Episoden)
    ├─ induziert Policy-Kandidaten
    ├─ prüft Evidenz + Gegenbeispiele; misst V_operational über die Sandbox
    ├─ emittiert SKILL_CANDIDATE (probationary) — KEIN neuer Glaubenssatz
    └─ verwaltet den Lifecycle-Vorschlag probationary/active/archived
```

Die Ausgabe ist ein **Vorschlag**, kein Zustand. **Layer 9 / DESi entscheidet** anschließend
deterministisch: Sind die referenzierten Episoden echt? Waren sie epistemisch legitim? Gibt es
widersprechende Constraints? Ist die Generalisierung zulässig? Darf der Skill autonom laufen oder muss
ein Mensch zustimmen? — **Aktivierung bleibt human-gated.**

## 4. Das SKILL_CANDIDATE-Schema (aus ihrem `k = (ϕ,π,κ,ℬ,𝒜,𝒟,η)`, Joni-benannt)

```
SKILL_CANDIDATE
  trigger:               wann anwenden (ϕ)
  procedure:             das Vorgehen — Text UND, wo möglich, ein geprüfter Solver (π)
  verification:          Prüf-/Fallback-Kriterien; welches Aufgabenset/Metrik (κ)
  applicability_boundary: Geltungsgrenzen — wo NICHT anwenden (ℬ)
  evidence_anchors:      IDs der stützenden Episoden/Trials — überprüfbar (𝒜)
  decision_guidance:     Präferenzen und Anti-Patterns (𝒟)
  operational_reliability: geglättete Erfolgsrate der Sandbox-Trials — V_operational (η)
  status:                probationary | active | archived
  version:               versioniert; eine Revision ist ein neues Objekt, kein Overwrite
```

Kernunterschied zu heute: Jonis `Method` ist **nur Text** (name/summary/steps-als-Prosa). Das Schema
oben ist die reiche, versionierte, evidenz-verankerte Fähigkeit — genau die Lücke aus Tagebuch XLVIII.

## 5. Was Joni schon hat (P0–P3) vs. was neu ist

**Schon gebaut — das Mess-Rückgrat:**
- P0 isolierter Sandbox-Harness · P1 generalisierter Trial (Metrik entscheidet + Negativkontrolle) ·
  P2 Text→Solver · P3 Lifecycle-Recording (`record_method_trial` bewegt `trial_count`/`success`) +
  probationary/active/archived über die bestehende Ausmusterung/Aktivierung.
- Der Sandbox-Trial IST die `verification`/`operational_reliability`-Quelle. Wir bauen sie nicht neu.

**Neu:**
1. **Episoden** (§ 4 unten) — Joni hat heute keine strukturierten `Aktion → Observation → Ausgang`-Spuren
   mit belastbarem Erfolgslabel; das Protokoll ist ein Operations-Log. Ohne diese Episoden gibt es nichts
   zu *induzieren* (der Consolidator fiele auf den Paper-Harvest-Pfad zurück, den P2 schon trialt).
2. **Das SKILL_CANDIDATE-Objekt** als versioniertes, evidenz-verankertes Schema (statt Text-nur-Method).
3. **Policy-Induktion**: aus ≥ N Episoden mit gemeinsamem erfolgreichem Ablauf einen Policy-Kandidaten
   formen (deterministische Rekurrenz zuerst; LLM nur zum *Formulieren* des Vorgehens, nie zum Werten).

## 6. Stufenplan (jede Stufe einzeln umsetzbar & prüfbar)

| Stufe | Inhalt | Akzeptanz |
|---|---|---|
| **S0 — Episode definieren** | Was ist eine prozedurale Episode für Joni: `(Kontext, Aktion, Beobachtung, belastbarer Ausgang)`. Append-only, aus vorhandenen Signalen (Trials, PR-Outcomes, Layer-9-Statusübergänge — die `ROBUST_OUTCOME_SOURCES` des Metakognitions-Supervisors). **Kein** LLM-Reflexions-Value. | Episoden werden read-only aus echtem Zustand gebildet; nichts erfunden; `unknown` bleibt `unknown`. |
| **S1 — SKILL_CANDIDATE-Schema** | Das Objekt (§4), non-core, strikt validiert (unbekannte Felder/Typen abgelehnt), versioniert, `evidence_anchors` referenzieren echte IDs. Noch keine Induktion — nur das Objekt + sein Gate-Vorschlag. | Ein von Hand gebautes SKILL_CANDIDATE fließt als Vorschlag durch die Gate; Layer 9 entscheidet; keine Auto-Aktivierung. |
| **S2 — Policy-Induktion** | Aus ≥ N Episoden mit gemeinsamem Ablauf einen Policy-Kandidaten formen (Rekurrenz deterministisch; `procedure`-Text via `joni-hard`, captured, budget-metered). | Mindestens ein Policy-Kandidat aus ECHTEN Episoden; die stützenden Episoden sind verlinkt und prüfbar. |
| **S3 — Kristallisierung (Gate)** | Ein Policy-Kandidat wird zu `probationary` SKILL, wenn: (a) V_operational über die Sandbox positiv (P1/P2), (b) Stabilität — jüngste Evidenz passt zu trigger/procedure/boundary ohne wesentliche Revision, (c) `applicability_boundary` + **Gegenbeispiele** vorhanden, (d) Negativkontrolle bestanden. | Ein Skill kristallisiert nur bei belegtem operationalem Nutzen; ein Fehlschlag wird ehrlich als `no_benefit`/`harmful` archiviert. |
| **S4 — Lifecycle** | probationary → active (human/Layer-9-gated) → archived. Bewährung über wiederholte Sandbox-Pässe; `operational_reliability` als geglättete Erfolgsrate; Verfall bei ausbleibender Bewährung. | Ein Skill reift über ECHTE Bewährung Richtung active (weiter human-gated); ein durchgefallener wird archiviert. |

## 7. Was es ausdrücklich NICHT tut

- **Keine MemOS-Abhängigkeit**, kein zweiter Gedächtniskern; Layer 9 bleibt die eine Autorität.
- **Kein reflection-weighted value backfilling** (vorerst). LLM-geschätztes, reflexions-gewichtetes
  Credit-Assignment bringt genau das Rauschen zurück, das die Architektur draußenhält. Wir nutzen nur die
  **deterministische** Sandbox-Metrik für V_operational. Backfilling erst, wenn ein *gemessener* Bedarf
  besteht — und dann strikt V_operational + explizit als low-confidence markiert.
- **Kein epistemischer Wert aus operationalem Erfolg.** Ein Skill-Pass erzeugt nie einen bestätigten
  Claim. V_operational fließt nie nach V_epistemic.
- **Kein Auto-Confirm / keine Selbst-Aktivierung.** Der Consolidator schreibt den Zustand nie; er schlägt
  vor, Layer 9 entscheidet, Aktivierung bleibt human-gated.
- **Kein Ersatz** für Emergence/Doktores — er ergänzt sie um die prozedurale Achse („wie tut man X
  zuverlässig"), während Layer 9 die deklarative Achse hält („was ist wahr, warum, woran gebunden").

## 8. Risiken

- **Zwei-Autoritäten-Falle (hoch)** — durch §1/§3 adressiert: der Consolidator liest, schlägt vor, schreibt
  nie; Layer 9 entscheidet.
- **Circularität / operational→epistemic-Leck (hoch)** — durch §2 (die V-Trennung) und die read-only-
  Ausgabe adressiert.
- **Episoden-Herkunft (mittel)** — S0 zuerst; nur belastbare Ausgänge (`ROBUST_OUTCOME_SOURCES`), nichts
  erfunden.
- **Budget (niedrig–mittel)** — Induktion/Formulierung kosten `joni-hard`; über Cadence + Wochenbudget
  gedeckelt, captured.

## 9. Offene Fragen (vor S2 zu klären)

1. Episoden-Granularität: ein Zyklus? eine Commission? eine Trial-Sequenz? Was ist der „belastbare
   Ausgang" pro Typ?
2. Verhältnis `Method` ↔ `SKILL_CANDIDATE`: wird `Method` zum Skill migriert, oder ist der Skill ein
   höherwertiges Objekt, das eine geprüfte `Method` einbettet?
3. Reicht der bestehende Method-Lifecycle (candidate/provisional/active/rejected) als Träger, oder braucht
   der Skill einen eigenen, parallelen Status?

---

*Sicherheits- und autoritäts-zuerst, stufig. Kern: der Consolidator lernt, WIE etwas zuverlässig getan
wird (V_operational, deterministisch gemessen); Layer 9 bleibt das System, das festhält, WAS Joni weiß,
WARUM er es weiß und WORAN er gebunden ist (V_epistemic). Umsetzung später, in einzelnen Schritten.*
