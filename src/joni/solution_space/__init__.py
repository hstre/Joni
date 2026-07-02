"""Baustein B of the solution-space pipeline (docs/SOLUTION_SPACE_PIPELINE.md).

The deep-method OPERATOR layer over DESi's epistemic gap map. Where DESi's
``solution_space_gap.analyze_gaps`` proposes a shallow AFFINITY per open gap, this proposes a DEEP
METHOD (with its Kernfrage) as the operator to try on that gap — and, via the same 'success in
another scope' logic, a BRIDGE between solution spaces. Consumes DESi's read-only
``EpistemicGapSnapshot`` (Joni depends on DESi, never the reverse); reads Joni's deep-methods DB.
Baustein A (cartography) maps the product space into islands/gaps/bridges; the pipeline composes
A->B; Baustein C (discovery) learns new method<->gap-kind affinities from trials, holdout-validated.
Deterministic, no LLM, fail-open.
"""

from .cartography import (
    BridgeCandidate,
    Cartography,
    Island,
    SolutionPoint,
    cartograph,
)
from .coordinates import (
    build_points,
    embed_texts,
    embeddings_backend,
    state_vector_of,
)
from .core_points import points_from_core, state_vector_from_object
from .discovery import (
    DiscoveredAffinity,
    discover_affinities,
    discovery_report,
    to_extra_affinities,
)
from .navigation import (
    NavigationReport,
    NavItem,
    NavStep,
    navigate,
    navigate_core,
    navigate_iteratively,
)
from .operator_cycle import grade_by_resolution, run_operator_cycle
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
    # Baustein C — discovery
    "DiscoveredAffinity",
    "discover_affinities",
    "to_extra_affinities",
    "discovery_report",
    # navigation — the prioritised exploration agenda + live hookup + iterative loop
    "navigate",
    "navigate_core",
    "navigate_iteratively",
    "NavigationReport",
    "NavItem",
    "NavStep",
    # coordinate plumbing (records -> SolutionPoints)
    "build_points",
    "embed_texts",
    "embeddings_backend",
    "state_vector_of",
    # (a) live coordinate source + (b) the learning cycle
    "points_from_core",
    "state_vector_from_object",
    "run_operator_cycle",
    "grade_by_resolution",
]
