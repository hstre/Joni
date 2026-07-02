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

# HARD battery — computation-heavy checkable conflicts (verified ground truth) where a SPECIFIC deep
# method is genuinely the key. Each carries the RIGHT method (4th element) so the measurement can route
# the CORRECT method (not the taxonomy's default), removing the mis-routing confound. Pure-arithmetic
# facts (raw multiplication etc.) are deliberately excluded — no deep method is "right" for those.
# Balanced 6 correct-A / 6 correct-B.
HARD_CASES = [
    ("Among 1 to 1000, exactly 228 integers are divisible by none of 2, 3, 5, 7.",
     "Among 1 to 1000, exactly 226 integers are divisible by none of 2, 3, 5, 7.",
     "A", "inclusion_exclusion"),
    ("The number of derangements of 5 distinct items is 46.",
     "The number of derangements of 5 distinct items is 44.", "B", "inclusion_exclusion"),
    ("The number of derangements of 6 distinct items is 265.",
     "The number of derangements of 6 distinct items is 264.", "A", "inclusion_exclusion"),
    ("A 3-by-8 board has 155 domino tilings.", "A 3-by-8 board has 153 domino tilings.",
     "B", "dynamic_programming"),
    ("A 3-by-12 board has 2131 domino tilings.", "A 3-by-12 board has 2135 domino tilings.",
     "A", "dynamic_programming"),
    ("A 2-by-10 board has 89 domino tilings.", "A 2-by-10 board has 91 domino tilings.",
     "A", "dynamic_programming"),
    ("The number of ways to fully parenthesize a product of 6 factors is 48.",
     "The number of ways to fully parenthesize a product of 6 factors is 42.",
     "B", "dynamic_programming"),
    ("The minimum number of people that guarantees at least 5 share a birth month is 49.",
     "The minimum number of people that guarantees at least 5 share a birth month is 48.",
     "A", "pigeonhole"),
    ("The minimum number of integers that guarantees at least 3 share the same remainder mod 7 is 14.",
     "The minimum number of integers that guarantees at least 3 share the same remainder mod 7 is 15.",
     "B", "pigeonhole"),
    ("At a party of 12 where every pair shakes hands once, there are 66 handshakes total.",
     "At a party of 12 where every pair shakes hands once, there are 78 handshakes total.",
     "A", "double_counting"),
    ("The number of shortest lattice paths from (0,0) to (4,4) is 72.",
     "The number of shortest lattice paths from (0,0) to (4,4) is 70.", "B", "bijection"),
    ("The number of shortest lattice paths from (0,0) to (5,5) is 250.",
     "The number of shortest lattice paths from (0,0) to (5,5) is 252.", "B", "bijection"),
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
    for i, case in enumerate(cases):
        a_text, b_text = case[0], case[1]
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
        case = cases[idx]
        registry[c.id] = {"correct": case[2], "a_id": a_id, "b_id": b_id,
                          "method": case[3] if len(case) > 3 else None}
    return core, registry
