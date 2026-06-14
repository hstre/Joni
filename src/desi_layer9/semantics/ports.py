"""The Semantic-Layer *port* - Layer 9's boundary to the existing DESi Semantic Layer.

Layer 9 does not re-implement semantics. It defines this narrow interface and *injects*
the real DESi components behind it (FrameDetector / LogicalAuditor / FrameTensionRouter,
and Π-distance/duplication if exposed). This keeps ``desi_layer9`` dependency-free and
extractable while the authoritative semantic judgement comes from DESi.

A ``SemanticMeasurement`` is exactly what DESi measured - never a decision. The governed
decision is Layer 9's, in ``decision.py``. When no layer is available (``NullSemanticLayer``)
the measurement carries an ``error`` and Layer 9 returns *insufficient-semantic-evidence* -
it never falls back to lexical overlap for a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

FRAME_UNDECLARED = "frame_undeclared"


@dataclass(frozen=True)
class SemanticMeasurement:
    """Raw outputs of the DESi Semantic Layer for one pair of claims. No interpretation."""

    frame_a: str = FRAME_UNDECLARED
    frame_b: str = FRAME_UNDECLARED
    frame_a_confidence: float = 0.0
    frame_b_confidence: float = 0.0
    logical_audit_a: str = "under_logical_audit"
    logical_audit_b: str = "under_logical_audit"
    frame_tension: str = "undecidable"            # FrameConsistency value (confirmed|tension|...)
    routed_pipeline: str | None = None
    inheritance_allowed: bool = False
    en_recommended: bool = False                  # an EN operation is warranted (tension)
    # √JSD path - reserved for an actual text->distribution projector. Stays None until one
    # exists; an embedding cosine distance is NEVER reported here (it is not √JSD).
    pi_distance: float | None = None
    # Embedding channel (an ADDITIONAL measure): cosine distance, explicitly labelled, with
    # the exact model identity so a measurement is reproducible and a model change is visible.
    cosine_distance: float | None = None
    distance_metric: str = ""                     # "cosine" when cosine_distance is set
    embedding_model: str = ""
    embedding_revision: str = ""
    embedding_dim: int = 0
    embedding_normalized: bool = False
    polarity_clash: bool = False                  # negation/antonym opposition between the claims
    duplicate: bool | None = None                 # explicit duplication signal, if any
    layer_name: str = "absent"
    layer_version: str = "0"
    error: str = ""                               # non-empty => layer absent/invalid output
    # which semantic components actually produced this measurement, and which were not
    # available (e.g. no domain-agnostic projector for Π/√JSD). Recorded on every measure.
    components: tuple[str, ...] = ()
    components_unavailable: tuple[str, ...] = ()
    extra: dict = field(default_factory=dict)

    @property
    def frames_declared(self) -> bool:
        return self.frame_a != FRAME_UNDECLARED and self.frame_b != FRAME_UNDECLARED

    @property
    def frames_match(self) -> bool:
        return self.frames_declared and self.frame_a == self.frame_b

    def to_dict(self) -> dict:
        return {
            "frame_a": self.frame_a, "frame_b": self.frame_b,
            "frame_a_confidence": round(self.frame_a_confidence, 4),
            "frame_b_confidence": round(self.frame_b_confidence, 4),
            "logical_audit_a": self.logical_audit_a, "logical_audit_b": self.logical_audit_b,
            "frame_tension": self.frame_tension, "routed_pipeline": self.routed_pipeline,
            "inheritance_allowed": self.inheritance_allowed,
            "en_recommended": self.en_recommended, "pi_distance": self.pi_distance,
            "cosine_distance": self.cosine_distance, "distance_metric": self.distance_metric,
            "embedding_model": self.embedding_model,
            "embedding_revision": self.embedding_revision,
            "embedding_dim": self.embedding_dim,
            "embedding_normalized": self.embedding_normalized,
            "polarity_clash": self.polarity_clash,
            "duplicate": self.duplicate, "layer_name": self.layer_name,
            "layer_version": self.layer_version, "error": self.error,
            "components": list(self.components),
            "components_unavailable": list(self.components_unavailable),
        }


@runtime_checkable
class SemanticLayerPort(Protocol):
    """What Layer 9 needs from a semantic layer: measure one ordered pair of claims."""

    name: str
    version: str

    def analyse_pair(self, *, a_id: str, a_text: str, b_id: str,
                     b_text: str) -> SemanticMeasurement: ...


@dataclass(frozen=True)
class NullSemanticLayer:
    """Used when the DESi Semantic Layer is unavailable. Always returns 'insufficient' -
    Layer 9 must never invent a semantic verdict, so this fails closed."""

    name: str = "absent"
    version: str = "0"

    def analyse_pair(self, *, a_id, a_text, b_id, b_text) -> SemanticMeasurement:
        return SemanticMeasurement(layer_name=self.name, layer_version=self.version,
                                   error="semantic layer unavailable")
