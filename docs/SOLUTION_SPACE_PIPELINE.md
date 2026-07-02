# Ziel-Architektur: Lösungsraum-Kartografie mit tiefen Methoden als Operatoren

> **Status: Reifegrad 0 — Design, festgehalten, NICHT gebaut.** Dies ist die vereinbarte Ziel-Architektur
> (Betreiber + Claude, 2026-07-02), damit sie nicht verloren geht. Sie ordnet die schon vorhandenen Bausteine
> und benennt die eine echte Lücke. Kein Code hängt hieran, bis ein Baustein bewusst begonnen wird.

## Warum die Methoden-DB überhaupt existiert

Der Zweck der Datenbank tiefer Methoden ist **nicht**, einem One-Shot-Modell eine Methode als Prompt-Hinweis
voranzustellen. Das ist über sechs Batterien (micro/hard/deep/cross/novel/search) **widerlegt**, zuletzt auch
im All-Methods-Lauf: alle 36 Methoden auf einmal (Portfolio 0.2 ≈ Baseline 0.1) bzw. jede einzeln
(Oracle 0.6, aber reines Mehrfachvergleichs-Rauschen — die richtige Methode rettete 1 von 5 Aufgaben, der
harte Kern 0). Methode-als-Text ist inert.

Der eigentliche Zweck ist eine **Pipeline**, in der die Methoden **Operatoren** sind, die eine kartografierte
Lösungsraum-Karte durchqueren:

1. **DESi kartografiert** den Lösungsraum zu einer wissenschaftlichen Zielfrage.
2. **Bekannte Lösungen** (aus Training/Erfahrung) werden **Inseln** in dieser Karte zugeordnet.
3. **Unerreichte Inseln** werden mit Hilfe der Methoden-DB **gesucht**, und **Brücken zwischen
   Lösungsräumen** werden gefunden.
4. **Joni entdeckt** mit der Zeit **selbst neue tiefe Methoden**.

## Der Raum: Produkt aus zwei realen Räumen

Ein Lösungspunkt lebt im **Produkt** zweier Räume (Betreiber-Entscheidung: „im Produkt beider, natürlich"):

| Achse | Was er misst | Status im Code |
|---|---|---|
| **9-dim Governance-`StateVector`** (das *Wie*) | Zustand des Ringens: `frame_id`, `contradiction_load`, `anchor_density`, `source_quality`, `novelty`, `confidence`, `branch_cost`, `support_state`, `routing_state` | **gebaut** — `desi.epistemic_trajectory.state`; die Kompression Φ (Trajektorie → 9 Zahlen, ≈96,5 %) ist das „Falten" |
| **semantisches Embedding** (das *Wo*) | Worum es inhaltlich geht — Nähe = Verwandtschaft | **ableitbar, klein zu bauen** — Embedding-Modell (`fastembed`, Cosinus) auf den Lösungstext |

**Ehrliche Feinheit:** DESis SPL-Adapter (`desi.spl_adapter`) ist **symbolisch** — er liefert typisierte
`Claim`-Objekte, **keinen** Koordinatenvektor. Die semantischen Koordinaten kommen daher aus dem
Embedding-Modell, nicht aus der SPL direkt. Das „geometrische Falten" des Raums war eine Idee, die nie
umgesetzt wurde, und bleibt **Nicht-Ziel** — Φ ist das Falten, und das ist fertig.

- **Insel** = Cluster im Produktraum.
- **Gap** = leere/unterverankerte Region **plus** die offenen Konflikte aus dem `EpistemicGapSnapshot`.

## Die Operatoren: tiefe Methoden

Jede tiefe Methode (`joni.method_trial.deep_methods`, 36 Stück, alle mit Kernfrage + Domänen) ist ein
**content-freier Zug** im Produktraum:

- im **9-dim Raum**: eine Bewegung, z. B. „senke `contradiction_load` über eine **Invariante**", „erhöhe
  `anchor_density` über **Reduktion** auf ein gelöstes Problem", „prüfe den Rand über **Grenzfall**";
- im **semantischen Raum**: eine **Brücke** zur Nachbarinsel (Methode, die auf Insel A trug, als Kandidat
  für Insel B).

## Was schon läuft — und die eine Lücke

DESis Modul **`desi.solution_space_gap`** implementiert die Stufen 1–3 bereits — aber auf dem **flachen**
Affinitäts-Vokabular (`causal`, `boundary`, `adversarial`, `invariant` …), nicht auf den tiefen Methoden:

- `snapshot.EpistemicGapSnapshot` = die **Karte** (Konflikte, Evidenzlücken, offene Fragen, Methoden-Historie
  + scope-gebundene Trial-Ergebnisse).
- `analysis.analyze_gaps` = zeigt **unterbearbeitete-aber-relevante** Züge an offenen Gaps an — **inklusive
  der Brücken-Logik**: „Erfolg in anderem Scope → Gap hochstufen" (die Verknüpfung zwischen Lösungsräumen ist
  im Ansatz schon da, Zeilen 78–90).

