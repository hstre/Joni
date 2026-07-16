"""Functional externalized metacognition - system-level monitoring & control, SHADOW ONLY.

This subsystem measures, per decision, which structured signals were available, what the
system predicted, which control it chose, what it cost, and what belastbare outcome was
later observed - then scores the calibration of that monitoring. It is *functional,
externalized* metacognition (system-level metacognitive monitoring and control); it makes
NO claim of consciousness, sentience, or phenomenal introspection, and it never classifies
a model's free prose as self-knowledge - only structured signals from the responsible
subsystem enter here.

In this stage the supervisor OBSERVES only: it holds no decision authority, changes no
threshold, blocks nothing, and never flips an enforce mode. Aggregation, thresholds,
outcome-linking and metrics are deterministic; LLM-produced scores may enter only as
*signals*, never as facts.
"""
from __future__ import annotations

from . import audit, metrics, models

__all__ = ["models", "audit", "metrics"]
