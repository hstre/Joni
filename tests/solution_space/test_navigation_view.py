"""Joni's read-only navigation capability over a live core."""
import pytest

pytest.importorskip("desi_layer9")

import desi_layer9 as l9  # noqa: E402
from desi_layer9 import Operator as OP  # noqa: E402
from desi_layer9 import ProposalType as PT  # noqa: E402
from desi_layer9.provenance import Provenance  # noqa: E402
from joni.autonomy.navigation_view import run_navigation, top_agenda_line  # noqa: E402


def _op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
    return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                            provenance=Provenance.from_operator(), **kw)


def _core():
    core = l9.Layer9()
    for text, topic in [
        ("sepsis needs early antibiotics", "sepsis"),
        ("sepsis mortality rises with delay", "sepsis"),
        ("pneumonia is a lung infection", "pneumonia"),
        ("arrhythmia is an irregular heartbeat", "cardio"),
    ]:
        core.submit(_op(OP.CLAIM_CREATE, {"text": text, "topic": topic}, ptype=PT.CLAIM_PROPOSAL))
    return core


def test_run_navigation_is_read_only_and_returns_a_report():
    core = _core()
    before = len(core.all(l9.ObjectType.CLAIM))
    rep = run_navigation(core, top=5)
    assert rep["available"] is True and "n_islands" in rep
    assert len(core.all(l9.ObjectType.CLAIM)) == before      # read-only: core unchanged


def test_top_agenda_line_is_a_string():
    line = top_agenda_line(_core())
    assert isinstance(line, str)                             # empty or a one-liner, never a crash


def test_fail_open_on_a_non_core():
    class _Dummy:
        pass
    rep = run_navigation(_Dummy())
    assert rep["available"] is True and rep["n_islands"] == 0   # points_from_core -> [] -> empty
