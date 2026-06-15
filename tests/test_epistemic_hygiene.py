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


# -- P10: honest epistemically-usable, not a generous 100% ---------------------------------- #
def test_epistemic_usability_is_honest_about_duplicates():
    cs = CoreState(l9.Layer9())
    cs.learn("routing reduces latency", "routing", source_id="arxiv:1")
    cs.learn("routing reduces latency", "routing", source_id="arxiv:2")   # exact-dup text
    cs.learn("memory helps continuity", "memory", source_id="arxiv:3")
    u = cs.epistemic_usability()
    assert u["n"] == 3 and u["rate"] < 1.0                  # the duplicate pulls it below 100%
    assert u["flags"]["non_duplicate"] == 1                 # only one of the three is unique


# -- P5: independence and derivation depth ------------------------------------------------- #
def test_independent_source_count_and_derivation_depth():
    cs = CoreState(l9.Layer9())
    h = cs.hypothesize("routing transfers to memory", "routing")
    a = cs.learn("supporter A", "routing", source_id="arxiv:a")
    b = cs.learn("supporter B", "routing", source_id="arxiv:b")
    cs.corroborate(h, cs.core.get(a), relation="supports")
    cs.corroborate(h, cs.core.get(b), relation="supports")
    assert cs.independent_source_count(h) == 2              # two distinct papers
    # three claims from ONE thread are not three independent sources
    cs2 = CoreState(l9.Layer9())
    hh = cs2.hypothesize("x", "routing")
    for _ in range(3):
        c = cs2.learn("same-thread supporter", "routing", source_id="moltbook:T1")
        cs2.corroborate(hh, cs2.core.get(c), relation="supports")
    assert cs2.independent_source_count(hh) == 1


def test_accepted_proposal_count_tracks_model_origin_claims():
    cs = CoreState(l9.Layer9())
    cs.learn("a granite-proposed claim", "routing", source_id="granite:call-1")
    cs.learn("a deepseek-proposed claim", "routing", source_id="deepseek:call-2")
    cs.learn("a plain paper claim", "routing", source_id="arxiv:9")
    assert cs.proposal_accepted_count() == 2                # only the model-proposed, gated claims
