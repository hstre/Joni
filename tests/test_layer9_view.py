"""The human-facing Layer-9 map renders the five prototype elements from real state."""

import json

import desi_layer9 as l9
from joni.autonomy import layer9_view
from joni.autonomy.core_state import CoreState, seed_core
from semantic_stub import StubSemanticLayer


class _Proto:
    def record(self, *a, **k):
        pass


def _rich_cs():
    cs = CoreState(seed_core())
    for t, txt in [("routing", "cheap local routing keeps latency low"),
                   ("routing", "cheap local routing improves decision quality"),
                   ("memory", "memory pressure changes routing under load")]:
        cs.learn(txt, t)
    from joni.autonomy import develop
    develop.develop(cs, {}, _Proto(), layer=StubSemanticLayer())
    a, b = cs.active_claims()[0].id, cs.active_claims()[1].id
    cs.open_conflict((a, b), severity="soft")
    cs.propose_self_model("I prefer small verifiable experiments", evidence=[a, b])
    cs.render_narrative("I have decided to keep routing local.", basis=[a, b])
    return cs


def test_export_separates_truth_from_salience_and_records_taint():
    cs = _rich_cs()
    exp = cs.epistemic_export()
    claim = exp["claims"][0]
    # truth (status/support) and salience are separate channels, plus taint + evidence
    for field in ("status", "authority", "support", "salience", "evidence_strength", "taint"):
        assert field in claim
    assert "taint_summary" in exp and "authority_summary" in exp
    assert "tainted_authoritative" in exp            # the red-flag list
    assert exp["narratives"] and exp["narratives"][0]["basis"]   # an utterance with provenance


def test_page_renders_the_five_elements(tmp_path):
    cs = _rich_cs()
    out = tmp_path / "layer9.html"
    layer9_view.render(out, {"export": cs.epistemic_export(),
                             "budget": {"spent_eur": 0.0, "cap_eur": 20.0},
                             "window": {"start": "2026-06-13"}})
    h = out.read_text()
    for marker in ("Conversation View", "Epistemic graph", "Audit timeline",
                   "influence map", "current state", "provenance"):
        assert marker in h
    # the embedded data is valid JSON the page parses
    blob = h.split("const DATA = ", 1)[1].split(";\nconst X", 1)[0]
    assert json.loads(blob)["export"]["claims"]


def test_cycle_writes_the_layer9_map(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.delenv("JONI_ONLINE", raising=False)
    from joni.autonomy.run import one_cycle
    one_cycle()
    page = tmp_path / "docs" / "layer9.html"
    assert page.exists() and "Layer 9" in page.read_text()
    assert "layer9.html" in (tmp_path / "docs" / "index.html").read_text()   # linked from dashboard


def test_governance_keeps_taint_out_of_authority_and_the_flag_clean():
    cs = CoreState(l9.Layer9())
    # a model (Kevin) tries to create an authoritative goal: the gate refuses, so no
    # contaminated object ever reaches high authority - the influence-map flag stays clean.
    from desi_layer9 import Operator, ProposalType, make_proposal
    from desi_layer9.provenance import Provenance
    d = cs.core.submit(make_proposal(
        ProposalType.GOAL_PROPOSAL, Operator.GOAL_CREATE, payload={"text": "ship it"},
        proposer="kevin", provenance=Provenance.from_model(external=False)), actor="human")
    assert not d.accepted                            # model may not grant authority
    exp = cs.epistemic_export()
    assert exp["tainted_authoritative"] == []        # the red flag is computed and clean
