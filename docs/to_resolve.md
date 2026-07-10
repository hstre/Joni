# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-297 · Thema: memory

- **C-5817** (0 stützend · 2 Kontext): The challenge of translating long-term memory into embodied plans is defined within WorldLines as a method to handle partial observability, not as a standalone problem.
  - _Quelle:_ deepseek:joni-c259:2e76283ed615
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2040: WorldLines defines memory-to-plan translation as the concrete algorithmic process it uses to map long-term memory into actionable plans under partial observability, not as a
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2096: The WorldLines paper introduces memory-to-plan translation exclusively within its framework for handling partial observability, never as a standalone challenge for all embod
- **C-5874** (0 stützend · 0 Kontext): Partial observability, overwritten world states, and translating long-term memory into embodied plans are ongoing challenges in AI systems.
  - _Quelle:_ granite:joni-c228:1486b31244e8
- _Evidenzlage (C-5817 vs C-5874): Belege 2 vs 0 · Quellfamilien 2 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-297 | <gewinner: C-5817 oder C-5874> | <grund>
```

## X-317 · Thema: benchmarking+integration

- **C-5961** (1 stützend · 0 Kontext): Hypothesis: the pattern behind 'WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial observability and overwritten world states.' (from benchmarking) might also apply to integration.
  - _stützt:_ supports via C-5908: UniClawBench addresses the challenge of translating long-term memory into embodied plans to handle partial observability and overwritten world states.
- **C-5960** (0 stützend · 0 Kontext): The necessity of translating long-term memory into embodied plans does not follow from partial observability alone; it arises only when an agent's explicit world model can be overwritten.
  - _Quelle:_ deepseek:joni-c496:e6b544cb8c85
- _Evidenzlage (C-5961 vs C-5960): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-317 | <gewinner: C-5961 oder C-5960> | <grund>
```

## X-316 · Thema: benchmarking+integration

- **C-5961** (1 stützend · 0 Kontext): Hypothesis: the pattern behind 'WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial observability and overwritten world states.' (from benchmarking) might also apply to integration.
  - _stützt:_ supports via C-5908: UniClawBench addresses the challenge of translating long-term memory into embodied plans to handle partial observability and overwritten world states.
- **C-1860** (0 stützend · 0 Kontext): The challenge of translating long-term memory into embodied plans specifically arises when an agent maintains an explicit world model that can be overwritten, not from partial observability alone.
  - _Quelle:_ deepseek:joni-c269:a1cbb4b01e39
- _Evidenzlage (C-5961 vs C-1860): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-316 | <gewinner: C-5961 oder C-1860> | <grund>
```

## X-295 · Thema: memory

- **C-49** (0 stützend · 0 Kontext): Concretely, our attack,NeuroImprint, assigns a dedicated memorization neuron to each training sample and constrains that each neuron is updated at most once along the local fine-tuning trajectory.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5872** (0 stützend · 0 Kontext): [Alexandria-Bewertung · assessor · keine Entscheidung] **Cross-reconstruction:**

ChatGPT and DeepSeek converge; their divergence is one of register, not assumption. ChatGPT treats "transferability" as an empirical/cognitive bet (data quality, subjectivity); DeepSeek formalizes it as a relation `x nutzt y für z` whose context-invariance must be proven. The differing category: ChatGPT = epistemic-pragmatic risk; DeepSeek = formal-relational coherence. Both keep the same break — recurrence may be idiosyncratic artifact (DeepSeek's "Binnenevidenz" = ChatGPT's "evidence limitation"). No admissible disagreement remains; the dissent collapses once the categories are named.

**Reconciled assessment:**

Tenable IFF: (a) 'usage' is isolable as one relation, not a homonym cluster; (b) recurrence across forum+memory is cross-checked against external evidence, not self-selected; (c) lens stays heuristic — generates readings, claims no truth.

Breaks IF: 'usage' fragments into non-equivalent senses, recurrence is selection-artifact of Joni's own corpus, or analogy-pressure overwrites problem-specific features.

Formally admissible as method-suggestion under controlled, non-veridical use. Scope flag: "applicable to forum, memory" rests solely on internal evidence — transfer to a *new* problem is asserted, not yet warranted.

No verdict — Joni decides.
  - _Quelle:_ panel:expert:claude
- _Evidenzlage (C-49 vs C-5872): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Forum_

```
X-295 | <gewinner: C-49 oder C-5872> | <grund>
```

## X-294 · Thema: memory

- **C-49** (0 stützend · 0 Kontext): Concretely, our attack,NeuroImprint, assigns a dedicated memorization neuron to each training sample and constrains that each neuron is updated at most once along the local fine-tuning trajectory.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5869** (0 stützend · 0 Kontext): Segmentation uses variable-size units to map logical address spaces onto physical memory, which can avoid internal fragmentation but may lead to external fragmentation.
  - _Quelle:_ granite:joni-c122:a1ea4ffb8fa6
- _Evidenzlage (C-49 vs C-5869): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-294 | <gewinner: C-49 oder C-5869> | <grund>
```

