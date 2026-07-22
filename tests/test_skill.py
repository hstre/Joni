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
