from joni import Joni


def test_dual_view_after_a_mind_change_matches_the_worked_example():
    """The headline demo: an apparent opinion change, fully dissolved into receipts."""
    j = Joni()
    j.live(ticks=8)
    r = j.respond("what's your take on privacy these days?")

    # Conversation View: the apparent person reports a reasoned change of mind.
    assert "privacy" in r.conversation.lower()
    assert "used to think" in r.conversation.lower()

    # Epistemic View: the receipts, field for field (cf. the C-184 / L9-7741 example).
    e = r.epistemic
    assert e.operator is not None and e.operator.value == "conflict_resolution"
    assert e.trigger is not None and e.trigger.value == "contradictory_evidence"
    assert e.ledger_event is not None and e.ledger_event.startswith("L9-")
    assert e.claims  # references the rejected (and current) claim ids
    # The cited ledger event really exists and is the rejecting one.
    cited = next(ev for ev in j.state.ledger if ev.id == e.ledger_event)
    assert cited.operator.value == "conflict_resolution"


def test_conversation_is_replay_stable():
    a, b = Joni(), Joni()
    a.live(ticks=8)
    b.live(ticks=8)
    ra = a.respond("your take on privacy?")
    rb = b.respond("your take on privacy?")
    assert ra.conversation == rb.conversation
    assert ra.epistemic.ledger_event == rb.epistemic.ledger_event


def test_snapshot_reports_a_living_identity():
    j = Joni()
    j.live(ticks=8)
    snap = j.snapshot()
    assert snap["tick"] == 8
    assert snap["claims"]["total"] > snap["claims"]["active"]  # some were rejected
    assert snap["ledger_events"] > 0
    assert snap["memory"] > 0
    assert set(snap["topics"])  # has subject matter


def test_every_claim_change_has_a_ledger_event():
    """No apparent trait without a receipt - the core invariant."""
    j = Joni()
    j.live(ticks=10)
    ledger_ids = {e.id for e in j.state.ledger}
    for claim in j.state.claims.values():
        for transition in claim.history:
            assert transition.ledger_id in ledger_ids
