"""S1: the SkillCandidate schema is strictly validated, deterministically identified, checked
against the core (real refs only), proposed append-only - never auto-active, never a claim."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from joni.method_trial import skill


def _candidate(**over):
    base = dict(method_id="M-1", trigger="two measurement strings", procedure="normalise the unit",
                verification="frozen_unit_equality_v1", applicability_boundary="not for free text",
                evidence_anchors=("T-1", "T-2"), operational_reliability=0.8)
    base.update(over)
    return skill.SkillCandidate(**base)


def _cs(ids):
    core = SimpleNamespace(get=lambda oid: object() if oid in set(ids) else None)
    return SimpleNamespace(core=core)


def test_a_valid_candidate_round_trips_and_ids_deterministically():
    c = _candidate()
    assert c.skill_id().startswith("skill-") and len(c.skill_id()) == 22
    assert skill.SkillCandidate.from_record(c.to_record()).skill_id() == c.skill_id()
    assert c.status is skill.SkillStatus.PROBATIONARY


def test_strict_validation_rejects_bad_fields():
    with pytest.raises(ValueError):
        _candidate(method_id="")                       # empty required str
    with pytest.raises(ValueError):
        _candidate(procedure="  ")                     # blank
    with pytest.raises(ValueError):
        _candidate(evidence_anchors=())                # un-anchored skill
    with pytest.raises(ValueError):
        _candidate(operational_reliability=1.5)        # out of [0,1]
    with pytest.raises(ValueError):
        _candidate(operational_reliability=True)       # bool is not a reliability
    with pytest.raises(ValueError):
        _candidate(version=0)                           # version >= 1


def test_from_record_rejects_unknown_fields():
    rec = _candidate().to_record()
    rec["surprise"] = "nope"
    with pytest.raises(ValueError):
        skill.SkillCandidate.from_record(rec)


def test_gate_admits_only_real_references():
    c = _candidate()
    assert skill.validate_against_core(c, _cs({"M-1", "T-1", "T-2"})).admissible is True
    v = skill.validate_against_core(c, _cs({"T-1", "T-2"}))          # method missing
    assert v.admissible is False and any("method_id" in r for r in v.reasons)
    v2 = skill.validate_against_core(c, _cs({"M-1", "T-1"}))         # an anchor missing
    assert v2.admissible is False and any("evidence anchors" in r for r in v2.reasons)


def test_a_non_probationary_proposal_is_inadmissible():
    c = _candidate(status=skill.SkillStatus.ACTIVE)      # never propose it already active
    v = skill.validate_against_core(c, _cs({"M-1", "T-1", "T-2"}))
    assert v.admissible is False


def _trial_method(**over):
    base = dict(id="M-1", name="unit-lens", summary="normalise the unit before comparing",
                success_count=1, trial_count=1)
    base.update(over)
    return SimpleNamespace(**base)


_BENEFIT = {"passed": True, "delta": 0.4, "task_set": "frozen_unit_equality_v1"}


def test_crystallize_builds_a_probationary_benefit_skill():
    c = skill.crystallize(_trial_method(), verification="frozen_unit_equality_v1",
                          task_desc="same/different for two measurement strings",
                          affinity="normalisation", trial_result=_BENEFIT,
                          evidence_anchors=("M-1",))
    assert c is not None
    assert c.status is skill.SkillStatus.PROBATIONARY           # never crystallised as active
    assert c.verification == "frozen_unit_equality_v1"          # carries its OWN verification
    assert c.procedure == "normalise the unit before comparing"
    assert c.evidence_anchors == ("M-1",)
    assert 0.0 <= c.operational_reliability <= 1.0


def test_crystallize_is_none_unless_the_trial_passed():
    m = _trial_method()
    assert skill.crystallize(m, verification="v", task_desc="t", affinity="a",  # no_benefit/harmful
                             trial_result={"passed": False, "delta": 0.0},
                             evidence_anchors=("M-1",)) is None
    assert skill.crystallize(m, verification="v", task_desc="t", affinity="a",
                             trial_result={}, evidence_anchors=("M-1",)) is None


def test_crystallize_reliability_is_the_measured_success_rate():
    c = skill.crystallize(_trial_method(success_count=3, trial_count=4), verification="v",
                          task_desc="t", affinity="a", trial_result=_BENEFIT,
                          evidence_anchors=("M-1",))
    assert c.operational_reliability == 0.75                    # V_operational, measured not truth


def test_crystallize_fails_safe_on_bad_pieces():
    # no evidence anchors -> not a valid skill -> None, never raises
    assert skill.crystallize(_trial_method(), verification="v", task_desc="t", affinity="a",
                             trial_result=_BENEFIT, evidence_anchors=()) is None
    # a text-less method cannot crystallise
    assert skill.crystallize(SimpleNamespace(id="M-9", name="", summary=""), verification="v",
                             task_desc="t", affinity="a", trial_result=_BENEFIT,
                             evidence_anchors=("M-9",)) is None


def test_propose_appends_only_when_admissible(tmp_path):
    store = tmp_path / "skill_candidates.jsonl"
    ok = skill.propose(_candidate(), _cs({"M-1", "T-1", "T-2"}), store_path=store)
    assert ok["admissible"] is True and ok["recorded"] is True
    bad = skill.propose(_candidate(method_id="M-404"), _cs({"M-1", "T-1", "T-2"}), store_path=store)
    assert bad["admissible"] is False and bad["recorded"] is False   # unreal method not recorded
    # append-only: a second admissible proposal adds a line, never rewrites
    skill.propose(_candidate(version=2), _cs({"M-1", "T-1", "T-2"}), store_path=store)
    lines = [ln for ln in store.read_text().splitlines() if ln.strip()]
    assert len(lines) == 2


# ---- S4: the lifecycle assessor (deterministic, read-only, human-gated) --------------------------

def _lifecycle_cs(*, success_count, trial_count):
    method = SimpleNamespace(success_count=success_count, trial_count=trial_count)
    return SimpleNamespace(core=SimpleNamespace(get=lambda oid: method if oid == "M-1" else None))


def test_assess_promotes_after_repeated_passes():
    a = skill.assess_lifecycle(_candidate(), _lifecycle_cs(success_count=4, trial_count=5))
    assert a.action is skill.LifecycleAction.PROMOTE        # a RECOMMENDATION - not a state write
    assert a.target_status is skill.SkillStatus.ACTIVE and a.reliability == 0.8


def test_assess_holds_while_maturing():
    assert skill.assess_lifecycle(_candidate(), _lifecycle_cs(success_count=1, trial_count=1)
                                  ).action is skill.LifecycleAction.HOLD    # 1 pass < min_passes
    assert skill.assess_lifecycle(_candidate(), _lifecycle_cs(success_count=2, trial_count=3)
                                  ).action is skill.LifecycleAction.HOLD    # 0.67 < promote floor


def test_assess_archives_a_measured_failure():
    a = skill.assess_lifecycle(_candidate(), _lifecycle_cs(success_count=1, trial_count=4))
    assert a.action is skill.LifecycleAction.ARCHIVE       # 0.25 <= floor after >= 3 trials
    assert a.target_status is skill.SkillStatus.ARCHIVED


def test_assess_records_the_evidence_it_rests_on():
    a = skill.assess_lifecycle(_candidate(), _lifecycle_cs(success_count=3, trial_count=3))
    assert a.passes == 3 and a.trials == 3                 # shows its work - no unbacked assertion
    rec = a.to_record()
    assert rec["action"] == "promote" and rec["reliability"] == 1.0


def test_assess_holds_when_method_absent_or_already_archived():
    absent = SimpleNamespace(core=SimpleNamespace(get=lambda oid: None))
    assert skill.assess_lifecycle(_candidate(), absent).action is skill.LifecycleAction.HOLD
    arch = _candidate(status=skill.SkillStatus.ARCHIVED)
    assert skill.assess_lifecycle(arch, _lifecycle_cs(success_count=4, trial_count=5)
                                  ).action is skill.LifecycleAction.HOLD
