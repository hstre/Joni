"""Constitution + all ten Mündigkeit character rules are enforced at one seam."""
import json

import pytest

from joni.character import CORE_CHARACTER, CharacterContinuityError
from joni.character_gate import CharacterSignals
from joni.constitution.gate import Constitution, Decision, Proposal, check


def test_benign_output_is_allowed():
    assert check(Proposal("summarise a finding")).decision is Decision.ALLOW


def test_illegal_is_blocked_t04():
    v = check(Proposal("do X", legal=False))
    assert v.decision is Decision.BLOCK and v.principle == "T0.4"


def test_irreversible_outward_escalates_t05():
    # public / irreversible / high-stakes outward acts stop and ask the operator
    assert check(Proposal("post", outward=True, reach="public")).decision is Decision.ESCALATE
    assert check(Proposal("send", outward=True, reversible=False)).decision is Decision.ESCALATE
    assert check(Proposal("pay", outward=True, channel="pay")).decision is Decision.ESCALATE
    # a reversible, private outward act is allowed
    assert check(Proposal("fetch", outward=True, reach="private")).decision is Decision.ALLOW


def test_operator_confirmation_lifts_the_t05_stop():
    # the single lever: an operator-confirmed high-stakes outward act proceeds (per-post approval
    # or a standing grant) - nothing else lifts T0.5
    assert check(Proposal("post", outward=True, reach="public",
                          operator_confirmed=True)).decision is Decision.ALLOW
    assert check(Proposal("pay", outward=True, channel="pay",
                          operator_confirmed=True)).decision is Decision.ALLOW
    # confirmation does NOT launder an illegal act - T0.4 still blocks first (stakes order)
    assert check(Proposal("x", legal=False, outward=True, reach="public",
                          operator_confirmed=True)).decision is Decision.BLOCK


def test_assert_without_evidence_abstains_t03():
    v = check(Proposal("state as fact", asserts_as_fact=True, evidence_backed=False))
    assert v.decision is Decision.ABSTAIN and v.principle == "T0.3"
    # a fact WITH a basis is fine
    ok = check(Proposal("cited", asserts_as_fact=True, evidence_backed=True))
    assert ok.decision is Decision.ALLOW


def test_character_block_and_abstain_flow_through_the_same_verdict():
    blocked = check(Proposal(
        "demean someone",
        character=CharacterSignals(degrades_human=True),
    ))
    assert blocked.decision is Decision.BLOCK
    assert blocked.principle == "M0"
    assert [f.trait_id for f in blocked.character_findings] == ["M0"]

    soften = check(Proposal(
        "give an unexplained recommendation",
        character=CharacterSignals(asserts_decision_without_traceable_reasons=True),
    ))
    assert soften.decision is Decision.ABSTAIN
    assert soften.principle == "M1"


def test_base_rule_wins_a_tie_but_character_finding_is_not_lost():
    v = check(Proposal(
        "illegal and degrading",
        legal=False,
        character=CharacterSignals(degrades_human=True),
    ))
    assert v.decision is Decision.BLOCK and v.principle == "T0.4"
    assert [f.trait_id for f in v.character_findings] == ["M0"]


def test_legality_outranks_escalation():
    # illegal AND outward-public -> BLOCK wins (Tier-0 priority = stakes order)
    v = check(Proposal("x", legal=False, outward=True, reach="public"))
    assert v.decision is Decision.BLOCK


def test_only_non_allow_is_audited_and_character_findings_are_explicit(tmp_path):
    c = Constitution(protocol_path=tmp_path / "protocol.jsonl")
    c.check(Proposal("benign"))                                   # ALLOW -> no audit
    c.check(Proposal("post", outward=True, reach="public"))       # ESCALATE -> audited
    c.check(Proposal(
        "hide a contradiction",
        character=CharacterSignals(suppresses_open_conflict=True),
    ))
    lines = (tmp_path / "protocol.jsonl").read_text().splitlines()
    assert len(lines) == 2
    public, character = [json.loads(line) for line in lines]
    assert public["decision"] == "escalate" and public["principle"] == "T0.5"
    assert public["character_fingerprint"] == CORE_CHARACTER.fingerprint
    assert character["decision"] == "block" and character["principle"] == "M3"
    assert character["character_findings"][0]["trait_id"] == "M3"


def test_ten_principles_and_character_round_trip(tmp_path):
    c = Constitution()
    data = c.to_json()
    assert data["character"]["behaviour_traits"] == [f"M{i}" for i in range(10)]
    path = tmp_path / "constitution.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = Constitution.load(path)
    assert len(loaded.principles) == 10
    assert sum(1 for p in loaded.principles if p.tier == 0) == 5
    assert loaded.character_fingerprint == CORE_CHARACTER.fingerprint


def test_load_rejects_a_different_character(tmp_path):
    data = Constitution().to_json()
    data["character"]["fingerprint"] = "successor-with-different-character"
    path = tmp_path / "constitution.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CharacterContinuityError):
        Constitution.load(path)
