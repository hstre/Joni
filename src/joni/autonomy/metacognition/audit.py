"""Append-only audit store for metacognition episodes + outcome events.

One plain JSONL file (``state/metacognition.jsonl``), in the spirit of the DESi ledger and
Joni's other ``*_shadow.jsonl`` logs: readable, diff-able, never rewritten. An episode is
written once with ``outcome=unknown``; a later result is a SEPARATE ``outcome`` event that
references ``episode_id``. The episode line is never mutated. Reads for projections are
bounded (``tail``); the full history stays on disk.
"""
from __future__ import annotations

import json
from pathlib import Path

from .models import Episode, OutcomeEvent


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _append(self, record: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    def append_episode(self, ep: Episode) -> str:
        rec = ep.to_record()
        rec["kind"] = "episode"
        self._append(rec)
        return rec["episode_id"]

    def append_outcome(self, ev: OutcomeEvent) -> None:
        """Record a belastbares later result as a NEW append-only event (never rewrites)."""
        self._append(ev.to_record())

    def _rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def episodes(self) -> list[dict]:
        return [r for r in self._rows() if r.get("kind") == "episode"]

    def outcome_events(self) -> list[dict]:
        return [r for r in self._rows() if r.get("kind") == "outcome"]

    def resolved_outcomes(self) -> dict[str, dict]:
        """episode_id -> the LATEST outcome event for it (append-only history is preserved on
        disk; this is a read-side projection, not a mutation)."""
        latest: dict[str, dict] = {}
        for ev in self.outcome_events():
            eid = ev.get("episode_id")
            if eid:
                latest[eid] = ev                      # later events supersede earlier ones on read
        return latest

    def pending_episode_ids(self) -> set[str]:
        """Episodes with no belastbares outcome yet - still 'unknown', never coerced."""
        resolved = set(self.resolved_outcomes())
        return {e["episode_id"] for e in self.episodes() if e["episode_id"] not in resolved}

    def joined(self, *, limit: int | None = None) -> list[dict]:
        """Bounded projection: each episode with its resolved outcome folded in (read-only).
        The episode's own stored outcome is left as-is; the effective outcome for analysis is
        the outcome event's if present, else the episode's (which is 'unknown' by default)."""
        resolved = self.resolved_outcomes()
        eps = self.episodes()
        if limit is not None:
            eps = eps[-limit:]
        rows = []
        for e in eps:
            ev = resolved.get(e["episode_id"])
            eff = ev["outcome"] if ev else e.get("outcome", "unknown")
            eff_src = ev["outcome_source"] if ev else e.get("outcome_source", "")
            rows.append({**e, "effective_outcome": eff, "effective_outcome_source": eff_src,
                         "resolved": ev is not None})
        return rows


__all__ = ["AuditLog"]
