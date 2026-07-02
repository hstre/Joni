"""The real apply_fn + first-measurement mechanics, verified offline with a stub (no network).

Proves the honest grading: a stub that answers the objectively-correct letter resolves every
conflict; a stub that always answers 'A' scores exactly the fraction whose correct answer is A;
resolving actually closes the conflict in the core.
"""
import pytest

pytest.importorskip("desi_layer9")

from joni.method_trial.solver import StubSolver  # noqa: E402
from joni.solution_space.llm_apply import make_llm_apply  # noqa: E402
from joni.solution_space.measure_apply import propose_for_core, run_mode  # noqa: E402
from joni.solution_space.operator_cycle import open_conflict_ids  # noqa: E402
from joni.solution_space.resolvable_conflicts import CASES, seed_core  # noqa: E402


def _oracle_solver():
    # answer the objectively-correct letter for whichever conflict's claims are in the prompt
    def solve(prompt):
        for a, b, correct in CASES:
            if a in prompt and b in prompt:
                return f"Answer: {correct}"
        return "Answer: A"
    return StubSolver(solve)


def test_oracle_apply_resolves_every_conflict():
    core, registry = seed_core()
    apply = make_llm_apply(_oracle_solver(), registry, mode="method")
    props = {p.target.split(":", 1)[-1]: p for p in propose_for_core(core, top_k_per_gap=1)}
    assert open_conflict_ids(core)                      # conflicts start open
    for p in props.values():
        apply(core, p)
    assert open_conflict_ids(core) == set()             # a correct answer resolved them all


def test_always_A_scores_the_fraction_correct_is_A():
    solver = StubSolver(lambda p: "Answer: A")
    r = run_mode(solver, "none")
    expected = sum(1 for *_, c in CASES if c == "A") / len(CASES)
    assert r["accuracy"] == round(expected, 3)
    assert r["n"] == len(CASES)


def test_wrong_answer_leaves_conflict_open():
    core, registry = seed_core()
    # always answer 'A' — resolves only the conflicts whose correct answer is A
    apply = make_llm_apply(StubSolver(lambda p: "Answer: A"), registry, mode="method")
    props = {p.target.split(":", 1)[-1]: p for p in propose_for_core(core, top_k_per_gap=1)}
    for p in props.values():
        apply(core, p)
    still_open = open_conflict_ids(core)
    # every still-open conflict is one whose correct answer was B (the stub got it wrong)
    for cid in still_open:
        assert registry[cid]["correct"] == "B"
