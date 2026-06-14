"""A configurable stand-in for the DESi Semantic Layer, for tests.

Lets a test pin exactly what the Semantic Layer "measured" so the Layer-9 governed
decision and the Joni wiring can be checked deterministically, without DESi installed.
``cosine_distance`` defaults to 0.20 (clearly related, non-duplicate) - the happy path -
mirroring an installed embedding projector; frame/logic/tension can be set per case.
"""

from __future__ import annotations

from desi_layer9.semantics.ports import SemanticMeasurement


class StubSemanticLayer:
    def __init__(self, *, frame_a="empirical_causal", frame_b="empirical_causal",
                 tension="confirmed", audit_a="gap_detected", audit_b="gap_detected",
                 cosine_distance=0.20, duplicate=None, polarity_clash=False,
                 en_recommended=False, pi_distance=None, error="",
                 name="stub-spl", version="9"):
        self.name = name
        self.version = version
        self._m = dict(frame_a=frame_a, frame_b=frame_b, tension=tension, audit_a=audit_a,
                       audit_b=audit_b, cosine_distance=cosine_distance, pi_distance=pi_distance,
                       duplicate=duplicate, polarity_clash=polarity_clash,
                       en=en_recommended, error=error)

    def analyse_pair(self, *, a_id, a_text, b_id, b_text) -> SemanticMeasurement:
        m = self._m
        cos = m["cosine_distance"]
        return SemanticMeasurement(
            frame_a=m["frame_a"], frame_b=m["frame_b"], frame_tension=m["tension"],
            logical_audit_a=m["audit_a"], logical_audit_b=m["audit_b"],
            pi_distance=m["pi_distance"], cosine_distance=cos,
            distance_metric="cosine" if cos is not None else "",
            embedding_model="stub-embed" if cos is not None else "",
            embedding_revision="t" if cos is not None else "",
            embedding_dim=3 if cos is not None else 0,
            embedding_normalized=bool(cos is not None),
            polarity_clash=m["polarity_clash"], duplicate=m["duplicate"],
            en_recommended=m["en"], error=m["error"],
            components=("local_embedding:stub-embed@t",) if cos is not None else (),
            layer_name=self.name, layer_version=self.version)


class BrokenSemanticLayer:
    """Raises inside analyse_pair - to test that failures fail closed (no crash)."""

    name = "broken-spl"
    version = "9"

    def analyse_pair(self, *, a_id, a_text, b_id, b_text):
        raise RuntimeError("semantic layer exploded")
