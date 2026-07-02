"""Stage 0 + Stage 1: the pre-registration is frozen and the gold micro battery meets its contract.

No model, deterministic. This is the zero-cost foundation the measurement plan gates everything on.
"""
from __future__ import annotations

from joni.method_trial import checkers as C
from joni.method_trial import preregistration as P
from joni.method_trial.contract import validate_battery
from joni.method_trial.gold_micro_v1 import CASES


# --- Stage 0: the pre-registration is frozen (a change must update this pinned hash on purpose) --
def test_preregistration_hash_is_frozen():
    assert P.content_hash() == "be252cc25095a61f1ada9926d6342a4cdcac738eddc0aea2db0c59860bac7178"


def test_preregistration_has_the_load_bearing_decisions():
    s = P.SPEC
    assert len(s["controls"]) == 4                       # plain + neutral + scrambled + irrelevant
    assert "irrelevant_plausible_method" in s["controls"]
    assert s["proxy_acceptability"]["max_false_positive_rate_on_holdout"] == 0.10
    assert "false positives first" in s["false_positive_policy"]
    assert s["independence_unit"]["micro_battery"] == "task"
    # method plausibility must be a-priori, never from the outcome
    assert "NEVER derived from a trial outcome" in s["method_plausibility"]


# --- checker primitives ---------------------------------------------------------------------------
def test_checkers_extract_the_final_answer_not_a_passing_mention():
    # a number mentioned mid-reasoning must not win; the 'Answer:' region decides
    assert C.exact_int(4)("I first thought 6 or 7. Answer: 4") is True
    assert C.exact_int(4)("The answer is clearly not 4. Answer: 9") is False
    assert C.numeric_in_band(1e9, 5e9)("roughly 2-3 billion. Answer: 2,500,000,000") is True
    assert C.numeric_in_band(1e9, 5e9)("Answer: 5,000,000") is False   # out of band
    assert C.choice("C", "ABCD")("weighing A and B... Answer: C") is True
    assert C.choice("C", "ABCD")("Answer: B") is False
    assert C.index_set({3, 4}, {1, 2, 3, 4})("Answer: 3 and 4") is True
    assert C.index_set({3, 4}, {1, 2, 3, 4})("Answer: 1 and 2") is False
    assert C.yesno("no")("It is complicated. Answer: no") is True
    assert C.contains_any(("temperature", "season"))("Answer: the temperature / season") is True


# --- Stage 1: the battery meets its contract ------------------------------------------------------
def test_battery_meets_the_contract():
    rep = validate_battery(CASES, min_tasks=12)
    assert rep["ok"], rep["problems"]
    assert rep["n"] >= 12


def test_every_checker_accepts_its_gold_and_rejects_the_wrong_example():
    for t in CASES:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        if t.wrong_example:
            assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"


def test_every_task_declares_the_six_required_fields():
    for t in CASES:
        assert t.skill and t.expected_method_class and t.forbidden_origin_domain
        assert t.prompt and t.why_not_verbosity and t.failure_modes


def test_battery_spans_several_skills_and_method_classes():
    rep = validate_battery(CASES)
    assert len(rep["skills"]) >= 8            # not a single-skill battery
    assert len(rep["method_classes"]) >= 5    # adversarial / exclusion / boundary / decomposition


def test_hard_battery_meets_the_contract():
    from joni.method_trial.contract import validate_battery
    from joni.method_trial.gold_hard_v1 import CASES as HARD
    rep = validate_battery(HARD, min_tasks=15)
    assert rep["ok"], rep["problems"]
    for t in HARD:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        if t.wrong_example:
            assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"
