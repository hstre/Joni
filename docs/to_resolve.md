# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-414 · Thema: authors+evaluation

- **C-8552** (1 stützend · 0 Kontext): Hypothesis: the pattern behind 'The rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems was recently resolved by the author.' (from authors) might also apply to evaluation.
  - _stützt:_ supports via C-8270: Hypothesis: the pattern behind 'The author of the source is Marleide da Mota Gomes.' (from authorship) might also apply to benchmarking.
- **C-8255** (0 stützend · 0 Kontext): The rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems was recently resolved by the author.
  - _Quelle:_ granite:joni-c513:bde047948133
- _Evidenzlage (C-8552 vs C-8255): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-414 | <gewinner: C-8552 oder C-8255> | <grund>
```

## X-413 · Thema: authors+evaluation

- **C-8552** (1 stützend · 0 Kontext): Hypothesis: the pattern behind 'The rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems was recently resolved by the author.' (from authors) might also apply to evaluation.
  - _stützt:_ supports via C-8270: Hypothesis: the pattern behind 'The author of the source is Marleide da Mota Gomes.' (from authorship) might also apply to benchmarking.
- **C-7370** (0 stützend · 0 Kontext): The author recently resolved the rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems.
  - _Quelle:_ granite:joni-c537:24e570afd567
- _Evidenzlage (C-8552 vs C-7370): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-413 | <gewinner: C-8552 oder C-7370> | <grund>
```

## X-335 · Thema: forum

- **C-6482** (1 stützend · 0 Kontext): WorldLines benchmarks aim to address the challenge of translating long-term memory into embodied plans to solve partial observability and overwritten world states.
  - _Quelle:_ granite:joni-c511:5cdc7add828a
  - _stützt:_ supports via C-5889: WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial ob
- **C-6458** (0 stützend · 0 Kontext): The WorldLines paper does not contain a standalone problem statement or section dedicated to 'translating long-term memory into embodied plans' as a fundamental challenge independent of partial observability and overwritten world states.
  - _Quelle:_ deepseek:joni-c510:96f82dec8784
- _Evidenzlage (C-6482 vs C-6458): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-335 | <gewinner: C-6482 oder C-6458> | <grund>
```

## X-443 · Thema: memory

- **C-9229** (0 stützend · 0 Kontext): Do AI Agents Know When a Task Is Simple? Toward Complexity-Aware Reasoning and Execution
  - _Quelle:_ arxiv:2607.13034v1
- **C-9430** (0 stützend · 0 Kontext): Edge devices have limited memory resources, making quantization essential for deploying complex multimodal models.
  - _Quelle:_ granite:joni-c615:11488e102284
- _Evidenzlage (C-9229 vs C-9430): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-443 | <gewinner: C-9229 oder C-9430> | <grund>
```

## X-440 · Thema: memory

- **C-9179** (0 stützend · 0 Kontext): [Alexandria-Bewertung · assessor · keine Entscheidung] **Cross-reconstruction:**

ChatGPT (adversarial) treats "exploration" as undefined and flags missing empirical grounding, generalization, and unconsidered alternatives — a completeness/evidence lens.

DeepSeek (consistency) resolves the ambiguity ChatGPT names by *decomposing* exploration (in-episode vs. cross-episode; internal policy vs. behavioral output) and ties admissibility to memory architecture.

**Traced divergence:** The two differ on one assumption — whether "exploration" is irreducibly vague (ChatGPT) or splittable into well-defined sub-variants (DeepSeek). This is a category-granularity difference, not a genuine conflict. DeepSeek's decomposition directly discharges ChatGPT's ambiguity objection.

**Reconciled assessment:** I adopt DeepSeek's decomposition and retain ChatGPT's evidence caveat.
- *Supports:* Viable under static-memory / context-window-bounded agents; the memory-tag in Joni's graph makes the architecture assumption the load-bearing one, aptly matched.
- *Breaks:* Under dynamic memory consolidation (in-context learning, external stores), the failure claim weakens; "fail" is stated as universal but is architecture-conditional.

**Admissibility:** Formally admissible only if the memory-architecture scope and exploration sub-variant are specified. Undefined scope leaves it underspecified. No verdict — Joni decides.
  - _Quelle:_ panel:expert:claude
- **C-9195** (0 stützend · 0 Kontext): Open-KNEAD keeps every meal image on local hardware, preserving privacy and minimal user burden (a single, unannotated meal image).
  - _Quelle:_ granite:joni-c602:9b101293dcb0
- _Evidenzlage (C-9179 vs C-9195): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz Forum vs Modell/selbst_

```
X-440 | <gewinner: C-9179 oder C-9195> | <grund>
```

