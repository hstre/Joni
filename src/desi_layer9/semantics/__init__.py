"""Layer 9's semantic boundary.

This package does **not** implement semantics. It defines the port to the existing DESi
Semantic Layer (FrameDetector / LogicalAuditor / FrameTensionRouter, and Π-distance /
duplication / EN if exposed), the governed decision Layer 9 makes over its measurements,
and the adapter that records that analysis as append-only annotations through the gate.

Lexical overlap survives only as a cheap candidate trigger (``candidate_extractor``); it
never decides a relation.
"""

from __future__ import annotations

from . import adapter, candidate_extractor, decision
from .candidate_extractor import candidate_groups, candidate_pairs, lexical_overlap
from .decision import classify
from .ports import NullSemanticLayer, SemanticLayerPort, SemanticMeasurement

__all__ = [
    "adapter", "candidate_extractor", "decision", "classify",
    "candidate_pairs", "candidate_groups", "lexical_overlap",
    "SemanticLayerPort", "SemanticMeasurement", "NullSemanticLayer",
]
