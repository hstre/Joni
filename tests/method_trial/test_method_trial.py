"""Stage 0 + Stage 1: the pre-registration is frozen and the gold micro battery meets its contract.

No model, deterministic. This is the zero-cost foundation the measurement plan gates everything on.
"""
from __future__ import annotations

from joni.method_trial import checkers as C
from joni.method_trial import preregistration as P
from joni.method_trial.contract import validate_battery
from joni.method_trial.gold_micro_v1 import CASES


# --- Stage 0: the pre-registration is frozen (a change must update this pinned hash on purpose) --
def test_preregistration_hash_is_frozen():
    assert P.content_hash() == "be252cc25095a61f1ada9926d6342a4cdcac738eddc0aea2db0c59860bac7178"


def test_preregistration_has_the_load_bearing_decisions():
    s = P.SPEC
    assert len(s["controls"]) == 4                       # plain + neutral + scrambled + irrelevant
    assert "irrelevant_plausible_method" in s["controls"]
    assert s["proxy_acceptability"]["max_false_positive_rate_on_holdout"] == 0.10
    assert "false positives first" in s["false_positive_policy"]
    assert s["independence_unit"]["micro_battery"] == "task"
    # method plausibility must be a-priori, never from the outcome
    assert "NEVER derived from a trial outcome" in s["method_plausibility"]


# --- checker primitives ---------------------------------------------------------------------------
def test_checkers_extract_the_final_answer_not_a_passing_mention():
    # a number mentioned mid-reasoning must not win; the 'Answer:' region decides
    assert C.exact_int(4)("I first thought 6 or 7. Answer: 4") is True
    assert C.exact_int(4)("The answer is clearly not 4. Answer: 9") is False
    assert C.numeric_in_band(1e9, 5e9)("roughly 2-3 billion. Answer: 2,500,000,000") is True
    assert C.numeric_in_band(1e9, 5e9)("Answer: 5,000,000") is False   # out of band
    assert C.choice("C", "ABCD")("weighing A and B... Answer: C") is True
    assert C.choice("C", "ABCD")("Answer: B") is False
    assert C.index_set({3, 4}, {1, 2, 3, 4})("Answer: 3 and 4") is True
    assert C.index_set({3, 4}, {1, 2, 3, 4})("Answer: 1 and 2") is False
    assert C.yesno("no")("It is complicated. Answer: no") is True
    assert C.contains_any(("temperature", "season"))("Answer: the temperature / season") is True


# --- Stage 1: the battery meets its contract ------------------------------------------------------
def test_battery_meets_the_contract():
    rep = validate_battery(CASES, min_tasks=12)
    assert rep["ok"], rep["problems"]
    assert rep["n"] >= 12


def test_every_checker_accepts_its_gold_and_rejects_the_wrong_example():
    for t in CASES:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        if t.wrong_example:
            assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"


def test_every_task_declares_the_six_required_fields():
    for t in CASES:
        assert t.skill and t.expected_method_class and t.forbidden_origin_domain
        assert t.prompt and t.why_not_verbosity and t.failure_modes


def test_battery_spans_several_skills_and_method_classes():
    rep = validate_battery(CASES)
    assert len(rep["skills"]) >= 8            # not a single-skill battery
    assert len(rep["method_classes"]) >= 5    # adversarial / exclusion / boundary / decomposition


def test_hard_battery_meets_the_contract():
    from joni.method_trial.contract import validate_battery
    from joni.method_trial.gold_hard_v1 import CASES as HARD
    rep = validate_battery(HARD, min_tasks=15)
    assert rep["ok"], rep["problems"]
    for t in HARD:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        if t.wrong_example:
            assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"


def test_search_battery_is_verifiable_and_recall_proof():
    """NP-style battery: self-certifying certificates (Hamiltonian cycle, subset-sum) + exact optima
    (knapsack, TSP) cross-checked against brute force. Every gold is accepted, every wrong rejected,
    and the self-certifying checkers really validate against the instance itself."""
    from joni.method_trial import deep_methods as D
    from joni.method_trial import gold_search_v1 as S
    from joni.method_trial.contract import validate_battery
    from joni.method_trial.gold_search_v1 import CASES as SEARCH
    S.selftest()                          # exact solvers == brute force; checkers accept/reject
    rep = validate_battery(SEARCH, min_tasks=10)
    assert rep["ok"], rep["problems"]
    for t in SEARCH:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"
        assert D.by_id(t.expected_method_class) is not None, f"{t.id}: unknown method"
    # a Hamiltonian answer is checked against THIS instance: a wrong node set must be rejected
    ham = next(t for t in SEARCH if t.id.startswith("hamilton_"))
    assert not ham.checker("Answer: " + " ".join(str(i) for i in range(1, 99)))


def test_novel_battery_reference_solvers_are_cross_checked():
    """The recall-proof battery is only usable if its GOLD is trustworthy: every reference solver is
    cross-checked against an independent method (brute force / BFS / sieve vs inclusion-excl.)."""
    from joni.method_trial import gold_novel_v1 as N
    N.selftest()  # raises on any disagreement between the two independent computations


