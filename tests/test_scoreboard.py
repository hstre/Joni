"""Priority 1: the Consolidator scoreboard measures the OUTPUT (episodes, crystallised skills,
re-trials, promote/hold/archive, valid-tests:discarded-mappings) read-only, and persists a per-cycle
series + human panel. It never writes Layer 9 and never activates anything."""
from __future__ import annotations

import json
from types import SimpleNamespace

from joni.method_trial import episodes, scoreboard, skill


def _paths(tmp_path):
    return SimpleNamespace(
        episodes=tmp_path / "episodes.jsonl",
        skill_candidates=tmp_path / "skill_candidates.jsonl",
        scoreboard_series=tmp_path / "consolidator_series.jsonl",
        scoreboard_panel=tmp_path / "consolidator.md")


def _seed_episode(store, cycle):
    ep = episodes.ProceduralEpisode(
        context="benchmark:frozen_unit_equality_v1", action="apply_method:M-1",
        observation="delta=0.4 vs baseline", outcome=episodes.Outcome.SUCCESS,
        outcome_source="deterministic_checker", refs=("M-1",), cycle=cycle)
    episodes.record([ep], store_path=store)


def _seed_skill(store, **over):
    base = dict(method_id="M-1", trigger="t", procedure="normalise the unit",
                verification="frozen_unit_equality_v1", applicability_boundary="b",
                evidence_anchors=("M-1",), operational_reliability=1.0)
    base.update(over)
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as f:
        f.write(json.dumps(skill.SkillCandidate(**base).to_record(), ensure_ascii=False) + "\n")


def test_ratio_is_honest_at_the_edges():
    assert scoreboard._ratio(4, 0) == 4.0          # nothing discarded -> the valid count itself
    assert scoreboard._ratio(0, 0) == 0.0          # nothing measured yet
    assert scoreboard._ratio(3, 6) == 0.5


def test_compute_reads_all_five_output_metrics(tmp_path):
    p = _paths(tmp_path)
    _seed_episode(p.episodes, 1)
    _seed_episode(p.episodes, 2)
    _seed_skill(p.skill_candidates)
    ext = {
        "episodes_new": [{"x": 1}],                                    # 1 new this cycle
        "skills_proposed": [{"admissible": True, "skill_id": "skill-a"}],
        "skill_retrials": [{"skill_id": "skill-a", "verdict": "benefit"}],
        "skill_lifecycle": [{"action": "promote"}, {"action": "hold"}, {"action": "hold"}],
        "trial_funnel": {"considered": 3, "matched": 2, "trialed": 1, "discarded": 1},
    }
    rec = scoreboard.compute(None, ext, paths=p, cycle=2, run=2)
    assert rec["episodes"] == {"new": 1, "total": 2, "resolved": 2, "unknown": 0}
    assert rec["skills"]["total"] == 1 and rec["skills"]["by_status"] == {"probationary": 1}
    assert rec["skills"]["new_admissible"] == 1
    assert rec["retrials_this_cycle"] == 1
    assert rec["recommendations"] == {"promote": 1, "hold": 2, "archive": 0}
    assert rec["window"]["valid_tests"] == 1 and rec["window"]["discarded_mappings"] == 1
    assert rec["window"]["valid_to_discarded"] == 1.0


def test_window_totals_accumulate_over_prior_rows(tmp_path):
    p = _paths(tmp_path)
    # a prior scoreboard row already recorded 2 valid / 4 discarded
    p.scoreboard_series.write_text(json.dumps(
        {"trial_funnel": {"trialed": 2, "discarded": 4, "matched": 6}}) + "\n")
    ext = {"trial_funnel": {"considered": 1, "matched": 1, "trialed": 1, "discarded": 0}}
    rec = scoreboard.compute(None, ext, paths=p, cycle=5, run=5)
    assert rec["window"]["valid_tests"] == 3 and rec["window"]["discarded_mappings"] == 4
    assert rec["window"]["valid_to_discarded"] == 0.75


def test_run_scoreboard_persists_series_and_panel(tmp_path):
    p = _paths(tmp_path)
    _seed_episode(p.episodes, 1)
    proto = SimpleNamespace(record=lambda *a, **k: None)
    ext = {"episodes_new": [{"x": 1}], "trial_funnel": {"trialed": 1, "discarded": 0, "matched": 1}}
    rec = scoreboard.run_scoreboard(None, ext, proto, 1, run=1, paths=p)
    assert rec["episodes"]["total"] == 1
    assert p.scoreboard_series.exists() and p.scoreboard_series.read_text().strip()
    assert "Consolidator-Scoreboard" in p.scoreboard_panel.read_text()


def test_run_scoreboard_is_fail_open(tmp_path):
    # a broken paths object must not raise - the scoreboard can never break the loop
    proto = SimpleNamespace(record=lambda *a, **k: None)
    assert scoreboard.run_scoreboard(None, {}, proto, 1, run=1, paths=SimpleNamespace()) == {}


def test_empty_cycle_is_all_zeros(tmp_path):
    p = _paths(tmp_path)
    rec = scoreboard.compute(None, {}, paths=p, cycle=0, run=0)
    assert rec["episodes"]["total"] == 0 and rec["skills"]["total"] == 0
    assert rec["recommendations"] == {"promote": 0, "hold": 0, "archive": 0}
    assert rec["window"]["valid_to_discarded"] == 0.0
