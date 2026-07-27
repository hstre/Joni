# Joni — Methoden-Breakdown (warum ist die Trial-Pipeline ausgehungert?)

**279 Kandidaten-Methoden**  

_Read-only Diagnose. Zeigt, ob der Fix „mehr Benchmarks" (viel `kein_benchmark`) oder „Extraktion reparieren" (viel `nicht_ausfuehrbar`/`scope_unklar`) ist. Kein Trial, keine Retirierung, kein Layer-9-Schreiben._

| Bucket | Anzahl | Bedeutung |
|---|---|---|
| testbereit | 2 | matcht ein Benchmark → trialbar |
| kein_benchmark | 62 | echtes kurzes Verfahren, aber kein Gold-Set |
| nicht_ausfuehrbar | 189 | langer Paper-Titel, kein Verfahren |
| scope_unklar | 13 | kurz, aber kein Verfahrens-Hinweis |
| duplikat | 13 | wiederholt einen früheren Kandidaten |

**testbereit** (Beispiele): `bids-validator` · `converts-as-a-lens`
**kein_benchmark** (Beispiele): `ignacioi-as-a-lens` · `kiskalla-as-a-lens` · `ed-lau/riana: RIANA v1.0.0` · `amnesia-as-a-lens`
**nicht_ausfuehrbar** (Beispiele): `Formalizzazione avanzata e rigorosa di un sistema di Rappresentazione della Cono` · `DREAM: Dense Retrieval Embeddings via Autoregressive Modeling` · `FedOT: Ownership Verification and Leakage Tracing via Watermarks for Federated L` · `DiffusionBench: On Holistic Evaluation of Diffusion Transformers`
**scope_unklar** (Beispiele): `σ-IASI` · `Long Short-Term Memory` · `github.com/phylyc/somatic_workflow/PhylogicNDT` · `mex`
**duplikat** (Beispiele): `QVal: Cheaply Evaluating Dense Supervision Signals for Long-Horizon LLM Agents` · `From SRA to Self-Flow: Data Augmentation or Self-Supervision?` · `AutoMem: Automated Learning of Memory as a Cognitive Skill` · `MV-Forcing: Long Multi-View Video Generation via 4D-Grounded Spatio-Temporal Sel`

