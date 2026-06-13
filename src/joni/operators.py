"""Operators - the only ways the identity may change.

Every apparently personal move ("I started a project", "I changed my mind", "I now
prefer X") is exactly one of these deterministic operators applied to Layer 9, and
exactly one append-only ledger event. None of them is an LLM call.

``revise_opinion`` is the showcase. The user's worked example -

    "I have since abandoned this idea."
        previous_claim: C-184  old_status: active  new_status: rejected
        trigger: contradictory_evidence  operator: conflict_resolution
        reviewed_by: granite-micro  ledger_event: L9-7741

- is produced here, field for field, with no narrative magic.
"""

from __future__ import annotations

from .models import (
    Claim,
    ClaimStatus,
    Conflict,
    Goal,
    GoalStatus,
    Horizon,
    LedgerEvent,
    MemoryEpisode,
    Operator,
    Preference,
    Project,
    ProjectStatus,
    Transition,
    Trigger,
)
from .state import Layer9

# --------------------------------------------------------------------------- #
# Claims and opinion change
# --------------------------------------------------------------------------- #


def assert_claim(
    state: Layer9, text: str, topic: str, *, support: float = 0.5,
    status: ClaimStatus = ClaimStatus.TENTATIVE, reviewed_by: str = "deterministic",
    trigger: Trigger = Trigger.USER_INPUT, cost: float = 0.0,
) -> Claim:
    """Bring a new belief into being, audited from birth."""
    claim = Claim(
        id=state.next_id("C"), text=text, topic=topic, status=status,
        support=round(min(1.0, max(0.0, support)), 4),
        created_tick=state.tick, last_changed_tick=state.tick,
    )
    state.claims[claim.id] = claim
    event = state.record(
        Operator.CLAIM_ASSERT, f"assert {claim.id} [{status}] on '{topic}': {text}",
        refs=(claim.id,), reviewed_by=reviewed_by, cost=cost,
    )
    # The birth of a belief is itself a recallable episode (continuity).
    _remember(state, "learned", f"Came to hold {claim.id}: {text}", (claim.id, event.id))
    return claim


def revise_opinion(
    state: Layer9, claim_id: str, new_status: ClaimStatus, *, trigger: Trigger,
    operator: Operator = Operator.OPINION_REVISE, reviewed_by: str = "deterministic",
    cost: float = 0.0,
) -> tuple[Transition, LedgerEvent]:
    """Change a belief's status - the audited unit of 'changing one's mind'."""
    claim = state.claims[claim_id]
    old = claim.status
    if old is new_status:
        # No-op revisions are not recorded - the ledger stays meaningful.
        raise ValueError(f"{claim_id} is already {new_status}")
    event = state.record(
        operator, f"{claim_id} {old}->{new_status} ({trigger})",
        refs=(claim_id,), reviewed_by=reviewed_by, cost=cost,
    )
    transition = Transition(
        from_status=old, to_status=new_status, trigger=trigger, operator=operator,
        tick=state.tick, reviewed_by=reviewed_by, ledger_id=event.id,
    )
    claim.history.append(transition)
    claim.status = new_status
    claim.last_changed_tick = state.tick
    _remember(
        state, "changed_mind",
        f"Revised {claim_id} from {old} to {new_status} due to {trigger}",
        (claim_id, event.id),
    )
    return transition, event


def resolve_conflict(
    state: Layer9, conflict_id: str, *, reject: str, reviewed_by: str = "deterministic",
    cost: float = 0.0,
) -> tuple[Transition, LedgerEvent]:
    """Settle a contradiction by rejecting the weaker claim - a justified revision.

    This is the operator behind "I have since abandoned this idea": the rejected
    claim's transition names trigger=contradictory_evidence and
    operator=conflict_resolution, signed off by ``reviewed_by``.
    """
    conflict = state.conflicts[conflict_id]
    transition, event = revise_opinion(
        state, reject, ClaimStatus.REJECTED, trigger=Trigger.CONTRADICTORY_EVIDENCE,
        operator=Operator.CONFLICT_RESOLUTION, reviewed_by=reviewed_by, cost=cost,
    )
    conflict.resolved = True
    return transition, event


# --------------------------------------------------------------------------- #
# Goals
# --------------------------------------------------------------------------- #


