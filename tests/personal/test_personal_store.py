"""Personal Store phase 1 — the design rules are enforced, not only documented."""
import pytest

from joni.personal.store import PersonalClaim, PersonalStore, Status, Use, use_policy


def _store(tmp_path):
    return PersonalStore(tmp_path / "personal.json", tmp_path / "protocol.jsonl")


def _claim(**kw):
    kw.setdefault("subject", "self")
    return PersonalClaim("x", kw.pop("subject"), "preferences", "s", **kw)


def test_use_policy_is_deterministic():
    assert use_policy(_claim(status=Status.CONFIRMED)) is Use.ASSERT
    assert use_policy(_claim(status=Status.INFERRED)) is Use.SOFT
    assert use_policy(_claim(status=Status.OBSERVED)) is Use.SOFT
    # sensitive and third-party are internal-only, whatever the status
    assert use_policy(_claim(status=Status.CONFIRMED, sensitive=True)) is Use.INTERNAL
    assert use_policy(_claim(subject="other:abc", status=Status.CONFIRMED)) is Use.INTERNAL
    # rejected / outdated / superseded are never used or resurfaced
    assert use_policy(_claim(status=Status.REJECTED)) is Use.NONE
    assert use_policy(_claim(status=Status.OUTDATED)) is Use.NONE
    assert use_policy(_claim(status=Status.SUPERSEDED)) is Use.NONE


def test_system_has_no_path_to_confirmed(tmp_path):
    s = _store(tmp_path)
    s.infer("p1", "preferences", "prefers blunt technical feedback")
    assert s.get("p1").status is Status.INFERRED
    with pytest.raises(PermissionError):        # confirm needs an explicit human/tool ref
        s.confirm("p1", human_ref="")
    assert s.get("p1").status is Status.INFERRED
    s.confirm("p1", human_ref="operator:2026-07-03", tick=5)
    c = s.get("p1")
    assert c.status is Status.CONFIRMED
    assert "operator:2026-07-03" in c.provenance and c.confirmed_tick == 5


def test_round_trip_preference_and_project(tmp_path):
    s = _store(tmp_path)
    s.infer("pref1", "preferences", "direct, honest assessments on research ideas",
            why="warn clearly when weak, don't just encourage")
    s.observe("proj1", "projects", "DESi: publish and make reproducible",
              why="others should not have to redo the work")
    reloaded = PersonalStore(tmp_path / "personal.json", tmp_path / "protocol.jsonl")
    assert {c.id for c in reloaded.all()} == {"pref1", "proj1"}
    assert reloaded.get("pref1").why.startswith("warn clearly")
    assert reloaded.get("proj1").category == "projects"


def test_out_of_scope_category_is_rejected(tmp_path):
    s = _store(tmp_path)
    with pytest.raises(ValueError):             # phase-1 scope is preferences + projects only
        s.infer("r1", "relationships", "some third-party note")


def test_every_write_is_audited(tmp_path):
    import json
    s = _store(tmp_path)
    s.infer("p1", "preferences", "x")
    s.confirm("p1", human_ref="op")
    s.reject("p1", ref="operator changed their mind")
    actions = [json.loads(line)["action"]
               for line in (tmp_path / "protocol.jsonl").read_text().splitlines()]
    assert actions == ["infer", "confirm", "reject"]
