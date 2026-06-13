from joni.model_client import MockModel
from joni.renderer import respond
from joni.router import Router
from joni.seed import seed_identity


def test_response_is_grounded_in_real_claims():
    s = seed_identity()
    r = respond(s, Router(), MockModel(), "tell me about routing")
    # Every claim id in the trace exists in state.
    for cid in r.epistemic.claims:
        assert cid in s.claims
    # And the conversation is non-empty, first-person-ish.
    assert r.conversation
    assert r.epistemic.utterance == r.conversation


def test_no_opinion_change_means_no_operator():
    s = seed_identity()  # fresh, nothing rejected yet
    r = respond(s, Router(), MockModel(), "what about routing?")
    assert r.epistemic.operator is None
    assert r.epistemic.ledger_event is None


def test_unknown_topic_does_not_crash():
    s = seed_identity()
    r = respond(s, Router(), MockModel(), "")
    assert isinstance(r.conversation, str)
