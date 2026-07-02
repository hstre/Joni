"""LIVE: a real Layer-9 core drives a full operator cycle, and the store feeds discovery.

Skipped without the DESi schema. A no-op apply leaves the conflict open, so the cycle honestly
records 'no_benefit' — proving the whole seam (from_core -> apply -> grade -> store) runs live.
"""
import pytest

pytest.importorskip("desi.solution_space_gap")

import desi_layer9 as l9  # noqa: E402
from desi_layer9 import Operator as OP  # noqa: E402
from desi_layer9 import ProposalType as PT  # noqa: E402
from desi_layer9.provenance import Provenance  # noqa: E402
from joni.solution_space.core_points import points_from_core  # noqa: E402
from joni.solution_space.operator_cycle import run_operator_cycle  # noqa: E402
from joni.solution_space.trial_store import load_trials  # noqa: E402


def _op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


def _core_with_conflict():
    core = l9.Layer9()
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x reduces y", "topic": "t"},
                    ptype=PT.CLAIM_PROPOSAL))
    core.submit(_op(OP.CLAIM_CREATE, {"text": "x does not reduce y", "topic": "t"},
                    ptype=PT.CLAIM_PROPOSAL))
    a, b = (c.id for c in core.all(l9.ObjectType.CLAIM))
    core.submit(_op(OP.CONFLICT_OPEN, {"claim_ids": [a, b], "severity": "hard"},
                    target_objects=(a, b)))
    return core


def test_points_from_a_live_core_carry_real_statevectors():
    pts = points_from_core(_core_with_conflict(), allow_model=False)
    assert len(pts) == 2                          # two claims -> two points
    for p in pts:
        assert len(p.state_vector) == 9 and any(x > 0 for x in p.state_vector)


def test_live_cycle_records_no_benefit_for_a_noop_apply(tmp_path):
    store = str(tmp_path / "trials.jsonl")
    trial = run_operator_cycle(_core_with_conflict(), store, lambda core, p: None)
    assert trial is not None and trial.result == "no_benefit"   # conflict still open after a no-op
    assert trial.method_id and load_trials(store) == [trial]
