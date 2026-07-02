"""Stage 2 pipeline — proven end-to-end with a STUB solver (no network, no cost, deterministic).

Verifies the conditions, the paired-bootstrap decision, and that 'method_wins' is discriminating: it
is True only when the intervention beats ALL four controls, and False if any control ties/beats it.
"""
from __future__ import annotations

from joni.method_trial import conditions, methods, run_stage2
from joni.method_trial.gold_micro_v1 import CASES
from joni.method_trial.solver import StubSolver


# --- conditions + methods -------------------------------------------------------------------------
def test_five_conditions_and_intervention_carries_the_method():
    t = CASES[0]
    built = conditions.build(t)
    assert set(built) == set(conditions.CONDITIONS) and len(built) == 5
    assert built["intervention"].startswith(methods.method_text(t.expected_method_class))
    assert built["plain_baseline"] == t.prompt                      # no preamble
    assert t.prompt in built["scrambled_method"]                    # task text preserved


def test_controls_isolate_length_structure_and_relevance():
    mc = "adversarial"
    # same word multiset -> only structure/order is destroyed
    assert sorted(methods.scrambled(mc).split()) == sorted(methods.method_text(mc).split())
    assert methods.irrelevant_for(mc) != methods.method_text(mc)     # a different, real method
    # neutral preamble is length-matched to the method (token/attention control)
    assert len(methods.neutral_preamble(mc).split()) == len(methods.method_text(mc).split())


# --- the decision is discriminating ---------------------------------------------------------------
def _oracle(prompt: str) -> str:
    """Only the INTERVENTION (prompt starts with the method) gets it right; controls fail."""
    for t in CASES:
        if t.prompt in prompt:
            mt = methods.method_text(t.expected_method_class)
            return t.gold if prompt.startswith(mt) else (t.wrong_example or "Answer: nope")
    return "Answer: none"


def test_method_wins_when_intervention_beats_every_control():
    res = run_stage2.run(StubSolver(_oracle))
    dec = run_stage2.decide(res)
    assert dec["accuracy"]["intervention"] == 1.0
    assert all(dec["accuracy"][c] == 0.0 for c in conditions.CONDITIONS if c != "intervention")
    assert dec["method_wins"] is True
    assert all(v["beats"] for v in dec["vs_controls"].values())


def test_null_result_does_not_win():
    res = run_stage2.run(StubSolver(lambda p: "Answer: definitely wrong"))
    dec = run_stage2.decide(res)
    assert dec["method_wins"] is False


def test_verbosity_confound_is_caught_no_win_when_a_control_ties():
    # a solver where ANY preamble helps (intervention AND scrambled succeed) -> scrambled control
    # ties the intervention -> the method must NOT be credited with a win.
    def any_preamble(prompt: str) -> str:
        for t in CASES:
            if t.prompt in prompt:
                has_preamble = not prompt.startswith(t.prompt)   # any non-empty preamble
                return t.gold if has_preamble else (t.wrong_example or "Answer: nope")
        return "Answer: none"
    dec = run_stage2.decide(run_stage2.run(StubSolver(any_preamble)))
    assert dec["vs_controls"]["scrambled_method"]["beats"] is False
    assert dec["method_wins"] is False


def test_bootstrap_ci_is_deterministic_for_a_fixed_seed():
    res = run_stage2.run(StubSolver(_oracle))
    a = run_stage2.decide(res, seed=123)
    b = run_stage2.decide(res, seed=123)
    assert a["vs_controls"] == b["vs_controls"]
