"""Real integration with the *installed* DESi Semantic Layer (not the stub).

This is the honest counterpart to test_semantic_layer.py (which uses a stub). It loads the
actual DESi FrameDetector / LogicalAuditor / FrameTensionRouter and asserts:

  * which semantic components actually ran is recorded on every measurement;
  * two claims DESi frames differently are NOT merged;
  * an ordinary Joni-style claim pair currently FAILS CLOSED to insufficient - because the
    stronger pair measures (Π-projection / √JSD / duplication) have no domain-agnostic
    projector in the installed packages (only a clinical one). The test documents this gap
    rather than papering over it.

Skips cleanly where DESi is not importable.
"""

import os

import pytest

import desi_layer9 as l9
from desi_layer9 import SemanticDecision, SemanticState
from desi_layer9.semantics import adapter


def _real_layer():
    from joni.autonomy import desi_semantics
    for root in (os.getenv("DESI_ROOT"), "/home/user/DESi", "_desi"):
        if root and os.path.isdir(root):
            os.environ["DESI_ROOT"] = root
            break
    layer = desi_semantics.get_semantic_layer()
    if getattr(layer, "name", "") != "desi-semantic-layer":
        pytest.skip("the real DESi semantic layer is not importable in this environment")
    return layer


def _pair(a_text, b_text):
    core = l9.Layer9()
    from desi_layer9 import Operator, ProposalType, make_proposal
    from desi_layer9.provenance import Provenance

    def mk(text, sid):
        core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": "t"}, proposer="source",
            provenance=Provenance.from_source(sid)), actor="joni")
        return core.all(l9.ObjectType.CLAIM)[-1]

    return core, mk(a_text, "A"), mk(b_text, "B")


def test_real_layer_records_which_components_ran():
    layer = _real_layer()
    m = layer.analyse_pair(a_id="A", a_text="entropy increases over time",
                           b_id="B", b_text="information grows as bits accumulate")
    assert m.error == ""
    assert "frame_detector" in m.components
    assert "logical_auditor" in m.components
    assert "frame_tension_router" in m.components
    # the honest gap is recorded, not hidden: no domain-agnostic Π/√JSD projector
    assert "pi_projection" in m.components_unavailable
    assert m.pi_distance is None


def test_different_frames_are_not_merged():
    layer = _real_layer()
    core, a, b = _pair("the gas temperature rises when heated",      # thermodynamic
                       "the entropy of the message source is high")  # information-theoretic
    sc = adapter.analyse_pair(core, a, b, layer=layer)
    # whatever DESi returns, the governed decision must not be a synthesis-eligible merge
    assert sc.semantic_state is not SemanticState.SYNTHESIS_ELIGIBLE
    assert sc.decision in (SemanticDecision.UNRELATED, SemanticDecision.INSUFFICIENT,
                           SemanticDecision.CONTRADICTORY, SemanticDecision.TENSION)


def test_ordinary_joni_pair_fails_closed_to_insufficient():
    layer = _real_layer()
    core, a, b = _pair("local routing reduces request latency for short tasks",
                       "memory pressure changes how routing is decided")
    sc = adapter.analyse_pair(core, a, b, layer=layer)
    # DESi finds no frame in these short claims -> undecidable -> Layer 9 fails closed.
    # This is the documented limitation: real DESi runs, but the projector is missing.
    assert sc.decision is SemanticDecision.INSUFFICIENT
    assert sc.semantic_state in (SemanticState.HUMAN_REVIEW_REQUIRED,
                                 SemanticState.INSUFFICIENT_EVIDENCE)
    assert "pi_projection" in sc.measurement["components_unavailable"]


def test_alexandria_sqrt_jsd_math_is_real_when_importable():
    # the √JSD *math* exists and is dependency-free; only the projector is missing.
    from joni.autonomy.desi_semantics import _alexandria_jsd
    for root in (os.getenv("ALEXIONA_ROOT"), "/home/user/AleXiona"):
        if root and os.path.isdir(root):
            os.environ["ALEXIONA_ROOT"] = root
            break
    jsd = _alexandria_jsd()
    if jsd is None:
        pytest.skip("Alexandria SPL compute_jsd not importable here")
    assert jsd({"x": 1.0}, {"x": 1.0}) == 0.0           # identical distributions -> 0
    assert round(jsd({"x": 1.0}, {"y": 1.0}), 6) == 1.0  # disjoint distributions -> 1 (base-2)
