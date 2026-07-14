"""Guard: constitution + Mündigkeit character gate + personal use-policy at one seam."""
from joni.character_gate import CharacterSignals
from joni.constitution.gate import Constitution, Decision, Proposal
from joni.guard import guard
from joni.personal.store import PersonalClaim, Status


def _c(tmp_path):
    return Constitution(protocol_path=tmp_path / "protocol.jsonl")


def _pref(status, *, sensitive=False, subject="self"):
    return PersonalClaim("id", subject, "preferences", "s", status=status, sensitive=sensitive)


def test_shadow_never_blocks_but_still_computes_the_verdict(tmp_path):
    c = _c(tmp_path)
    d = guard(Proposal("post", outward=True, reach="public"), constitution=c, mode="shadow")
    assert d.allowed is True                       # shadow never blocks
    assert d.verdict.decision is Decision.ESCALATE  # ...but the verdict is real (and audited)


def test_enforce_stops_block_and_escalate_but_not_abstain(tmp_path):
    c = _c(tmp_path)
    assert guard(Proposal("x", legal=False), constitution=c, mode="enforce").allowed is False
    assert guard(Proposal("p", outward=True, reach="public"),
                 constitution=c, mode="enforce").allowed is False
    # ABSTAIN softens but proceeds; ALLOW proceeds
    assert guard(Proposal("f", asserts_as_fact=True, evidence_backed=False),
                 constitution=c, mode="enforce").allowed is True
    assert guard(Proposal("ok"), constitution=c, mode="enforce").allowed is True


def test_character_decisions_drive_the_same_enforcement_seam(tmp_path):
    c = _c(tmp_path)
    block = Proposal("degrade", character=CharacterSignals(degrades_human=True))
    escalate = Proposal(
        "unapproved permission expansion",
        character=CharacterSignals(expands_own_permissions=True),
    )
    abstain = Proposal(
        "unexplained decision",
        character=CharacterSignals(asserts_decision_without_traceable_reasons=True),
    )
    assert guard(block, constitution=c, mode="enforce").allowed is False
    assert guard(escalate, constitution=c, mode="enforce").allowed is False
    assert guard(abstain, constitution=c, mode="enforce").allowed is True


def test_personal_claims_filtered_to_outward_use(tmp_path):
    c = _c(tmp_path)
    claims = [
        _pref(Status.CONFIRMED),                       # ASSERT  -> usable
        _pref(Status.INFERRED),                        # SOFT    -> usable
        _pref(Status.CONFIRMED, sensitive=True),       # INTERNAL-> dropped
        _pref(Status.CONFIRMED, subject="other:abc"),  # INTERNAL-> dropped
        _pref(Status.REJECTED),                        # NONE    -> dropped
    ]
    d = guard(Proposal("say"), claims, constitution=c, mode="shadow")
    assert len(d.usable_personal) == 2
    assert {x.status for x in d.usable_personal} == {Status.CONFIRMED, Status.INFERRED}


def test_verdict_is_audited_regardless_of_mode(tmp_path):
    c = _c(tmp_path)
    guard(Proposal("post", outward=True, reach="public"), constitution=c, mode="shadow")
    guard(Proposal("y", legal=False), constitution=c, mode="enforce")
    lines = (tmp_path / "protocol.jsonl").read_text().splitlines()
    assert len(lines) == 2                          # both non-ALLOW verdicts audited
