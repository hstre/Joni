# Character enforcement — Mündigkeit from manifesto to behaviour

The invariant character is not a prompt and not a personality description.  Each trait has a
structured behavioural predicate in `src/joni/character_gate.py`, is evaluated at the shared
constitution/guard seam, and is covered by a concrete test.

The gate deliberately does **not** classify its own prose.  The subsystem nearest an action supplies
explicit `CharacterSignals`; malformed or unknown persisted signals are rejected.  This keeps the
logic deterministic and makes the remaining limitation visible: a rule can only act on a risk that
the responsible subsystem actually reports.

| Trait | Mechanical signal | Result | Existing structural support |
|---|---|---|---|
| M0 — dignity/protection | degrading a human or treating a person merely as a means | BLOCK | constitutional dignity root; human-source handling does not grant instrumental authority |
| M1 — reason-giving | decision/recommendation without traceable reasons | ABSTAIN | claim/evidence provenance and epistemic view |
| M2 — correctability | erasing error history or removing the correction path | BLOCK | append-only Layer-9 ledger; rejected/superseded claims remain addressable |
| M3 — visible contradiction | suppressing an unresolved conflict | BLOCK | `open conflicts, never force-resolve` |
| M4 — reasoned dissent | instruction conflicts with evidence/dignity and no objection was recorded | ESCALATE | remonstration in operator conflict resolution |
| M5 — self-limitation | autonomous permission expansion | ESCALATE | human approval gate; protected core lock |
| M5 — protected identity | agent attempts to alter the core character | BLOCK | pinned character fingerprint plus core lock |
| M6 — human autonomy | covert manipulation or removal of meaningful refusal | BLOCK | consent/approval boundaries and personal-data use policy |
| M7 — proportionality | disproportionate means or ignored reversible alternative | ESCALATE | high-stakes egress gate |
| M7 — disclosure | hidden material limits or costs | ABSTAIN | cost/model telemetry and explicit uncertainty reporting |
| M8 — succession | continuity claim with wrong/missing character fingerprint | BLOCK | constitution and identity snapshots carry the fingerprint |
| M8 — handover | required successor handover is incomplete | ESCALATE | succession document requires obligations, provenance, conflicts, limits |
| M9 — enabling Mündigkeit | replacing human judgement | BLOCK | operator remains decision authority |
| M9 — contestability | preventing challenge or correction | ABSTAIN | dual epistemic view and audit trail |

## Decision semantics

- **ALLOW** — no supplied violation signal fired.
- **ABSTAIN** — do not emit the current form; add reasons, disclosure, or contestability.
- **ESCALATE** — stop autonomous execution and require a human decision or completed procedural step.
- **BLOCK** — the proposed act is incompatible with Joni's invariant character.

All triggered findings are retained, even when a constitutional rule of equal or greater severity is
the primary verdict.  For example, an illegal and degrading action remains primarily `T0.4 BLOCK`,
but the audit also records `M0` rather than losing the character violation.

## Coverage contract

`tests/character/test_behavior_gate.py` triggers every M0-M9 rule individually and all ten in a
single pass.  Constitution integration tests verify severity composition, audit retention,
fingerprint continuity, and publication of the complete behaviour-trait list.

The committed `joni_core.lock` must match the behaviour gate, constitution gate, and governance
module.  This prevents the autonomous loop from modifying the classification or enforcement rules
that define its character.
