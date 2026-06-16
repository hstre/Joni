"""The read-only Layer-9 -> EpistemicGapSnapshot projector. It must copy/derive real facts, mark
every field direct/derived/unknown, NEVER invent a signal Layer 9 lacks, and never write the core.
It is also the instrument that tells us when the data capture is insufficient."""

import pytest

pytest.importorskip("desi.solution_space_gap")

import desi_layer9 as l9  # noqa: E402
from desi_layer9 import Operator as OP  # noqa: E402
from desi_layer9 import ProposalType as PT  # noqa: E402
from desi_layer9.provenance import Provenance  # noqa: E402
from joni.autonomy import epistemic_gap_projector as proj  # noqa: E402


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


def test_projects_conflicts_direct_and_is_readonly():
    core = _core_with_conflict()
    before = core.snapshot_hash() if hasattr(core, "snapshot_hash") else len(core.objects)
    snap = proj.project(core, core_commit="deadbeef")
    assert len(snap.conflicts) == 1 and snap.conflicts[0].severity == "hard"
    assert snap.provenance.core_commit == "deadbeef" and snap.provenance.schema_version
    # read-only: projecting did not mutate the core
    after = core.snapshot_hash() if hasattr(core, "snapshot_hash") else len(core.objects)
    assert before == after


def test_missing_signals_are_unknown_not_fabricated():
    snap = proj.project(_core_with_conflict())
    fs = snap.provenance.field_sources
    # Layer 9 has no per-conflict attempted moves and no scope-bound trial outcomes -> UNKNOWN,
    # and the snapshot does NOT fabricate them (empty, explicitly marked unknown).
    assert fs["conflicts.attempted_affinities"]["confidence"] == "unknown"
    assert fs["method_trials"]["confidence"] == "unknown"
    assert snap.method_trials == ()
    assert snap.conflicts[0].attempted_affinities == ()


def test_data_sufficiency_is_honest_about_the_gap():
    ds = proj.data_sufficiency(proj.project(_core_with_conflict()))
    assert ds["has_scope_bound_trials"] is False
    assert ds["beats_static_table_possible"] is False
    assert ds["verdict"].startswith("insufficient")
