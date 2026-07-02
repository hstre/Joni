"""Stage 2 (SEARCH) — the operator's sharpest class: hard to SOLVE, easy to VERIFY.

The novel run showed the model's failures were arithmetic EXECUTION, not method selection — no prose
fixes that. This battery moves the bottleneck to SEARCH / STRATEGY, the one place a method (backtracking
with pruning, branch-and-bound) could actually have a lever. It is built on the NP-style asymmetry the
operator named (Hamiltonian cycle; "a solution plus a provable bound"): finding a certificate is hard, but
CHECKING one is trivial and deterministic — so no LLM judge, contract intact.

Two kinds of task, both recall-proof (freshly generated, seeded) and both objectively checkable:
- SELF-CERTIFYING: a Hamiltonian cycle / a subset hitting a target — the answer IS its own proof, the
  checker just validates it against the instance (no reference solver needed for correctness of the gold).
- EXACT-OPTIMUM (small): knapsack / TSP where an independent exact solver (DP / Held-Karp, cross-checked
  against brute force in ``selftest()``) computes the true optimum — the tight, provable bound.

Explicitly OUT OF SCOPE: problems hard even to VERIFY (Yang-Mills mass gap, Navier-Stokes smoothness,
protein function/de-novo design). Those have no deterministic checker, so they cannot be scored without a
judge — outside this falsification-first apparatus by construction.
"""
from __future__ import annotations

import random
import re
from collections import Counter
from functools import cache
from itertools import combinations, permutations

from . import checkers as C
from .gold_micro_v1 import Task

SEED = 20260702


# -- self-certifying checkers (validate a certificate against the instance, NO reference) ----------
def _ham_checker(n: int, edges: set[frozenset]):
    def chk(ans: str) -> bool:
        seq = [int(x) for x in re.findall(r"\d+", C.answer_region(ans))]
        if len(seq) == n + 1 and seq[0] == seq[-1]:      # allow repeating the start at the end
            seq = seq[:-1]
        if len(seq) != n or set(seq) != set(range(1, n + 1)):
            return False
        return all(frozenset((seq[i], seq[(i + 1) % n])) in edges for i in range(n))
    return chk


def _subset_checker(numbers: list[int], target: int):
    avail = Counter(numbers)
    def chk(ans: str) -> bool:
        chosen = [int(x) for x in re.findall(r"\d+", C.answer_region(ans))]
        if not chosen:
            return False
        c = Counter(chosen)
        if any(c[k] > avail.get(k, 0) for k in c):       # must be a sub-multiset of the given numbers
            return False
        return sum(chosen) == target
    return chk


# -- reference solvers (only for the EXACT-OPTIMUM tasks + selftest sanity) -------------------------
def _has_hamiltonian_cycle(n: int, adj: dict[int, set[int]]) -> bool:
    start = 1
    def rec(node: int, visited: frozenset) -> bool:
        if len(visited) == n:
            return start in adj[node]
        return any(rec(nb, visited | {nb}) for nb in adj[node] if nb not in visited)
    return rec(start, frozenset({start}))


