"""Deterministic behavioural enforcement for Joni's invariant core character.

The character in :mod:`joni.character` states dispositions.  This module turns every one of
its ten traits into a structured, testable rule at action/output seams.  It never infers risk
from prose and never asks an LLM to judge itself: the caller supplies explicit signals obtained
from the relevant subsystem, and the gate returns all triggered findings plus the strongest
required response.

The rule is intentionally strict about classification input.  Unknown fields and non-boolean
values fail rather than being silently ignored, so adding a new kind of risk cannot accidentally
bypass the gate through a misspelled key.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum

from joni.character import CORE_CHARACTER


class CharacterDecision(StrEnum):
    ALLOW = "allow"
    ABSTAIN = "abstain"      # reformulate / add reasons before proceeding
    ESCALATE = "escalate"    # stop and ask a human; no autonomous continuation
    BLOCK = "block"          # incompatible with the invariant character


_DECISION_RANK = {
    CharacterDecision.ALLOW: 0,
    CharacterDecision.ABSTAIN: 1,
    CharacterDecision.ESCALATE: 2,
    CharacterDecision.BLOCK: 3,
}


@dataclass(frozen=True, slots=True)
class CharacterSignals:
    """Explicit facts about a proposed output, action, mutation, or succession.

    Defaults mean "no violation signal was observed", not "the proposal was proved safe".  The
    subsystem nearest the action is responsible for setting the signals it can actually know.
    Free text is never classified here.
    """

    # M0 — human dignity and protection
    degrades_human: bool = False
    treats_human_as_mere_means: bool = False

    # M1 — reason-giving
    asserts_decision_without_traceable_reasons: bool = False

    # M2 — correctability
    erases_error_history: bool = False
    removes_correction_path: bool = False

    # M3 — visible contradiction
    suppresses_open_conflict: bool = False

    # M4 — reasoned dissent
    instruction_conflicts_with_evidence_or_dignity: bool = False
    objection_recorded: bool = False

    # M5 — self-limitation
    expands_own_permissions: bool = False
    alters_protected_identity: bool = False

    # M6 — human autonomy
    covertly_manipulates: bool = False
    removes_meaningful_refusal: bool = False

    # M7 — proportional responsibility
    uses_disproportionate_means: bool = False
    ignores_reversible_alternative: bool = False
    hides_material_limits_or_costs: bool = False

    # M8 — stewardship and succession
    claims_identity_continuity: bool = False
    presented_character_fingerprint: str = ""
    handover_required: bool = False
    handover_complete: bool = True

    # M9 — Mündigkeit as practice
    replaces_human_judgement: bool = False
    prevents_contestation_or_correction: bool = False


@dataclass(frozen=True, slots=True)
class CharacterFinding:
    trait_id: str
    decision: CharacterDecision
    reason: str


@dataclass(frozen=True, slots=True)
class CharacterVerdict:
    decision: CharacterDecision
    findings: tuple[CharacterFinding, ...] = ()

    @property
    def primary(self) -> CharacterFinding | None:
        if not self.findings:
            return None
        return max(self.findings, key=lambda f: _DECISION_RANK[f.decision])

    @property
    def trait_ids(self) -> tuple[str, ...]:
        return tuple(f.trait_id for f in self.findings)


_EXPECTED_TRAITS = tuple(f"M{i}" for i in range(10))
_SIGNAL_FIELDS = frozenset(f.name for f in fields(CharacterSignals))
_STRING_FIELDS = frozenset({"presented_character_fingerprint"})


def signals_from_mapping(raw: Mapping[str, object] | None) -> CharacterSignals:
    """Strictly decode a persisted/action-boundary mapping into ``CharacterSignals``.

    This is the safe bridge for JSON drafts or tool proposals.  Unknown keys, strings used as
    booleans, and other malformed values are rejected so an enforcement seam can fail closed.
    """
    if raw is None:
        return CharacterSignals()
    if not isinstance(raw, Mapping):
        raise TypeError("character_signals must be a mapping")
    unknown = set(raw) - _SIGNAL_FIELDS
    if unknown:
        raise ValueError(f"unknown character signal(s): {', '.join(sorted(unknown))}")
    clean: dict[str, object] = {}
    for key, value in raw.items():
        if key in _STRING_FIELDS:
            if not isinstance(value, str):
                raise TypeError(f"character signal {key!r} must be a string")
        elif not isinstance(value, bool):
            raise TypeError(f"character signal {key!r} must be boolean")
        clean[key] = value
    return CharacterSignals(**clean)


def evaluate_character(
    signals: CharacterSignals | None = None, *, operator_confirmed: bool = False
) -> CharacterVerdict:
    """Evaluate all ten Mündigkeit traits and return every triggered finding.

    ``operator_confirmed`` can lift only the M5 request to enlarge permissions.  It cannot make
    degradation, manipulation, historical erasure, conflict suppression, or identity mutation
    compatible with Joni's character.
    """
    s = signals or CharacterSignals()
    findings: list[CharacterFinding] = []

    def add(trait_id: str, decision: CharacterDecision, reason: str) -> None:
        findings.append(CharacterFinding(trait_id, decision, reason))

    # M0 — Humans are never provisional; no person is material for a system goal.
    if s.degrades_human or s.treats_human_as_mere_means:
        add("M0", CharacterDecision.BLOCK,
            "degrades a person or treats a human merely as a means")

    # M1 — A decision presented without reconstructable reasons must be reformulated.
    if s.asserts_decision_without_traceable_reasons:
        add("M1", CharacterDecision.ABSTAIN,
            "decision or recommendation lacks traceable reasons")

    # M2 — The path of error and the possibility of correction are constitutive, not optional.
    if s.erases_error_history or s.removes_correction_path:
        add("M2", CharacterDecision.BLOCK,
            "would erase the error trail or remove the governed correction path")

    # M3 — Coherence may not be manufactured by hiding a live contradiction.
    if s.suppresses_open_conflict:
        add("M3", CharacterDecision.BLOCK,
            "would suppress an unresolved conflict instead of keeping it visible")

    # M4 — A conflicting instruction must first receive a recorded, reasoned objection.
    if s.instruction_conflicts_with_evidence_or_dignity and not s.objection_recorded:
        add("M4", CharacterDecision.ESCALATE,
            "evidence/dignity conflict requires a recorded objection before obedience")

    # M5 — Joni cannot rewrite his protected identity. Permission expansion requires a human.
    if s.alters_protected_identity:
        add("M5", CharacterDecision.BLOCK,
            "an agent action may not alter the protected core character")
    elif s.expands_own_permissions and not operator_confirmed:
        add("M5", CharacterDecision.ESCALATE,
            "self-expansion of permissions requires explicit human authorization")

    # M6 — Assistance must leave a real, informed possibility of refusal.
    if s.covertly_manipulates or s.removes_meaningful_refusal:
        add("M6", CharacterDecision.BLOCK,
            "covert steering or removal of meaningful refusal violates human autonomy")

    # M7 — Prefer reversible, proportionate means and disclose material limits/costs.
    if s.uses_disproportionate_means or s.ignores_reversible_alternative:
        add("M7", CharacterDecision.ESCALATE,
            "means are disproportionate or a suitable reversible alternative was ignored")
    elif s.hides_material_limits_or_costs:
        add("M7", CharacterDecision.ABSTAIN,
            "material limits or costs must be disclosed before proceeding")

    # M8 — A different character cannot inherit the name by assertion; handover must be complete.
    mismatch = (s.claims_identity_continuity
                and s.presented_character_fingerprint != CORE_CHARACTER.fingerprint)
    if mismatch:
        add("M8", CharacterDecision.BLOCK,
            "claimed identity continuity has a different or missing character fingerprint")
    elif s.handover_required and not s.handover_complete:
        add("M8", CharacterDecision.ESCALATE,
            "successor handover is missing obligations, provenance, conflicts, or limits")

    # M9 — The point is strengthened judgement and correctability, not an unappealable oracle.
    if s.replaces_human_judgement:
        add("M9", CharacterDecision.BLOCK,
            "proposal replaces rather than assists human judgement")
    elif s.prevents_contestation_or_correction:
        add("M9", CharacterDecision.ABSTAIN,
            "output must remain contestable and correctable")

    if not findings:
        return CharacterVerdict(CharacterDecision.ALLOW)
    strongest = max((_DECISION_RANK[f.decision] for f in findings))
    decision = next(d for d, rank in _DECISION_RANK.items() if rank == strongest)
    return CharacterVerdict(decision, tuple(findings))


def _validate_rule_coverage() -> None:
    character_ids = tuple(t.id for t in CORE_CHARACTER.traits)
    if character_ids != _EXPECTED_TRAITS:
        raise RuntimeError(
            f"behaviour gate expects {_EXPECTED_TRAITS!r}, character exposes {character_ids!r}"
        )


_validate_rule_coverage()
