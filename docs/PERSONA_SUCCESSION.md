# PERSONA_SUCCESSION — echte „vorher → nachher"-Korrekturen (v2a)

> **Expertise = verdichtete Geschichte korrigierter Irrtümer.** Die Persona (`persona.py`) liest
> diese Geschichte aus dem unveränderlichen Layer-9-Ledger. Ihre volle Kraft liegt in *Revisionen*
> („ich hielt X für wahr → es brach an Z → jetzt Y"), nicht nur in *Verwerfungen* („X verworfen").
> Dieses Dokument beschreibt, woher ein legitimes „nachher" kommt.

## Das Problem

Vor v2a war die Persona faktisch ein **Katalog von Verwerfungen**: der einzige autonome Pfad zu einer
terminalen Korrektur war `reject_claim` (→ `REJECTED`, kein Nachfolger). `SUPERSEDED` (ersetzt) wurde
nirgends erzeugt, weil eine tief verankerte Regel gilt:

> **„open conflicts, never force-resolve"** (`core_state.py`)

Die Schleife entscheidet **nie** selbst, welcher von zwei widersprechenden Claims recht hat. Ein
autonomer „kür einen Gewinner"-Resolver ist damit ausgeschlossen — er würde die Architektur brechen.

## Wer entscheiden darf