def test_novel_battery_meets_the_contract_and_is_recall_proof():
    from joni.method_trial import deep_methods as D
    from joni.method_trial.contract import validate_battery
    from joni.method_trial.gold_novel_v1 import CASES as NOVEL
    rep = validate_battery(NOVEL, min_tasks=10)
    assert rep["ok"], rep["problems"]
    for t in NOVEL:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"
        assert D.by_id(t.expected_method_class) is not None, f"{t.id}: unknown method"
    # the boolean tasks are balanced (both yes and no appear) so the battery is not degenerate
    yesno_golds = {t.gold for t in NOVEL if "yes" in t.gold or "no" in t.gold}
    assert any("yes" in g for g in yesno_golds) and any("no" in g for g in yesno_golds)
    # at least one count is large enough to be genuinely un-memorisable
    assert any(t.id.startswith("tiling_") for t in NOVEL)


def test_cross_battery_is_well_formed_and_content_independent():
    """The cross-domain battery: every task is cracked by a DEEP method whose ORIGIN differs from
    the task's surface domain (the operator's 'Induktion in der Chemie' idea). Contract holds,
    checkers discriminate, and every expected method resolves to a real deep-methods entry."""
    from joni.method_trial import deep_methods as D
    from joni.method_trial.contract import validate_battery
    from joni.method_trial.gold_cross_v1 import CASES as CROSS
    rep = validate_battery(CROSS, min_tasks=10)
    assert rep["ok"], rep["problems"]
    for t in CROSS:
        assert t.checker(t.gold), f"{t.id}: checker rejected its gold"
        if t.wrong_example:
            assert not t.checker(t.wrong_example), f"{t.id}: checker accepted the wrong example"
        m = D.by_id(t.expected_method_class)
        assert m is not None, f"{t.id}: method {t.expected_method_class} not in the deep-methods DB"
    # the battery spans several distinct deep methods (not one method dressed up ten ways)
    assert len({t.expected_method_class for t in CROSS}) >= 6


def test_cross_battery_builds_five_conditions_via_deep_procedures():
    """The intervention supplies the deep method's actual procedure; the four controls neutralise
    length / structure / relevance — all via conditions.build_deep, one prompt per condition."""
    from joni.method_trial import conditions
    from joni.method_trial.gold_cross_v1 import CASES as CROSS
    t = CROSS[0]
    conds = conditions.build_deep(t)
    assert set(conds) == set(conditions.CONDITIONS)
    assert conds["plain_baseline"] == t.prompt          # baseline is the naked task
    assert conds["intervention"].endswith(t.prompt)     # method prepended, task preserved
    assert conds["intervention"] != conds["plain_baseline"]
    assert all(conds[c] for c in conditions.CONDITIONS)  # every condition is a non-empty prompt


def test_deep_methods_database_is_well_formed():
    from joni.method_trial import deep_methods as D
    ms = D.DEEP_METHODS
    assert len(ms) >= 12
    assert len({m.id for m in ms}) == len(ms)          # unique ids
    assert len(D.kinds()) >= 4                          # spans proof / counting / existence / ...
    for m in ms:
        assert m.name and m.aka and m.kind and m.when_to_use and m.worked_example and m.provenance
        assert len(m.steps) >= 3, f"{m.id}: a deep method needs a real multi-step procedure"
        assert m.correctness_conditions, f"{m.id}: must state what its correctness rests on"
        assert m.failure_modes, f"{m.id}: must name how it is applied wrong"
    # it behaves like a database
    assert D.by_id("mathematical_induction").aka == "vollständige Induktion"
    assert D.by_kind("counting") and D.applicable("union of overlapping sets")
    assert len(D.to_records()) == len(ms)


def test_deep_methods_are_cross_domain_and_content_independent():
    """The catalogue's point: a method is a Kernfrage applied ACROSS domains, not a domain fact
    (vollständige Induktion in der Chemie). Every method carries a core question and its domains,
    the catalogue spans math + physics + chemistry, and most methods transfer to >= 2 domains."""
    from joni.method_trial import deep_methods as D
    ms = D.DEEP_METHODS
    for m in ms:
        assert m.core_question, f"{m.id}: must state its Kernfrage (the content-free question)"
        assert m.domains, f"{m.id}: must declare the domains its schema applies in"
    doms = set(D.domains())
    assert {"math", "physics", "chemistry"} <= doms, f"catalogue must span the three: {doms}"
    assert D.by_domain("chemistry") and D.by_domain("physics") and D.by_domain("math")
    # the physics/chemistry deep methods the operator named are present
    for mid in ("conservation_law", "symmetry_argument", "mass_balance",
                "thermodynamic_feasibility", "structure_property"):
        assert D.by_id(mid) is not None, f"missing named deep method: {mid}"
    # most methods are genuinely cross-domain (schema travels independent of content)
    assert len(D.cross_domain()) >= len(ms) // 2
    # to_records round-trips the new fields
    rec = next(r for r in D.to_records() if r["id"] == "conservation_law")
    assert rec["core_question"] and rec["domains"]
