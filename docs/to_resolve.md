# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

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

## X-388 · Thema: memory

- **C-154** (0 stützend · 0 Kontext): By leveraging the autoregressive nature of user behavior, GR aims to predict the next interactions of users based on their historical contexts using large language model (LLM) architectures, thereby providing users with a more personalized and responsive experience.
  - _Quelle:_ arxiv:2606.20554v1
- **C-7920** (0 stützend · 0 Kontext): The pull request focuses on making the TensorFlow-free ONNX-to-TFLite conversion path more reliable, easier to reason about, and less expensive to maintain while preserving existing CLI, Python API, artifact naming, report schemas, and conversion behavior.
  - _Quelle:_ granite:joni-c556:827feac21572
- _Evidenzlage (C-154 vs C-7920): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-388 | <gewinner: C-154 oder C-7920> | <grund>
```

## X-387 · Thema: memory

- **C-152** (0 stützend · 0 Kontext): Overall, G2Rec enables recommendation models to capture holistic and semantically grounded user interest prototypes without requiring ground-truth user interests, thereby providing more comprehensive and accurate modeling of user behavior contexts in industrial sequential recommendation.
  - _Quelle:_ arxiv:2606.20554v1
- **C-7920** (0 stützend · 0 Kontext): The pull request focuses on making the TensorFlow-free ONNX-to-TFLite conversion path more reliable, easier to reason about, and less expensive to maintain while preserving existing CLI, Python API, artifact naming, report schemas, and conversion behavior.
  - _Quelle:_ granite:joni-c556:827feac21572
- _Evidenzlage (C-152 vs C-7920): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-387 | <gewinner: C-152 oder C-7920> | <grund>
```

## X-386 · Thema: memory

- **C-122** (0 stützend · 0 Kontext): Thus, hour-long videos can consume more than2 million tokens, making full-video inference difficult to scale.
  - _Quelle:_ arxiv:2606.20561v1
- **C-7920** (0 stützend · 0 Kontext): The pull request focuses on making the TensorFlow-free ONNX-to-TFLite conversion path more reliable, easier to reason about, and less expensive to maintain while preserving existing CLI, Python API, artifact naming, report schemas, and conversion behavior.
  - _Quelle:_ granite:joni-c556:827feac21572
- _Evidenzlage (C-122 vs C-7920): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-386 | <gewinner: C-122 oder C-7920> | <grund>
```

## X-384 · Thema: memory

- **C-6835** (0 stützend · 0 Kontext): WorldDirector: Building Controllable World Simulators with Persistent Dynamic Memory
  - _Quelle:_ arxiv:2607.02517v1
- **C-7820** (0 stützend · 0 Kontext): WorldDirector introduces persistent dynamic object memory to enable controllable world simulators without continuous visual observation.
  - _Quelle:_ granite:joni-c552:7162357c4ff5
- _Evidenzlage (C-6835 vs C-7820): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-384 | <gewinner: C-6835 oder C-7820> | <grund>
```

