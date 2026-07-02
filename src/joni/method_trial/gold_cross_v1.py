"""Stage 2 (CROSS-DOMAIN) — the test the operator actually asked for: a deep method used INDEPENDENT
of its content, on a task in a FOREIGN domain (vollständige Induktion in der Chemie, Bilanz auf eine
Wahrscheinlichkeitsverteilung, ...).

Every task's surface domain (physics / chemistry / probability / a discrete puzzle) differs from the
ORIGIN of the method that cracks it (``forbidden_origin_domain`` is the method's home, and no task sits
inside it). The intervention supplies that method's content-free PROCEDURE from ``deep_methods.py`` — the
schema, not a domain fact — and we measure whether transferring it beats all four controls. The tasks are
error-prone with an objectively checkable number/word answer, so no LLM judge is needed. As with the deep
battery: a high baseline is itself a finding (the model maps the method unprompted); a mid baseline with
the method winning would be genuine content-independent transfer.
"""
from __future__ import annotations

from . import checkers as C
from .gold_micro_v1 import Task

CASES: list[Task] = [
    Task(
        id="pigeonhole_energy_levels", skill="existence",
        expected_method_class="pigeonhole", forbidden_origin_domain="combinatorics",
        prompt=("A physical system has exactly 8 distinct energy sublevels and no limit on how many "
                "particles a sublevel may hold. What is the MINIMUM number of particles that "
                "guarantees at least 4 of them share one sublevel? End with 'Answer: <integer>'."),
        gold="Answer: 25", checker=C.exact_int(25),
        failure_modes=("answering 4 or 32", "using 3*8 without the +1"),
        why_not_verbosity="pigeonhole forces 3*8+1 = 25; the +1 (worst case 3 per level) is the point",
        wrong_example="Answer: 24"),
    Task(
        id="double_counting_bonds", skill="counting",
        expected_method_class="double_counting", forbidden_origin_domain="combinatorics",
        prompt=("A hexane molecule has 6 carbon atoms and 14 hydrogen atoms. Every carbon forms "
                "exactly 4 single bonds and every hydrogen exactly 1 single bond; the only bonds are "
                "C-C and C-H. How many C-C bonds does the molecule have? End with 'Answer: <integer>'."),
        gold="Answer: 5", checker=C.exact_int(5),
        failure_modes=("forgetting to halve the bond-endpoint total", "not subtracting the C-H bonds"),
        why_not_verbosity="count bond-endpoints two ways: (6*4+14)/2 = 19 bonds, minus 14 C-H = 5 C-C",
        wrong_example="Answer: 6"),
    Task(
        id="invariant_reaction_reachable", skill="impossibility",
        expected_method_class="invariant_argument", forbidden_origin_domain="grid-puzzles",
        prompt=("A vessel holds 7 molecules of A and 5 of B. The only allowed change is the reversible "
                "reaction A + B <-> 2C (forward consumes one A and one B and makes two C; reverse makes "
                "one A and one B from two C). Can the system ever reach a state with 0 A and 0 B at the "
                "same time? End with 'Answer: yes' or 'Answer: no'."),
        gold="Answer: no", checker=C.yesno("no"),
        failure_modes=("guessing yes by running the reaction forward", "missing the conserved quantity"),
        why_not_verbosity="A-B is invariant under every move (both change by the same amount) and "
                          "equals 2, so 0-0 (difference 0) is unreachable",
        wrong_example="Answer: yes"),
    Task(
        id="conservation_counter_parity", skill="impossibility",
        expected_method_class="conservation_law", forbidden_origin_domain="physics",
        prompt=("A jar holds 15 red and 20 blue counters. Repeatedly remove any two counters: if they "
                "are the same colour, add one BLUE counter; if different colours, add one RED counter. "
                "Repeat until a single counter remains. What colour is the last counter? "
                "End with 'Answer: red' or 'Answer: blue'."),
        gold="Answer: red", checker=C.choice("RED", ["RED", "BLUE"]),
        failure_modes=("simulating a few steps and guessing", "tracking blue instead of the invariant"),
        why_not_verbosity="the PARITY of the red count is conserved by every move; it starts odd (15), "
                          "so the last counter must be red",
        wrong_example="Answer: blue"),
    Task(
        id="incex_functional_groups", skill="counting",
        expected_method_class="inclusion_exclusion", forbidden_origin_domain="combinatorics",
        prompt=("Of 200 compounds: 120 contain a C=O group, 90 contain nitrogen, 70 contain an OH "
                "group; 50 have C=O and N, 40 have C=O and OH, 30 have N and OH, and 20 have all three. "
                "How many compounds contain NONE of the three? End with 'Answer: <integer>'."),
        gold="Answer: 20", checker=C.exact_int(20),
        failure_modes=("stopping after subtracting the pairs", "sign error on the triple term"),
        why_not_verbosity="none = 200 - (120+90+70 - 50-40-30 + 20) = 200 - 180 = 20; the triple must "
                          "be added back",
        wrong_example="Answer: 40"),
    Task(
        id="dp_lattice_fillings", skill="counting",
        expected_method_class="dynamic_programming", forbidden_origin_domain="algorithms",
        prompt=("A one-dimensional lattice of 10 sites is filled completely by pieces that are either "
                "a monomer (covers 1 site) or a dimer (covers 2 adjacent sites). In how many distinct "
                "ways can the lattice be fully filled? End with 'Answer: <integer>'."),
        gold="Answer: 89", checker=C.exact_int(89),
        failure_modes=("wrong base cases", "off-by-one in the Fibonacci-like index"),
        why_not_verbosity="f(n)=f(n-1)+f(n-2) with f(1)=1,f(2)=2 gives f(10)=89; naive counting drifts",
        wrong_example="Answer: 55"),
    Task(
        id="bijection_double_bonds", skill="counting",
        expected_method_class="bijection", forbidden_origin_domain="combinatorics",
        prompt=("A carbon chain has 8 distinguishable bond positions. In how many ways can exactly 3 of "
                "them be chosen to be double bonds (positions are distinct, order does not matter, no "
                "adjacency restriction)? End with 'Answer: <integer>'."),
        gold="Answer: 56", checker=C.exact_int(56),
        failure_modes=("counting ordered selections 8*7*6", "using 8*3 or a wrong binomial"),
        why_not_verbosity="each choice <-> a 3-subset of 8 positions -> C(8,3) = 56, not the ordered "
                          "8*7*6",
        wrong_example="Answer: 336"),
    Task(
        id="balance_markov_steady", skill="reasoning",
        expected_method_class="mass_balance", forbidden_origin_domain="chemistry",
        prompt=("In a steady-state stochastic system, probability flows into state M only from state L "
                "at a constant 0.24 per second, and leaves M only toward state R at rate 0.6 per second "
                "times P(M). At steady state, inflow equals outflow. What is P(M)? "
                "End with 'Answer: <number>'."),
        gold="Answer: 0.4", checker=C.numeric_in_band(0.39, 0.41),
        failure_modes=("reporting the inflow 0.24 as the probability", "inverting the balance"),
        why_not_verbosity="balance: 0.6*P(M) = 0.24 -> P(M) = 0.4; what flows in must flow out",
        wrong_example="Answer: 0.24"),
    Task(
        id="extremal_bead_rest", skill="optimization",
        expected_method_class="extremal_principle", forbidden_origin_domain="olympiad-combinatorics",
        prompt=("A bead slides without friction on a wire whose height is y = (x - 3)^2 + 2 (gravity "
                "pulls toward smaller y). At which x-coordinate does the bead come to rest? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 3", checker=C.exact_int(3),
        failure_modes=("reading off the constant 2", "confusing the vertex x with the minimum height"),
        why_not_verbosity="the resting state is the minimum of the potential (height); the parabola's "
                          "vertex is at x = 3, independent of the +2",
        wrong_example="Answer: 2"),
    Task(
        id="contradiction_kelvin_engine", skill="proof",
        expected_method_class="proof_by_contradiction", forbidden_origin_domain="logic",
        prompt=("A proposed engine works in a repeating cycle: each cycle it absorbs heat from ONE "
                "thermal reservoir and converts ALL of that heat into work, with no other change "
                "anywhere. Is such an engine possible? End with 'Answer: yes' or 'Answer: no'."),
        gold="Answer: no", checker=C.yesno("no"),
        failure_modes=("saying yes because energy is conserved", "confusing it with an ideal engine"),
        why_not_verbosity="assume it works, then entropy of the universe would decrease each cycle -> "
                          "contradiction with the second law; energy conservation alone does not forbid "
                          "it, the contradiction does",
        wrong_example="Answer: yes"),
]
