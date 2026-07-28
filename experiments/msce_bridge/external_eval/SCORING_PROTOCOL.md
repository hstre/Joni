# Scoring protocol

1. Claude may use `entailment_dev_with_gold.json` for integration and debugging.
2. Freeze code, prompt, parser model, model provider, and commit hash.
3. Give Claude only `entailment_test_blind.json`.
4. Require a JSONL prediction file containing case ID, verdict, violations, normalized structures, field agreement, model ID, k, prompt hash, and run ID.
5. Freeze that output before opening `entailment_test_gold_PRIVATE.json`.
6. Score outside Claude's implementation context.
7. Report verdict accuracy, macro-F1, false-pass rate, false-block rate, violation micro/macro-F1, and repeated-run stability.
8. Separate normalization errors from deterministic rule errors.
9. Do not edit failed test cases after results are known. Disputed cases must be marked contestable by a documented rule.
