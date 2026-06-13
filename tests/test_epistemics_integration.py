"""PR 4 - Joni on the one core: dual view, self/operational/narrative split, reload."""

import desi_layer9 as l9
from joni.epistemics import EpistemicIdentity


def test_conversation_view_still_works():
    me = EpistemicIdentity()
    me.learn_claim("local-first models keep prompts on the box", "privacy")
    me.adopt_goal("run locally for weeks", priority=0.9)
    text = me.conversation("privacy?")
    assert text and "local-first" in text.lower()


def test_epistemic_view_dissolves_an_utterance():
    me = EpistemicIdentity()
    cid = me.learn_claim("x is the case", "t")
    me.record_memory("I learned x", refs=(cid,))
    trace = me.epistemic_trace("I believe x", refs=(cid,))
    for key in ("utterance", "claims", "evidence", "goals", "memories",
                "self_model_claims", "operator", "proposal", "decision",
                "taint", "review", "ledger_event"):
        assert key in trace
    assert cid in trace["claims"]
    assert trace["ledger_event"] and trace["ledger_event"].startswith("L9-")


def test_self_model_operational_and_narrative_are_separate():
    me = EpistemicIdentity()
    # operational truth: 3 projects abandoned, 1 shipped
    os_id = me.snapshot_operational({"projects_abandoned": 3, "projects_shipped": 1})
    # a provisional self-model claim about it
    sm_id = me.propose_self_model("I tend to abandon projects too quickly.",
                                  evidence=("P-3", "P-7"), counterevidence=("P-2",))
    assert me.core.get(sm_id).status is l9.Status.CANDIDATE     # provisional, not fact
    # a narrative that flatters cannot overwrite the operational metrics
    me.render_narrative("I always finish what I start.", basis=(os_id,))
    assert me.core.get(os_id).metrics == {"projects_abandoned": 3, "projects_shipped": 1}
    assert me.core.all(l9.ObjectType.OPERATIONAL_STATE)[0].object_type \
        is l9.ObjectType.OPERATIONAL_STATE
    assert me.core.all(l9.ObjectType.SELF_MODEL_CLAIM)[0].object_type \
        is l9.ObjectType.SELF_MODEL_CLAIM


def test_conflicts_can_stay_open_in_the_narrative():
    me = EpistemicIdentity()
    a = me.learn_claim("the cause is A", "topic")
    b = me.learn_claim("the cause is not A", "topic")
    me.open_conflict((a, b), severity="hard")
    text = me.conversation("what's the cause?")
    assert "two incompatible explanations" in text


def test_reload_continues_the_same_audited_trajectory(tmp_path):
    me = EpistemicIdentity()
    cid = me.learn_claim("a durable belief", "topic")
    me.adopt_goal("a long goal")
    path = me.save(tmp_path / "joni_l9.json")

    resumed = EpistemicIdentity.load(path)
    assert l9.snapshot_hash(resumed.core) == l9.snapshot_hash(me.core)
    # it keeps writing onto the same trajectory
    resumed.attach_evidence(cid, "supporting note", reviewed=True)
    ok, _ = l9.verify_chain(resumed.core)
    assert ok


def test_migration_from_legacy_joni_state():
    legacy = {
        "claims": [{"id": "C-1", "text": "old belief", "topic": "t", "status": "confirmed"}],
        "goals": [{"id": "G-1", "text": "old goal", "horizon": "long", "priority": 0.5}],
    }
    me = EpistemicIdentity.from_legacy(legacy)
    claim = me.core.all(l9.ObjectType.CLAIM)[0]
    assert claim.status is l9.Status.ACTIVE                 # confirmed must be re-earned
    assert claim.provenance.origin_type is l9.OriginType.IMPORTED_STATE
    assert me.core.all(l9.ObjectType.GOAL)
