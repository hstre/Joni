"""A configurable stand-in for the DESi Semantic Layer, for tests.

Lets a test pin exactly what the Semantic Layer "measured" so the Layer-9 governed
decision and the Joni wiring can be checked deterministically, without DESi installed.
``pi_distance`` defaults to 0.5 so the happy path is *not* read as a duplicate purely
because the texts overlap lexically.
"""

from __future__ import annotations

from desi_layer9.semantics.ports import SemanticMeasurement


class StubSemanticLayer:
    def __init__(self, *, frame_a="empirical_causal", frame_b="empirical_causal",
                 tension="confirmed", audit_a="gap_detected", audit_b="gap_detected",
                 pi_distance=0.5, duplicate=None, en_recommended=False,
                 error="", name="stub-spl", version="9"):
        self.name = name
        self.version = version
        self._m = dict(frame_a=frame_a, frame_b=frame_b, tension=tension, audit_a=audit_a,
                       audit_b=audit_b, pi_distance=pi_distance, duplicate=duplicate,
                       en=en_recommended, error=error)

    def analyse_pair(self, *, a_id, a_text, b_id, b_text) -> SemanticMeasurement:
        m = self._m
        return SemanticMeasurement(
            frame_a=m["frame_a"], frame_b=m["frame_b"], frame_tension=m["tension"],
            logical_audit_a=m["audit_a"], logical_audit_b=m["audit_b"],
            pi_distance=m["pi_distance"], duplicate=m["duplicate"],
            en_recommended=m["en"], error=m["error"],
            layer_name=self.name, layer_version=self.version)


class BrokenSemanticLayer:
    """Raises inside analyse_pair - to test that failures fail closed (no crash)."""

    name = "broken-spl"
    version = "9"

    def analyse_pair(self, *, a_id, a_text, b_id, b_text):
        raise RuntimeError("semantic layer exploded")
