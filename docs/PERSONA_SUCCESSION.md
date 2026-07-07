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
