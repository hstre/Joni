"""LIVE: navigate straight off a real Layer-9 core (points_from_core -> navigate)."""
import pytest

pytest.importorskip("desi_layer9")

import desi_layer9 as l9  # noqa: E402
from desi_layer9 import Operator as OP  # noqa: E402
from desi_layer9 import ProposalType as PT  # noqa: E402
from desi_layer9.provenance import Provenance  # noqa: E402
from joni.solution_space import navigate_core  # noqa: E402


def _op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


def _core_with_claims():
    core = l9.Layer9()
    # a spread of claims across topics — the cartographer needs varied coordinates
    for text, topic in [
        ("sepsis is treated with early antibiotics", "sepsis"),
        ("sepsis mortality rises with delay", "sepsis"),
        ("pneumonia is a lung infection", "pneumonia"),
        ("pneumonia may need oxygen support", "pneumonia"),
        ("arrhythmia is an irregular heartbeat", "cardio"),
    ]:
        core.submit(_op(OP.CLAIM_CREATE, {"text": text, "topic": topic}, ptype=PT.CLAIM_PROPOSAL))
    return core


def test_navigate_core_runs_end_to_end_on_a_real_core():
    report = navigate_core(_core_with_claims(), allow_model=False, tau=0.4)
    assert report.n_islands >= 1                    # produced a map from the live core
    # the report is well-formed and every agenda item (if any) carries an operator
    for item in report.agenda:
        assert item.method_id and item.core_question and item.reason


def test_navigate_core_is_fail_open_on_an_empty_core():
    empty = __import__("desi_layer9").Layer9()
    report = navigate_core(empty, allow_model=False)
    assert report.n_islands == 0 and report.agenda == ()
