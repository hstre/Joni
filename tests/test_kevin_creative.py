"""Kevin's REAL orchestrator running inside Joni: DESi predicts the solution-space islands, the wild
brother explores, selection keeps the promising ones - ingested as NON-AUTHORITATIVE hypotheses."""

import desi_layer9 as l9
from desi_layer9 import Operator, ProposalType, make_proposal
from desi_layer9.provenance import Provenance
from joni.autonomy import kevin_creative
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_conflict():
    cs = CoreState(l9.Layer9())
    a = cs.learn("local routing reduces inference latency", "routing", source_id="arxiv:a")
    b = cs.learn("local routing does not reduce inference latency", "routing", source_id="arxiv:b")
    cs.core.submit(make_proposal(ProposalType.CLAIM_PROPOSAL, Operator.CONFLICT_OPEN,
                   payload={"claim_ids": [a, b], "kind": "contradiction"}, proposer="joni",
                   provenance=Provenance.from_operator(), target_objects=(a, b)), actor="joni")
    return cs, a, b


def test_no_op_without_a_real_llm_client(monkeypatch):
    # The MockLLM must NEVER seed the authoritative core: off unless KEVIN_USE_REAL_LLM=1.
    monkeypatch.delenv("KEVIN_USE_REAL_LLM", raising=False)
    cs, _, _ = _cs_with_conflict()
    assert kevin_creative.enabled() is False
    out = kevin_creative.run(cs, {}, _Proto(), 1)
    assert out == {"kevin_runs": 0, "candidates": 0, "ingested": 0}
    assert cs.hypotheses() == []                         # nothing entered the core


def test_problem_is_built_from_a_real_conflict(monkeypatch):
    import pytest
    pytest.importorskip("kevin")
    cs, a, b = _cs_with_conflict()
    built = kevin_creative._problem_from(cs)
    assert built is not None
    problem, topic, parents = built
    assert set(parents) == {a, b} and topic == "routing"
    assert "discriminating" in problem.statement.lower()


def test_orchestrator_runs_and_ingests_non_authoritative_candidates(monkeypatch):
    # of production is enabled(), bypassed here on a THROWAWAY core to exercise the ingestion path
    # of production is enabled(), bypassed here on a THROWAWAY core to exercise the ingestion path.
    import pytest
    pytest.importorskip("kevin")
    monkeypatch.setattr(kevin_creative, "enabled", lambda: True)
    cs, a, b = _cs_with_conflict()
    before = {c.id for c in cs.hypotheses()}
    out = kevin_creative.run(cs, {}, _Proto(), 6)
    assert out["kevin_runs"] == 1 and out["candidates"] >= 1
    new = [c for c in cs.hypotheses() if c.id not in before]
    # every ingested candidate is a non-authoritative, model-origin, taint-flagged hypothesis tied
    # to the conflict it addresses (derived_from its claims). Kevin never promotes.
    for c in new:
        assert c.status is l9.Status.CANDIDATE
        assert c.provenance.is_model_output and c.taint.is_contaminated
        assert set(c.derived_from) <= {a, b}
