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
    def provisional(self) -> Path:
        # HindsightTag H0: the provisional-episodic layer (staging between working memory and Layer
        # 9). Append-only entries with a lifecycle stage + two salience values. Not a record store.
        return self.root / "state" / "provisional.jsonl"

    @property
    def hindsight_provenance(self) -> Path:
        # HindsightTag H2: append-only provenance of every review-trigger (event, cycle, capture
        # strength, reactivated entries) - a human can reconstruct WHY an entry was reactivated.
        return self.root / "state" / "hindsight_provenance.jsonl"

    @property
    def hindsight_panel(self) -> Path:
        # HindsightTag: the short human/site view of the provisional layer (stages, tags, reviews).
        return self.root / "docs" / "hindsight.md"

    @property
    def ext_disabled(self) -> Path:
        # Self-regulation sensor: which extensions the benefit-review has auto-deactivated. Surfaced
        # on the scoreboard so a wrong disable is visible immediately, not weeks later.
        return self.root / "state" / "ext_disabled.json"

    @property
    def digestion(self) -> Path:
        # Priority 2: the intake<->digestion coupling marker (last cycle real digestion happened).
        return self.root / "state" / "digestion.json"

    @property
    def sleep_state(self) -> Path:
        # Schlafmodus S0: the four-state machine (AWAKE/SLEEP_LIGHT/SLEEP_DEEP/WAKE_TRANSITION),
        # its trigger reason, and the maturation delta of the last sleep window.
        return self.root / "state" / "sleep_state.json"

    @property
    def refragment(self) -> Path:
        # Schlafmodus S1: append-only proposed associative links between provisional entries.
        return self.root / "state" / "refragment.jsonl"

    @property
    def sleep_audit(self) -> Path:
        # Schlafmodus S2: append-only per-cycle procedural-structure scores over candidate methods.
        return self.root / "state" / "sleep_audit.jsonl"

    @property
    def sleep_revisions(self) -> Path:
        # Schlafmodus S3: append-only, versioned defect reports. Nothing here is ever applied.
        return self.root / "state" / "sleep_revisions.jsonl"

    @property
    def wake_queue(self) -> Path:
        # Schlafmodus S4: the handover - what the waking Joni should look at first.
        return self.root / "state" / "wake_queue.json"

    @property
    def sleep_report(self) -> Path:
        # Schlafmodus S4: the human view, led by the maturation delta, not the activity count.
        return self.root / "docs" / "sleep_report.md"

    @property
    def disputes_sheet(self) -> Path:
        # Priority 5: the human view of the condensed Streitfragen (few disputes, not 273 pairs).
        return self.root / "docs" / "streitfragen.md"

    @property
    def disputes_series(self) -> Path:
        # Priority 5: append-only per-cycle count row (conflicts -> disputes, largest tangle).
        return self.root / "state" / "disputes_series.jsonl"

    @property
    def method_breakdown_sheet(self) -> Path:
        # Operator measure 2: the human view of WHY the trial pipeline is starved (5 buckets).
        return self.root / "docs" / "method_breakdown.md"

    @property
    def method_breakdown_series(self) -> Path:
        # Operator measure 2: append-only per-cycle bucket counts over the candidate methods.
        return self.root / "state" / "method_breakdown.jsonl"

    @property
    def scoreboard_series(self) -> Path:
        # Priority 1: append-only per-cycle Consolidator scoreboard (episodes/skills/re-trials/
        # recommendations/valid-vs-discarded). Success measured at the output, not claim growth.
        return self.root / "state" / "consolidator_series.jsonl"

    @property
    def scoreboard_panel(self) -> Path:
        # Priority 1: the short human/site view of the latest scoreboard row.
        return self.root / "docs" / "consolidator.md"

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
        # ``index.html`` gehoert seit 2026-07-30 der Architekturkarte (``joni.architecture``).
        # Die Statusseite der Schleife liegt daneben unter ``status.html``: sonst haette ein
        # spaeterer Lauf der Autonomie-Schleife die Karte still ueberschrieben - und zwar genau
        # dann, wenn niemand hinsieht.
        return self.root / "docs" / "status.html"

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
