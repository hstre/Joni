"""Budget - the hard weekly cap on paid API spend.

Joni is frugal by construction: most work is deterministic and free. When a task does
need a model, the frugal executor (frugal.py) tries the cheapest first and only
escalates if DESi measures the cheap answer inadequate. This module is the wallet: a
persisted weekly ledger that refuses any spend over the cap, and paces per-run spend so
one run cannot burn the whole week.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


@dataclass
class Budget:
    week_start: str
    spent_eur: float
    runs: int
    cap_eur: float

    def remaining(self) -> float:
        return round(max(0.0, self.cap_eur - self.spent_eur), 6)

    def per_run_allowance(self, runs_per_week: int) -> float:
        """Even pacing: don't let one run outspend its fair share of the week."""
        runs_left = max(1, runs_per_week - self.runs)
        return round(min(self.remaining(), self.remaining() / runs_left + 1e-9), 6)

    def can_spend(self, amount: float, *, runs_per_week: int) -> bool:
        return amount <= self.remaining() and amount <= self.per_run_allowance(runs_per_week)

    def charge(self, amount: float) -> None:
        self.spent_eur = round(self.spent_eur + amount, 6)


def _now() -> datetime:
    return datetime.now(UTC)


def load(path: Path, *, cap_eur: float) -> Budget:
    if path.exists():
        d = json.loads(path.read_text(encoding="utf-8"))
        b = Budget(week_start=d["week_start"], spent_eur=d["spent_eur"],
                   runs=d["runs"], cap_eur=cap_eur)
    else:
        b = Budget(week_start=_now().isoformat(), spent_eur=0.0, runs=0, cap_eur=cap_eur)
    # Roll the week over if the window has passed.
    start = datetime.fromisoformat(b.week_start)
    if _now() - start > timedelta(days=7):
        b = Budget(week_start=_now().isoformat(), spent_eur=0.0, runs=0, cap_eur=cap_eur)
    return b


def save(budget: Budget, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(budget), indent=2) + "\n", encoding="utf-8")
