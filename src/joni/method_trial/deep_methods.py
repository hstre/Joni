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
    core_question: str = ""         # the Kernfrage — the one question the method asks, content-free
    domains: tuple[str, ...] = ()   # where the SCHEMA applies — math, physics, chemistry, ... (transfer)


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
        provenance="standard mathematics (induction axiom / Peano)",
        core_question="Gilt es am Anfang, und vererbt der Schritt es weiter? Dann gilt es fuer alle.",
        domains=("math", "computer-science", "chemistry", "physics")),  # e.g. homologe Reihe: property of unit n -> n+1
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
        provenance="standard mathematics",
        core_question="Braucht der Schritt ALLE kleineren Faelle, nicht nur den letzten?",
        domains=("math", "computer-science")),
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
        provenance="classical logic",
        core_question="Wenn das Gegenteil galt — welche Unmoeglichkeit erzwingt es?",
        domains=("math", "physics", "chemistry")),  # e.g. Perpetuum mobile widerspricht Energieerhaltung
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
        provenance="classical logic",
        core_question="Ist 'nicht-B erzwingt nicht-A' leichter zu zeigen als 'A erzwingt B'?",
        domains=("math", "computer-science")),
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
        provenance="combinatorics",
        core_question="Was habe ich doppelt gezaehlt, und auf welcher Ueberlappungsstufe?",
        domains=("math", "computer-science", "chemistry")),  # e.g. counting isomers avoiding several substituent clashes
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
        provenance="combinatorics (Dirichlet)",
        core_question="Sind mehr Objekte als Faecher da? Dann teilt sich ein Fach.",
        domains=("math", "computer-science", "physics")),  # e.g. more states than energy levels -> degeneracy forced
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
        provenance="olympiad combinatorics",
        core_question="Welche Groesse bleibt unter JEDEM erlaubten Schritt gleich (oder faellt streng)?",
        domains=("math", "physics", "chemistry")),  # the shared root of Erhaltungssaetze / Invarianten below
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
        provenance="olympiad combinatorics",
        core_question="Was gilt fuer das groesste/kleinste Objekt — und was bricht, wenn es nicht gilt?",
        domains=("math", "physics")),  # e.g. a system settles at the extremum of a potential
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
        provenance="combinatorics",
        core_question="Kann ich DASSELBE auf zwei Arten zaehlen und die Ergebnisse gleichsetzen?",
        domains=("math", "physics", "chemistry")),  # e.g. bonds counted per-atom vs per-molecule (valence balance)
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
        provenance="combinatorics",
        core_question="Gibt es eine umkehrbare Zuordnung, die zwei Mengen gleich gross macht?",
        domains=("math", "physics")),  # e.g. microstate correspondences in statistical mechanics
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
        provenance="Cantor; adapted by Turing/Gödel",
        core_question="Kann ich ein Objekt bauen, das sich von jedem gelisteten an einer Stelle unterscheidet?",
        domains=("math", "computer-science")),
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
        provenance="Bellman",
        core_question="Baut sich die optimale Loesung aus optimalen Teilloesungen auf?",
        domains=("math", "computer-science", "physics")),  # e.g. optimal-path / least-action discretisations
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
        provenance="classical algorithms",
        core_question="Zerfaellt das Problem in unabhaengige Teile, die ich einzeln loese und zusammenfuege?",
        domains=("math", "computer-science", "chemistry")),  # e.g. retrosynthesis: split a target into sub-syntheses

    # -- UNIVERSAL / PHYSICS / CHEMISTRY deep methods --------------------------------------------
    # These are the content-independent schemata the operator named: a method is a QUESTION you ask
    # of a system, not a fact about one domain. Erhaltung, Symmetrie, Bilanz, Grenzfall, Skalierung,
    # Gleichgewicht, Stabilitaet, Optimierung, Mechanismus, Invariante — each usable on a foreign
    # system (e.g. a mass-balance argument applied to a probability distribution).
    DeepMethod(
        id="conservation_law", name="Conservation-law argument", aka="Erhaltungssatz",
        kind="invariant",
        when_to_use="constrain or forbid an outcome via a quantity that cannot change",
        steps=("Name a conserved quantity (energy, momentum, charge, mass, particle number).",
               "Evaluate it in the initial and final states.",
               "Impose initial = final; any outcome violating the balance is impossible.",
               "Read off the constraint the conservation forces."),
        correctness_conditions=("the quantity is genuinely conserved under the actual dynamics/closure",
                                "the system boundary is drawn so nothing leaks unaccounted"),
        failure_modes=("assuming conservation across an open boundary (leak/source ignored)",
                       "conflating a conserved quantity with one that is merely often constant"),
        worked_example="A perpetuum mobile is impossible: it would output work with no input, "
                       "violating energy conservation (first law).",
        provenance="physics (Noether); chemistry (mass/charge balance)",
        core_question="Welche Groesse kann nicht verschwinden — und was erzwingt ihre Bilanz?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="symmetry_argument", name="Symmetry argument", aka="Symmetrieargument",
        kind="invariant",
        when_to_use="deduce structure/vanishing/degeneracy from a transformation the system ignores",
        steps=("Identify a transformation under which the system is invariant (mirror, rotation, "
               "exchange, gauge).",
               "Argue that any result must respect that invariance.",
               "Conclude: asymmetric answers are forbidden; a conserved current or selection rule "
               "follows (Noether: symmetry -> conservation)."),
        correctness_conditions=("the system really is invariant under the transformation (check the "
                                "Hamiltonian / structure, not just the picture)",
                                "the observable transforms the way you assume"),
        failure_modes=("assuming a symmetry that a small term actually breaks",
                       "ignoring spontaneous symmetry breaking (symmetric law, asymmetric state)"),
        worked_example="A symmetric charge distribution has zero dipole moment; a centrosymmetric "
                       "molecule is IR-inactive for modes that preserve the centre.",
        provenance="physics (Noether, group theory); chemistry (molecular point groups)",
        core_question="Was bleibt gleich, wenn ich das System spiegle/drehe/vertausche?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="dimensional_analysis", name="Dimensional analysis", aka="Dimensionsanalyse",
        kind="estimation",
        when_to_use="find the FORM of a relation, or sanity-check one, from units alone",
        steps=("List the relevant quantities and their dimensions (M, L, T, ...).",
               "Form dimensionless groups (Buckingham pi).",
               "The target must be a function of those groups; fix scaling exponents by matching "
               "dimensions.",
               "A leftover pure number needs experiment/theory, but the scaling is forced."),
        correctness_conditions=("all relevant quantities are included and no irrelevant one sneaks in",
                                "dimensions balance on both sides exactly"),
        failure_modes=("omitting a governing quantity, giving a wrong power law",
                       "treating a dimensionless constant as if dimensions could set it"),
        worked_example="Pendulum period: [T] from length L and g ([L/T^2]) forces T ~ sqrt(L/g); "
                       "mass cannot enter (no way to cancel M).",
        provenance="physics; engineering (Buckingham pi)",
        core_question="Welche Form erzwingen die Einheiten allein, bevor ich rechne?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="limiting_case", name="Limiting-case / boundary analysis", aka="Grenzfallbetrachtung",
        kind="estimation",
        when_to_use="check or narrow a result by pushing a parameter to an extreme",
        steps=("Pick a parameter and send it to a limit (0, infinity, equal, symmetric).",
               "Predict the known behaviour there from first principles.",
               "Compare the candidate expression's limit to that prediction.",
               "A mismatch falsifies the candidate; agreement constrains it."),
        correctness_conditions=("the limit is taken consistently across the whole expression",
                                "the 'known' limiting behaviour is itself trustworthy"),
        failure_modes=("a singular limit where terms silently blow up or cancel",
                       "assuming a smooth limit across a phase change / discontinuity"),
        worked_example="Relativistic KE (gamma-1)mc^2 must reduce to (1/2)mv^2 as v<<c — a Taylor "
                       "limit that any correct formula has to pass.",
        provenance="physics; applied mathematics",
        core_question="Was passiert am Rand des Modells — und stimmt es dort mit dem Bekannten?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="variational_principle", name="Variational / extremal principle", aka="Variationsprinzip",
        kind="optimization",
        when_to_use="find the realised state as the extremum of a functional (action, energy, entropy)",
        steps=("Write the quantity nature extremises (action S, free energy G, entropy).",
               "Set its first variation to zero over admissible states (delta S = 0).",
               "Solve the resulting Euler-Lagrange / stationarity condition.",
               "Check it is the right kind of extremum (min/max/saddle)."),
        correctness_conditions=("the functional and the admissible-variation space are correct",
                                "boundary/constraint terms are handled (Lagrange multipliers)"),
        failure_modes=("finding a stationary point that is a saddle, not the physical minimum",
                       "wrong or missing constraints"),
        worked_example="Light path (Fermat): the ray extremises travel time, giving Snell's law "
                       "n1 sin(t1) = n2 sin(t2).",
        provenance="physics (Lagrange, Hamilton, Fermat); chemistry (free-energy minimisation)",
        core_question="Welche Groesse macht die Natur extremal — und was folgt aus delta=0?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="perturbation", name="Perturbation / linearization", aka="Stoerungstheorie",
        kind="approximation",
        when_to_use="a hard problem is a small correction to a solvable one",
        steps=("Split into a solvable base plus a small term: H = H0 + eps*V.",
               "Expand the answer in powers of eps around the base solution.",
               "Keep leading corrections; linearize about the base state.",
               "Check the expansion parameter is genuinely small (convergence)."),
        correctness_conditions=("the perturbation is actually small relative to the base",
                                "no degeneracy/resonance that makes naive terms diverge"),
        failure_modes=("using it where the 'small' term is not small (series diverges)",
                       "missing a secular term that grows without bound"),
        worked_example="Anharmonic oscillator: treat the x^4 term as a small correction to the "
                       "harmonic solution; first-order shift of the energy levels.",
        provenance="physics (QM/celestial mechanics); applied mathematics",
        core_question="Ist das Problem eine kleine Stoerung eines loesbaren Falls?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="scaling_argument", name="Scaling / renormalization argument", aka="Skalierungsargument",
        kind="estimation",
        when_to_use="understand how behaviour changes with size/scale, or extract critical exponents",
        steps=("Rescale the governing variables by a factor.",
               "See which terms dominate / are invariant under the rescaling.",
               "Extract the scaling law (power) that the invariance forces.",
               "Identify the scale at which the dominant balance changes (crossover)."),
        correctness_conditions=("the rescaling respects the actual governing equations",
                                "the dominant balance is correctly identified in each regime"),
        failure_modes=("assuming one power law holds across a crossover it doesn't",
                       "ignoring a scale-dependent coupling"),
        worked_example="Surface-to-volume ratio scales as 1/L: why small animals lose heat faster and "
                       "why nanoparticles are disproportionately reactive.",
        provenance="physics (renormalization group); biology/chemistry (allometry, surface effects)",
        core_question="Wie aendert sich das Verhalten, wenn ich alles um einen Faktor skaliere?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="equilibrium_thinking", name="Equilibrium analysis", aka="Gleichgewichtsdenken",
        kind="invariant",
        when_to_use="find the resting state where opposing tendencies balance (forces, rates, potentials)",
        steps=("Identify the opposing tendencies (forward/back rates, drive/restore forces).",
               "Set them equal: net force = 0, or forward rate = backward rate.",
               "Solve for the equilibrium state (Le Chatelier: how it shifts under a push).",
               "Distinguish stable from unstable equilibria."),
        correctness_conditions=("the system can actually reach equilibrium (closed enough, given time)",
                                "all opposing contributions are included in the balance"),
        failure_modes=("confusing steady-state (throughput) with true equilibrium (no net flux)",
                       "ignoring kinetic barriers that prevent reaching it"),
        worked_example="A + B <=> C: at equilibrium k_f[A][B] = k_r[C], giving K = k_f/k_r; add A and "
                       "the system shifts toward C (Le Chatelier).",
        provenance="chemistry (mass action, Le Chatelier); physics (mechanical equilibrium)",
        core_question="Wo heben sich die gegenlaeufigen Tendenzen genau auf?",
        domains=("chemistry", "physics", "math")),
    DeepMethod(
        id="stability_analysis", name="Stability analysis", aka="Stabilitaetsanalyse",
        kind="invariant",
        when_to_use="decide whether a state persists or runs away under a small disturbance",
        steps=("Take an equilibrium/steady state and perturb it slightly.",
               "Linearize the dynamics about that state.",
               "Check whether the perturbation decays (stable) or grows (unstable) — sign of the "
               "eigenvalues / second derivative of the potential.",
               "Classify: stable, unstable, marginal."),
        correctness_conditions=("the linearization is valid for small enough perturbations",
                                "all relevant modes/directions are checked, not just one"),
        failure_modes=("declaring stability from one direction while another is unstable (saddle)",
                       "missing a nonlinear instability the linear analysis can't see"),
        worked_example="A ball at the bottom of a bowl returns (stable, potential minimum); on a hill "
                       "top it rolls away (unstable, maximum) — the sign of V''.",
        provenance="physics/dynamical systems; chemistry (reaction stability)",
        core_question="Kehrt das System nach einer kleinen Stoerung zurueck, oder laeuft es weg?",
        domains=("physics", "chemistry", "math")),
    DeepMethod(
        id="mass_balance", name="Balance / accounting argument", aka="Bilanzierung",
        kind="counting",
        when_to_use="track a conserved substance through a system: what goes in must come out or accumulate",
        steps=("Draw a boundary around the system.",
               "Sum all inflows and outflows of the tracked quantity.",
               "in - out = accumulation (0 at steady state).",
               "Solve for the unknown flow/amount the balance pins down."),
        correctness_conditions=("the boundary is closed and every flow across it is counted",
                                "the same units/species are tracked consistently"),
        failure_modes=("forgetting a stream (unaccounted source or sink)",
                       "mixing species or basis (mass vs moles) mid-balance"),
        worked_example="Balancing CH4 + 2 O2 -> CO2 + 2 H2O: atoms of each element in = out; the "
                       "coefficients are forced by the element balances.",
        provenance="chemistry/chemical engineering (mass balance); physics (continuity)",
        core_question="Was geht rein, was kommt raus, was reichert sich an?",
        domains=("chemistry", "physics", "math")),
    DeepMethod(
        id="thermodynamic_feasibility", name="Thermodynamic feasibility", aka="thermodynamische Triebkraft",
        kind="invariant",
        when_to_use="decide whether a process CAN happen spontaneously (direction), ignoring speed",
        steps=("Identify the relevant potential (Gibbs free energy G at const T,p).",
               "Compute its change: delta G = delta H - T*delta S.",
               "delta G < 0 -> spontaneous in that direction; > 0 -> not; = 0 -> equilibrium.",
               "Separate the enthalpy (bond/energy) and entropy (disorder) drivers."),
        correctness_conditions=("the right potential for the constraints is used (G for T,p; A for T,V)",
                                "state-function values are taken between the actual end states"),
        failure_modes=("confusing feasibility (thermodynamics) with rate (kinetics)",
                       "sign errors in delta H vs delta S trade-off"),
        worked_example="Diamond -> graphite has delta G < 0 (favourable) yet is unobservably slow: "
                       "feasible thermodynamically, forbidden kinetically.",
        provenance="chemistry/physics (thermodynamics, Gibbs)",
        core_question="Zeigt die Triebkraft (delta G) ueberhaupt in diese Richtung?",
        domains=("chemistry", "physics")),
    DeepMethod(
        id="kinetic_accessibility", name="Kinetic-barrier analysis", aka="kinetische Zugaenglichkeit",
        kind="invariant",
        when_to_use="decide whether a thermodynamically-allowed process is FAST enough to matter",
        steps=("Find the highest barrier on the path (transition state / activation energy Ea).",
               "Estimate the rate from Ea and temperature (Arrhenius: k ~ exp(-Ea/RT)).",
               "Compare the timescale to the one that matters.",
               "If blocked, ask what lowers the barrier (catalyst, temperature, alternate path)."),
        correctness_conditions=("the rate-limiting step (highest barrier) is correctly identified",
                                "the mechanism/path assumed is the one actually taken"),
        failure_modes=("assuming a favourable delta G implies a usable rate",
                       "missing a lower-barrier alternative pathway"),
        worked_example="H2 + O2 is hugely favourable but stable at room temperature until a spark "
                       "provides the activation energy; a catalyst lowers Ea instead.",
        provenance="chemistry (Arrhenius, transition-state theory)",
        core_question="Ist der Weg dorthin schnell genug — oder blockiert eine Barriere?",
        domains=("chemistry", "physics")),
    DeepMethod(
        id="structure_property", name="Structure-property / structure-reactivity reasoning",
        aka="Struktur-Eigenschafts-Prinzip", kind="mechanism",
        when_to_use="predict a substance's behaviour from its structure (bonds, geometry, electronics)",
        steps=("Read the structure: connectivity, geometry, polarity, charge distribution.",
               "Map structural features to the governing property (acidity, reactivity, colour, "
               "conductivity) via known trends.",
               "Locate the reactive/vulnerable site the structure dictates.",
               "Predict behaviour; where trends conflict, weigh the dominant one."),
        correctness_conditions=("the structure is right (correct isomer/conformer/charge state)",
                                "the trend invoked actually governs this property"),
        failure_modes=("reasoning from a wrong structure",
                       "over-generalising one trend against a dominant opposing effect"),
        worked_example="More electronegative substituents stabilise a carboxylate's negative charge, "
                       "so trichloroacetic acid is far stronger than acetic acid.",
        provenance="chemistry (physical-organic; structure-activity relationships)",
        core_question="Was an der STRUKTUR erzwingt dieses Verhalten?",
        domains=("chemistry", "physics")),
    DeepMethod(
        id="mechanism_decomposition", name="Mechanistic decomposition", aka="Mechanismusanalyse",
        kind="mechanism",
        when_to_use="explain an overall change by the ordered sequence of elementary steps behind it",
        steps=("Break the overall transformation into elementary steps.",
               "Track what each step does to the key participants (electrons, atoms, energy).",
               "Identify intermediates and the rate-/outcome-determining step.",
               "Check the steps sum to the overall change and conserve everything."),
        correctness_conditions=("each elementary step is itself valid and conserves mass/charge",
                                "the steps compose to exactly the observed overall change"),
        failure_modes=("a step that violates conservation or geometry",
                       "an intermediate that can't actually form"),
        worked_example="SN1 vs SN2: the mechanism (carbocation intermediate vs concerted backside "
                       "attack) predicts the rate law and the stereochemistry, not the overall "
                       "equation alone.",
        provenance="chemistry (reaction mechanisms); physics (multi-step processes)",
        core_question="Welche Kette von Elementarschritten steckt hinter der Gesamtaenderung?",
        domains=("chemistry", "physics")),
    DeepMethod(
        id="state_function_cycle", name="State-function / thermodynamic-cycle argument",
        aka="Hess'scher Satz", kind="invariant",
        when_to_use="get a hard-to-measure change from easy ones, because the total is path-independent",
        steps=("Recognise the quantity is a state function (path-independent: enthalpy, energy, "
               "entropy).",
               "Build a cycle/alternate path from steps whose values you know.",
               "Sum the known steps; the total equals the direct (unknown) change.",
               "Close the cycle: around any loop the net change is zero."),
        correctness_conditions=("the quantity really is a state function (path-independent)",
                                "the constructed path starts and ends at the same states"),
        failure_modes=("applying it to a path-dependent quantity (heat/work in general)",
                       "steps that don't actually connect the same end states"),
        worked_example="Hess's law: delta H of a reaction = sum of delta H of any set of steps that "
                       "add up to it, even steps you can't run directly.",
        provenance="chemistry (Hess); physics (potentials, exact differentials)",
        core_question="Ist die Groesse wegunabhaengig — kann ich sie ueber einen Umweg berechnen?",
        domains=("chemistry", "physics", "math")),

    # -- COMPUTER-SCIENCE deep methods ------------------------------------------------------------
    # Informatik is a catalogue of content-free problem-solving schemata: reduce an unknown problem
    # to a solved one, halve a search space, map structure to a graph, sample instead of enumerate.
    # Each asks a question of ANY problem, not just of code — reduction on a chemical synthesis, a
    # graph model of a molecule, Monte-Carlo on a physics integral, binary search on a threshold.
    DeepMethod(
        id="reduction", name="Reduction / problem mapping", aka="Reduktion",
        kind="reduction",
        when_to_use="an unfamiliar problem might be a disguised version of one you already solved",
        steps=("Identify a target problem you CAN solve.",
               "Build a mapping: translate this problem's instances into the target's inputs.",
               "Solve in the target; translate the answer back.",
               "Check the mapping preserves the answer (a correct reduction, both directions)."),
        correctness_conditions=("the transformation preserves the property being asked about",
                                "the back-translation is valid and the map is computable"),
        failure_modes=("a mapping that changes the answer (not answer-preserving)",
                       "reducing to a problem that is itself unsolved/harder"),
        worked_example="Show a scheduling task is hard by mapping graph-colouring onto it; or plan a "
                       "synthesis by mapping the target onto a known named reaction.",
        provenance="computer science (reductions, NP-completeness); mathematics",
        core_question="Ist das ein verkleidetes Problem, das ich schon geloest habe?",
        domains=("computer-science", "math", "chemistry", "physics")),
    DeepMethod(
        id="binary_search", name="Binary search / bisection", aka="binaere Suche / Bisektion",
        kind="search",
        when_to_use="find a threshold in a range where a yes/no test is monotone (once true, stays true)",
        steps=("Confirm the property is monotone along the parameter (a single tipping point).",
               "Test the midpoint of the current range.",
               "Keep the half that must contain the boundary; discard the other.",
               "Repeat until the range is a point — the threshold."),
        correctness_conditions=("the predicate really is monotone in the search parameter",
                                "the range provably brackets the answer at the start"),
        failure_modes=("bisecting a non-monotone predicate (may miss the answer)",
                       "off-by-one on which half to keep"),
        worked_example="Root of a continuous f with f(a)<0<f(b): halve [a,b] by the sign of f(mid); "
                       "also: find the minimum temperature at which a reaction ignites.",
        provenance="computer science; numerical analysis (bisection)",
        core_question="Kann ich den Suchraum mit jeder Ja/Nein-Entscheidung halbieren?",
        domains=("computer-science", "math", "physics")),
    DeepMethod(
        id="greedy_exchange", name="Greedy with exchange argument", aka="Greedy-Verfahren",
        kind="optimization",
        when_to_use="build an optimum by repeated locally-best choices — when a swap argument justifies it",
        steps=("Define the locally-best choice at each step by a clear criterion.",
               "Build the solution by taking that choice repeatedly.",
               "Prove optimality by an exchange argument: any optimal solution can be swapped toward "
               "the greedy one without getting worse.",
               "If the exchange fails, greedy is not valid here — use DP instead."),
        correctness_conditions=("the exchange/greedy-choice property actually holds for this problem",
                                "the local criterion is well-defined"),
        failure_modes=("assuming greedy works without the exchange proof (often wrong)",
                       "a criterion that is locally good but globally trapping"),
        worked_example="Activity selection: always take the earliest-finishing compatible task; an "
                       "exchange argument shows no schedule fits more.",
        provenance="computer science (greedy algorithms); optimization",
        core_question="Fuehrt die lokal beste Wahl — per Vertauschungsargument — zum globalen Optimum?",
        domains=("computer-science", "math", "physics")),
    DeepMethod(
        id="backtracking", name="Backtracking with pruning", aka="Backtracking mit Beschneidung",
        kind="search",
        when_to_use="search all possibilities systematically while cutting branches that cannot succeed",
        steps=("Extend a partial solution one choice at a time (a search tree).",
               "After each extension, test constraints; if already violated, prune the whole branch.",
               "Recurse into promising branches; undo the choice on return (backtrack).",
               "Report solutions found; the pruning is what makes it tractable."),
        correctness_conditions=("the pruning test never discards a branch that could still succeed",
                                "every candidate is reachable by some sequence of choices"),
        failure_modes=("over-aggressive pruning that cuts real solutions",
                       "no pruning at all (degenerates to brute force)"),
        worked_example="N-queens: place one queen per row, prune the moment two attack; or "
                       "retrosynthesis: expand disconnections, prune chemically impossible ones.",
        provenance="computer science (search, constraint satisfaction); chemistry (retrosynthesis)",
        core_question="Kann ich systematisch suchen und aussichtslose Zweige frueh abschneiden?",
        domains=("computer-science", "chemistry", "math")),
    DeepMethod(
        id="graph_modeling", name="Graph modelling", aka="Graphmodellierung",
        kind="modeling",
        when_to_use="a problem is really about entities and the relations between them",
        steps=("Choose what the NODES are (entities/states) and what the EDGES are (relations/moves).",
               "Restate the question as a graph property (path, cycle, connectivity, matching, colouring).",
               "Apply the matching standard graph algorithm.",
               "Translate the graph answer back to the original terms."),
        correctness_conditions=("nodes and edges capture exactly the relevant structure",
                                "the graph property is truly equivalent to the question"),
        failure_modes=("modelling with the wrong node/edge choice so the property doesn't match",
                       "ignoring edge direction/weight that matters"),
        worked_example="Shortest route = shortest path in a weighted graph; a molecule IS a graph "
                       "(atoms=nodes, bonds=edges) so isomerism becomes graph isomorphism.",
        provenance="computer science (graph theory); chemistry (molecular graphs)",
        core_question="Geht es eigentlich um Knoten und ihre Verbindungen?",
        domains=("computer-science", "chemistry", "physics", "math")),
    DeepMethod(
        id="hashing_fingerprint", name="Hashing / fingerprinting", aka="Hashing / Fingerprint",
        kind="modeling",
        when_to_use="compare or deduplicate many objects fast by mapping each to a short key",
        steps=("Choose a function mapping each object to a short key (a fingerprint).",
               "Equal objects must get equal keys; different ones rarely collide.",
               "Compare/bucket by key instead of by the full object.",
               "Confirm true matches (keys equal) to rule out the rare collision."),
        correctness_conditions=("the key is invariant under the equivalences you care about",
                                "collisions are rare enough or resolved by a full check"),
        failure_modes=("a key that ignores a distinguishing feature (false matches)",
                       "trusting a collision without the confirming check"),
        worked_example="Detect duplicate files by hash, not byte-by-byte; molecular fingerprints let a "
                       "database screen millions of structures for similarity fast.",
        provenance="computer science (hashing); cheminformatics (molecular fingerprints)",
        core_question="Kann ich Objekte auf kurze Schluessel abbilden, sodass Gleichheit schnell prueft?",
        domains=("computer-science", "chemistry")),
    DeepMethod(
        id="monte_carlo", name="Monte-Carlo / random sampling", aka="Monte-Carlo-Methode",
        kind="approximation",
        when_to_use="an exact computation is intractable but random samples estimate it",
        steps=("Frame the target as an expectation or a ratio of counts/volumes.",
               "Draw many independent random samples from the right distribution.",
               "Estimate the target as the sample average / hit fraction.",
               "Quantify the error: it shrinks like 1/sqrt(number of samples)."),
        correctness_conditions=("samples are drawn from the correct distribution and are independent",
                                "the estimator is unbiased for the target"),
        failure_modes=("sampling from a biased/wrong distribution",
                       "claiming more precision than 1/sqrt(N) allows"),
        worked_example="Estimate pi by the fraction of random points landing in a quarter circle; "
                       "the same idea integrates a molecular partition function no formula reaches.",
        provenance="computer science / physics (Monte-Carlo, Metropolis)",
        core_question="Kann ich das Schwere durch Zufallsstichproben schaetzen statt exakt zu rechnen?",
        domains=("computer-science", "physics", "chemistry", "math")),
    DeepMethod(
        id="amortized_analysis", name="Amortized analysis", aka="amortisierte Analyse",
        kind="estimation",
        when_to_use="judge the average cost over a SEQUENCE of operations, though single ones spike",
        steps=("Consider a whole sequence of operations, not one in isolation.",
               "Assign an amortized cost (accounting/potential method) that smooths the spikes.",
               "Show the amortized costs bound the true total.",
               "Divide by the count for the per-operation average."),
        correctness_conditions=("the potential/credit never goes negative",
                                "the amortized bound really covers the actual total cost"),
        failure_modes=("reasoning from the single worst case instead of the sequence",
                       "a potential function that can go negative"),
        worked_example="A dynamic array doubling on overflow is O(1) per insert AMORTIZED though one "
                       "insert is O(n); likewise average cost per cycle of a bursty physical process.",
        provenance="computer science (amortized analysis)",
        core_question="Was kostet es im Schnitt ueber eine Folge, auch wenn einzelne Schritte teuer sind?",
        domains=("computer-science", "math", "physics")),
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


