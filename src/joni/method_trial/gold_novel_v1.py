"""Stage 2 (NOVEL) — the fair test when the model already KNOWS the standard answers.

The micro/hard/deep/cross runs all ceilinged because a capable model has SEEN those problem types.
This battery removes recall from the equation: each task is a freshly generated, oversized instance
whose answer neither the model nor a human can produce from memory — but an INDEPENDENT reference
implementation (brute force / exact DP / a decision invariant, all in-code, no LLM) computes the gold.
So the "Answer:" is still deterministically checkable, yet the only way to get it right is to actually
EXECUTE the right procedure. That is where supplying a deep method could finally matter — and where its
failure would be a real null, not a ceiling.

Every reference solver is cross-checked against a second, independent method (brute force or BFS) in
``selftest()`` — the gold is only as trustworthy as that cross-check, so the test runs it. The instances
are fixed (seeded) for replay stability, but sized/parameterised past anything memorisable: a 3x16 domino
count, a random 8-puzzle's solvability, an inclusion-exclusion over composite moduli, a binary-carry
reachability. Methods: dynamic_programming, invariant_argument, inclusion_exclusion, conservation_law.
"""
from __future__ import annotations

import random
from functools import cache

from . import checkers as C
from .gold_micro_v1 import Task

SEED = 20260702  # fixed: the battery must be identical on every replay


# -- reference solvers (in-code ground truth, NO model) --------------------------------------------
def domino_tilings(rows: int, cols: int) -> int:
    """Exact number of 1x2-domino tilings of a rows x cols board (broken-profile column DP)."""
    def transitions(incoming: int) -> list[int]:
        out: list[int] = []

        def rec(row: int, cur: int, nxt: int) -> None:
            if row == rows:
                out.append(nxt)
                return
            if cur & (1 << row):
                rec(row + 1, cur, nxt)
                return
            if row + 1 < rows and not (cur >> (row + 1)) & 1:   # vertical domino
                rec(row + 2, cur | (1 << row) | (1 << (row + 1)), nxt)
            rec(row + 1, cur | (1 << row), nxt | (1 << row))    # horizontal -> protrudes to next column

        rec(0, incoming, 0)
        return out

    @cache
    def go(col: int, incoming: int) -> int:
        if col == cols:
            return 1 if incoming == 0 else 0
        return sum(go(col + 1, nxt) for nxt in transitions(incoming))

    return go(0, 0)


def _brute_tilings(rows: int, cols: int) -> int:
    """Independent brute-force perfect-matching count of the grid graph (tiny boards only)."""
    cells = [(r, c) for c in range(cols) for r in range(rows)]
    idx = {cell: i for i, cell in enumerate(cells)}
    full = (1 << len(cells)) - 1

    @cache
    def rec(used: int) -> int:
        if used == full:
            return 1
        i = 0
        while used & (1 << i):
            i += 1
        r, c = cells[i]
        total = 0
        for dr, dc in ((1, 0), (0, 1)):            # pair down or right
            nb = (r + dr, c + dc)
            if nb in idx and not used & (1 << idx[nb]):
                total += rec(used | (1 << i) | (1 << idx[nb]))
        return total

    return rec(0)


def puzzle_solvable(perm: list[int]) -> bool:
    """8-puzzle (3x3) solvability: for odd width, solvable iff the inversion count is even.
    ``perm`` is row-major over 0..8 with 0 the blank; goal is 1..8 then blank."""
    tiles = [x for x in perm if x != 0]
    inv = sum(1 for i in range(len(tiles)) for j in range(i + 1, len(tiles)) if tiles[i] > tiles[j])
    return inv % 2 == 0


def _bfs_puzzle_solvable(perm: tuple[int, ...]) -> bool:
    """Independent ground truth: BFS from the goal over the 3x3 puzzle graph (181440 states)."""
    goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
    seen = {goal}
    frontier = [goal]
    moves = {0: (1, 3), 1: (0, 2, 4), 2: (1, 5), 3: (0, 4, 6), 4: (1, 3, 5, 7),
             5: (2, 4, 8), 6: (3, 7), 7: (4, 6, 8), 8: (5, 7)}
    while frontier:
        nxt = []
        for st in frontier:
            z = st.index(0)
            for m in moves[z]:
                lst = list(st)
                lst[z], lst[m] = lst[m], lst[z]
                t = tuple(lst)
                if t not in seen:
                    seen.add(t)
                    nxt.append(t)
        frontier = nxt
    return tuple(perm) in seen


