"""Belastbare PR/CI outcomes for the literature-Doktores episodes, from observable sources.

Both index builders produce ``{component_key: 'success' | 'failure'}`` and are PURE (testable):

- ``index_from_commissions_done``: a commission recorded as *implemented* is a documented PR
  outcome -> success. This source records only implementations, so it yields success or nothing,
  never failure.
- ``index_from_issues``: parse GitHub ``joni-auftrag`` issues/PRs - a merged PR -> success, a
  closed-unmerged PR -> failure, an open one -> skipped. Matching a commission to its issue is
  best-effort (the component key appearing in the title/body), so many stay unresolved.

This module performs **no egress** on purpose: the shadow observer never opens its own socket in
the autonomy loop (docs/EGRESS_GATE.md - egress stays with Joni's research fetchers). The in-loop
PR index comes from local ``commissions_done`` (zero network). The live GitHub read is an
operator-run convenience in ``scripts/metacognition_report.py`` (gate-exempt), which fetches the
closed ``joni-auftrag`` issues and feeds the JSON straight into ``index_from_issues`` here.
"""
from __future__ import annotations


def _match_keys(blob: str, component_keys) -> list[str]:
    low = blob.lower()
    return [k for k in component_keys if k and k.lower() in low]


def index_from_commissions_done(rows: list[dict], component_keys) -> dict[str, str]:
    idx: dict[str, str] = {}
    for r in rows:
        blob = f"{r.get('component', '')} {r.get('ref', '')} {r.get('title', '')}"
        for k in _match_keys(blob, component_keys):
            idx[k] = "success"                       # implemented == documented PR outcome
    return idx


def index_from_issues(issues: list[dict], component_keys) -> dict[str, str]:
    idx: dict[str, str] = {}
    for it in issues:
        labels = {lab.get("name", "") for lab in it.get("labels", []) if isinstance(lab, dict)}
        if "joni-auftrag" not in labels:
            continue
        pr = it.get("pull_request") or {}
        if not pr and "pull_request" not in it:
            continue                                 # a plain issue, not a PR - no PR outcome yet
        if it.get("state", "open") == "open":
            continue                                 # still open -> unknown, skip
        merged = bool(pr.get("merged_at") or pr.get("merged"))
        outcome = "success" if merged else "failure"
        blob = f"{it.get('title', '')} {it.get('body', '')}"
        for k in _match_keys(blob, component_keys):
            idx[k] = outcome
    return idx


__all__ = ["index_from_commissions_done", "index_from_issues"]
