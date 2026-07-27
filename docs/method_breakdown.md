# Joni — Methoden-Breakdown (warum ist die Trial-Pipeline ausgehungert?)

**266 Kandidaten-Methoden**  

_Read-only Diagnose. Zeigt, ob der Fix „mehr Benchmarks" (viel `kein_benchmark`) oder „Extraktion reparieren" (viel `nicht_ausfuehrbar`/`scope_unklar`) ist. Kein Trial, keine Retirierung, kein Layer-9-Schreiben._

| Bucket | Anzahl | Bedeutung |
|---|---|---|
| testbereit | 2 | matcht ein Benchmark → trialbar |
| kein_benchmark | 58 | echtes kurzes Verfahren, aber kein Gold-Set |
| nicht_ausfuehrbar | 180 | langer Paper-Titel, kein Verfahren |
| scope_unklar | 13 | kurz, aber kein Verfahrens-Hinweis |
| duplikat | 13 | wiederholt einen früheren Kandidaten |

**testbereit** (Beispiele): `bids-validator` · `converts-as-a-lens`
**kein_benchmark** (Beispiele): `retrieve-as-a-lens` · `reasoning-as-a-lens` · `supervision-as-a-lens` · `memory-dependent-as-a-lens`
**nicht_ausfuehrbar** (Beispiele): `Formalizzazione avanzata e rigorosa di un sistema di Rappresentazione della Cono` · `FedOT: Ownership Verification and Leakage Tracing via Watermarks for Federated L` · `DiffusionBench: On Holistic Evaluation of Diffusion Transformers` · `BenchX: Benchmarking AI Models for Cancer Detection and Localization with Demogr`
**scope_unklar** (Beispiele): `σ-IASI` · `Long Short-Term Memory` · `github.com/phylyc/somatic_workflow/PhylogicNDT` · `mex`
**duplikat** (Beispiele): `QVal: Cheaply Evaluating Dense Supervision Signals for Long-Horizon LLM Agents` · `From SRA to Self-Flow: Data Augmentation or Self-Supervision?` · `AutoMem: Automated Learning of Memory as a Cognitive Skill` · `MV-Forcing: Long Multi-View Video Generation via 4D-Grounded Spatio-Temporal Sel`

