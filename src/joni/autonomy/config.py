"""Where the autonomous Joni keeps its things, and how it is dialled.

Everything autonomous writes lives under the governance allowlist (state/, protocol/,
docs/) so the protected core is never touched. Paths and dials are env-overridable so
the GitHub Actions workflow and local runs agree.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(os.getenv("JONI_AUTONOMY_ROOT", ".")).resolve()


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def state(self) -> Path:
        return self.root / "state" / "joni_state.json"     # legacy (migration source)

    @property
    def core(self) -> Path:
        return self.root / "state" / "layer9.json"          # the authoritative core

    @property
    def budget(self) -> Path:
        return self.root / "state" / "budget.json"

    @property
    def extensions(self) -> Path:
        return self.root / "state" / "extensions.json"

    @property
    def window(self) -> Path:
        return self.root / "state" / "run_window.json"

    @property
    def asks_new(self) -> Path:
        # Asks raised this run, for the workflow to file as GitHub issues.
        return self.root / "state" / "asks_new.json"

    @property
    def commissions_new(self) -> Path:
        # Aufträge an Claude raised this run, for the workflow to file as GitHub issues.
        return self.root / "state" / "commissions_new.json"

    @property
    def protocol(self) -> Path:
        return self.root / "protocol" / "protocol.jsonl"

    @property
    def docs_index(self) -> Path:
        return self.root / "docs" / "index.html"

    @property
    def docs_data(self) -> Path:
        return self.root / "docs" / "data.json"

    @property
    def docs_layer9(self) -> Path:
        return self.root / "docs" / "layer9.html"

    @property
    def pdf_inbox(self) -> Path:
        return self.root / "inbox"               # drop PDFs here for Joni to read

    @property
    def pdf_urls(self) -> Path:
        return self.root / "state" / "pdf_urls.json"   # a queue of direct PDF urls (incl. SSRN)


def paths() -> Paths:
    return Paths(repo_root())


# Dials (env-overridable; the workflow sets these).
def weekly_budget_eur() -> float:
    return float(os.getenv("JONI_WEEKLY_BUDGET_EUR", "20"))


def runtime_days() -> int:
    return int(os.getenv("JONI_RUNTIME_DAYS", "7"))


def runs_per_week() -> int:
    # Used to pace per-run budget; default assumes hourly over a week.
    return int(os.getenv("JONI_RUNS_PER_WEEK", str(24 * 7)))


def online() -> bool:
    return os.getenv("JONI_ONLINE") == "1"


def read_pdfs() -> bool:
    return os.getenv("JONI_READ_PDFS", "1") != "0"
