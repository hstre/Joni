"""Who may request which operator.

The gate uses this to keep generative contributors in their lane: a model (and thus
Kevin, whose candidates are model-generated) may *propose*, record trials, and recall -
but may never confirm a claim, promote a method, resolve a conflict, or touch the
control plane. Those authoritative operators require a deterministic operator or a human,
and control-plane changes additionally require explicit governance approval.
"""

from __future__ import annotations

from .enums import (
    OPERATORS_GRANTING_AUTHORITATIVE,
    OPERATORS_GRANTING_CONTROL,
    Operator,
    OriginType,
)

# Operators that confer authority or settle disputed state - never a raw model/user.
AUTHORITATIVE_OPERATORS: frozenset[Operator] = (
    OPERATORS_GRANTING_AUTHORITATIVE
    | OPERATORS_GRANTING_CONTROL
    | frozenset({
        Operator.CLAIM_CONFIRM, Operator.CLAIM_REJECT, Operator.CLAIM_SUPERSEDE,
        Operator.CONFLICT_RESOLVE, Operator.METHOD_PROMOTE,
    })
)

# Control-plane operators - require governance approval at the gate.
CONTROL_OPERATORS: frozenset[Operator] = OPERATORS_GRANTING_CONTROL

# Origins that may only ever produce candidates (no authority, no settlement).
_GENERATIVE = frozenset({
    OriginType.LOCAL_MODEL, OriginType.EXTERNAL_MODEL, OriginType.USER, OriginType.SOURCE,
})


def may_request(origin_type: OriginType, operator: Operator) -> bool:
    """Whether a proposer of this origin may even request this operator."""
    if operator in CONTROL_OPERATORS and origin_type not in (
        OriginType.HUMAN, OriginType.DETERMINISTIC_OPERATOR
    ):
        return False
    return not (origin_type in _GENERATIVE and operator in AUTHORITATIVE_OPERATORS)
