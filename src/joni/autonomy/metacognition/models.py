"""Versioned, strictly-validated data model for one metacognition episode.

A single episode records the chain:
    situation -> available monitoring signals -> predicted success/error -> chosen control
    -> route & cost -> (later) belastbare outcome -> calibration/utility measurement.

Hard rules enforced here:
  * closed enumerations for ``knowledge_boundary``, ``selected_control``, ``outcome``;
  * numeric ``signals`` and ``predicted_success`` must lie in [0, 1];
  * unknown fields and wrong types are rejected (no silent coercion);
  * ``episode_id`` is a deterministic content hash (never a random UUID);
  * an ``outcome`` starts as ``unknown`` and a later result is an APPEND-ONLY
    ``OutcomeEvent`` that references ``episode_id`` - the episode is never rewritten;
  * ``unknown`` is never silently reinterpreted as success/failure/mixed.

No free-text prompt/answer/secret is stored - only ids, categories, bounded hashes,
short pre-cleaned reasons, existing references and numeric signals.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

MONITOR_VERSION = "metacog-v1"


class KnowledgeBoundary(StrEnum):
    INSIDE = "inside"
    OUTSIDE = "outside"
    CONFLICTING = "conflicting"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MONITOR_DARK = "monitor_dark"          # the relevant monitor was absent/disabled
    UNKNOWN = "unknown"


class SelectedControl(StrEnum):
    PROCEED = "proceed"
    RETRIEVE = "retrieve"
    VERIFY = "verify"
    ASK_HUMAN = "ask_human"
    ABSTAIN = "abstain"
    DEFER = "defer"
    ESCALATE = "escalate"


class Outcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    MIXED = "mixed"
    UNKNOWN = "unknown"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _num01(name: str, v: object) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(v).__name__}")
    f = float(v)
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"{name} must be in [0,1], got {f}")
    return f


# the closed set of episode fields - anything else is rejected on load
_EPISODE_FIELDS = frozenset({
    "episode_id", "cycle", "created_tick", "task_family", "decision_seam", "subject_refs",
    "signal_sources", "signals", "predicted_success", "confidence_source",
    "knowledge_boundary", "selected_control", "plain_control", "expected_cost",
    "actual_cost", "route", "model_or_tool", "outcome", "outcome_source", "outcome_cycle",
    "outcome_refs", "monitor_version", "configuration_hash",
})


@dataclass(frozen=True)
class Episode:
    cycle: int
    created_tick: int
    task_family: str
    decision_seam: str
    subject_refs: tuple[str, ...]
    signal_sources: tuple[str, ...]
    signals: dict[str, float]                 # numeric monitoring signals, each in [0,1]
    predicted_success: float                  # in [0,1] (predicted_error = 1 - this)
    confidence_source: str                    # WHICH subsystem produced it (never free prose)
    knowledge_boundary: KnowledgeBoundary
    selected_control: SelectedControl
    expected_cost: float
    route: str
    model_or_tool: str
    configuration_hash: str
    plain_control: SelectedControl | None = None
    actual_cost: float = 0.0
    outcome: Outcome = Outcome.UNKNOWN
    outcome_source: str = ""
    outcome_cycle: int | None = None
    outcome_refs: tuple[str, ...] = ()
    monitor_version: str = MONITOR_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.cycle, int) or isinstance(self.cycle, bool):
            raise ValueError("cycle must be an int")
        if not isinstance(self.created_tick, int) or isinstance(self.created_tick, bool):
            raise ValueError("created_tick must be an int")
        for name in ("task_family", "decision_seam", "confidence_source", "route",
                     "model_or_tool", "configuration_hash"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty str")
        _num01("predicted_success", self.predicted_success)
        if not isinstance(self.expected_cost, (int, float)) or self.expected_cost < 0:
            raise ValueError("expected_cost must be a number >= 0")
        if not isinstance(self.actual_cost, (int, float)) or self.actual_cost < 0:
            raise ValueError("actual_cost must be a number >= 0")
        if not isinstance(self.signals, dict):
            raise ValueError("signals must be a dict")
        for k, v in self.signals.items():
            if not isinstance(k, str):
                raise ValueError("signal keys must be str")
            _num01(f"signals[{k}]", v)
        if not isinstance(self.knowledge_boundary, KnowledgeBoundary):
            raise ValueError("knowledge_boundary must be a KnowledgeBoundary")
        if not isinstance(self.selected_control, SelectedControl):
            raise ValueError("selected_control must be a SelectedControl")
        if self.plain_control is not None and not isinstance(self.plain_control, SelectedControl):
            raise ValueError("plain_control must be a SelectedControl or None")
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome must be an Outcome")

    def episode_id(self) -> str:
        """Deterministic content hash - identical normalised inputs -> identical id."""
        core = {
            "cycle": self.cycle, "decision_seam": self.decision_seam,
            "subject_refs": sorted(self.subject_refs),
            "signal_sources": sorted(self.signal_sources),
            "signals": {k: round(float(v), 6) for k, v in sorted(self.signals.items())},
            "predicted_success": round(self.predicted_success, 6),
            "knowledge_boundary": self.knowledge_boundary.value,
            "selected_control": self.selected_control.value,
            "monitor_version": self.monitor_version,
            "configuration_hash": self.configuration_hash,
        }
        return _sha(json.dumps(core, sort_keys=True, ensure_ascii=False))[:16]

    def to_record(self) -> dict:
        return {
            "episode_id": self.episode_id(), "cycle": self.cycle,
            "created_tick": self.created_tick, "task_family": self.task_family,
            "decision_seam": self.decision_seam, "subject_refs": list(self.subject_refs),
            "signal_sources": list(self.signal_sources),
            "signals": {k: round(float(v), 6) for k, v in sorted(self.signals.items())},
            "predicted_success": round(self.predicted_success, 6),
            "confidence_source": self.confidence_source,
            "knowledge_boundary": self.knowledge_boundary.value,
            "selected_control": self.selected_control.value,
            "plain_control": self.plain_control.value if self.plain_control else None,
            "expected_cost": round(float(self.expected_cost), 6),
            "actual_cost": round(float(self.actual_cost), 6),
            "route": self.route, "model_or_tool": self.model_or_tool,
            "outcome": self.outcome.value, "outcome_source": self.outcome_source,
            "outcome_cycle": self.outcome_cycle, "outcome_refs": list(self.outcome_refs),
            "monitor_version": self.monitor_version,
            "configuration_hash": self.configuration_hash,
        }

    @staticmethod
    def from_record(d: dict) -> Episode:
        if not isinstance(d, dict):
            raise ValueError("episode record must be a dict")
        extra = set(d) - _EPISODE_FIELDS
        if extra:
            raise ValueError(f"unknown episode field(s): {sorted(extra)}")
        return Episode(
            cycle=d["cycle"], created_tick=d["created_tick"], task_family=d["task_family"],
            decision_seam=d["decision_seam"], subject_refs=tuple(d.get("subject_refs", ())),
            signal_sources=tuple(d.get("signal_sources", ())), signals=dict(d.get("signals", {})),
            predicted_success=d["predicted_success"], confidence_source=d["confidence_source"],
            knowledge_boundary=KnowledgeBoundary(d["knowledge_boundary"]),
            selected_control=SelectedControl(d["selected_control"]),
            plain_control=(SelectedControl(d["plain_control"]) if d.get("plain_control") else None),
            expected_cost=d.get("expected_cost", 0.0), actual_cost=d.get("actual_cost", 0.0),
            route=d["route"], model_or_tool=d["model_or_tool"],
            outcome=Outcome(d.get("outcome", "unknown")),
            outcome_source=d.get("outcome_source", ""),
            outcome_cycle=d.get("outcome_cycle"), outcome_refs=tuple(d.get("outcome_refs", ())),
            monitor_version=d.get("monitor_version", MONITOR_VERSION),
            configuration_hash=d["configuration_hash"],
        )


# outcome sources that carry a belastbares result (a result is otherwise 'unknown')
ROBUST_OUTCOME_SOURCES = frozenset({
    "deterministic_checker", "gold_label", "existing_test", "ci_result",
    "later_layer9_status", "human_decision", "reproducible_tool", "pr_outcome",
})


@dataclass(frozen=True)
class OutcomeEvent:
    """Append-only resolution of an episode - references the id, never rewrites the episode."""
    episode_id: str
    outcome: Outcome
    outcome_source: str
    outcome_cycle: int
    resolved_tick: int
    outcome_refs: tuple[str, ...] = ()
    detail: str = ""                       # short, pre-cleaned; no free prose/secrets
    monitor_version: str = MONITOR_VERSION

    def __post_init__(self) -> None:
        if not self.episode_id or not isinstance(self.episode_id, str):
            raise ValueError("episode_id required")
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome must be an Outcome")
        if self.outcome is Outcome.UNKNOWN:
            raise ValueError("do not emit an outcome event for 'unknown' - leave it pending")
        if self.outcome_source not in ROBUST_OUTCOME_SOURCES:
            raise ValueError(
                f"outcome_source must be a belastbare source, got {self.outcome_source!r}")

    def to_record(self) -> dict:
        return {
            "kind": "outcome", "episode_id": self.episode_id, "outcome": self.outcome.value,
            "outcome_source": self.outcome_source, "outcome_cycle": self.outcome_cycle,
            "resolved_tick": self.resolved_tick, "outcome_refs": list(self.outcome_refs),
            "detail": self.detail[:200], "monitor_version": self.monitor_version,
        }


__all__ = [
    "MONITOR_VERSION", "KnowledgeBoundary", "SelectedControl", "Outcome",
    "Episode", "OutcomeEvent", "ROBUST_OUTCOME_SOURCES",
]
