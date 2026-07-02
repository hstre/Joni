"""Baustein B of the solution-space pipeline (docs/SOLUTION_SPACE_PIPELINE.md).

The deep-method OPERATOR layer over DESi's epistemic gap map. Where DESi's
``solution_space_gap.analyze_gaps`` proposes a shallow AFFINITY per open gap, this proposes a DEEP
METHOD (with its Kernfrage) as the operator to try on that gap — and, via the same 'success in
another scope' logic, a BRIDGE between solution spaces. Consumes DESi's read-only
``EpistemicGapSnapshot`` (Joni depends on DESi, never the reverse); reads Joni's deep-methods DB.
Deterministic, no LLM, fail-open.
"""

from .cartography import (
    BridgeCandidate,
    Cartography,
    Island,
    SolutionPoint,
    cartograph,
)
from .operators import (
    DeepMethodProposal,
    DeepMethodTrial,
    from_core,
    propose_operators,
)
from .pipeline import ReachPlan, plan

__all__ = [
    # Baustein B — deep-method operators over the gap map
    "DeepMethodProposal",
    "DeepMethodTrial",
    "propose_operators",
    "from_core",
    # Baustein A — the product-space cartographer
    "SolutionPoint",
    "Island",
    "BridgeCandidate",
    "Cartography",
    "cartograph",
    # end-to-end pipeline A -> B
    "ReachPlan",
    "plan",
]
