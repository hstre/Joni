# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

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

## X-297 · Thema: memory

- **C-5817** (0 stützend · 1 Kontext): The challenge of translating long-term memory into embodied plans is defined within WorldLines as a method to handle partial observability, not as a standalone problem.
  - _Quelle:_ deepseek:joni-c259:2e76283ed615
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2096: The WorldLines paper introduces memory-to-plan translation exclusively within its framework for handling partial observability, never as a standalone challenge for all embod
- **C-5874** (0 stützend · 0 Kontext): Partial observability, overwritten world states, and translating long-term memory into embodied plans are ongoing challenges in AI systems.
  - _Quelle:_ granite:joni-c228:1486b31244e8
- _Evidenzlage (C-5817 vs C-5874): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-297 | <gewinner: C-5817 oder C-5874> | <grund>
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

