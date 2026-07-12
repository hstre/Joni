# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-335 · Thema: forum

- **C-6482** (2 stützend · 0 Kontext): WorldLines benchmarks aim to address the challenge of translating long-term memory into embodied plans to solve partial observability and overwritten world states.
  - _Quelle:_ granite:joni-c511:5cdc7add828a
  - _stützt:_ supports via C-5889: WorldLines: Benchmarking and Modeling Long-Horizon Stateful Embodied Agents addresses the challenge of translating long-term memory into embodied plans as a solution to partial ob
  - _stützt:_ supports via C-5908: UniClawBench addresses the challenge of translating long-term memory into embodied plans to handle partial observability and overwritten world states.
- **C-6458** (0 stützend · 0 Kontext): The WorldLines paper does not contain a standalone problem statement or section dedicated to 'translating long-term memory into embodied plans' as a fundamental challenge independent of partial observability and overwritten world states.
  - _Quelle:_ deepseek:joni-c510:96f82dec8784
- _Evidenzlage (C-6482 vs C-6458): Belege 2 vs 0 · Quellfamilien 2 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-335 | <gewinner: C-6482 oder C-6458> | <grund>
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

## X-384 · Thema: memory

- **C-6835** (0 stützend · 0 Kontext): WorldDirector: Building Controllable World Simulators with Persistent Dynamic Memory
  - _Quelle:_ arxiv:2607.02517v1
- **C-7820** (0 stützend · 0 Kontext): WorldDirector introduces persistent dynamic object memory to enable controllable world simulators without continuous visual observation.
  - _Quelle:_ granite:joni-c552:7162357c4ff5
- _Evidenzlage (C-6835 vs C-7820): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-384 | <gewinner: C-6835 oder C-7820> | <grund>
```

## X-383 · Thema: memory

- **C-6800** (0 stützend · 0 Kontext): WorldDirector: Building Controllable World Simulators with Persistent Dynamic Memory
  - _Quelle:_ huggingface:2607.02517
- **C-7820** (0 stützend · 0 Kontext): WorldDirector introduces persistent dynamic object memory to enable controllable world simulators without continuous visual observation.
  - _Quelle:_ granite:joni-c552:7162357c4ff5
- _Evidenzlage (C-6800 vs C-7820): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-383 | <gewinner: C-6800 oder C-7820> | <grund>
```

