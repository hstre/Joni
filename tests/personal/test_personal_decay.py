"""Personal Store decay + re-confirmation (PERSONAL_STATE.md §8) — enforced, not just docs.

Ticks are DAYS for the personal store; half-lives per category (preferences 180, projects 45).
"""
import json

from joni.personal.store import PersonalStore, Status, Use, use_policy, weight


def _store(tmp_path):
    return PersonalStore(tmp_path / "personal.json", tmp_path / "protocol.jsonl")


def test_weight_decays_by_category_half_life(tmp_path):
    s = _store(tmp_path)
    s.infer("pref", "preferences", "direct feedback", tick=0)   # half-life 180
    s.infer("proj", "projects", "DESi publish", tick=0)         # half-life 45
    assert abs(weight(s.get("pref"), 0) - 1.0) < 1e-9
    assert abs(weight(s.get("pref"), 180) - 0.5) < 1e-6         # one half-life
    assert weight(s.get("proj"), 60) < weight(s.get("pref"), 60)  # projects decay faster


def test_confirm_resets_the_decay_clock(tmp_path):
    s = _store(tmp_path)
    s.infer("pref", "preferences", "x", tick=0)
    assert abs(weight(s.get("pref"), 180) - 0.5) < 1e-6
    s.confirm("pref", human_ref="op", tick=180)                 # re-freshen
    assert abs(weight(s.get("pref"), 180) - 1.0) < 1e-9


def test_age_marks_decayed_claims_outdated_and_audits(tmp_path):
    s = _store(tmp_path)
    s.infer("proj", "projects", "x", tick=0)                    # half-life 45
    assert s.age(10) == []                                      # still fresh
    aged = s.age(60)                                            # 0.5^(60/45)=0.40 < 0.5
    assert aged == ["proj"] and s.get("proj").status is Status.OUTDATED
    assert use_policy(s.get("proj")) is Use.NONE                # decayed -> unusable
    actions = [json.loads(line)["action"]
               for line in (tmp_path / "protocol.jsonl").read_text().splitlines()]
    assert actions[-1] == "outdated"


def test_due_for_reconfirm_surfaces_aging_not_fresh(tmp_path):
    s = _store(tmp_path)
    s.infer("proj", "projects", "aging", tick=0)               # 0.5^(30/45)=0.63 -> in window
    s.infer("pref", "preferences", "fresh", tick=0)            # 0.5^(30/180)=0.89 -> not yet
    due = {c.id for c in s.due_for_reconfirm(30)}
    assert due == {"proj"}
    # an outdated claim is always due until re-confirmed
    s.age(60)
    assert "proj" in {c.id for c in s.due_for_reconfirm(60)}
