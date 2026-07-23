"""Priority 3: lexical recurrence is not a hypothesis. A well-formed hypothesis states a mechanism,
a scope, an expected observation AND a possible refutation; anything short of that is a pattern hint
and must not trigger a reflection cycle."""
from __future__ import annotations

from joni.autonomy import hypothesis_form as hf


def test_the_recurrence_templates_are_barred_from_reflection():
    # exactly the emerge/invent shapes the operator flagged - barred AND not well-formed
    emerge = ("Across my archaeology claims, the term 'archaeological' recurs; whether this "
              "reflects a shared mechanism remains untested.")
    invent = "Hypothesis: the pattern behind 'ransomware' (security) might also apply to carpet."
    bare = "electrical"
    for text in (emerge, invent, bare):
        assert hf.is_reflection_barred(text) is True
        assert hf.well_formed(text) is False
    assert hf.classify(emerge)["is_recurrence_template"] is True


def test_a_substantive_plain_hypothesis_is_not_barred_even_if_not_well_formed():
    # the targeted bar must NOT catch a real, plainly-phrased claim - it just isn't fully operative
    text = "routing is always local-first"
    assert hf.is_reflection_barred(text) is False       # still earns reflection...
    assert hf.well_formed(text) is False                # ...though it hasn't reached 4/4
    assert 0 <= hf.completeness(text) <= 4


def test_completeness_scores_the_four_components():
    assert hf.completeness("electrical") == 0
    full = ("Because latency drives retries, when load is heavy we should observe errors rising; "
            "refuted if errors stay flat.")
    assert hf.completeness(full) == 4


def test_a_fully_stated_hypothesis_passes():
    text = ("Because elevated latency drives retries, when request volume is under load we should "
            "observe error rates rising; this would be refuted if errors stay flat.")
    c = hf.classify(text)
    assert c["well_formed"] is True and c["missing"] == []
    assert hf.well_formed(text) is True


def test_missing_any_single_component_makes_it_a_pattern_hint():
    # has mechanism + scope + expected observation, but NO refutation
    no_refute = ("Because caching reduces load, when traffic is under peak we should observe "
                 "lower latency.")
    c = hf.classify(no_refute)
    assert c["missing"] == ["refutation"] and hf.well_formed(no_refute) is False


def test_scope_is_not_trivially_satisfied_by_common_words():
    # bare 'in'/'for' must NOT count as a scope marker
    assert hf._has_marker("this holds in general for everything", hf._MARKERS["scope"]) is False
    assert hf._has_marker("this holds when traffic is high", hf._MARKERS["scope"]) is True


def test_markers_are_word_boundary_matched():
    # 'since' the token, not inside 'sincerely'; 'unless' the token, not inside a word
    assert hf._has_marker("sincerely yours", hf._MARKERS["mechanism"]) is False
    assert hf._has_marker("it holds since the load is high", hf._MARKERS["mechanism"]) is True


def test_german_markers_are_recognised():
    text = ("Weil hohe Last Wiederholungen verursacht, sollte sich bei Spitzenlast eine höhere "
            "Fehlerrate zeigen; das wäre falsch, falls die Fehler flach bleiben.")
    assert hf.well_formed(text) is True
