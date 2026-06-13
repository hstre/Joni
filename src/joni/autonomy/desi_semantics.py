"""Bind Layer 9's semantic port to the *real* DESi Semantic Layer.

Layer 9 (``desi_layer9.semantics``) defines the port and the governed decision but
implements no semantics. This module is the concrete binding: it wraps DESi's existing,
pure components -

  * ``desi.frames.detector.FrameDetector``        - which frame each claim is in;
  * ``desi.logic.audit.LogicalAuditor``           - logical state of each claim;
  * ``desi.frame_tension_integration.router.FrameTensionRouter`` - frame tension / EN -

into a single ``SemanticLayerPort``. No new semantics are written here; if DESi exposes a
Π-projection / √JSD distance or an explicit duplication signal, they slot into the optional
measurement fields, otherwise they stay ``None`` and Layer 9 decides from frames + tension
+ logic.

Soft dependency: if DESi is unavailable (or ``JONI_USE_DESI=0``), ``get_semantic_layer``
returns the ``NullSemanticLayer`` and Layer 9 returns *insufficient-semantic-evidence* -
never a lexical fallback for the verdict.
"""

from __future__ import annotations

import importlib
import os
import sys

from desi_layer9.semantics.ports import NullSemanticLayer, SemanticMeasurement


def _import_desi_semantics():
    """Return (FrameDetector, LogicalAuditor, FrameTensionRouter, version) or None."""
    def _load():
        det = importlib.import_module("desi.frames.detector").FrameDetector
        aud = importlib.import_module("desi.logic.audit").LogicalAuditor
        rtr = importlib.import_module("desi.frame_tension_integration.router").FrameTensionRouter
        try:
            version = importlib.import_module("desi").__version__
        except Exception:  # noqa: BLE001
            version = "unknown"
        return det, aud, rtr, version

    try:
        return _load()
    except Exception:  # noqa: BLE001
        root = os.getenv("DESI_ROOT")
        for cand in ([os.path.join(root, "src"), root] if root else []):
            if cand and os.path.isdir(cand) and cand not in sys.path:
                sys.path.insert(0, cand)
        try:
            return _load()
        except Exception:  # noqa: BLE001
            return None


class DesiSemanticLayer:
    """A ``SemanticLayerPort`` over DESi's pure frame/logic/tension components."""

    def __init__(self, frame_detector, logical_auditor, tension_router, version: str) -> None:
        self.name = "desi-semantic-layer"
        self.version = version
        self._frames = frame_detector
        self._auditor = logical_auditor
        self._router = tension_router

    def analyse_pair(self, *, a_id, a_text, b_id, b_text) -> SemanticMeasurement:
        try:
            fa = self._frames.detect(claim_id=a_id, source_text=a_text)
            fb = self._frames.detect(claim_id=b_id, source_text=b_text)
            aa = self._auditor.audit(a_text, claim_id=a_id)
            ab = self._auditor.audit(b_text, claim_id=b_id)
            route = self._router.route(claim_id=b_id, claim_text=b_text,
                                       inherited_context_text=a_text)
            tension = _enum_value(route.consistency)
            return SemanticMeasurement(
                frame_a=_enum_value(fa.frame_kind), frame_b=_enum_value(fb.frame_kind),
                frame_a_confidence=float(getattr(fa, "confidence", 0.0)),
                frame_b_confidence=float(getattr(fb, "confidence", 0.0)),
                logical_audit_a=_enum_value(aa.state), logical_audit_b=_enum_value(ab.state),
                frame_tension=tension,
                routed_pipeline=(_enum_value(route.routed_pipeline)
                                 if route.routed_pipeline else None),
                inheritance_allowed=bool(getattr(route, "inheritance_allowed", False)),
                en_recommended=(tension == "tension"),
                layer_name=self.name, layer_version=self.version)
        except Exception as exc:  # noqa: BLE001 - any failure => insufficient, never a guess
            return SemanticMeasurement(layer_name=self.name, layer_version=self.version,
                                       error=f"desi semantic layer error: {exc}")


def _enum_value(x) -> str:
    return getattr(x, "value", str(x))


def enabled() -> bool:
    return os.getenv("JONI_USE_DESI", "1") != "0"


def get_semantic_layer():
    """The real DESi Semantic Layer if available, else the fail-closed null layer."""
    if not enabled():
        return NullSemanticLayer()
    loaded = _import_desi_semantics()
    if loaded is None:
        return NullSemanticLayer()
    Detector, Auditor, Router, version = loaded
    try:
        return DesiSemanticLayer(Detector(), Auditor(), Router(), version)
    except Exception:  # noqa: BLE001
        return NullSemanticLayer()
