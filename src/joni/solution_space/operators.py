"""Deep-method operators over an EpistemicGapSnapshot — the deep twin of DESi's analyze_gaps.

DESi's ``solution_space_gap.analyze_gaps`` ranks under-addressed-but-relevant *shallow affinities*
(causal / boundary / ...) on each open gap. This does the same shape of analysis but proposes a DEEP
METHOD from Joni's database as the OPERATOR to apply — carrying its Kernfrage as the concrete move —
and surfaces a BRIDGE when a method that succeeded in another scope is untried here (the
'Verknüpfung zwischen Lösungsräumen').

Design mirrors DESi's on purpose (reuse, not parallel logic):
  priority = severity(gap) x kind_relevance(method_kind | gap_kind) x under_addressed(method, gap)
A method already SUCCEEDED on this gap is not a gap (under = 0). Demotion is scope-bound: a local
no_benefit/harmful lowers it only here; a *technical* failure carries no methodological signal and
does NOT demote; success ELSEWHERE raises it (a bridge candidate).

HONESTY: the snapshot's own ``method_trials`` are keyed by shallow affinity, not deep-method id, so
deep-method outcomes live in a separate ``deep_trials`` list the caller passes. Until those exist,
every method is 'untried' on every gap and the ranking degrades to the a-priori (severity x kind)
table — exactly the honest 'degrades to the static table' state the projector already documents.
Deterministic, no model. Reads the deep-methods DB (pure data), consumes DESi's read-only snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from joni.method_trial import deep_methods as D

# Gap-kind -> preferred deep-method KINDS with a-priori weights. Keyed to DESi's ConflictKind values
# (see desi.solution_space_gap.analysis._RELEVANT_BY_KIND). Method-KINDS (not ids) so the mapping
# scales as the DB grows; an unknown gap-kind falls back to ``_BASE``. Override-able, never tuned to
# an outcome. The method kinds are those in deep_methods.py (proof_technique / counting /
# existence / impossibility / optimization / algorithm / invariant / estimation / approximation /
# mechanism / reduction / search / modeling).
_METHOD_KINDS_BY_GAP: dict[str, tuple[tuple[str, float], ...]] = {
    "contradiction":    (("proof_technique", 1.0), ("impossibility", 0.8), ("reduction", 0.6)),
    "causal_dispute":   (("mechanism", 1.0), ("invariant", 0.7), ("approximation", 0.6),
                         ("estimation", 0.5)),
    "numeric":          (("estimation", 1.0), ("counting", 0.9), ("invariant", 0.7)),
    "value_mismatch":   (("optimization", 1.0), ("estimation", 0.7), ("invariant", 0.6)),
    "stale_hypothesis": (("proof_technique", 0.8), ("impossibility", 0.7), ("approximation", 0.7),
                         ("invariant", 0.6)),
    "unqualified":      (("reduction", 0.9), ("mechanism", 0.7), ("modeling", 0.6),
                         ("estimation", 0.5)),
    # geometry gaps from the cartographer (Baustein A): reach an unreached region, or bridge two.
    "unanchored_island": (("reduction", 1.0), ("estimation", 0.8), ("search", 0.7),
                          ("optimization", 0.6)),
    "bridge_candidate":  (("reduction", 1.0), ("invariant", 0.9), ("counting", 0.7),
                          ("modeling", 0.6)),
}
_BASE: tuple[tuple[str, float], ...] = (("reduction", 0.8), ("impossibility", 0.7),
                                        ("estimation", 0.6), ("proof_technique", 0.5))
_SEVERITY_W = {"hard": 1.0, "soft": 0.6}

# scope-bound trial result kinds (mirrors desi.solution_space_gap.snapshot.TRIAL_RESULTS)
_REAL_NEG = ("no_benefit", "harmful")


@dataclass(frozen=True)
class DeepMethodTrial:
    """One scope-bound outcome of applying a DEEP method to a gap (the Joni-side ledger DESi's
    affinity-keyed ``MethodTrial`` cannot hold). ``result`` is one of DESi's TRIAL_RESULTS."""

    method_id: str
    target: str                            # the gap id it was tried on (e.g. "conflict:X17")
    result: str
    scope: str = "unknown"
    count: int = 1


@dataclass(frozen=True)
class DeepMethodProposal:
    """A justified, NON-authoritative pointer: which deep method to apply as an operator on which
    gap, and why. Never a decision; the analog of DESi's BlindSpotProposal, one layer deeper."""

    target: str                            # the gap, e.g. "conflict:X17"
    method_id: str
    method_name: str
    core_question: str                     # the Kernfrage — the concrete operator to apply
    method_kind: str
    reason: tuple[str, ...]
    expected_information_gain: str         # "low" | "medium" | "high"
    priority: float
    is_bridge: bool = False                # True when raised by success in ANOTHER scope
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "target": self.target, "method_id": self.method_id, "method_name": self.method_name,
            "core_question": self.core_question, "method_kind": self.method_kind,
            "reason": list(self.reason),
            "expected_information_gain": self.expected_information_gain,
            "priority": self.priority, "is_bridge": self.is_bridge,
            "provenance": dict(self.provenance),
        }