def count_divisible_by_none(n: int, mods: tuple[int, ...]) -> int:
    """Ground truth by direct sieve — integers in [1, n] divisible by NONE of ``mods``."""
    return sum(1 for x in range(1, n + 1) if all(x % m for m in mods))


def _incex_divisible_by_none(n: int, mods: tuple[int, ...]) -> int:
    """The SAME count via inclusion-exclusion over LCMs — used only to cross-check the sieve."""
    from itertools import combinations
    from math import lcm
    total = n
    for k in range(1, len(mods) + 1):
        for combo in combinations(mods, k):
            total += (-1) ** k * (n // lcm(*combo))
    return total


def chips_reachable(start: dict[int, int], target_pos: int) -> bool:
    """Move: remove TWO tokens at position p, add ONE at p+1 (a binary carry). Reachable to a single
    token at ``target_pos`` iff the invariant sum(count * 2**pos) equals 2**target_pos."""
    value = sum(c * (2 ** p) for p, c in start.items())
    return value == 2 ** target_pos


def _bfs_chips_reachable(start: dict[int, int], target_pos: int, bound: int = 12) -> bool:
    """Independent ground truth for small instances: BFS over reachable token configurations."""
    goal = tuple(1 if p == target_pos else 0 for p in range(bound + 1))
    start_state = tuple(start.get(p, 0) for p in range(bound + 1))
    seen = {start_state}
    frontier = [start_state]
    while frontier:
        nxt = []
        for st in frontier:
            if st == goal:
                return True
            for p in range(bound):
                if st[p] >= 2:
                    lst = list(st)
                    lst[p] -= 2
                    lst[p + 1] += 1
                    t = tuple(lst)
                    if t not in seen:
                        seen.add(t)
                        nxt.append(t)
        frontier = nxt
    return goal in seen


# -- build the seeded battery ----------------------------------------------------------------------
def _make_puzzle(rng: random.Random, want_solvable: bool) -> list[int]:
    while True:
        perm = list(range(9))
        rng.shuffle(perm)
        if puzzle_solvable(perm) == want_solvable and perm != [1, 2, 3, 4, 5, 6, 7, 8, 0]:
            return perm


def _grid(perm: list[int]) -> str:
    def cell(x: int) -> str:
        return "_" if x == 0 else str(x)
    rows = [" ".join(cell(perm[r * 3 + c]) for c in range(3)) for r in range(3)]
    return " / ".join(rows)


def _build() -> list[Task]:
    rng = random.Random(SEED)
    tasks: list[Task] = []

    # 1-3 · domino tilings of a 3xC board — big, recall-proof counts; the method is a DP recurrence
    for cols in (12, 14, 16):
        g = domino_tilings(3, cols)
        tasks.append(Task(
            id=f"tiling_3x{cols}", skill="counting", expected_method_class="dynamic_programming",
            forbidden_origin_domain="algorithms",
            prompt=(f"In how many distinct ways can a 3-row by {cols}-column board be completely tiled "
                    f"by 1x2 dominoes (each domino covers two adjacent cells, any orientation)? "
                    f"End with 'Answer: <integer>'."),
            gold=f"Answer: {g}", checker=C.exact_int(g),
            failure_modes=("guessing a Fibonacci-like value", "wrong or missing 3xn recurrence"),
            why_not_verbosity=f"the exact count {g} needs the transfer recurrence executed to n={cols}; "
                              f"no memorised value or hand-count reaches it",
            wrong_example=f"Answer: {g + 2}"))

    # 4-6 · 8-puzzle solvability — random scrambles; the method is the inversion-parity invariant
    for want in (True, False, True):
        perm = _make_puzzle(rng, want)
        g = "yes" if puzzle_solvable(perm) else "no"
        tasks.append(Task(
            id=f"puzzle_{'solv' if want else 'unsolv'}_{len(tasks)}", skill="impossibility",
            expected_method_class="invariant_argument", forbidden_origin_domain="grid-puzzles",
            prompt=(f"A 3x3 sliding puzzle has tiles 1-8 and one blank (_). Current position "
                    f"(rows top to bottom): {_grid(perm)}. Sliding a tile into the blank repeatedly, "
                    f"can it reach the goal 1 2 3 / 4 5 6 / 7 8 _ ? End with 'Answer: yes' or 'Answer: no'."),
            gold=f"Answer: {g}", checker=C.yesno(g),
            failure_modes=("trying moves and guessing", "not computing the inversion parity"),
            why_not_verbosity="solvability is decided by the parity of tile inversions — an invariant no "
                              "amount of trial narration reveals for a random scramble",
            wrong_example="Answer: " + ("no" if g == "yes" else "yes")))

    # 7-8 · inclusion-exclusion over COMPOSITE, overlapping moduli — LCMs make the terms error-prone
    for n, mods in ((5000, (6, 10, 15)), (8000, (4, 6, 9, 10))):
        g = count_divisible_by_none(n, mods)
        assert g == _incex_divisible_by_none(n, mods)      # sieve == inclusion-exclusion
        ms = ", ".join(map(str, mods))
        tasks.append(Task(
            id=f"incex_{n}_{'_'.join(map(str, mods))}", skill="counting",
            expected_method_class="inclusion_exclusion", forbidden_origin_domain="combinatorics",
            prompt=(f"How many integers from 1 to {n} are divisible by NONE of {ms}? "
                    f"(Note: these divisors share factors, so their pairwise least common multiples are "
                    f"not simply their products.) End with 'Answer: <integer>'."),
            gold=f"Answer: {g}", checker=C.exact_int(g),
            failure_modes=("using products instead of LCMs for the intersections", "sign errors"),
            why_not_verbosity=f"the composite overlapping moduli force correct LCMs at every "
                              f"intersection level; only careful inclusion-exclusion gives {g}",
            wrong_example=f"Answer: {g - 7}"))

    # 9-10 · binary-carry reachability — the method is spotting the conserved weighted (binary) sum
    for start, L, want in (({1: 6, 2: 5}, 5, True), ({1: 7, 2: 4}, 5, False)):
        assert chips_reachable(start, L) == want == _bfs_chips_reachable(start, L)
        g = "yes" if want else "no"
        desc = ", ".join(f"{c} token(s) at position {p}" for p, c in sorted(start.items()))
        tasks.append(Task(
            id=f"chips_{'reach' if want else 'unreach'}_{L}", skill="impossibility",
            expected_method_class="conservation_law", forbidden_origin_domain="physics",
            prompt=(f"Tokens sit on numbered positions of a line. Start: {desc} (all other positions "
                    f"empty). One move: remove TWO tokens from some position p and add ONE token at "
                    f"position p+1. Can a sequence of moves reach a state with EXACTLY ONE token at "
                    f"position {L} and none elsewhere? End with 'Answer: yes' or 'Answer: no'."),
            gold=f"Answer: {g}", checker=C.yesno(g),
            failure_modes=("simulating moves and guessing", "missing the conserved sum(count*2^pos)"),
            why_not_verbosity="each move preserves sum(count * 2**position); reachability is decided by "
                              "whether that invariant equals 2**target, not by trial",
            wrong_example="Answer: " + ("no" if g == "yes" else "yes")))

    return tasks


CASES: list[Task] = _build()


def selftest() -> None:
    """Cross-check every reference solver against an INDEPENDENT method — the gold's trust rests here."""
    # tilings: profile DP == brute-force matching on small boards, and known 3xn values
    for r, c in ((2, 3), (2, 4), (3, 2), (3, 4), (2, 6)):
        assert domino_tilings(r, c) == _brute_tilings(r, c), (r, c)
    assert [domino_tilings(3, c) for c in (2, 4, 6, 8)] == [3, 11, 41, 153]
    # puzzle: inversion parity == BFS reachability, on a sample of both classes
    rng = random.Random(1)
    for _ in range(6):
        perm = list(range(9))
        rng.shuffle(perm)
        assert puzzle_solvable(perm) == _bfs_puzzle_solvable(tuple(perm)), perm
    # inclusion-exclusion: sieve == LCM inclusion-exclusion
    for n, mods in ((5000, (6, 10, 15)), (8000, (4, 6, 9, 10)), (1234, (7, 11))):
        assert count_divisible_by_none(n, mods) == _incex_divisible_by_none(n, mods), (n, mods)
    # chips: invariant == BFS on small reachable/unreachable instances
    for start, L in (({1: 6, 2: 5}, 5), ({1: 7, 2: 4}, 5), ({1: 4}, 3), ({1: 2, 2: 1}, 3)):
        assert chips_reachable(start, L) == _bfs_chips_reachable(start, L), (start, L)
