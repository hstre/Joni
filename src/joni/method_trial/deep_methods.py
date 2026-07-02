"""A database of DEEP methods — non-trivial, procedural techniques, not shallow thinking-move shapes.

The Stage-2 experiment tested SHALLOW heuristics ("try to break each statement") and found no transfer
on a strong model — no surprise, a capable model already internalises those. That never was the goal.
A *deep* method (vollständige Induktion, Inklusion-Exklusion, Diagonalisierung, dynamische Programmierung)
is a **structured procedure** with a base/step form, correctness-critical parts, and named ways to get
it wrong. This is Joni's store of such methods: each carries its actual STEPS, the conditions its
correctness rests on, its failure modes, and a worked example — a reusable, composable knowledge asset,
independent of any benchmark. Offline, non-core, deterministic, no model.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeepMethod:
    id: str
    name: str                       # English name (German aka in `aka`)
    aka: str                        # the German / common name
    kind: str                       # proof_technique | counting | existence | optimization | ...
    when_to_use: str                # the trigger signature: which problems it applies to
    steps: tuple[str, ...]          # the ordered PROCEDURE — the non-trivial structure
    correctness_conditions: tuple[str, ...]   # what must hold for the application to be valid
    failure_modes: tuple[str, ...]  # named ways it is applied WRONG
    worked_example: str
    provenance: str                 # where it comes from (a-priori / cited), never a trial outcome


DEEP_METHODS: list[DeepMethod] = [
    DeepMethod(
        id="mathematical_induction", name="Mathematical induction", aka="vollständige Induktion",
        kind="proof_technique",
        when_to_use="prove a statement P(n) holds for every integer n >= n0",
        steps=("Base case: prove P(n0) directly.",
               "Induction hypothesis: assume P(k) for an arbitrary fixed k >= n0.",
               "Induction step: using the hypothesis, prove P(k+1).",
               "Conclude: P(n) holds for all n >= n0."),
        correctness_conditions=("the base case is actually verified, not asserted",
                                "the step genuinely USES P(k) (else it is not induction)",
                                "n0 matches the claim's lower bound"),
        failure_modes=("skipping or mis-stating the base case",
                       "proving P(k+1) independently, never using P(k)",
                       "off-by-one in the base n0"),
        worked_example="Sum 1..n = n(n+1)/2: base n=1 -> 1=1; assume for k; then "
                       "1..k+(k+1) = k(k+1)/2 + (k+1) = (k+1)(k+2)/2.",
        provenance="standard mathematics (induction axiom / Peano)"),
    DeepMethod(
        id="strong_induction", name="Strong induction", aka="starke Induktion",
        kind="proof_technique",
        when_to_use="prove P(n) when P(k+1) needs ALL earlier cases, not just P(k)",
        steps=("Base case(s): prove the small cases the step will lean on.",
               "Hypothesis: assume P(m) for ALL n0 <= m <= k.",
               "Step: prove P(k+1) using any of those earlier cases.",
               "Conclude for all n >= n0."),
        correctness_conditions=("enough base cases are covered for the step's largest 'reach back'",
                                "the step is allowed to use any earlier case, not only P(k)"),
        failure_modes=("too few base cases for the step's dependencies",
                       "silently assuming exactly one predecessor"),
        worked_example="Every n>=2 factors into primes: if n is prime, done; else n=ab with "
                       "2<=a,b<n, and by strong hypothesis both a,b factor.",
        provenance="standard mathematics"),
    DeepMethod(
        id="proof_by_contradiction", name="Proof by contradiction", aka="Widerspruchsbeweis",
        kind="proof_technique",
        when_to_use="prove P by showing that assuming not-P forces an impossibility",
        steps=("Assume the negation not-P.",
               "Derive consequences by valid steps.",
               "Reach a contradiction (a statement and its negation).",
               "Conclude P, since not-P is untenable."),
        correctness_conditions=("the assumed negation is the exact logical negation of P",
                                "every derivation step is valid",
                                "the contradiction is genuine, not a mere surprise"),
        failure_modes=("negating P incorrectly (e.g. dropping a quantifier)",
                       "declaring a counter-intuitive result a 'contradiction'"),
        worked_example="sqrt(2) irrational: assume = p/q in lowest terms; then p^2=2q^2, so p even, "
                       "p=2r, q^2=2r^2, q even -> p,q share factor 2, contradicting lowest terms.",
        provenance="classical logic"),
    DeepMethod(
        id="contrapositive", name="Proof by contrapositive", aka="Kontraposition",
        kind="proof_technique",
        when_to_use="prove 'if A then B' when 'if not-B then not-A' is easier",
        steps=("Form the contrapositive: not-B implies not-A.",
               "Prove the contrapositive directly.",
               "Conclude the original, which is logically equivalent."),
        correctness_conditions=("the contrapositive is formed correctly (swap AND negate both)",
                                "not confused with the (invalid) converse or inverse"),
        failure_modes=("proving the converse 'if B then A' instead",
                       "negating only one side"),
        worked_example="'if n^2 is even then n is even': contrapositive 'if n is odd then n^2 is odd'; "
                       "n=2k+1 -> n^2=4k^2+4k+1, odd.",
        provenance="classical logic"),
    DeepMethod(
        id="inclusion_exclusion", name="Inclusion-exclusion", aka="Inklusion-Exklusion",
        kind="counting",
        when_to_use="count a union of overlapping sets, or objects avoiding several properties",
        steps=("Add the sizes of the individual sets.",
               "Subtract every pairwise intersection.",
               "Add back every triple intersection; alternate signs by size.",
               "|A1 u ... u An| = sum singles - sum pairs + sum triples - ..."),
        correctness_conditions=("every intersection level is included with the right sign",
                                "the sets/properties are defined on the same universe"),
        failure_modes=("stopping after subtracting pairs (over-subtracting triples)",
                       "sign errors on higher-order terms"),
        worked_example="1..1000 divisible by 3 or 5: 333+200-|by15|=333+200-66=467.",
        provenance="combinatorics"),
    DeepMethod(
        id="pigeonhole", name="Pigeonhole principle", aka="Schubfachprinzip",
        kind="existence",
        when_to_use="prove SOME collision/repeat must exist, without constructing it",
        steps=("Identify the 'pigeons' (objects) and the 'holes' (categories).",
               "Show #pigeons > k * #holes.",
               "Conclude some hole holds > k pigeons (a forced collision)."),
        correctness_conditions=("the mapping from pigeons to holes is well-defined and total",
                                "the counting inequality is strict where needed"),
        failure_modes=("mis-defining the holes so the count fails",
                       "claiming WHICH hole (pigeonhole only gives existence)"),
        worked_example="Among 13 people, two share a birth month: 13 pigeons, 12 months -> a month "
                       "has >= 2.",
        provenance="combinatorics (Dirichlet)"),
    DeepMethod(
        id="invariant_argument", name="Invariant / monovariant argument", aka="Invariantenmethode",
        kind="impossibility",
        when_to_use="prove a state is unreachable, or a process must terminate",
        steps=("Find a quantity preserved by every allowed move (an invariant) OR one that strictly "
               "decreases (a monovariant).",
               "Compute it for the start and target states.",
               "If an invariant differs, the target is unreachable; a bounded monovariant forces "
               "termination."),
        correctness_conditions=("the invariant is preserved by EVERY legal move (check all)",
                                "a monovariant is bounded and strictly monotone"),
        failure_modes=("an invariant that breaks under one overlooked move",
                       "a 'monovariant' that can stall"),
        worked_example="Two opposite corners removed from an 8x8 board can't be tiled by dominoes: each "
                       "domino covers one black+one white; removing two same-colour squares leaves an "
                       "imbalance the tiling can't match.",
        provenance="olympiad combinatorics"),
    DeepMethod(
        id="extremal_principle", name="Extremal principle", aka="Extremalprinzip",
        kind="existence",
        when_to_use="prove existence/structure by considering a maximal or minimal object",
        steps=("Consider an object that is extremal (largest/smallest/first) for some measure.",
               "Argue about its neighbours: assuming a defect contradicts its extremality.",
               "Conclude the desired property."),
        correctness_conditions=("an extremal object actually exists (finite/well-ordered set)",
                                "the measure is well-defined"),
        failure_modes=("assuming a maximum exists in an unbounded/infinite set",
                       "picking a measure the argument can't use"),
        worked_example="In a finite set of points not all collinear, a Sylvester-Gallai line through "
                       "exactly two exists — take the point/line pair with the smallest positive "
                       "distance and argue.",
        provenance="olympiad combinatorics"),
    DeepMethod(
        id="double_counting", name="Double counting", aka="doppeltes Abzählen",
        kind="counting",
        when_to_use="prove an identity by counting one set two different ways",
        steps=("Choose a set of configurations to count.",
               "Count it one way (e.g. by rows).",
               "Count the SAME set another way (e.g. by columns).",
               "Equate the two counts."),
        correctness_conditions=("both methods count exactly the same set",
                                "no configuration is missed or double-listed in either count"),
        failure_modes=("the two counts range over subtly different sets",
                       "an ordering/labelling mismatch"),
        worked_example="Sum of degrees in a graph = 2*(#edges): count edge-endpoints by vertices, and "
                       "by edges.",
        provenance="combinatorics"),
    DeepMethod(
        id="bijection", name="Bijective proof", aka="bijektiver Beweis",
        kind="counting",
        when_to_use="show two sets are equinumerous by an explicit reversible map",
        steps=("Define a map f from set A to set B.",
               "Show f is injective (no two collide) and surjective (hits everything) — or give f^-1.",
               "Conclude |A| = |B|."),
        correctness_conditions=("f is well-defined on all of A and lands in B",
                                "both injectivity and surjectivity are shown (or an explicit inverse)"),
        failure_modes=("a map that is only injective and calling it a bijection",
                       "an inverse that isn't actually inverse"),
        worked_example="#subsets of an n-set = 2^n: map each subset to its 0/1 indicator string, a "
                       "bijection to {0,1}^n.",
        provenance="combinatorics"),
    DeepMethod(
        id="diagonalization", name="Diagonalization", aka="Diagonalisierung",
        kind="proof_technique",
        when_to_use="prove non-existence via self-reference (uncountability, undecidability)",
        steps=("Assume an enumeration of all objects of the type exists.",
               "Construct a new object that differs from the i-th listed object in the i-th place.",
               "The new object is of the type but not in the list -> contradiction."),
        correctness_conditions=("the diagonal object is genuinely of the required type",
                                "it provably differs from EVERY listed object"),
        failure_modes=("the constructed object accidentally coincides with a later entry",
                       "the enumeration assumption is not actually used"),
        worked_example="Reals in (0,1) are uncountable: given any list, build x differing from the n-th "
                       "number in its n-th decimal; x is not on the list.",
        provenance="Cantor; adapted by Turing/Gödel"),
    DeepMethod(
        id="dynamic_programming", name="Dynamic programming", aka="dynamische Programmierung",
        kind="optimization",
        when_to_use="optimize/count over overlapping subproblems with optimal substructure",
        steps=("Define a state that captures a subproblem's answer.",
               "Write a recurrence expressing a state from smaller states.",
               "Fix an evaluation order (or memoize) so each state is solved once.",
               "Read the answer from the final state; reconstruct via stored choices if needed."),
        correctness_conditions=("optimal substructure holds (an optimal solution uses optimal "
                                "sub-solutions)",
                                "the recurrence covers all transitions and base cases",
                                "the order respects dependencies"),
        failure_modes=("a state that doesn't capture enough to be Markovian",
                       "missing base cases or transitions",
                       "recomputation from a wrong evaluation order"),
        worked_example="Longest common subsequence: dp[i][j] from dp[i-1][j-1]+1 on a match, else "
                       "max(dp[i-1][j], dp[i][j-1]).",
        provenance="Bellman"),
    DeepMethod(
        id="divide_and_conquer", name="Divide and conquer", aka="Teile und herrsche",
        kind="algorithm",
        when_to_use="solve by splitting into independent sub-instances and combining",
        steps=("Divide the instance into smaller independent sub-instances.",
               "Conquer each recursively (base case solved directly).",
               "Combine the sub-solutions into the whole.",
               "Analyse cost via the recurrence (e.g. Master theorem)."),
        correctness_conditions=("the sub-instances are independent and cover the whole",
                                "the combine step is correct and the base case terminates"),
        failure_modes=("overlapping sub-instances (should be DP instead)",
                       "an incorrect or costly combine step"),
        worked_example="Mergesort: split in halves, sort each, merge in linear time -> O(n log n).",
        provenance="classical algorithms"),
]


# -- query / persistence: this is a database, so it is indexable and serialisable ------------------
def by_id(mid: str) -> DeepMethod | None:
    return next((m for m in DEEP_METHODS if m.id == mid), None)


def by_kind(kind: str) -> list[DeepMethod]:
    return [m for m in DEEP_METHODS if m.kind == kind]


def kinds() -> tuple[str, ...]:
    return tuple(sorted({m.kind for m in DEEP_METHODS}))


def applicable(keyword: str) -> list[DeepMethod]:
    """Methods whose trigger signature mentions a keyword (a crude, deterministic retrieval)."""
    k = (keyword or "").lower()
    return [m for m in DEEP_METHODS if k and k in m.when_to_use.lower()]


def to_records() -> list[dict]:
    """A JSON-serialisable dump — the seed for a persisted deep-methods DB."""
    return [{"id": m.id, "name": m.name, "aka": m.aka, "kind": m.kind, "when_to_use": m.when_to_use,
             "steps": list(m.steps), "correctness_conditions": list(m.correctness_conditions),
             "failure_modes": list(m.failure_modes), "worked_example": m.worked_example,
             "provenance": m.provenance} for m in DEEP_METHODS]
