# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-297 · Thema: memory

- **C-5817** (0 stützend · 3 Kontext): The challenge of translating long-term memory into embodied plans is defined within WorldLines as a method to handle partial observability, not as a standalone problem.
  - _Quelle:_ deepseek:joni-c259:2e76283ed615
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1699: The WorldLines paper defines 'translating long-term memory into embodied plans' as a design element of its planner, not as a general fundamental challenge for all agents.
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2040: WorldLines defines memory-to-plan translation as the concrete algorithmic process it uses to map long-term memory into actionable plans under partial observability, not as a
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2096: The WorldLines paper introduces memory-to-plan translation exclusively within its framework for handling partial observability, never as a standalone challenge for all embod
- **C-5874** (0 stützend · 0 Kontext): Partial observability, overwritten world states, and translating long-term memory into embodied plans are ongoing challenges in AI systems.
  - _Quelle:_ granite:joni-c228:1486b31244e8
- _Evidenzlage (C-5817 vs C-5874): Belege 3 vs 0 · Quellfamilien 3 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-297 | <gewinner: C-5817 oder C-5874> | <grund>
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

## X-293 · Thema: memory

- **C-49** (0 stützend · 0 Kontext): Concretely, our attack,NeuroImprint, assigns a dedicated memorization neuron to each training sample and constrains that each neuron is updated at most once along the local fine-tuning trajectory.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5868** (0 stützend · 0 Kontext): Paging divides memory into fixed-size units called frames and pages, eliminating external fragmentation but potentially causing internal fragmentation.
  - _Quelle:_ granite:joni-c122:a1ea4ffb8fa6
- _Evidenzlage (C-49 vs C-5868): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-293 | <gewinner: C-49 oder C-5868> | <grund>
```

## X-292 · Thema: memory

- **C-49** (0 stützend · 0 Kontext): Concretely, our attack,NeuroImprint, assigns a dedicated memorization neuron to each training sample and constrains that each neuron is updated at most once along the local fine-tuning trajectory.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5867** (0 stützend · 0 Kontext): [Alexandria-Bewertung · assessor · keine Entscheidung] **Cross-reconstruction:**

ChatGPT and DeepSeek converge: both name *context-dependency* as the central break and *transferability* as the load-bearing assumption. DeepSeek adds two sharper points ChatGPT lacks: (a) circularity — the recurrence may be self-confirming (availability heuristic as confounder), and (b) absence of a *falsification criterion*. These are stronger and I adopt them; ChatGPT's "subjectivity/overgeneralization" are special cases of DeepSeek's projection-risk.

**Disagreement kept (justified):** ChatGPT treats recurrence-across-three-sources as neutral; DeepSeek treats it as weak robustness evidence. The differing assumption is the *evidential status of recurrence*: ChatGPT assumes self-evidence requires external warrant, DeepSeek assumes pattern-frequency carries it. I side with ChatGPT here — recurrence in *one's own* evidence (forum/memory/tools) is precisely the confounder DeepSeek itself flags, so it cannot also count as independent support.

**Reconciled assessment:** Tragfähig *only if* (1) a domain-invariant operative function of "relevant" is shown, and (2) a falsification criterion separates lens from projection. Absent these, formally underspecified — admissible as hypothesis, not as method.
  - _Quelle:_ panel:expert:claude
- _Evidenzlage (C-49 vs C-5867): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Forum_

```
X-292 | <gewinner: C-49 oder C-5867> | <grund>
```

