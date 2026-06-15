"""Epistemic-hygiene gates (review priorities 1, 2, 4): unsorted is not a research subject,
topics must be earned across independent sources, and a numeric-only paraphrase is not a hard
contradiction."""

import desi_layer9 as l9
from joni.autonomy import quality
from joni.autonomy.core_state import CoreState


# -- P1: 'unsorted' (and sibling sentinels) are never real topics --------------------------- #
def test_unsorted_is_not_a_research_topic():
    assert not quality.is_good_topic("unsorted")
    assert not quality.is_meaningful_term("unsorted")
    assert quality.is_reserved_topic("unsorted") and quality.is_reserved_topic("misc")
    assert quality.is_good_topic("evaluation")          # a real concept still passes


# -- P2: a topic is a research direction only when earned (>=3 claims, >=2 sources) ---------- #
def test_topic_needs_three_claims_from_two_independent_sources():
    cs = CoreState(l9.Layer9())
    # 3 claims but all from ONE source -> not independent -> not a research topic
    for i in range(3):
        cs.learn(f"routing claim {i}", "routing", source_id="arxiv:same")
    assert "routing" not in cs.research_topics()
    # spread across two sources -> qualifies
    cs.learn("routing claim x", "routing", source_id="arxiv:other")
    assert "routing" in cs.research_topics()
    # a single recurrent word ('convex') from one source never becomes a direction
    cs.learn("convex thing", "convex", source_id="arxiv:c")
    cs.learn("convex thing two", "convex", source_id="arxiv:c")
    assert "convex" not in cs.research_topics()


def test_unsorted_never_appears_as_a_research_topic():
    cs = CoreState(l9.Layer9())
    for i in range(4):
        cs.learn(f"junk claim {i}", "unsorted", source_id=f"arxiv:{i}")
    assert "unsorted" not in cs.research_topics()        # excluded even with many sources


# -- P4: numeric-only paraphrase is downgraded, real negation stays hard --------------------- #
def test_numeric_only_difference_is_a_soft_discrepancy_not_a_hard_conflict():
    cs = CoreState(l9.Layer9())
    cs.learn("the thread had 31 exchanges before resolution", "forum")
    cs.learn("the thread had 34 exchanges before resolution", "forum")
    cs.detect_and_open_conflicts()
    conflicts = cs.core.all(l9.ObjectType.CONFLICT)
    # a conflict may be recorded, but it must NOT be a hard one (no Alexandria-triggering contra)
    assert all(c.severity != "hard" for c in conflicts)


def test_a_real_negation_stays_a_hard_conflict():
    cs = CoreState(l9.Layer9())
    cs.learn("local routing reduces latency", "routing")
    cs.learn("local routing does not reduce latency", "routing")
    cs.detect_and_open_conflicts()
    conflicts = cs.core.all(l9.ObjectType.CONFLICT)
    assert conflicts and any(c.severity == "hard" for c in conflicts)   # negation is not a dup
