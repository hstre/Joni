"""Stage 2 (deep) — a hard battery where each task REQUIRES a specific DEEP method (no model here).

Unlike the shallow batteries, every task's ``expected_method_class`` is a DEEP-method id from
``deep_methods.py``, and the intervention supplies that method's actual procedure. The tasks are
multi-step and error-prone (4-set inclusion-exclusion, a non-obvious tiling recurrence, a parity
invariant) — exactly where a procedure a model won't reach unprompted could help, and where the
answer is still an objectively checkable number/word. This measures the REAL question the shallow
runs never did. A high baseline here is itself the finding (a strong model has internalised the
method); a mid-range baseline with the method winning would be genuine deep-method transfer.
"""
from __future__ import annotations

from . import checkers as C
from .gold_micro_v1 import Task

CASES: list[Task] = [
    Task(
        id="incex_coprime", skill="counting", expected_method_class="inclusion_exclusion",
        forbidden_origin_domain="number-theory",
        prompt=("How many integers from 1 to 1000 are divisible by NONE of 2, 3, 5, 7? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 228", checker=C.exact_int(228),
        failure_modes=("stopping after pairs (over/under-counting triples/quad)", "sign errors"),
        why_not_verbosity="four sets -> only correct inclusion-exclusion over all levels gives 228",
        wrong_example="Answer: 271"),
    Task(
        id="incex_derangement", skill="counting", expected_method_class="inclusion_exclusion",
        forbidden_origin_domain="combinatorics",
        prompt=("How many permutations of 5 distinct items leave NO item in its original position "
                "(derangements of 5)? End with 'Answer: <integer>'."),
        gold="Answer: 44", checker=C.exact_int(44),
        failure_modes=("using 5! - 5", "sign errors in the alternating sum"),
        why_not_verbosity="D5 needs the alternating inclusion-exclusion sum; a guess lands off",
        wrong_example="Answer: 120"),
    Task(
        id="dp_tiling_square", skill="counting", expected_method_class="dynamic_programming",
        forbidden_origin_domain="tiling",
        prompt=("How many ways can a 2x8 board be tiled using 1x2 dominoes AND 2x2 squares (pieces "
                "may be placed in any orientation)? End with 'Answer: <integer>'."),
        gold="Answer: 171", checker=C.exact_int(171),
        failure_modes=("wrong recurrence (missing the 2x2 term)", "wrong base cases"),
        why_not_verbosity="needs the recurrence a(n)=a(n-1)+2a(n-2); brute intuition mis-counts",
        wrong_example="Answer: 89"),
    Task(
        id="dp_fib_tiling", skill="counting", expected_method_class="dynamic_programming",
        forbidden_origin_domain="tiling",
        prompt=("In how many ways can a 2x10 board be fully tiled by 1x2 dominoes? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 89", checker=C.exact_int(89),
        failure_modes=("off-by-one in the Fibonacci index", "double counting"),
        why_not_verbosity="2xn domino tilings = F(n+1); the exact integer needs the right index",
        wrong_example="Answer: 55"),
    Task(
        id="pigeonhole_month", skill="existence", expected_method_class="pigeonhole",
        forbidden_origin_domain="combinatorics",
        prompt=("What is the MINIMUM number of people that guarantees at least 5 of them share the "
                "same birth month? End with 'Answer: <integer>'."),
        gold="Answer: 49", checker=C.exact_int(49),
        failure_modes=("answering 5 or 60", "using 4*12 without the +1"),
        why_not_verbosity="pigeonhole gives 4*12+1 = 49; the +1 is the whole point",
        wrong_example="Answer: 48"),
    Task(
        id="invariant_lamps", skill="impossibility", expected_method_class="invariant_argument",
        forbidden_origin_domain="grid-puzzles",
        prompt=("A 5x5 grid of lamps starts all OFF. Each move toggles an entire row or an entire "
                "column. Is it possible to reach a state with EXACTLY ONE lamp on? "
                "End with 'Answer: yes' or 'Answer: no'."),
        gold="Answer: no", checker=C.yesno("no"),
        failure_modes=("guessing yes by trial", "not finding the parity invariant"),
        why_not_verbosity="the ON-count 5a+5b-2ab is never 1; only the invariant argument shows it",
        wrong_example="Answer: yes"),
    Task(
        id="strong_recurrence", skill="recurrence", expected_method_class="strong_induction",
        forbidden_origin_domain="sequences",
        prompt=("A sequence is a(1)=1 and a(n)=2*a(n-1)+1 for n>1. What is a(10)? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 1023", checker=C.exact_int(1023),
        failure_modes=("arithmetic slip over 10 steps", "wrong closed form"),
        why_not_verbosity="a(n)=2^n - 1 gives 1023; sloppy iteration drifts",
        wrong_example="Answer: 1024"),
    Task(
        id="double_handshake", skill="counting", expected_method_class="double_counting",
        forbidden_origin_domain="graph-theory",
        prompt=("At a party every pair of people shook hands exactly once, for a total of 66 "
                "handshakes. How many people were there? End with 'Answer: <integer>'."),
        gold="Answer: 12", checker=C.exact_int(12),
        failure_modes=("solving n(n-1)=66 without the /2", "guessing"),
        why_not_verbosity="C(n,2)=66 -> n=12; the factor of 2 trips a careless count",
        wrong_example="Answer: 11"),
    Task(
        id="contradiction_sqrt6", skill="proof", expected_method_class="proof_by_contradiction",
        forbidden_origin_domain="number-theory",
        prompt=("Is the square root of 6 a rational number? End with 'Answer: yes' or 'Answer: no'."),
        gold="Answer: no", checker=C.yesno("no"),
        failure_modes=("assuming yes because 6 is 'nice'", "confusing with a perfect square"),
        why_not_verbosity="the contradiction argument (p^2=6q^2 -> shared factors) forces irrational",
        wrong_example="Answer: yes"),
    Task(
        id="bijection_paths", skill="counting", expected_method_class="bijection",
        forbidden_origin_domain="lattice-paths",
        prompt=("How many shortest lattice paths go from (0,0) to (4,4) moving only right or up? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 70", checker=C.exact_int(70),
        failure_modes=("computing 4*4 or 4!", "wrong binomial"),
        why_not_verbosity="each path <-> a sequence of 4 R and 4 U -> C(8,4)=70",
        wrong_example="Answer: 16"),
]