def adopt_goal(
    state: Layer9, text: str, *, horizon: Horizon = Horizon.LONG, priority: float = 0.5,
    reviewed_by: str = "deterministic",
) -> Goal:
    goal = Goal(
        id=state.next_id("G"), text=text, horizon=horizon,
        priority=round(min(1.0, max(0.0, priority)), 4), created_tick=state.tick,
    )
    state.goals[goal.id] = goal
    state.record(Operator.GOAL_ADOPT, f"adopt {goal.id} [{horizon}]: {text}",
                 refs=(goal.id,), reviewed_by=reviewed_by)
    return goal


def advance_goal(
    state: Layer9, goal_id: str, *, by: float, reviewed_by: str = "deterministic"
) -> Goal:
    goal = state.goals[goal_id]
    goal.progress = round(min(1.0, max(0.0, goal.progress + by)), 4)
    summary = f"advance {goal_id} to {goal.progress:.2f}"
    if goal.progress >= 1.0:
        goal.status = GoalStatus.ACHIEVED
        summary += " (achieved)"
        _remember(state, "achieved_goal", f"Reached {goal_id}: {goal.text}", (goal_id,))
    state.record(Operator.GOAL_ADVANCE, summary, refs=(goal_id,), reviewed_by=reviewed_by)
    return goal


def drop_goal(state: Layer9, goal_id: str, *, reviewed_by: str = "deterministic") -> Goal:
    goal = state.goals[goal_id]
    goal.status = GoalStatus.ABANDONED
    state.record(Operator.GOAL_DROP, f"drop {goal_id}: {goal.text}", refs=(goal_id,),
                 reviewed_by=reviewed_by)
    return goal


# --------------------------------------------------------------------------- #
# Preferences and projects
# --------------------------------------------------------------------------- #


def form_preference(
    state: Layer9, subject: str, stance: str, *, strength: float = 0.5,
    formed_from: tuple[str, ...] = (), reviewed_by: str = "deterministic",
) -> Preference:
    pref = Preference(
        id=state.next_id("PR"), subject=subject, stance=stance,
        strength=round(min(1.0, max(0.0, strength)), 4), formed_from=formed_from,
        created_tick=state.tick,
    )
    state.preferences[pref.id] = pref
    state.record(Operator.PREFERENCE_FORM, f"form {pref.id}: {stance} {subject}",
                 refs=(pref.id, *formed_from), reviewed_by=reviewed_by)
    return pref


def start_project(
    state: Layer9, title: str, topic: str, *, reviewed_by: str = "deterministic",
) -> Project:
    project = Project(id=state.next_id("P"), title=title, topic=topic, created_tick=state.tick)
    state.projects[project.id] = project
    event = state.record(Operator.PROJECT_START, f"start {project.id}: {title}",
                         refs=(project.id,), reviewed_by=reviewed_by)
    _remember(state, "started_project", f"Started {project.id}: {title}",
              (project.id, event.id))
    return project


def abandon_project(
    state: Layer9, project_id: str, *, reviewed_by: str = "deterministic"
) -> Project:
    project = state.projects[project_id]
    project.status = ProjectStatus.ABANDONED
    event = state.record(Operator.PROJECT_ABANDON, f"abandon {project_id}: {project.title}",
                         refs=(project_id,), reviewed_by=reviewed_by)
    _remember(state, "abandoned_project", f"Abandoned {project_id}: {project.title}",
              (project_id, event.id))
    return project


# --------------------------------------------------------------------------- #
# Memory (internal helper + explicit operator)
# --------------------------------------------------------------------------- #


def _remember(state: Layer9, kind: str, summary: str, refs: tuple[str, ...]) -> MemoryEpisode:
    """Append an autobiographical episode. Used by operators that constitute one."""
    episode = MemoryEpisode(
        id=state.next_id("M"), tick=state.tick, kind=kind, summary=summary, refs=refs
    )
    state.memory.append(episode)
    return episode


def record_memory(
    state: Layer9, kind: str, summary: str, *, refs: tuple[str, ...] = (),
    reviewed_by: str = "deterministic",
) -> MemoryEpisode:
    """Explicitly record an episode and audit it (the MEMORY_RECORD operator)."""
    episode = _remember(state, kind, summary, refs)
    state.record(Operator.MEMORY_RECORD, f"record {episode.id} [{kind}]: {summary}",
                 refs=(episode.id, *refs), reviewed_by=reviewed_by)
    return episode


def open_conflict(state: Layer9, claim_a: str, claim_b: str, kind: str) -> Conflict:
    """Register a detected contradiction (see conflict.py for detection)."""
    conflict = Conflict(
        id=state.next_id("X"), claim_a=claim_a, claim_b=claim_b, kind=kind, tick=state.tick
    )
    state.conflicts[conflict.id] = conflict
    return conflict