**Die eine echte Lücke:** `solution_space_gap` von **flachen Affinitäten** auf **tiefe Methoden-Operatoren**
heben. Das ist Reuse, kein Parallel-Code — es verdrahtet die DB endlich *wirksam* und erzeugt die Trial-Daten,
aus denen der Entdecker (Stufe 4) später Methoden abstrahiert.

## Stufe 4: Selbst-Entdeckung tiefer Methoden (der Meta-Loop)

Aus den `MethodTrial`-Ergebnissen wiederkehrende erfolgreiche Muster `(Methode, Gap-Art)` zu neuen
`DeepMethod`-Kandidaten **abstrahieren**. Disziplin (aus den Batterien gelernt): eine selbst-entdeckte Methode
gilt erst, wenn sie auf einer **zurückgehaltenen Insel** trägt — sonst ist sie ein Zufallsmuster (genau der
Holdout-/Falsifikations-Reflex, der den Methoden-Trial-Apparat trägt).

## Baureihenfolge (offen, Betreiber entscheidet)

- **A · Kartograph:** Lösungspunkte in (9-dim ⊕ Embedding) einbetten, clustern → Inseln + Gaps. Fundament,
  aber braucht Trajektorien-+Embedding-Plumbing (größerer Lift).
- **B · Operator-Layer:** ✅ **GEBAUT** (`joni.solution_space.operators`, `propose_operators`). Der tiefe
  Zwilling von DESis `analyze_gaps`: derselbe `EpistemicGapSnapshot` rein → **tiefe Methoden als Operatoren**
  raus, jede mit ihrer Kernfrage, gerankt `severity × kind_relevance × under_addressed`, inkl. Brücken-Logik
  (Erfolg in anderem Scope → `is_bridge`) und scope-gebundener Trial-Awareness (`DeepMethodTrial`; technical
  vs. no_benefit unterscheidet). Gap-Art → Methoden-*Art*-Taxonomie (skaliert mit der DB). Deterministisch,
  fail-open (`from_core` degradiert zu `[]` bei DESi-Schema-Skew). 8 Tests grün.
  **Offen darunter:** die `DeepMethodTrial`-Ergebnisse müssen noch befüllt werden (heute leer → Ranking = die
  a-priori severity×kind-Tabelle, ehrlich markiert); und der Joni↔DESi-Projektor-Schema-Skew
  (`SCHEMA_VERSION`) blockiert lokal den `from_core`-Pfad (CI zieht DESi main, dort läuft er).
- **C · Entdecker:** der Meta-Loop — erst sinnvoll, wenn B echte Trial-Daten produziert.

## Offene, ehrlich benannte Punkte

- Die semantischen Koordinaten sind **ableitbar, aber nicht gratis** (Embedding-Schritt auf den Lösungstext).
- Die „Insel"-Geometrie ist im 9-dim Raum ein **Governance-Zustandsraum** (wie das Denken sich verhält),
  **nicht** ein Inhaltsraum — deshalb braucht es das Produkt mit dem Embedding, damit „worum es geht" und „in
  welchem Zustand" beide zählen.
- Alles hier ist **Stufe 0/1**. Ein Null-Ergebnis oder eine Sackgasse bei jedem Baustein ist ein gültiges,
  festzuhaltendes Ergebnis — kein Grund, eine Struktur zu behaupten, die nicht trägt.