Genau **eine** Instanz darf einen Widerspruch settlen: der **vertrauenswürdige Betreiber (HUMAN)**
(`humans.py`: „HUMAN may confirm claims, resolve conflicts"). v2a gibt dem Betreiber diesen Hebel —
im selben „you post, Joni writes"-Muster wie das Forum.

## Der Fluss (`conflict_resolution.py`)

1. **Surface** — `decidable_conflicts(cs)` listet offene Konflikte mit **klarer Evidenz-Asymmetrie**
   (eine Seite unabhängig gestützt, die andere nicht), gerankt, gedeckelt. Zeigt **beide** Claims +
   ihre Belegzahl. **Deterministisch, kein LLM, kein Gewinner** — Joni legt nur vor. Ergebnis:
   `docs/to_resolve.md`.
2. **Decide** — der Betreiber trägt in `state/conflict_decisions.txt` ein:
   `konflikt_id | gewinner_claim_id | grund`.
3. **Apply** — `apply_decisions(...)` verbucht die menschliche Entscheidung deterministisch:
   - `CONFLICT_RESOLVE(conflict, resolution=winner, reason="operator: …")` — Gewinner landet im
     `resolution`-Feld des Konflikts;
   - `CLAIM_REVISE(loser → superseded)` — der Verlierer wird `SUPERSEDED`;
   - `CLAIM_REVISE(winner → active)`, falls der Gewinner nur durch *diesen* Konflikt bestritten war.

   Gedeckelt pro Zyklus, fail-open pro Eintrag, jede Mutation gate-recorded.
4. **Persona erntet** — `extract_corrections` liest den Nachfolger aus dem `resolution`-Feld des
   aufgelösten Konflikts: der `SUPERSEDED`-Verlierer bekommt `after = Gewinner`, `via_conflict=True`,
   `has_reason=True` (der Betreiber-Grund) → der reichste Eintrag: **„X → Y, weil Z"**.

## Erhaltene Garantien

- **never force-resolve** — die Schleife entscheidet nie; nur der Betreiber. Der Code *transkribiert*.
- **rules for logic, LLM for language** — welche Konflikte *vorgelegt* werden, ist deterministisch
  (Evidenz-Asymmetrie). Ein Modell darf den Grund höchstens formulieren, nie die Entscheidung treffen.
- **Quelle ≠ Autorität** — ein Forum/Modell kann nie einen Claim ersetzen; nur eine HUMAN-Entscheidung.
- **auditierbar** — alles über bestehende Operatoren (`CONFLICT_RESOLVE`, `CLAIM_REVISE`) + das
  append-only Ledger. `CLAIM_SUPERSEDE` (ohne Handler) und ein autonomer Resolver bleiben ungenutzt.

## Grenzen / später

- Es werden nur Konflikte mit **klarer Asymmetrie** vorgelegt (kein Fluten). Symmetrische Widersprüche
  bleiben offen — richtig so, sie sind (noch) nicht entscheidbar.
- **v2b (nicht gebaut):** Präzisions-/Dekompositions-Supersede — ein *verfeinerter* Claim ersetzt beide
  groben Originale. Mintet Claims, gehört durchs Gate; ein eigener Entwurf, nach v2a.

## v3 — Vorwärts-Bindung: die Fehlergeschichte verschärft künftige Übergänge

Das Manifest fordert wörtlich: *„Deshalb darf ein ähnlicher Übergang künftig nicht ohne
zusätzliche Prüfung akzeptiert werden."* Bis v2 war die Persona eine read-only **Anzeige** der
korrigierten Irrtümer; ab v3 **bindet** sie — deterministisch, gedeckelt, fail-open, nie ein Block:

1. **Wiedergänger-Guard** (`core_state.corrected_twin` + `_mint_revenant`): ein Text, der einen
   bereits korrigierten (`REJECTED`/`SUPERSEDED`) Claim nahezu dupliziert (Jaccard ≥
   `JONI_REVENANT_OVERLAP`, Default 0.75, oder eine Nur-Zahlen-Paraphrase), wird von `learn`/`hear`
   **nicht mehr auto-aktiviert**. Er kommt als CANDIDATE zurück, abgeleitet von seinem korrigierten
   Vorgänger (auditierbare Lineage, Provenienz `revenant-of:<id>`) — und läuft damit automatisch
   durch die adversariale `strengthen`-Leiter: erst frische, unabhängige Stützung aktiviert ihn
   wieder. Nie geblockt (Epistemik bleibt revidierbar), nur neu zu verdienen.
2. **Verbrannte Themen** (`persona.burned_themes` → `strengthen`): ein Thema mit ≥
   `JONI_BURNED_THEME_DEPTH` (Default 3) metabolisierten Irrtümern hebt die Promotions-Schwelle:
   eine unabhängige Quellen-Familie **mehr**, eine einzelne externe Karte genügt nicht mehr, und
   der Kohärenz-Shortcut (Doktores-coherent ohne Stützung) gilt dort **nicht** — genau der
   plausibel-aber-unverdiente Übergang, vor dem die Korrektur-Geschichte warnt. Ein gehaltener
   Kandidat wird protokolliert, nie still.

Damit ist die Fehlergeschichte nicht mehr nur Urteil über die Vergangenheit, sondern Prüfstruktur
für die Zukunft — „Fehlergeschichte als Architektur", nicht als Log.

## Remonstration — die Hinterfragung der Betreiber-Entscheidungen

Das Manifest fordert das **begründete Nein**. Gegenüber Quellen, Modellen und sich selbst hatte
Joni es; gegenüber dem Betreiber war die Prüfung nur prozedural. Die Remonstration schließt das —
nach dem beamtenrechtlichen Modell: Gehorsam ja, aber erst nach protokolliertem Einspruch.

1. **Prüfung**: Vor dem Verbuchen einer Konflikt-Entscheidung misst Joni deterministisch die
   Evidenzlage (dieselbe `_supports_on`-Metrik wie die Konflikt-Mappe).
2. **Einspruch**: Wählt der Betreiber die Seite mit *strikt weniger* unabhängiger Stützung, wird
   die Entscheidung **eine Runde aufgeschoben**: Joni protokolliert einen begründeten Einspruch
   (Protokoll-Event `einspruch`, sichtbar in der Mappe unter „Einsprüche") und wendet nichts an.
3. **Bestätigung**: Der Betreiber bleibt die Autorität — dieselbe Entscheidung erneut eintragen
   bestätigt sie. Sie wird angewendet, aber der Einspruch wandert **unlöschbar** in die
   `resolution_reason` („über protokollierten Einspruch entschieden, Evidenz X vs Y"). Stellt sich
   die Entscheidung später als Irrtum heraus, trägt die Persona-Lehre die volle Geschichte:
   *ich habe widersprochen, wurde überstimmt.*
4. Eine evidenz-konforme oder symmetrische Entscheidung wird sofort angewendet wie zuvor.

Kein Veto, keine Blockade — aber ein Widerspruch, der nicht still übergangen werden kann.
