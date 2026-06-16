"""Kevin's creative arm, revised architecture: the hurdle is on ADOPTION, not GENERATION.

Kevin may fire on ANY one substantial input (a single rich topic, an open conflict, a
single-source candidate) - he never needs two independent sources or confirmed claims to *generate*.
Every output is a non-authoritative, kevin/model-origin CANDIDATE that requires downstream review;
single-source caps later promotion, not generation; Kevin can never confirm/resolve/promote.
"""

from pathlib import Path

import desi_layer9 as l9
from desi_layer9 import Authority, OriginType, Status
from joni.autonomy import kevin_llm, model_call
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _propose_json(profile, system, user):
    return '[{"text": "routing latency budgets could bound memory consolidation", "topic": "x"}]'


def _online(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", _propose_json)


def _cs_single_topic(source="arxiv:p1"):
    # ONE substantial topic from ONE source - no second source, nothing confirmed.
    cs = CoreState(seed_core())
    cs.learn("transformer routing reduces tail latency at serving time", "routing",
             source_id=source)
    cs.learn("the routing layer caches hot experts for reuse", "routing", source_id=source)
    return cs


def _cs_with_open_conflict():
    cs = CoreState(seed_core())
    a = cs.learn("local routing reduces inference latency", "routing", source_id="arxiv:a")
    b = cs.learn("local routing does not reduce inference latency", "routing",
                 source_id="arxiv:b")
    cs.open_conflict((a, b), severity="hard")
    return cs


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    out = kevin_llm.propose(CoreState(seed_core()), {}, _Proto(), 3)
    assert out == {"kevin_calls": 0, "hypotheses": 0}


def test_kevin_accepts_single_substantial_paper(monkeypatch, tmp_path):
    # KEVIN_ACCEPTS_SINGLE_SUBSTANTIAL_PAPER: one rich single-source topic is enough to GENERATE.
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    out = kevin_llm.propose(cs, ext, _Proto(), 3)
    assert out["kevin_calls"] == 1 and out["hypotheses"] >= 1
    assert ext["kevin_llm"][-1]["input_type"] == "single_topic_method_exploration"


def test_kevin_accepts_single_open_conflict(monkeypatch, tmp_path):
    # KEVIN_ACCEPTS_SINGLE_OPEN_CONFLICT + KEVIN_ACCEPTS_INTERNALLY_CONTRADICTORY_INPUT
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_with_open_conflict(), {}
    out = kevin_llm.propose(cs, ext, _Proto(), 3)
    assert out["kevin_calls"] == 1 and out["hypotheses"] >= 1
    entry = ext["kevin_llm"][-1]
    assert entry["input_type"] == "open_conflict"
    assert entry["internal_coherence"] == "contradictory"   # contradiction is fuel, not a blocker


def test_kevin_rejects_empty_or_technical_garbage(monkeypatch, tmp_path):
    # KEVIN_REJECTS_EMPTY_OR_TECHNICAL_GARBAGE: nothing substantial -> no call.
    _online(monkeypatch, tmp_path)
    cs = CoreState(seed_core())                         # empty core, no topics, no conflict
    out = kevin_llm.propose(cs, {}, _Proto(), 3)
    assert out["kevin_calls"] == 0 and out["hypotheses"] == 0


def test_kevin_output_is_always_nonauthoritative_kevin_origin(monkeypatch, tmp_path):
    # KEVIN_OUTPUT_ALWAYS_NONAUTHORITATIVE: candidate, kevin/model provenance, taint-flagged.
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    before = {c.id for c in cs.hypotheses()}
    kevin_llm.propose(cs, ext, _Proto(), 3)
    new = [c for c in cs.hypotheses() if c.id not in before]
    assert new, "Kevin produced no candidate hypothesis"
    h = new[0]
    assert h.status is Status.CANDIDATE and h.authority is not Authority.AUTHORITATIVE
    assert h.provenance.is_model_output                  # kevin/model origin, not operator
    assert h.taint.is_contaminated and not h.taint.human_validated


def test_single_source_limits_promotion_not_generation(monkeypatch, tmp_path):
    # SINGLE_SOURCE_LIMITS_PROMOTION_NOT_GENERATION: it FIRES (generation) but the candidate cannot
    # be confirmed without an explicit human validation (the ceiling), and is flagged provisional.
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    out = kevin_llm.propose(cs, ext, _Proto(), 3)
    assert out["hypotheses"] >= 1                        # generation NOT blocked by single source
    entry = ext["kevin_llm"][-1]
    assert entry["source_count"] == 1 and entry["confirmation_ceiling"] == "provisional"
    assert entry["external_corroboration"] == "missing"
    h = [c for c in cs.hypotheses()][-1]
    ok, reasons = l9.can_confirm_claim(h, [], unresolved_hard_contradiction=False)
    assert not ok and any("contaminated" in r for r in reasons)  # promotion ceiling enforced


def test_kevin_proposal_requires_review_and_is_logged_for_the_panel(monkeypatch, tmp_path):
    # KEVIN_PROPOSAL_REQUIRES_EXPERT_REVIEW: flagged requires_review, logged with id so the panel
    # (which convenes "when Kevin proposes something") can assess it.
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    kevin_llm.propose(cs, ext, _Proto(), 3)
    entry = ext["kevin_llm"][-1]
    assert entry["requires_review"] is True and entry["authority"] == "none"
    assert entry["proposals"] and entry["proposals"][0]["id"]


def test_kevin_cannot_confirm_or_resolve():
    # KEVIN_CANNOT_CONFIRM_OR_RESOLVE: the hard authority boundary, by policy (model-origin).
    from desi_layer9 import Operator
    from desi_layer9.policy import may_request
    assert may_request(OriginType.EXTERNAL_MODEL, Operator.CLAIM_CONFIRM) is False
    assert may_request(OriginType.EXTERNAL_MODEL, Operator.CONFLICT_RESOLVE) is False
    assert may_request(OriginType.EXTERNAL_MODEL, Operator.METHOD_PROMOTE) is False


def test_kevin_input_dedup_and_cooldown(monkeypatch, tmp_path):
    # KEVIN_INPUT_DEDUP_AND_COOLDOWN: the same input is not re-processed; cadence still applies.
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    assert kevin_llm.propose(cs, ext, _Proto(), 3)["kevin_calls"] == 1
    # cadence elapsed but the SAME input -> deduped, no second spend
    assert kevin_llm.propose(cs, ext, _Proto(), 9)["kevin_calls"] == 0


def test_end_to_end_single_paper_to_layer9_candidate(monkeypatch, tmp_path):
    # E2E: single paper -> Kevin call -> non-empty -> parsed -> candidate proposal in Layer 9,
    # NO auto-promotion (stays candidate, awaiting the panel + a human).
    _online(monkeypatch, tmp_path)
    cs, ext = _cs_single_topic(), {}
    out = kevin_llm.propose(cs, ext, _Proto(), 3)
    assert out["kevin_calls"] == 1 and out["hypotheses"] >= 1
    h = [c for c in cs.hypotheses()][-1]
    assert h.status is Status.CANDIDATE                  # entered Layer 9, never auto-promoted
    # the call is captured (telemetry) and replay-stable
    t = model_call.telemetry(Path(tmp_path) / "state" / "model_calls")
    assert t["kevin_calls"] == 1
