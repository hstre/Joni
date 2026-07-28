# External DESi Entailment Evaluation Set

Independent test construction for the DESi/MSCE Claim–Evidence Entailment Auditor.

- `entailment_dev_with_gold.json`: 20 labeled development cases. Claude may see these.
- `entailment_test_blind.json`: 40 blinded evaluation cases. Give this to Claude.
- `entailment_test_gold_PRIVATE.json`: private answer key. Do not provide before predictions are frozen.
- `SCORING_PROTOCOL.md`: anti-leakage procedure.

This is an evaluation instrument, not yet a validated benchmark. The private gold labels should receive a final human review before publication.
