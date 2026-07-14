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

## X-424 · Thema: memory

- **C-6658** (0 stützend · 0 Kontext): Memory is essential for long-horizon agents to retain decision-relevant information scattered across expanding trajectories, preventing task requirements, prior attempts, and open subgoals from being lost within context windows. Linear attention architectures study recurrent mechanisms as efficient alternatives to softmax attention for retrieving information from long contexts. Version-controlled scientific memory enables the persistent storage and reuse of hypotheses in autonomous physics experimentation.
  - _Quelle:_ synthesis:iris
- **C-8836** (0 stützend · 0 Kontext): Detection in the ordinal-recall system fails closed if any layer detects inconsistency, ensuring reliable answers to recall questions.
  - _Quelle:_ granite:joni-c586:946e9e440a7b
- _Evidenzlage (C-6658 vs C-8836): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz Forum vs Modell/selbst_

```
X-424 | <gewinner: C-6658 oder C-8836> | <grund>
```

## X-423 · Thema: memory

- **C-6080** (0 stützend · 0 Kontext): We formulate this as an open problem, prove a positive weighted-metric benchmark, and give a corridor lower-bound mechanism showing how denominator memory can hide large gradients.
  - _Quelle:_ arxiv:2606.23676v1
- **C-8836** (0 stützend · 0 Kontext): Detection in the ordinal-recall system fails closed if any layer detects inconsistency, ensuring reliable answers to recall questions.
  - _Quelle:_ granite:joni-c586:946e9e440a7b
- _Evidenzlage (C-6080 vs C-8836): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-423 | <gewinner: C-6080 oder C-8836> | <grund>
```

