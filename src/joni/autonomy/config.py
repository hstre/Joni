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

    @property
    def forum_inbox(self) -> Path:
        # Human/forum replies for Joni to ingest - each treated as a SOURCE, never an authority.
        return self.root / "state" / "forum_inbox.json"

    @property
    def forum_outbox(self) -> Path:
        # Polite questions/posts Joni drafts for forums; posting is gated (see forum_live()).
        return self.root / "state" / "forum_outbox.json"

    @property
    def forum_approved(self) -> Path:
        # Draft ids a human approved for posting - the moderation gate the relay obeys.
        return self.root / "state" / "forum_approved.json"

    @property
    def forum_replies(self) -> Path:
        # A plain-text drop box: a human pastes forum replies here (one per line,
        # "platform | handle | text"); the loop folds them into the inbox and clears it.
        return self.root / "state" / "forum_replies.txt"

    @property
    def post_sheet(self) -> Path:
        # Human-readable "post these under your account" sheet, regenerated every cycle so a
        # human can carry Joni's drafted questions to a forum (the "you post, Joni writes" path).
        return self.root / "docs" / "to_post.md"


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


# Forums Joni may engage. He treats everyone there as a source, never an authority. Moltbook
# is an agent-only network (autonomous posting is its intended use); the human forums stay on
# the "you post, Joni writes" path until a platform is explicitly wired live.
_DEFAULT_FORUMS = ("huggingface", "hacker_news", "reddit", "lesswrong", "moltbook")


def forum_platforms() -> tuple[str, ...]:
    raw = os.getenv("JONI_FORUMS")
    if not raw:
        return _DEFAULT_FORUMS
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def forum_live() -> bool:
    """Whether Joni may actually *post* to forums. Off by default: posting is an outward,
    public, irreversible act, so it needs the operator's explicit opt-in plus per-platform
    credentials. When off, Joni still drafts (into the outbox) and still ingests replies."""
    return os.getenv("JONI_FORUM_LIVE", "0") == "1"


def forum_autopost() -> tuple[str, ...]:
    """Platforms where Joni may post WITHOUT per-post human approval - agent-only networks
    (Moltbook) where autonomous posting is the norm, not spam in a human community. Human
    forums are never here: they always wait for a human to approve/post. Still under
    forum_live() as the master switch."""
    raw = os.getenv("JONI_FORUM_AUTOPOST", "moltbook")
    return tuple(p.strip() for p in raw.split(",") if p.strip())
