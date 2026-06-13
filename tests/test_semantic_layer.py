"""Layer 9 governs the DESi Semantic Layer; Joni only triggers and reads.

Integration matrix over the Layer-9 semantic adapter + governed decision, using a
configurable stand-in for DESi's Semantic Layer (the real frame/logic/tension components
are pure, so the wiring is what matters here). Every case asserts: the original claims are
untouched, the analysis is recorded append-only, and Layer 9 - not Joni - decided.
"""

import desi_layer9 as l9
from desi_layer9 import SemanticDecision, SemanticState
from desi_layer9.semantics import adapter
from desi_layer9.semantics.ports import NullSemanticLayer
from semantic_stub import BrokenSemanticLayer, StubSemanticLayer

D = SemanticDecision
S = SemanticState


def _core_with(a_text, b_text):
    core = l9.Layer9()
    from desi_layer9 import Operator, ProposalType, make_proposal
    from desi_layer9.provenance import Provenance

    def mk(text, sid):
        core.submit(make_proposal(
            ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
            payload={"text": text, "topic": "t"}, proposer="source",
            provenance=Provenance.from_source(sid)), actor="joni")
        return core.all(l9.ObjectType.CLAIM)[-1]

    return core, mk(a_text, "srcA"), mk(b_text, "srcB")


def _analyse(a_text, b_text, layer):
    core, a, b = _core_with(a_text, b_text)
    sc = adapter.analyse_pair(core, a, b, layer=layer)
    # the claims themselves are never rewritten, and the analysis is its own annotation
    assert a.text == a_text and b.text == b_text
    assert sc.authority is l9.Authority.UNTRUSTED and sc.status is l9.Status.CANDIDATE
    assert sc.members == (a.id, b.id)
    return core, sc


# --- the matrix ----------------------------------------------------------------- #

def test_lexical_difference_but_semantic_equivalence_is_a_duplicate():
    # different words, but the layer measures them as the same point (small Π distance)
    _, sc = _analyse("persistent state stabilises decisions",
                     "retained context keeps choices consistent",
                     StubSemanticLayer(pi_distance=0.03))
    assert sc.decision is D.DUPLICATE and sc.semantic_state is S.SYNTHESIS_REJECTED


def test_lexical_identity_but_different_frames_is_unrelated():
    _, sc = _analyse("memory improves the system", "memory improves the system",
                     StubSemanticLayer(frame_a="empirical_causal",
                                       frame_b="thermodynamic"))
    assert sc.decision is D.UNRELATED and sc.semantic_state is S.SYNTHESIS_REJECTED


def test_semantic_duplication_signal():
    _, sc = _analyse("a", "b", StubSemanticLayer(duplicate=True))
    assert sc.decision is D.DUPLICATE


def test_logical_contradiction():
    _, sc = _analyse("the cause is A", "the cause is not A",
                     StubSemanticLayer(audit_a="logically_rejected"))
    assert sc.decision is D.CONTRADICTORY and sc.semantic_state is S.SYNTHESIS_REJECTED


def test_frame_tension():
    _, sc = _analyse("memory improves routing", "routing is a moral duty",
                     StubSemanticLayer(tension="tension", en_recommended=True))
    assert sc.decision is D.TENSION and sc.semantic_state is S.HUMAN_REVIEW_REQUIRED


def test_en_triggering_is_recorded():
    _, sc = _analyse("x", "y", StubSemanticLayer(tension="tension", en_recommended=True))
    assert sc.measurement["en_recommended"] is True
    assert "EN" in sc.decision_rationale


def test_unrelated_with_shared_vocabulary():
    # frame conflict (different declared frames) despite identical surface words
    _, sc = _analyse("memory grows during the run", "memory grows during the run",
                     StubSemanticLayer(frame_a="tool_computable",
                                       frame_b="information_theoretic"))
    assert sc.decision is D.UNRELATED


def test_complementary_is_synthesis_eligible():
    _, sc = _analyse("local routing cuts latency", "local routing saves energy",
                     StubSemanticLayer())
    assert sc.decision is D.COMPLEMENTARY and sc.semantic_state is S.SYNTHESIS_ELIGIBLE


def test_missing_layer_is_insufficient():
    _, sc = _analyse("a", "b", NullSemanticLayer())
    assert sc.decision is D.INSUFFICIENT and sc.semantic_state is S.INSUFFICIENT_EVIDENCE


def test_invalid_layer_output_fails_closed():
    # a layer that raises must never crash the gate or auto-promote
    _, sc = _analyse("a", "b", BrokenSemanticLayer())
    assert sc.decision is D.INSUFFICIENT
    assert "raised" in sc.measurement["error"]


def test_deterministic_replay_preserves_annotations():
    import tempfile
    from pathlib import Path

    from desi_layer9 import persistence
    core, a, b = _core_with("local routing cuts latency", "local routing saves energy")
    adapter.analyse_pair(core, a, b, layer=StubSemanticLayer())
    before = [(c.id, c.decision.value, c.semantic_state.value)
              for c in core.all(l9.ObjectType.SEMANTIC_CLUSTER)]
    path = Path(tempfile.mkdtemp()) / "l9.json"
    persistence.save(core, path)
    core2 = persistence.load(path)                       # load re-verifies the hash chain
    after = [(c.id, c.decision.value, c.semantic_state.value)
             for c in core2.all(l9.ObjectType.SEMANTIC_CLUSTER)]
    assert before == after and before


def test_semantic_layer_version_change_is_recorded_not_rewritten():
    core, a, b = _core_with("local routing cuts latency", "local routing saves energy")
    sc1 = adapter.analyse_pair(core, a, b, layer=StubSemanticLayer(version="1"))
    sc2 = adapter.analyse_pair(core, a, b, layer=StubSemanticLayer(version="2"))
    # a newer version produces a NEW annotation; the older one is untouched (append-only)
    assert sc1.id != sc2.id
    assert sc1.semantic_layer_version == "1" and sc2.semantic_layer_version == "2"
    assert len(core.all(l9.ObjectType.SEMANTIC_CLUSTER)) == 2
