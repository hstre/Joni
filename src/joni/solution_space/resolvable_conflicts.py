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


def seed_core():
    """Build a fresh Layer-9 core with the checkable conflicts open. Returns ``(core, registry)`` where
    ``registry[conflict_id] = {"correct": "A"|"B", "a_id": ..., "b_id": ...}``. Fails loud if Layer 9
    is unavailable (this is a measurement seed, not a runtime path)."""
    import desi_layer9 as l9
    from desi_layer9 import Operator as OP
    from desi_layer9 import ProposalType as PT
    from desi_layer9.provenance import Provenance

    def op(operator, payload, ptype=PT.STATE_REVISION_PROPOSAL, **kw):
        return l9.make_proposal(ptype, operator, payload=payload, proposer="joni",
                                provenance=Provenance.from_operator(), **kw)

    core = l9.Layer9()
    registry: dict[str, dict] = {}
    for i, (a_text, b_text, _correct) in enumerate(CASES):
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
        registry[c.id] = {"correct": CASES[idx][2], "a_id": a_id, "b_id": b_id}
    return core, registry
