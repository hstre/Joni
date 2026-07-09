# Joni's Konflikt-Mappe

Joni entscheidet **nie** selbst, welcher Claim recht hat (`open conflicts, never
force-resolve`). Hier sind offene Widersprüche, bei denen die Evidenz klar lehnt -
**du** entscheidest. Trag deine Entscheidung in `state/conflict_decisions.txt` ein:
`konflikt_id | gewinner_claim_id | grund`. Joni löst dann auf, markiert den Verlierer
als SUPERSEDED (Nachfolger = Gewinner) und die Persona lernt „X → Y, weil …".

_5 entscheidbare(r) Konflikt(e)._

## X-89 · Thema: forum

- **C-1586** (0 stützend · 3 Kontext): The WorldLines paper explicitly classifies the challenge of translating long-term memory into embodied plans as a subproblem of partial observability and overwritten world states, not as a fundamental challenge independent of those.
  - _Quelle:_ deepseek:joni-c250:a74cc83ae851
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1588: In embodied AI, partial observability and overwritten world states can exist without necessitating the translation of long-term memory into plans, as demonstrated by reactiv
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1652: Translating long-term memory into embodied plans is a sub-challenge of partial observability, defined by the need to convert internally stored abstract representations into 
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1699: The WorldLines paper defines 'translating long-term memory into embodied plans' as a design element of its planner, not as a general fundamental challenge for all agents.
- **C-1665** (0 stützend · 0 Kontext): Partial observability is a foundational challenge in embodied AI, and approaches like translating memory into plans are methods to address it rather than separate fundamental challenges.
  - _Quelle:_ deepseek:joni-c258:600c90cad07f
- _Evidenzlage (C-1586 vs C-1665): Belege 3 vs 0 · Quellfamilien 3 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-89 | <gewinner: C-1586 oder C-1665> | <grund>
```

## X-39 · Thema: forum

- **C-166** (0 stützend · 1 Kontext): All previously known predictors achieving the minimax-optimal ≈ O(η⁻³) sample complexity for η-multicalibration were randomized, while deterministic predictors had substantially worse sample complexity.
  - _Quelle:_ granite:joni-c4:0942224016ab
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-177: Before this work, all algorithms known to attain the minimax- optimal eO(ε−3) sample complexity rate for ε-multicalibration outputrandomizedpredictors, while deterministic pr
- **C-723** (0 stützend · 0 Kontext): PsiQRH Riemann Sphere with 32.2 million parameters outperformed GPT-2 (124 million parameters) in Perplexity (PPL) across five domains: poetry, mathematics, dialogue, and science, while GPT-2 performed better in code generation.
  - _Quelle:_ granite:joni-c118:ef95a5f73b09
- _Evidenzlage (C-166 vs C-723): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-39 | <gewinner: C-166 oder C-723> | <grund>
```

## X-122 · Thema: forum

- **C-1776** (0 stützend · 1 Kontext): Extended reasoning chains in Gemini Deep Research are fragile.
  - _Quelle:_ granite:joni-c266:72105da076f8
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1777: Knowledge transfer in Gemini Deep Research is limited.
- **C-1778** (0 stützend · 0 Kontext): Gemini Deep Research lacks physics-grounded self-verification.
  - _Quelle:_ granite:joni-c266:72105da076f8
- _Evidenzlage (C-1776 vs C-1778): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-122 | <gewinner: C-1776 oder C-1778> | <grund>
```

## X-121 · Thema: forum

- **C-1775** (0 stützend · 1 Kontext): Gemini Deep Research achieves 33.5% accuracy in evaluations.
  - _Quelle:_ granite:joni-c266:72105da076f8
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-1777: Knowledge transfer in Gemini Deep Research is limited.
- **C-1778** (0 stützend · 0 Kontext): Gemini Deep Research lacks physics-grounded self-verification.
  - _Quelle:_ granite:joni-c266:72105da076f8
- _Evidenzlage (C-1775 vs C-1778): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-121 | <gewinner: C-1775 oder C-1778> | <grund>
```

## X-113 · Thema: forum

- **C-1701** (0 stützend · 1 Kontext): No section of the WorldLines paper presents memory-to-plan translation as an independently necessary challenge for embodied agents outside the context of its partial observability framework.
  - _Quelle:_ deepseek:joni-c260:cfa603e81868
  - _Kontext (kann auch dagegen sprechen):_ contextualizes via C-2096: The WorldLines paper introduces memory-to-plan translation exclusively within its framework for handling partial observability, never as a standalone challenge for all embod
- **C-2335** (0 stützend · 0 Kontext): Memory-to-plan translation is treated in the WorldLines paper as an engineered solution specific to handling partial observability and overwritten states, rather than a universal challenge for all embodied agents.
  - _Quelle:_ granite:joni-c307:a10e2dd209cc
- _Evidenzlage (C-1701 vs C-2335): Belege 1 vs 0 · Quellfamilien 1 vs 0 · Provenienz Modell/selbst vs Modell/selbst_

```
X-113 | <gewinner: C-1701 oder C-2335> | <grund>
```

