from datetime import UTC, datetime, timedelta

from joni.autonomy import budget


def test_fresh_budget_and_charge(tmp_path):
    b = budget.load(tmp_path / "b.json", cap_eur=20)
    assert b.remaining() == 20
    b.charge(0.5)
    assert b.remaining() == 19.5


def test_cap_blocks_overspend(tmp_path):
    b = budget.load(tmp_path / "b.json", cap_eur=1)
    assert not b.can_spend(2.0, runs_per_week=10)
    assert b.can_spend(0.05, runs_per_week=10)


def test_per_run_pacing_limits_a_single_run(tmp_path):
    b = budget.load(tmp_path / "b.json", cap_eur=20)
    # With 168 runs, a single run's fair share is well under the full €20.
    assert b.per_run_allowance(runs_per_week=168) < 1.0
    assert not b.can_spend(5.0, runs_per_week=168)


def test_week_rollover_resets_spend(tmp_path):
    p = tmp_path / "b.json"
    b = budget.load(p, cap_eur=20)
    b.charge(10)
    b.week_start = (datetime.now(UTC) - timedelta(days=8)).isoformat()
    budget.save(b, p)
    rolled = budget.load(p, cap_eur=20)
    assert rolled.spent_eur == 0.0
    assert rolled.runs == 0


def test_save_load_roundtrip(tmp_path):
    p = tmp_path / "b.json"
    b = budget.load(p, cap_eur=20)
    b.charge(1.25)
    b.runs = 3
    budget.save(b, p)
    again = budget.load(p, cap_eur=20)
    assert again.spent_eur == 1.25
    assert again.runs == 3
