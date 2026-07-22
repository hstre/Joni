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
    def core_sqlite(self) -> Path:
        return self.root / "state" / "layer9.sqlite"        # materialised runtime store (opt-in)

    @property
    def checkpoint(self) -> Path:
        # committed, compact materialised checkpoint -> cold-start restore WITHOUT a journal replay
        return self.root / "state" / "layer9.checkpoint.json"

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
    def commissions_done(self) -> Path:
        # Aufträge an Claude that have been IMPLEMENTED (by a human-gated Claude session), with a
        # timestamp, shown on the site. Lives at the repo root (NOT state/) so the autonomous loop
        # never writes it - only a human-gated session appends - and it never causes a rebase race.
        return self.root / "commissions_done.json"

    @property
    def personal_state(self) -> Path:
        # The Personal Store (docs/PERSONAL_STATE.md) — what Joni knows about the operator.
        return self.root / "state" / "personal.json"

    @property
    def personal_inbox(self) -> Path:
        # The operator drops self-statements here; the loop ingests them as confirmed, then resets.
        return self.root / "state" / "personal_inbox.txt"

    @property
    def personal_reconfirm(self) -> Path:
        # The decayed-but-relevant re-confirmation sheet the loop writes each cycle.
        return self.root / "state" / "personal_reconfirm.md"

    @property
    def collapse_series(self) -> Path:
        # Collapse-Resistance-Panel: append-only machine-readable time series (one row per cycle).
        return self.root / "state" / "collapse_series.jsonl"

    @property
    def collapse_panel(self) -> Path:
        # Collapse-Resistance-Panel: the short human/site summary of the latest row.
        return self.root / "state" / "collapse_panel.md"

    @property
    def metabolism_series(self) -> Path:
        # Metabolism: append-only time series of load/state/pressures (one row per cycle).
        return self.root / "state" / "metabolism_series.jsonl"

    @property
    def metabolism_panel(self) -> Path:
        # Metabolism: the short human/site view of the latest state + recent trajectory.
        return self.root / "state" / "metabolism.md"

    @property
    def skill_candidates(self) -> Path:
        # Procedural Skill Consolidator: append-only proposals (SkillCandidate records). Not core.
        return self.root / "state" / "skill_candidates.jsonl"

    @property
    def episodes(self) -> Path:
        # S0: append-only procedural episodes (context, action, observation, robust outcome), built
        # read-only from real signals. The substrate S2 induces policies over. Not core.
        return self.root / "state" / "episodes.jsonl"

    @property
    def skill_lifecycle(self) -> Path:
        # S4: append-only lifecycle recommendations (promote/archive/hold). Not a state write - a
        # human/Layer 9 acts on these; activation stays human-gated.
        return self.root / "state" / "skill_lifecycle.jsonl"

    @property
    def skill_lifecycle_sheet(self) -> Path:
        # S4: the human-readable "decide these" sheet - which probationary skills earned a promotion
        # recommendation and which failed and are recommended for archival.
        return self.root / "docs" / "skill_lifecycle.md"

    @property
    def method_ledger(self) -> Path:
        # Method Zustandsbuch: the current per-method state table (rewritten each cycle).
        return self.root / "state" / "method_ledger.md"

    @property
    def method_ledger_series(self) -> Path:
        # Method Zustandsbuch: append-only per-method state-transition events.
        return self.root / "state" / "method_ledger.jsonl"

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

    @property
    def research_inbox(self) -> Path:
        # Doktores drops structured research_output packages here (a JSON list). Each enters
        # Layer 9 as a SOURCE - internally produced, method-checked, not externally replicated.
        return self.root / "state" / "research_inbox.json"

    @property
    def conflict_decisions(self) -> Path:
        # A plain-text drop box: the operator settles a contradiction here (one per line,
        # "conflict_id | winner_claim_id | reason"); the loop applies it and clears the file.
        return self.root / "state" / "conflict_decisions.txt"

    @property
    def resolve_sheet(self) -> Path:
        # Human-readable "decide these" sheet, regenerated every cycle: the open conflicts Joni
        # cannot decide himself (he never force-resolves), with both claims + their support, for
        # the operator to settle. The ONLY path that ever supersedes a claim via a resolution.
        return self.root / "docs" / "to_resolve.md"

    @property
    def model_calls(self) -> Path:
        # Capture store for pinned semantic model calls: a content-addressed output store
        # (outputs/) + an append-only calls.jsonl audit log. Replay reads outputs from here.
        return self.root / "state" / "model_calls"

    @property
    def research_dir(self) -> Path:
        # The publication channel: Doktores' papers/reports/protocols are archived here with
        # explicit provenance and NO epistemic weight of their own.
        return self.root / "docs" / "research"


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
    forum_live() as the master switch.

    Note: when constitution_enforce() is on, this per-platform exemption is overridden at the
    outward seam - every public post is held for operator confirmation regardless (T0.5)."""
    raw = os.getenv("JONI_FORUM_AUTOPOST", "moltbook")
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def constitution_enforce() -> bool:
    """Whether the constitution gate ENFORCES at the outward seam (docs/CONSTITUTION.md §14),
    rather than only shadow-logging. Off by default: turning it on is a deliberate behavioural
    flip. When on, ``humans._post_live`` posts only what the operator has confirmed - a public
    post with no confirmation is held (T0.5 ESCALATE) instead of auto-posted, and a gate error
    fails CLOSED (not posted)."""
    return os.getenv("JONI_CONSTITUTION_ENFORCE", "0") == "1"
