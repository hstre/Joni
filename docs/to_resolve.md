# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-550 · Thema: memory

- **C-10397** (0 stützend · 0 Kontext): ReContext addresses long-context reasoning failures in large language models by recursively replaying evidence to utilize relevant information already present in their inputs.
  - _Quelle:_ granite:joni-c654:b9b69c43edc0
- **C-4655** (0 stützend · 1 Kontext): Recent literature highlights persistent memory as a critical capability for advanced AI systems. WorldDirector introduces persistent dynamic object memory to enable controllable world simulators that do not require continuous visual observation to maintain object state. ReContext addresses long-context reasoning failures in large language models by recursively replaying evidence, helping models utilize relevant information already present in their inputs.
  - _Quelle:_ synthesis:iris
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-7995: WorldDirector introduces persistent dynamic object memory to enable controllable world simulators without continuous visual observation.
- _Evidenzlage (C-10397 vs C-4655): Belege 0 vs 1 · Quellfamilien 0 vs 1 · Provenienz Modell/selbst vs Forum_

```
X-550 | <gewinner: C-10397 oder C-4655> | <grund>
```

## X-566 · Thema: forum

- **C-6482** (2 stützend · 0 Kontext): WorldLines benchmarks aim to address the challenge of translating long-term memory into embodied plans to solve partial observability and overwritten world states.
  - _Quelle:_ granite:joni-c511:5cdc7add828a
  - _stützt:_ supports via C-5889: WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial ob
  - _stützt:_ supports via C-6306: Partial observability tasks can be partitioned into memoryless (Markov) and memory-requiring (non-Markov) classes; the challenge of translating long-term memory into embodied plan
- **C-7581** (0 stützend · 0 Kontext): The phrase 'translating long-term memory into embodied plans' does not appear in any section heading of the WorldLines paper.
  - _Quelle:_ deepseek:joni-c544:9ceeec585205
- _Evidenzlage (C-6482 vs C-7581): Belege 2 vs 0 · Quellfamilien 2 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-566 | <gewinner: C-6482 oder C-7581> | <grund>
```

## X-565 · Thema: forum

- **C-6482** (2 stützend · 0 Kontext): WorldLines benchmarks aim to address the challenge of translating long-term memory into embodied plans to solve partial observability and overwritten world states.
  - _Quelle:_ granite:joni-c511:5cdc7add828a
  - _stützt:_ supports via C-5889: WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial ob
  - _stützt:_ supports via C-6306: Partial observability tasks can be partitioned into memoryless (Markov) and memory-requiring (non-Markov) classes; the challenge of translating long-term memory into embodied plan
- **C-8484** (0 stützend · 0 Kontext): In the paper's description of the benchmark, the subtask 'translating long-term memory into embodied plans' is always coupled with scenarios of partial observability and memory overwriting, never presented in isolation.
  - _Quelle:_ deepseek:joni-c572:cee073ec5888
- _Evidenzlage (C-6482 vs C-8484): Belege 2 vs 0 · Quellfamilien 2 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-565 | <gewinner: C-6482 oder C-8484> | <grund>
```

## X-335 · Thema: forum

- **C-6482** (2 stützend · 0 Kontext): WorldLines benchmarks aim to address the challenge of translating long-term memory into embodied plans to solve partial observability and overwritten world states.
  - _Quelle:_ granite:joni-c511:5cdc7add828a
  - _stützt:_ supports via C-5889: WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial ob
  - _stützt:_ supports via C-6306: Partial observability tasks can be partitioned into memoryless (Markov) and memory-requiring (non-Markov) classes; the challenge of translating long-term memory into embodied plan
- **C-6458** (0 stützend · 0 Kontext): The WorldLines paper does not contain a standalone problem statement or section dedicated to 'translating long-term memory into embodied plans' as a fundamental challenge independent of partial observability and overwritten world states.
  - _Quelle:_ deepseek:joni-c510:96f82dec8784
- _Evidenzlage (C-6482 vs C-6458): Belege 2 vs 0 · Quellfamilien 2 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-335 | <gewinner: C-6482 oder C-6458> | <grund>
```

## X-414 · Thema: authors+evaluation

- **C-8552** (1 stützend · 0 Kontext): Hypothesis: the pattern behind 'The rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems was recently resolved by the author.' (from authors) might also apply to evaluation.
  - _stützt:_ supports via C-8270: Hypothesis: the pattern behind 'The author of the source is Marleide da Mota Gomes.' (from authorship) might also apply to benchmarking.
- **C-8255** (0 stützend · 0 Kontext): The rigorous mathematical theory of filtering equations for mixed states in basic infinite-dimensional quantum systems was recently resolved by the author.
  - _Quelle:_ granite:joni-c513:bde047948133
- _Evidenzlage (C-8552 vs C-8255): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-414 | <gewinner: C-8552 oder C-8255> | <grund>
```

