"""End-to-end LIVE path: a real Layer-9 core -> DESi snapshot -> deep-method operators.

Skipped if the DESi schema is unavailable. Proves that with the SCHEMA_VERSION fix the projector
runs and Baustein B produces deep operators from an actual open conflict (no synthetic snapshot).
"""
import pytest

pytest.importorskip("desi.solution_space_gap")

import desi_layer9 as l9  # noqa: E402
from desi_layer9 import Operator as OP  # noqa: E402
from desi_layer9 import ProposalType as PT  # noqa: E402
from desi_layer9.provenance import Provenance  # noqa: E402
from joni.solution_space import from_core  # noqa: E402


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


def test_from_core_produces_deep_operators_for_an_open_conflict():
    props = from_core(_core_with_conflict(), core_commit="cafe", top_k_per_gap=3)
    assert props, "from_core should now yield deep operators (DESi schema fix)"
    for p in props:
        assert p.method_id and p.core_question
        assert p.target.startswith("conflict:")
        assert p.provenance.get("snapshot_hash")           # traceable to the projected snapshot
