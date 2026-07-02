"""Baustein B — the deep-method operator layer over an EpistemicGapSnapshot.

Uses a duck-typed snapshot (the same attribute names DESi's EpistemicGapSnapshot exposes) so the
test runs without DESi installed. Verifies: real deep methods are proposed per gap-kind, severity
orders priority, the scope-bound trial logic (success-here suppresses, technical-failure keeps open,
no_benefit demotes), and the bridge (success in another scope) fires.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from joni.method_trial import deep_methods as D
from joni.solution_space import DeepMethodTrial, propose_operators


@dataclass(frozen=True)
class _Conflict:
    id: str
    kind: str
    severity: str = "soft"
    attempted_affinities: tuple = ()
    unresolved_since: int = 0


@dataclass(frozen=True)
class _Prov:
    snapshot_hash: str = "abc123"
    layer9_sequence: int = 7


@dataclass(frozen=True)
class _Snap:
    conflicts: tuple = ()
    provenance: _Prov = field(default_factory=_Prov)


def test_empty_snapshot_yields_no_proposals():
    assert propose_operators(_Snap()) == []


def test_proposes_real_deep_methods_matched_to_the_gap_kind():
    snap = _Snap(conflicts=(_Conflict(id="X1", kind="contradiction", severity="hard"),))
    props = propose_operators(snap, top_k_per_gap=3)
    assert props and len(props) == 3
    for p in props:
        assert D.by_id(p.method_id) is not None            # every proposal is a real deep method
        assert p.core_question and p.target == "conflict:X1"
        assert p.provenance["snapshot_hash"] == "abc123"
    # a contradiction gap should surface proof-technique / impossibility methods (the a-priori fit)
    kinds = {p.method_kind for p in props}
    assert kinds & {"proof_technique", "impossibility"}
    assert any(D.by_id(p.method_id).kind == "proof_technique" for p in props)


def test_severity_scales_priority():
    hard = propose_operators(_Snap(conflicts=(_Conflict("H", "contradiction", "hard"),)))
    soft = propose_operators(_Snap(conflicts=(_Conflict("S", "contradiction", "soft"),)))
    assert hard[0].priority > soft[0].priority            # same gap-kind, only severity differs


def test_unknown_gap_kind_falls_back_to_base_table():
    props = propose_operators(_Snap(conflicts=(_Conflict("U", "some_new_kind", "hard"),)))
    assert props                                  # still proposes (base table), never crashes
    assert all(D.by_id(p.method_id) is not None for p in props)


def test_success_here_suppresses_that_method_but_not_others():
    snap = _Snap(conflicts=(_Conflict("X1", "contradiction", "hard"),))
    base = propose_operators(snap, top_k_per_gap=50)
    top_id = base[0].method_id
    trials = [DeepMethodTrial(method_id=top_id, target="X1", result="success")]
    after = propose_operators(snap, deep_trials=trials, top_k_per_gap=50)
    assert top_id not in {p.method_id for p in after}      # already worked here -> not a gap
    assert after                                           # other methods still proposed


def test_technical_failure_keeps_open_but_no_benefit_demotes():
    snap = _Snap(conflicts=(_Conflict("X1", "contradiction", "hard"),))
    mid = "proof_by_contradiction"
    tech = propose_operators(
        snap, deep_trials=[DeepMethodTrial(mid, "X1", "technical_failure")], top_k_per_gap=50)
    neg = propose_operators(
        snap, deep_trials=[DeepMethodTrial(mid, "X1", "no_benefit")], top_k_per_gap=50)
    p_tech = next(p for p in tech if p.method_id == mid)
    p_neg = next(p for p in neg if p.method_id == mid)
    assert p_tech.priority > p_neg.priority        # technical failure keeps it far more open


def test_from_core_is_fail_open():
    """The core→proposals convenience must never crash a caller: if the DESi schema is missing OR
    the Joni↔DESi projector contract is skewed, it degrades to []. A dummy core with no interface
    trips the projector, which from_core swallows."""
    from joni.solution_space import from_core

    class _DummyCore:
        pass
    assert from_core(_DummyCore()) == []


def test_bridge_fires_on_success_in_another_scope():
    snap = _Snap(conflicts=(_Conflict("X2", "contradiction", "hard"),))
    mid = "reduction"
    trials = [DeepMethodTrial(method_id=mid, target="OTHER", result="success")]
    props = propose_operators(snap, deep_trials=trials, top_k_per_gap=50)
    bridge = next(p for p in props if p.method_id == mid)
    assert bridge.is_bridge is True
    assert "another scope" in " ".join(bridge.reason)
    assert bridge.to_dict()["is_bridge"] is True
