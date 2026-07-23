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

## X-549 · Thema: memory

- **C-10267** (0 stützend · 0 Kontext): QFI serves as a momentum-resolved probe of entanglement, offering a novel perspective on quantum critical phenomena beyond being a lower bound for entanglement depth.
  - _Quelle:_ granite:joni-c650:b469c1511347
- **C-10279** (0 stützend · 0 Kontext): Taken together, QFI is not only helpful as a lower bound for entanglement depth, but serves as a momentum-resolved probe of entanglement that offers a novel perspective on quantum critical phenomena.
  - _Quelle:_ arxiv:2607.20424v1
- _Evidenzlage (C-10267 vs C-10279): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz Modell/selbst vs extern_

```
X-549 | <gewinner: C-10267 oder C-10279> | <grund>
```