def by_domain(domain: str) -> list[DeepMethod]:
    """Methods whose content-independent schema is declared to apply in a domain."""
    d = (domain or "").lower()
    return [m for m in DEEP_METHODS if d in m.domains]


def domains() -> tuple[str, ...]:
    return tuple(sorted({d for m in DEEP_METHODS for d in m.domains}))


def cross_domain() -> list[DeepMethod]:
    """The point of the catalogue: methods declared usable in more than one domain — the schema
    (vollständige Induktion, Erhaltung, Symmetrie, ...) travels independent of the content."""
    return [m for m in DEEP_METHODS if len(m.domains) >= 2]


def to_records() -> list[dict]:
    """A JSON-serialisable dump — the seed for a persisted deep-methods DB."""
    return [{"id": m.id, "name": m.name, "aka": m.aka, "kind": m.kind, "when_to_use": m.when_to_use,
             "steps": list(m.steps), "correctness_conditions": list(m.correctness_conditions),
             "failure_modes": list(m.failure_modes), "worked_example": m.worked_example,
             "provenance": m.provenance, "core_question": m.core_question,
             "domains": list(m.domains)} for m in DEEP_METHODS]


# -- as Stage-2 preambles: the intervention supplies the ACTUAL procedure ---------------------------
def as_preamble(method_id: str) -> str:
    m = by_id(method_id)
    if m is None:
        return ""
    body = "\n".join(f"- {s}" for s in m.steps)
    return f"Apply this method — {m.name}. Follow the procedure exactly:\n{body}"


def _seed(s: str) -> int:
    import hashlib
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def scrambled_deep(method_id: str) -> str:
    import random
    words = as_preamble(method_id).split()
    random.Random(_seed(method_id)).shuffle(words)
    return " ".join(words)


def irrelevant_deep(method_id: str) -> str:
    ids = [m.id for m in DEEP_METHODS]
    i = ids.index(method_id)
    return as_preamble(ids[(i + 1) % len(ids)])


def neutral_deep(method_id: str) -> str:
    target = len(as_preamble(method_id).split())
    filler = ("Take your time. Read the problem carefully. Work through it step by step. Be precise "
              "and double-check each computation before committing to a final answer.")
    ws = filler.split()
    out: list[str] = []
    while len(out) < target:
        out.extend(ws)
    return " ".join(out[:target])
