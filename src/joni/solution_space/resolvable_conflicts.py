"""A battery of CHECKABLE conflicts — the honest ground truth for measuring the real apply_fn.

Each conflict is two contradictory factual claims where exactly one is objectively correct, so
"resolved correctly" is a DETERMINISTIC check (no LLM judge). ``seed_core`` builds a fresh Layer-9
core holding these as open conflicts and returns a registry mapping each minted conflict id to the
correct letter — the key that lets the cycle grade an executed resolution without any judgement.

Mixed correct-answer positions (not always A) so a solver cannot win by always picking one side.
"""

from __future__ import annotations

# (claim_A, claim_B, correct_letter). One side is objectively true; the numbers are checkable.
CASES = [
    ("7 times 8 equals 56.", "7 times 8 equals 54.", "A"),
    ("Water boils at 90 degrees Celsius at sea level.",
     "Water boils at 100 degrees Celsius at sea level.", "B"),
    ("A leap year has 366 days.", "A leap year has 367 days.", "A"),
    ("The square root of 144 is 14.", "The square root of 144 is 12.", "B"),
    ("There are 12 prime numbers below 40.", "There are 11 prime numbers below 40.", "A"),
    ("The sum 1+2+...+10 equals 45.", "The sum 1+2+...+10 equals 55.", "B"),
    ("A carbon dioxide molecule (CO2) has two oxygen atoms.",
     "A carbon dioxide molecule (CO2) has three oxygen atoms.", "A"),
    ("A hexagon has eight sides.", "A hexagon has six sides.", "B"),
    ("The binary number 1010 equals 10 in decimal.",
     "The binary number 1010 equals 12 in decimal.", "A"),
    ("12 percent of 200 is 24.", "12 percent of 200 is 26.", "A"),
]

# HARD battery — computation-heavy checkable conflicts (verified ground truth); the two numbers are
# close, so a solver must actually COMPUTE to pick the right one. This is where a baseline can fail,
# creating the headroom an executed method would need to show any value.
HARD_CASES = [
    ("The number of derangements of 5 distinct items is 44.",
     "The number of derangements of 5 distinct items is 46.", "A"),
    ("A 3-by-8 board has 155 domino tilings.", "A 3-by-8 board has 153 domino tilings.", "B"),
    ("Among 1 to 1000, exactly 228 integers are divisible by none of 2, 3, 5, 7.",
     "Among 1 to 1000, exactly 226 integers are divisible by none of 2, 3, 5, 7.", "A"),
    ("A 3-by-12 board has 2135 domino tilings.", "A 3-by-12 board has 2131 domino tilings.", "B"),
    ("The number of ways to fully parenthesize a product of 6 factors is 42.",
     "The number of ways to fully parenthesize a product of 6 factors is 48.", "A"),
    ("234 multiplied by 567 equals 132778.", "234 multiplied by 567 equals 132678.", "B"),
    ("7 raised to the 4th power, modulo 100, equals 1.",
     "7 raised to the 4th power, modulo 100, equals 43.", "A"),
    ("13 cubed equals 2917.", "13 cubed equals 2197.", "B"),
    ("The binomial coefficient C(12,5) equals 792.",
     "The binomial coefficient C(12,5) equals 782.", "A"),
    ("The determinant of the matrix [[2,3],[4,5]] is 2.",
     "The determinant of the matrix [[2,3],[4,5]] is -2.", "B"),
    ("The number of derangements of 6 distinct items is 265.",
     "The number of derangements of 6 distinct items is 264.", "A"),
    ("A 3-by-16 board has 29671 domino tilings.", "A 3-by-16 board has 29681 domino tilings.", "B"),
]


def seed_core(cases=None):
    """Build a fresh Layer-9 core with the checkable conflicts open. Returns ``(core, registry)`` where
    ``registry[conflict_id] = {"correct": "A"|"B", "a_id": ..., "b_id": ...}``. ``cases`` defaults to
    the easy ``CASES``; pass ``HARD_CASES`` for the computation-heavy battery. Fails loud if Layer 9
    is unavailable (this is a measurement seed, not a runtime path)."""
    cases = cases if cases is not None else CASES
    import desi_layer9 as l9
    from desi_layer9 import Operator as OP
    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance

    def op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
        return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                                provenance=Provenance.from_operator(), **kw)

    core = l9.Layer9()
    registry: dict[str, dict] = {}
    for i, (a_text, b_text, _correct) in enumerate(cases):
        core.submit(op(OP.CLAIM_CREATE, {"text": a_text, "topic": f"fact_{i}"},
                       ptype=PT.CLAIM_PROPOSAL))
        core.submit(op(OP.CLAIM_CREATE, {"text": b_text, "topic": f"fact_{i}"},
                       ptype=PT.CLAIM_PROPOSAL))
        claims = [c for c in core.all(l9.ObjectType.CLAIM) if c.topic == f"fact_{i}"]
        a_id, b_id = claims[0].id, claims[1].id
        core.submit(op(OP.CONFLICT_OPEN, {"claim_ids": [a_id, b_id], "severity": "hard"},
                       target_objects=(a_id, b_id)))
    for c in core.open_conflicts():
        a_id, b_id = c.claim_ids[0], c.claim_ids[1]
        idx = int(next(cl for cl in core.all(l9.ObjectType.CLAIM)
                       if cl.id == a_id).topic.split("_")[1])
        registry[c.id] = {"correct": cases[idx][2], "a_id": a_id, "b_id": b_id}
    return core, registry
