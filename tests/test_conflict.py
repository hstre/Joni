from joni.conflict import detect_conflicts, weaker_claim
from joni.models import ClaimStatus
from joni.operators import assert_claim
from joni.state import Layer9


def test_detects_negation_conflict_same_topic():
    s = Layer9()
    assert_claim(s, "local-first models keep data private", "privacy",
                 status=ClaimStatus.ACTIVE, support=0.5)
    assert_claim(s, "local-first models do not keep data private", "privacy",
                 status=ClaimStatus.ACTIVE, support=0.7)
    opened = detect_conflicts(s)
    assert len(opened) == 1
    assert opened[0].kind == "negation"


def test_detects_antonym_conflict():
    s = Layer9()
    assert_claim(s, "we should increase external routing", "routing",
                 status=ClaimStatus.ACTIVE)
    assert_claim(s, "we should decrease external routing", "routing",
                 status=ClaimStatus.ACTIVE)
    opened = detect_conflicts(s)
    assert opened and opened[0].kind == "stance_opposition"


def test_no_conflict_across_different_topics():
    s = Layer9()
    assert_claim(s, "data is private", "privacy", status=ClaimStatus.ACTIVE)
    assert_claim(s, "data is not private", "memory", status=ClaimStatus.ACTIVE)
    assert detect_conflicts(s) == []


def test_detection_is_idempotent():
    s = Layer9()
    assert_claim(s, "keep it simple", "design", status=ClaimStatus.ACTIVE)
    assert_claim(s, "keep it complex", "design", status=ClaimStatus.ACTIVE)
    first = detect_conflicts(s)
    second = detect_conflicts(s)
    assert len(first) == 1
    assert second == []  # already registered, not re-opened


def test_weaker_claim_is_the_lower_support_one():
    s = Layer9()
    strong = assert_claim(s, "more local is better", "routing",
                          status=ClaimStatus.ACTIVE, support=0.8)
    weak = assert_claim(s, "more local is worse", "routing",
                        status=ClaimStatus.ACTIVE, support=0.3)
    opened = detect_conflicts(s)
    assert weaker_claim(s, opened[0]) == weak.id
    assert weaker_claim(s, opened[0]) != strong.id
