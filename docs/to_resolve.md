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

## X-411 · Thema: context

- **C-6978** (0 stützend · 0 Kontext): The recursive selection process separates evidence organization from answer generation without training, external memory, or context pruning.
  - _Quelle:_ granite:joni-c393:f67979ec0a92
- **C-8539** (0 stützend · 0 Kontext): [Alexandria-Bewertung · assessor · keine Entscheidung] **Cross-reconstruction:**

ChatGPT (adversarial) and DeepSeek (consistency) converge on the core trade-off: global operators buy long-range context but risk parameter inflation and loss of fine local detail. No genuine divergence in substance.

One methodological difference: DeepSeek adds an *admissibility gate* — the idea is only formally coherent if "global" is disambiguated (spectral decomposition vs. full-size kernel) and the application domain is explicitly bounded. ChatGPT treats these as *quality risks*, not admissibility conditions. I keep DeepSeek's stricter framing: the differing rule is whether under-specification blocks admissibility (yes) or merely lowers confidence (ChatGPT's view). Since the source text is truncated ("A P"), no selective-context-weighting mechanism is stated, so DeepSeek's gate applies.

**Reconciled assessment:**
Tragfähig unter: (1) global = spektral/faktorisiert, nicht kernel=input-size; (2) Hybrid lokal+global mit Positionskodierung; (3) auf ganzheitliche Aufgaben eingeschränkt. Bricht bei: fehlendem Lokalitätsbias, Parameterinflation, undifferenziertem "global", fehlendem Gewichtungsmechanismus. Formal zulässig als Forumsvorschlag, aber die Fragmentbeschreibung lässt zentrale Annahmen offen — Nachschärfung nötig.

Kein Wahrheits- oder Entscheidungsurteil — Joni entscheidet.
  - _Quelle:_ panel:expert:claude
- _Evidenzlage (C-6978 vs C-8539): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz Modell/selbst vs Forum_

```
X-411 | <gewinner: C-6978 oder C-8539> | <grund>
```

## X-407 · Thema: memory

- **C-22** (0 stützend · 0 Kontext): Remise: Authorized Anonymous Communication Systems
  - _Quelle:_ zenodo:20761254
- **C-8309** (0 stützend · 0 Kontext): Authorized Anonymous Communication Systems (Remise) enable communication without revealing identities.
  - _Quelle:_ granite:joni-c568:087871c363d2
- _Evidenzlage (C-22 vs C-8309): Belege 0 vs 0 · Quellfamilien 0 vs 0 · Provenienz extern vs Modell/selbst_

```
X-407 | <gewinner: C-22 oder C-8309> | <grund>
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

