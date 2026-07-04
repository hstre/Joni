"""Consumption of the Personal Store: usable preferences flow into Joni's operator-facing report,
guard-filtered — and nothing at all is said when there is no usable preference."""
from joni import guard
from joni.autonomy import self_review
from joni.autonomy.core_state import CoreState, seed_core
from joni.personal.store import PersonalClaim, Status

_SECTION = "What I keep in mind about you"


class _Proto:
    def record(self, *a, **k):
        pass


def _pref(cid, statement, *, status=Status.CONFIRMED, sensitive=False, subject="self"):
    return PersonalClaim(id=cid, subject=subject, category="preferences", statement=statement,
                         status=status, sensitive=sensitive)


def test_usable_personal_filters_to_the_outward_voice():
    claims = [
        _pref("a", "direct feedback"),                      # confirmed self -> ASSERT -> usable
        _pref("b", "terse", status=Status.INFERRED),        # inferred self  -> SOFT   -> usable
        _pref("c", "secret", sensitive=True),               # sensitive      -> INTERNAL -> dropped
        _pref("d", "third", subject="other:x"),             # third-party    -> INTERNAL -> dropped
        _pref("e", "gone", status=Status.REJECTED),         # rejected       -> NONE    -> dropped
    ]
    assert {c.id for c in guard.usable_personal(claims)} == {"a", "b"}


def test_self_review_states_confirmed_preferences():
    cs = CoreState(seed_core())
    usable = guard.usable_personal([_pref("a", "direct honest feedback")])
    review = self_review.run_review(cs, {"topics_added": []}, _Proto(), 1, days=0, spend=0.0,
                                    context={"personal": usable})
    sec = next((s for s in review["sections"] if s["title"] == _SECTION), None)
    assert sec is not None and "direct honest feedback" in sec["text"]


def test_self_review_says_nothing_without_a_usable_preference():
    cs = CoreState(seed_core())
    # a sensitive preference is present but not outward-usable -> no section at all
    usable = guard.usable_personal([_pref("s", "secret", sensitive=True)])
    review = self_review.run_review(cs, {"topics_added": []}, _Proto(), 1, days=0, spend=0.0,
                                    context={"personal": usable})
    assert all(s["title"] != _SECTION for s in review["sections"])
