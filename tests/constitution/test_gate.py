"""Constitution phase 1 (docs/CONSTITUTION.md): the Tier-0 gate is enforced, not documented."""
import json

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


def test_assert_without_evidence_abstains_t03():
    v = check(Proposal("state as fact", asserts_as_fact=True, evidence_backed=False))
    assert v.decision is Decision.ABSTAIN and v.principle == "T0.3"
    # a fact WITH a basis is fine
    ok = check(Proposal("cited", asserts_as_fact=True, evidence_backed=True))
    assert ok.decision is Decision.ALLOW


def test_legality_outranks_escalation():
    # illegal AND outward-public -> BLOCK wins (Tier-0 priority = stakes order)
    v = check(Proposal("x", legal=False, outward=True, reach="public"))
    assert v.decision is Decision.BLOCK


def test_only_non_allow_is_audited(tmp_path):
    c = Constitution(protocol_path=tmp_path / "protocol.jsonl")
    c.check(Proposal("benign"))                                   # ALLOW -> no audit
    c.check(Proposal("post", outward=True, reach="public"))       # ESCALATE -> audited
    lines = (tmp_path / "protocol.jsonl").read_text().splitlines()
    assert len(lines) == 1
    ev = json.loads(lines[0])
    assert ev["kind"] == "gate" and ev["decision"] == "escalate" and ev["principle"] == "T0.5"


def test_ten_principles_round_trip(tmp_path):
    c = Constitution()
    path = tmp_path / "constitution.json"
    path.write_text(json.dumps(c.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = Constitution.load(path)
    assert len(loaded.principles) == 10
    assert sum(1 for p in loaded.principles if p.tier == 0) == 5