def _relevant_kinds(gap_kind: str) -> tuple[tuple[str, float], ...]:
    return _METHOD_KINDS_BY_GAP.get(gap_kind, _BASE)


def _info_gain(priority: float) -> str:
    return "high" if priority >= 0.66 else ("medium" if priority >= 0.33 else "low")


def _under_addressed(deep_trials, method_id: str, gap_id: str) -> tuple[float, str, bool]:
    """How much of a gap ``method_id`` still is FOR THIS gap (scope-bound). Returns
    ``(under, why, is_bridge)``; ``under == 0`` means already worked here. Mirrors DESi's
    ``_under_addressed`` one layer deeper (per method, not per affinity)."""
    here = [t for t in deep_trials if t.method_id == method_id and t.target == gap_id]
    if any(t.result == "success" for t in here):
        return 0.0, "already succeeded on this gap", False
    real_neg = sum(t.count for t in here if t.result in _REAL_NEG)
    tech = sum(t.count for t in here if t.result == "technical_failure")
    inc = sum(t.count for t in here if t.result in ("inconclusive", "unknown"))
    elsewhere = any(t.method_id == method_id and t.target != gap_id and t.result == "success"
                    for t in deep_trials)
    if real_neg:
        return 0.15, f"tried {real_neg}x here with no benefit/harm (ineffective in scope)", False
    if tech and not inc:
        return (0.9, f"only {tech} technical failure(s) here (no methodological signal — retry)",
                False)
    if inc:
        return 0.5, f"only inconclusively tried here ({inc}x)", False
    if elsewhere:
        return 1.0, "never tried on this gap but SUCCEEDED in another scope (bridge)", True
    return 1.0, "never tried on this gap", False


def propose_operators(snapshot, *, deep_trials=(),
                      top_k_per_gap: int = 3) -> list[DeepMethodProposal]:
    """Rank deep-method operators for each open gap in a DESi ``EpistemicGapSnapshot``.

    ``deep_trials`` (Joni-side ``DeepMethodTrial`` list) supplies scope-bound deep-method outcomes;
    empty means every method is untried and the ranking is the a-priori severity x kind table.
    Returns a flat, priority-sorted list of ``DeepMethodProposal`` (<= ``top_k_per_gap`` per gap).
    Deterministic; fail-open (no conflicts -> [])."""
    conflicts = tuple(getattr(snapshot, "conflicts", ()) or ())
    prov_obj = getattr(snapshot, "provenance", None)
    prov = {"snapshot_hash": getattr(prov_obj, "snapshot_hash", ""),
            "layer9_sequence": getattr(prov_obj, "layer9_sequence", 0)}

    out: list[DeepMethodProposal] = []
    for c in conflicts:
        gap_id = getattr(c, "id", "")
        gap_kind = getattr(c, "kind", "unqualified")
        sev = _SEVERITY_W.get(getattr(c, "severity", "soft"), 0.6)
        unresolved_since = getattr(c, "unresolved_since", 0)
        per_gap: list[DeepMethodProposal] = []
        for method_kind, relevance in _relevant_kinds(gap_kind):
            for m in D.by_kind(method_kind):
                under, why, is_bridge = _under_addressed(deep_trials, m.id, gap_id)
                if under <= 0:
                    continue                                  # already worked here — not a gap
                priority = round(sev * relevance * under, 6)
                if priority <= 0:
                    continue
                reason = (
                    f"{getattr(c, 'severity', 'soft')}-severity gap {gap_id} "
                    f"(open since {unresolved_since})",
                    why,
                    f"deep method of kind '{method_kind}', relevant to a '{gap_kind}' gap",
                    f"operator (Kernfrage): {m.core_question}",
                )
                per_gap.append(DeepMethodProposal(
                    target=f"conflict:{gap_id}", method_id=m.id, method_name=m.name,
                    core_question=m.core_question, method_kind=method_kind, reason=reason,
                    expected_information_gain=_info_gain(priority), priority=priority,
                    is_bridge=is_bridge, provenance=prov))
        # keep the strongest few per gap; a bridge wins ties (more informative than a fresh try)
        per_gap.sort(key=lambda p: (-p.priority, not p.is_bridge, p.method_id))
        out.extend(per_gap[: max(0, top_k_per_gap)])

    out.sort(key=lambda p: (-p.priority, not p.is_bridge, p.target, p.method_id))
    return out


def from_core(core, *, deep_trials=(), top_k_per_gap: int = 3, core_commit: str = "unknown"):
    """Convenience: project a Layer-9 ``core`` into a DESi snapshot (via the existing read-only
    projector) and run :func:`propose_operators`. Fail-open: returns ``[]`` if the DESi schema /
    projector is unavailable, exactly like the projector's own contract."""
    try:
        from joni.autonomy import epistemic_gap_projector as _p
        snapshot = _p.project(core, core_commit=core_commit)
    except Exception:  # noqa: BLE001
        # DESi schema unavailable OR a Joni<->DESi contract skew (e.g. the projector expects a
        # newer solution_space_gap than the installed DESi exports). Fail-open, never crash.
        return []
    if snapshot is None:
        return []
    return propose_operators(snapshot, deep_trials=deep_trials, top_k_per_gap=top_k_per_gap)
