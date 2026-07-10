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

## X-321 · Thema: memory

- **C-50** (0 stützend · 0 Kontext): After fine- tuning, the resulting isolated per-sample updates can be an- alytically inverted in closed form to recover text embed- dings, which are then deterministically mapped back to to- ken sequences.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5966** (0 stützend · 0 Kontext): The manuscript investigates the analytic structure of three central objects in non-Markovian open quantum dynamics: the Nakajima-Zwanzig memory kernel, the reduced-state Laplace transform, and the effective kernel.
  - _Quelle:_ granite:joni-c131:0510bdb827ed
- _Evidenzlage (C-50 vs C-5966): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-321 | <gewinner: C-50 oder C-5966> | <grund>
```

## X-320 · Thema: memory

- **C-50** (0 stützend · 0 Kontext): After fine- tuning, the resulting isolated per-sample updates can be an- alytically inverted in closed form to recover text embed- dings, which are then deterministically mapped back to to- ken sequences.
  - _Quelle:_ arxiv:2606.20553v1
- **C-5959** (0 stützend · 0 Kontext): In the broader AI research context, translating long-term memory into embodied plans remains an open challenge, specifically when agents maintain explicit world models subject to overwriting.
  - _Quelle:_ deepseek:joni-c496:e6b544cb8c85
- _Evidenzlage (C-50 vs C-5959): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-320 | <gewinner: C-50 oder C-5959> | <grund>
```

