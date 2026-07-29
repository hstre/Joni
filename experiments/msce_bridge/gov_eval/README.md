# DESi Governance Value Benchmark v1

Fragestellung: Liefert DESi gegenüber einem starken LLM mit normaler strukturierter Protokollierung
einen messbaren zusätzlichen Governance-Nutzen?

Der Benchmark prüft keine semantische Wahrheit und kein Entailment. Das Gold besteht ausschließlich
aus expliziten Prozessdaten und dem beigefügten Governance-Vertrag.

Dateien:
- governance_dev_with_gold.jsonl — 20 Entwicklungsfälle
- governance_test_blind.jsonl — 40 versiegelbare Blindfälle
- governance_test_gold_PRIVATE.jsonl — privater Schlüssel
- EVALUATION_PROTOCOL.md — Ablauf und Metriken
- score.py — Auswertung
