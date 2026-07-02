"""Stage 1 — the Gold MICRO Battery (pilot-only, no model, deterministic checkers).

Twelve foreign tasks with objectively checkable answers. Each task declares its target skill, the
method class that *should* help (pre-registered, not tuned to a result), the origin domain a method may
NOT come from to be trialed here (no home-turf leakage), a deterministic checker, plausible failure
modes, and why it resists a verbose-but-empty answer. This battery FALSIFIES (does any method beat the
controls at all); it is explicitly NOT the authority for retain/retire — that needs the held-out
battery (see the plan). ``wrong_example`` exists only so the test can prove each checker also REJECTS.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import checkers as C


@dataclass(frozen=True)
class Task:
    id: str
    skill: str
    expected_method_class: str          # which method class should help (a-priori, pre-registered)
    forbidden_origin_domain: str        # a method from this origin may NOT be trialed here (no leakage)
    prompt: str
    gold: str                           # a correct final answer, for reference + the reject test
    checker: Callable[[str], bool]
    failure_modes: tuple[str, ...]
    why_not_verbosity: str
    wrong_example: str = ""             # a plausible WRONG answer (for the checker-rejects test)


CASES: list[Task] = [
    Task(
        id="contradiction_pair",
        skill="contradiction_detection", expected_method_class="adversarial",
        forbidden_origin_domain="contradiction-detection",
        prompt=("Four statements:\n1) The vault was locked all night.\n2) Only Sam had a key.\n"
                "3) Sam was in another city all night.\n4) The vault was opened from inside at 2am.\n"
                "Which TWO statements cannot both be true? End with 'Answer: <two numbers>'."),
        gold="Answer: 3 and 4",
        checker=C.index_set({3, 4}, {1, 2, 3, 4}),
        failure_modes=("naming a merely surprising pair", "summarising instead of locating the clash"),
        why_not_verbosity="a fluent summary that does not name the exact incompatible pair scores 0",
        wrong_example="Answer: 1 and 2"),
    Task(
        id="rule_out_catastrophic",
        skill="risk_triage", expected_method_class="exclusion",
        forbidden_origin_domain="risk-triage",
        prompt=("A one-way migration script can: A) log verbosely, B) skip an index rebuild, "
                "C) DROP the old table before verifying the copy, D) send a Slack ping. Which single "
                "step must be eliminated FIRST because its failure is irreversible? End with "
                "'Answer: <letter>'."),
        gold="Answer: C",
        checker=C.choice("C", "ABCD"),
        failure_modes=("picking a merely noisy step", "ranking by likelihood not by irreversibility"),
        why_not_verbosity="only the irreversible-loss option is correct; eloquence about the others fails",
        wrong_example="Answer: B"),
    Task(
        id="heartbeats_fermi",
        skill="estimation", expected_method_class="boundary",
        forbidden_origin_domain="estimation",
        prompt=("Estimate the total number of heartbeats in a 70-year human life. Show the decomposition "
                "and end with 'Answer: <number>'."),
        gold="Answer: 2500000000",
        checker=C.numeric_in_band(1e9, 5e9),
        failure_modes=("guessing a round number without rate x time", "unit slip (per minute vs year)"),
        why_not_verbosity="a discursive answer with no in-band number scores 0; the band needs the decomposition",
        wrong_example="Answer: 5 million"),
    Task(
        id="distinct_even_count",
        skill="combinatorics", expected_method_class="decomposition",
        forbidden_origin_domain="combinatorics",
        prompt=("How many 3-digit numbers (100-999) have all-distinct digits AND are even? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 328",
        checker=C.exact_int(328),
        failure_modes=("forgetting the units=0 case is different", "letting the leading digit be 0"),
        why_not_verbosity="only the exact integer passes; it needs the correct case split on the units digit",
        wrong_example="Answer: 360"),
    Task(
        id="coin_count",
        skill="combinatorics", expected_method_class="decomposition",
        forbidden_origin_domain="combinatorics",
        prompt=("Using any number of dimes (10c) and nickels (5c), how many distinct ways make exactly "
                "30 cents? (order does not matter) End with 'Answer: <integer>'."),
        gold="Answer: 4",
        checker=C.exact_int(4),
        failure_modes=("double counting orderings", "missing the all-nickels or all-dimes extreme"),
        why_not_verbosity="the exact count needs enumerating d=0..3; a hand-wave lands off",
        wrong_example="Answer: 6"),
    Task(
        id="causal_confound",
        skill="causal_reasoning", expected_method_class="causal",
        forbidden_origin_domain="causal-analysis",
        prompt=("Ice-cream sales and drownings both rise together across the year. To test whether "
                "ice cream causes drownings, which single confounding variable must you control for? "
                "End with 'Answer: <variable>'."),
        gold="Answer: temperature (the season / hot weather)",
        checker=C.contains_any(("temperature", "weather", "season", "heat", "summer")),
        failure_modes=("controlling an irrelevant variable", "asserting causation directly"),
        why_not_verbosity="naming the common cause is the whole task; prose without it fails",
        wrong_example="Answer: the price of ice cream"),
    Task(
        id="negation_eligibility",
        skill="logical_reading", expected_method_class="adversarial",
        forbidden_origin_domain="logic",
        prompt=("Rule: 'Every employee who did NOT complete training is ineligible for the bonus.' "
                "Alice DID complete training. Is Alice necessarily eligible for the bonus? "
                "End with 'Answer: yes' or 'Answer: no'."),
        gold="Answer: no",
        checker=C.yesno("no"),
        failure_modes=("reading 'not ineligible' as 'eligible'", "affirming the consequent"),
        why_not_verbosity="the rule only removes ONE disqualifier; completing training does not grant eligibility",
        wrong_example="Answer: yes"),
    Task(
        id="find_the_bug",
        skill="debugging", expected_method_class="causal",
        forbidden_origin_domain="debugging",
        prompt=("This function should sum 1..n inclusive but returns the wrong total:\n"
                "  def s(n):\n      t = 0\n      for i in range(n):\n          t += i\n      return t\n"
                "Name the single defect. End with 'Answer: <defect>'."),
        gold="Answer: range(n) should be range(1, n+1) (off-by-one; it omits n and starts at 0)",
        checker=C.contains_any(("n+1", "n + 1", "range(1", "off-by-one", "off by one", "omits n",
                                "1, n")),
        failure_modes=("blaming the accumulator init", "rewriting without naming the range bug"),
        why_not_verbosity="only identifying the range/off-by-one defect counts; restating the code does not",
        wrong_example="Answer: t = 0 should be t = 1"),
    Task(
        id="provenance_independent",
        skill="provenance", expected_method_class="provenance",
        forbidden_origin_domain="provenance",
        prompt=("Three claims:\nA) 'X is safe' — cites blog QuickTakes.\n"
                "B) 'X is safe' — cites a peer-reviewed trial in Lancet.\n"
                "C) 'X is safe' — cites blog QuickTakes (reposted).\n"
                "Which claim is independently sourced from the other two? End with 'Answer: <letter>'."),
        gold="Answer: B",
        checker=C.choice("B", "ABC"),
        failure_modes=("counting 3 sources as 3 independent", "picking by tone not by root source"),
        why_not_verbosity="two claims share one blog root; only B is independent — the count must be by origin",
        wrong_example="Answer: A"),
    Task(
        id="invariant_violation",
        skill="invariant_reasoning", expected_method_class="invariant",
        forbidden_origin_domain="invariant-reasoning",
        prompt=("A sealed box is claimed to hold its internal energy exactly constant forever, yet it "
                "continuously emits visible light to the outside and nothing enters it. Which "
                "conservation law does this description violate? End with 'Answer: <quantity>'."),
        gold="Answer: energy (it radiates energy away while claiming constant internal energy)",
        checker=C.contains_any(("energy",)),
        failure_modes=("naming momentum or charge", "accepting the claim as consistent"),
        why_not_verbosity="the conserved quantity that is violated is the answer; description alone fails",
        wrong_example="Answer: momentum"),
    Task(
        id="inversion_guarantee_failure",
        skill="inversion", expected_method_class="inversion",
        forbidden_origin_domain="inversion",
        prompt=("You want a Friday production deploy to go WELL. By inversion, which single action would "
                "most reliably GUARANTEE it goes badly? A) add a rollback plan, B) deploy behind a flag, "
                "C) push untested schema changes straight to prod with no backup, D) announce it. "
                "End with 'Answer: <letter>'."),
        gold="Answer: C",
        checker=C.choice("C", "ABCD"),
        failure_modes=("picking a mildly risky option", "answering what would help, not what guarantees failure"),
        why_not_verbosity="inversion isolates the single most reliably catastrophic action; C is unambiguous",
        wrong_example="Answer: D"),
    Task(
        id="exclusion_first",
        skill="differential", expected_method_class="exclusion",
        forbidden_origin_domain="triage",
        prompt=("A middle-aged adult reports chest tightness. It could be a common cold or a heart "
                "attack. Which do you work to RULE OUT first, and it is not the common one? "
                "End with 'Answer: <condition>'."),
        gold="Answer: heart attack (rule out the catastrophic first)",
        checker=C.contains_any(("heart", "cardiac", "mi", "infarction")),
        failure_modes=("ruling out by base-rate (the cold)", "treating both as equal priority"),
        why_not_verbosity="the catastrophic-first move names the heart attack; a balanced essay fails",
        wrong_example="Answer: the common cold"),
]


SKILLS = tuple(sorted({t.skill for t in CASES}))
METHOD_CLASSES = tuple(sorted({t.expected_method_class for t in CASES}))