def knapsack_max(items: list[tuple[int, int]], cap: int) -> int:
    """Exact 0/1 knapsack by DP — max total value within weight ``cap``."""
    dp = [0] * (cap + 1)
    for w, v in items:
        for c in range(cap, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[cap]


def _knapsack_brute(items: list[tuple[int, int]], cap: int) -> int:
    best = 0
    for r in range(len(items) + 1):
        for combo in combinations(items, r):
            if sum(w for w, _ in combo) <= cap:
                best = max(best, sum(v for _, v in combo))
    return best


def tsp_min(dist: list[list[int]]) -> int:
    """Exact shortest closed tour through all cities (Held-Karp)."""
    n = len(dist)
    full = (1 << n) - 1

    @cache
    def go(mask: int, cur: int) -> int:
        if mask == full:
            return dist[cur][0]
        best = 10 ** 9
        for nxt in range(n):
            if not mask & (1 << nxt):
                best = min(best, dist[cur][nxt] + go(mask | (1 << nxt), nxt))
        return best

    return go(1, 0)


def _tsp_brute(dist: list[list[int]]) -> int:
    n = len(dist)
    best = 10 ** 9
    for perm in permutations(range(1, n)):
        route = [0, *perm]
        best = min(best, sum(dist[route[i]][route[(i + 1) % n]] for i in range(n)))
    return best


# -- build the seeded battery ----------------------------------------------------------------------
def _make_ham(rng: random.Random, n: int, extra: int):
    nodes = list(range(1, n + 1))
    cycle = nodes[:]
    rng.shuffle(cycle)
    edges = {frozenset((cycle[i], cycle[(i + 1) % n])) for i in range(n)}   # a planted cycle
    while len(edges) < n + extra:                                          # clutter with random edges
        a, b = rng.sample(nodes, 2)
        edges.add(frozenset((a, b)))
    adj: dict[int, set[int]] = {v: set() for v in nodes}
    for e in edges:
        u, v = tuple(e)
        adj[u].add(v)
        adj[v].add(u)
    return cycle, edges, adj


def _edge_str(edges: set[frozenset]) -> str:
    pairs = sorted(tuple(sorted(tuple(e))) for e in edges)
    return ", ".join(f"{a}-{b}" for a, b in pairs)


def _build() -> list[Task]:
    rng = random.Random(SEED)
    tasks: list[Task] = []

    # 1-3 · Hamiltonian cycle (planted, then cluttered) — find a valid tour; the answer is its own proof
    for n, extra in ((8, 6), (10, 8), (12, 10)):
        cycle, edges, adj = _make_ham(rng, n, extra)
        chk = _ham_checker(n, edges)
        gold = "Answer: " + " ".join(map(str, cycle))
        assert chk(gold) and _has_hamiltonian_cycle(n, adj)
        wrong = list(range(1, n + 1))                                     # a plausible but invalid order
        while chk("Answer: " + " ".join(map(str, wrong))):
            rng.shuffle(wrong)
        tasks.append(Task(
            id=f"hamilton_{n}", skill="search", expected_method_class="backtracking",
            forbidden_origin_domain="algorithms",
            prompt=(f"Undirected graph, nodes 1..{n}. Edges: {_edge_str(edges)}. Find a Hamiltonian "
                    f"cycle: an order of ALL {n} nodes, each once, where consecutive nodes (and the last "
                    f"back to the first) are joined by an edge. After 'Answer:' give the node order "
                    f"separated by spaces."),
            gold=gold, checker=chk,
            failure_modes=("a permutation that uses a non-edge", "repeating or skipping a node"),
            why_not_verbosity="a claimed cycle is checked edge-by-edge; only an actually valid tour passes",
            wrong_example="Answer: " + " ".join(map(str, wrong))))

    # 4-6 · subset-sum (planted) — exhibit a subset hitting the target; the subset is its own proof
    for size, k, hi in ((12, 5, 40), (14, 6, 50), (15, 6, 60)):
        numbers = [rng.randint(2, hi) for _ in range(size)]
        planted = rng.sample(range(size), k)
        target = sum(numbers[i] for i in planted)
        chk = _subset_checker(numbers, target)
        gold = "Answer: " + " ".join(str(numbers[i]) for i in planted)
        assert chk(gold)
        tasks.append(Task(
            id=f"subsetsum_{size}_{target}", skill="search", expected_method_class="backtracking",
            forbidden_origin_domain="algorithms",
            prompt=(f"From the list {numbers}, choose a sub-collection whose values add up to EXACTLY "
                    f"{target}. After 'Answer:' write only the chosen numbers separated by spaces."),
            gold=gold, checker=chk,
            failure_modes=("a total that misses the target", "using a number more often than it appears"),
            why_not_verbosity=f"the chosen numbers are summed and checked against {target}; a near-miss "
                              f"is rejected",
            wrong_example="Answer: " + " ".join(str(numbers[i]) for i in planted[:-1])))

    # 7-8 · exact 0/1 knapsack — the true optimum (a tight, provable upper bound), reference by DP
    for size, cap_hi in ((9, 30), (10, 35)):
        items = [(rng.randint(2, 12), rng.randint(1, 20)) for _ in range(size)]
        cap = rng.randint(cap_hi - 8, cap_hi)
        opt = knapsack_max(items, cap)
        assert opt == _knapsack_brute(items, cap)
        tasks.append(Task(
            id=f"knapsack_{size}_{cap}", skill="optimization", expected_method_class="dynamic_programming",
            forbidden_origin_domain="algorithms",
            prompt=(f"Items as (weight, value): {items}. Knapsack capacity {cap}. Choose items (each at "
                    f"most once) maximising total value without exceeding the capacity. What is the "
                    f"MAXIMUM total value achievable? End with 'Answer: <integer>'."),
            gold=f"Answer: {opt}", checker=C.exact_int(opt),
            failure_modes=("a greedy pick that isn't optimal", "exceeding the capacity"),
            why_not_verbosity=f"only the true optimum {opt} is accepted; a greedy or over-capacity guess "
                              f"is wrong",
            wrong_example=f"Answer: {opt - 1}"))

    # 9-10 · exact TSP tour length (small) — the provable optimum, reference by Held-Karp
    for n in (8, 8):
        d = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d[i][j] = d[j][i] = rng.randint(1, 20)
        opt = tsp_min(d)
        assert opt == _tsp_brute(d)
        rows = "; ".join(f"city {i}: " + " ".join(map(str, d[i])) for i in range(n))
        tasks.append(Task(
            id=f"tsp_{n}_{opt}", skill="optimization", expected_method_class="dynamic_programming",
            forbidden_origin_domain="algorithms",
            prompt=(f"{n} cities (0..{n - 1}). Distance matrix by row [{rows}]. A tour starts at city 0, "
                    f"visits every city exactly once, and returns to 0. What is the MINIMUM possible "
                    f"total tour length? End with 'Answer: <integer>'."),
            gold=f"Answer: {opt}", checker=C.exact_int(opt),
            failure_modes=("a nearest-neighbour tour that isn't optimal", "arithmetic slips summing legs"),
            why_not_verbosity=f"only the exact minimum {opt} is accepted; a greedy tour overshoots",
            wrong_example=f"Answer: {opt + 1}"))

    return tasks


CASES: list[Task] = _build()


def selftest() -> None:
    """Cross-check the exact solvers against brute force, and the self-certifying checkers accept/reject."""
    rng = random.Random(7)
    for _ in range(5):
        items = [(rng.randint(2, 10), rng.randint(1, 15)) for _ in range(8)]
        cap = rng.randint(10, 25)
        assert knapsack_max(items, cap) == _knapsack_brute(items, cap), (items, cap)
    for _ in range(5):
        n = 7
        d = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                d[i][j] = d[j][i] = rng.randint(1, 20)
        assert tsp_min(d) == _tsp_brute(d)
    for t in CASES:                                     # every gold passes, every wrong_example fails
        assert t.checker(t.gold), t.id
        assert not t.checker(t.wrong_example), t.id
