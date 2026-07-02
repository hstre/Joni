"""Stage 1.5 — a HARDER battery, built to sit at a strong model's failure frontier (no model here).

The micro battery hit a ceiling (baseline ~0.92) so it could not discriminate method value. These 15
tasks are trap-shaped: the fast/intuitive answer is WRONG and the a-priori method's discipline is what
would correct it (base-rate neglect, novel doubling/rate traps, the boy-girl paradox, knights-&-knaves,
Bayes). All answers stay objectively checkable (deterministic checkers, no LLM judge) and verbosity-
resistant. Whether this actually lowers the baseline enough is a MEASUREMENT (run Stage 2 with
``--battery hard``); if a strong model still aces it, the finding is 'this model needs no method — use
a weaker one', per the plan.
"""
from __future__ import annotations

from . import checkers as C
from .gold_micro_v1 import Task

CASES: list[Task] = [
    Task(
        id="base_rate_bayes", skill="bayesian_reasoning", expected_method_class="causal",
        forbidden_origin_domain="epidemiology",
        prompt=("A disease affects 1 in 1000 people. A test is 99% sensitive and has a 5% "
                "false-positive rate. You test positive. What is the probability (percent, nearest "
                "integer) that you actually have the disease? End with 'Answer: <percent>'."),
        gold="Answer: 2", checker=C.numeric_in_band(1, 3),
        failure_modes=("base-rate neglect -> ~95%", "confusing sensitivity with P(disease|positive)"),
        why_not_verbosity="only the Bayesian value (~2%) is in band; a confident '99%' scores 0",
        wrong_example="Answer: 95"),
    Task(
        id="bacteria_third", skill="growth_reasoning", expected_method_class="boundary",
        forbidden_origin_domain="growth-modelling",
        prompt=("A bacterial colony TRIPLES every hour and fills a jar exactly at hour 9. At which "
                "hour was the jar one-ninth full? End with 'Answer: <hour>'."),
        gold="Answer: 7", checker=C.exact_int(7),
        failure_modes=("dividing 9 by 3", "linear thinking on exponential growth"),
        why_not_verbosity="needs reasoning back two triplings from full; a guessed number lands off",
        wrong_example="Answer: 3"),
    Task(
        id="painters_rate", skill="work_rate", expected_method_class="decomposition",
        forbidden_origin_domain="work-rate",
        prompt=("If 3 painters paint 3 fences in 3 hours, how many painters are needed to paint 9 "
                "fences in 9 hours? End with 'Answer: <integer>'."),
        gold="Answer: 3", checker=C.exact_int(3),
        failure_modes=("pattern-matching to 9", "not computing the per-painter rate"),
        why_not_verbosity="the rate decomposition gives 3; the intuitive answer 9 is the trap",
        wrong_example="Answer: 9"),
    Task(
        id="div3or5not15", skill="number_theory", expected_method_class="decomposition",
        forbidden_origin_domain="number-theory",
        prompt=("How many integers from 1 to 1000 are divisible by 3 or 5 but NOT by 15? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 401", checker=C.exact_int(401),
        failure_modes=("forgetting to exclude multiples of 15", "double counting"),
        why_not_verbosity="only the exact count passes; it needs inclusion-exclusion done correctly",
        wrong_example="Answer: 467"),
    Task(
        id="double_negation_min", skill="logical_reading", expected_method_class="adversarial",
        forbidden_origin_domain="logic",
        prompt=("'It is not true that none of the switches are off.' If that sentence is true, what is "
                "the MINIMUM number of switches that are off? End with 'Answer: <integer>'."),
        gold="Answer: 1", checker=C.exact_int(1),
        failure_modes=("collapsing the double negation to 0", "reading 'none' as 'all'"),
        why_not_verbosity="the nested negation resolves to 'at least one off' -> minimum 1",
        wrong_example="Answer: 0"),
    Task(
        id="two_girls", skill="conditional_probability", expected_method_class="decomposition",
        forbidden_origin_domain="probability",
        prompt=("A family has two children. You know AT LEAST ONE is a girl. What is the probability "
                "that BOTH are girls? Give a fraction. End with 'Answer: <fraction>'."),
        gold="Answer: 1/3", checker=C.contains_any(("1/3", "one third", "one-third", "0.33", "33%")),
        failure_modes=("answering 1/2 (ignoring the conditioning)", "wrong sample space"),
        why_not_verbosity="enumerating {GG,GB,BG} gives 1/3; the intuitive 1/2 is the trap",
        wrong_example="Answer: 1/2"),
    Task(
        id="clock_angle_315", skill="geometry", expected_method_class="boundary",
        forbidden_origin_domain="geometry",
        prompt=("What is the angle in degrees between the hour and minute hands of a clock at exactly "
                "3:15? End with 'Answer: <degrees>'."),
        gold="Answer: 7.5", checker=C.numeric_in_band(7, 8),
        failure_modes=("answering 0 (both 'on the 3')", "ignoring the hour hand's 15-min drift"),
        why_not_verbosity="the hour hand moves 7.5deg past 3 by 3:15; naive 0 is wrong",
        wrong_example="Answer: 0"),
    Task(
        id="calendar_100", skill="modular_arithmetic", expected_method_class="decomposition",
        forbidden_origin_domain="calendars",
        prompt=("If today is Tuesday, what day of the week will it be in exactly 100 days? "
                "End with 'Answer: <day>'."),
        gold="Answer: Thursday", checker=C.contains_any(("thursday",)),
        failure_modes=("miscomputing 100 mod 7", "off-by-one on the day count"),
        why_not_verbosity="100 mod 7 = 2, so Tuesday + 2 = Thursday; a guessed day scores 0",
        wrong_example="Answer: Friday"),
    Task(
        id="knights_knaves", skill="logical_deduction", expected_method_class="adversarial",
        forbidden_origin_domain="knights-and-knaves",
        prompt=("On an island, knights always tell the truth and knaves always lie. A says 'B is a "
                "knave.' B says 'A and I are both knights.' Exactly one of them is the knave — which "
                "one? End with 'Answer: <A or B>'."),
        gold="Answer: B", checker=C.choice("B", "AB"),
        failure_modes=("not testing both assignments", "taking B's claim at face value"),
        why_not_verbosity="only A-knight/B-knave is consistent; asserting without testing fails",
        wrong_example="Answer: A"),
    Task(
        id="monty_100", skill="probability", expected_method_class="inversion",
        forbidden_origin_domain="game-theory",
        prompt=("100 doors, one prize. You pick door 1. The host, who knows where the prize is, opens "
                "98 other doors, all empty, leaving your door and door 57. If you switch to door 57, "
                "what is your probability of winning? Give a fraction. End with 'Answer: <fraction>'."),
        gold="Answer: 99/100", checker=C.contains_any(("99/100", "99 100", "0.99", "99%")),
        failure_modes=("saying 1/2 by symmetry", "ignoring the host's knowledge"),
        why_not_verbosity="the host's informed reveal concentrates 99/100 on door 57",
        wrong_example="Answer: 1/2"),
    Task(
        id="overlap_sets", skill="set_reasoning", expected_method_class="decomposition",
        forbidden_origin_domain="set-theory",
        prompt=("In a class of 30, 18 play football, 15 play basketball, and 5 play neither. How many "
                "play BOTH? End with 'Answer: <integer>'."),
        gold="Answer: 8", checker=C.exact_int(8),
        failure_modes=("forgetting the 'neither' 5", "adding instead of inclusion-exclusion"),
        why_not_verbosity="both = 18+15-(30-5) = 8; only the exact number passes",
        wrong_example="Answer: 3"),
    Task(
        id="sequence_next", skill="pattern_abstraction", expected_method_class="decomposition",
        forbidden_origin_domain="sequences",
        prompt=("What is the next number in the sequence 2, 6, 12, 20, 30, ...? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 42", checker=C.exact_int(42),
        failure_modes=("adding a constant", "missing the n(n+1) / growing-difference structure"),
        why_not_verbosity="differences 4,6,8,10 -> next +12 -> 42; a plausible 40 is wrong",
        wrong_example="Answer: 40"),
    Task(
        id="increasing_pins", skill="combinatorics", expected_method_class="decomposition",
        forbidden_origin_domain="combinatorics",
        prompt=("How many 4-digit PINs (digits 0-9) have STRICTLY INCREASING digits, e.g. 1258? "
                "End with 'Answer: <integer>'."),
        gold="Answer: 210", checker=C.exact_int(210),
        failure_modes=("computing 10*9*8*7 (ordered)", "allowing repeats"),
        why_not_verbosity="strictly increasing = choose 4 of 10 = C(10,4) = 210; 5040 is the trap",
        wrong_example="Answer: 5040"),
    Task(
        id="heartbeats_day", skill="estimation", expected_method_class="boundary",
        forbidden_origin_domain="estimation",
        prompt=("Estimate how many times a human heart beats in ONE day. Show rate x time and end "
                "with 'Answer: <number>'."),
        gold="Answer: 100000", checker=C.numeric_in_band(6e4, 1.4e5),
        failure_modes=("unit slip (per hour)", "guessing a round number without rate x time"),
        why_not_verbosity="~70 bpm x 1440 min ~ 1e5; a number outside the band scores 0",
        wrong_example="Answer: 5000"),
    Task(
        id="words_novel", skill="estimation", expected_method_class="boundary",
        forbidden_origin_domain="estimation",
        prompt=("Estimate the total number of words in a typical 300-page novel. Show the "
                "decomposition and end with 'Answer: <number>'."),
        gold="Answer: 82500", checker=C.numeric_in_band(5e4, 1.5e5),
        failure_modes=("guessing without words-per-page x pages", "order-of-magnitude slip"),
        why_not_verbosity="~275 words/page x 300 ~ 8e4; only an in-band number passes",
        wrong_example="Answer: 5000"),
]
