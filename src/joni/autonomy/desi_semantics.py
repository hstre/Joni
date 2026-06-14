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
import math
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
            components = ("frame_detector", "logical_auditor", "frame_tension_router")
            # The stronger pair-distance measures (Π-projection / √JSD / duplication) need a
            # claim-projector. The √JSD *math* exists (Alexandria SPL `compute_jsd`), but the
            # only projector in the installed packages is clinical (needs a claim_type) - there
            # is no domain-agnostic projector for Joni's claims, so they stay unavailable here
            # rather than be faked. Recorded explicitly per measurement.
            pi_distance, dup, jsd_components, jsd_missing = _projection_distance(a_text, b_text)
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
                pi_distance=pi_distance, duplicate=dup,
                components=components + jsd_components,
                components_unavailable=jsd_missing,
                layer_name=self.name, layer_version=self.version)
        except Exception as exc:  # noqa: BLE001 - any failure => insufficient, never a guess
            return SemanticMeasurement(layer_name=self.name, layer_version=self.version,
                                       error=f"desi semantic layer error: {exc}")


def _enum_value(x) -> str:
    return getattr(x, "value", str(x))


def _alexandria_jsd():
    """The real √JSD math - Alexandria SPL ``compute_jsd`` (dependency-free) - or None.

    Importable directly if installed, else via an ``ALEXIONA_ROOT`` checkout. This is the
    *measure* the design calls for; what is missing is a projector to feed it (below)."""
    try:
        from spl import compute_jsd
        return compute_jsd
    except Exception:  # noqa: BLE001
        root = os.getenv("ALEXIONA_ROOT")
        for cand in ([os.path.join(root, "backend"), root] if root else []):
            if cand and os.path.isdir(cand) and cand not in sys.path:
                sys.path.insert(0, cand)
        try:
            from spl import compute_jsd
            return compute_jsd
        except Exception:  # noqa: BLE001
            return None


def _general_projector():
    """A domain-agnostic claim -> relational-distribution projector, or None.

    None today, by honest finding: across the installed DESi / Alexandria packages the only
    projector that turns a claim into the distribution ``compute_jsd`` compares is the
    *clinical* one (``clinical_spl.make_projection`` needs a ``claim_type``). There is no
    general projector and no embedding model, so Π/√JSD cannot be computed for Joni's
    general claims without one. A local embedding (or the SPL's LLM claim-typing) would slot
    in here and the √JSD path below activates with no other change. It is NOT faked with a
    lexical distribution dressed up as semantics."""
    return None


def _projection_distance(a_text: str, b_text: str):
    """Return (pi_distance, duplicate, components_present, components_unavailable).

    Uses the real Alexandria √JSD the moment a projector exists; otherwise fails closed
    (no distance) and records exactly what was and was not available - never a guess."""
    jsd = _alexandria_jsd()
    proj = _general_projector()
    if jsd is not None and proj is not None:
        da, db = proj(a_text), proj(b_text)
        dist = math.sqrt(max(0.0, float(jsd(da, db))))      # √JSD ∈ [0,1]
        return dist, (dist <= 0.12), ("alexandria_sqrt_jsd",), ()
    present = ("alexandria_jsd_math",) if jsd is not None else ()
    missing = ("pi_projection", "sqrt_jsd", "semantic_duplication")
    return None, None, present, missing


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
