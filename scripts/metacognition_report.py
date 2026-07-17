"""Reproducible shadow-evaluation of the metacognition supervisor.

    python scripts/metacognition_report.py                       # self-contained benchmark demo
    python scripts/metacognition_report.py --source state/metacognition.jsonl [--json out.json]
    python scripts/metacognition_report.py --github hstre/Joni --component-keys sources,router

Reads the joined episode+outcome rows (from the benchmark or a logged JSONL), builds the bounded
grouped report (per task family / seam calibration, coverage, control mix, cost - refused where
thin), prints Markdown and optionally writes the JSON. Observation only; it computes nothing new
and calls no model.

``--github`` is the operator-run PR-outcome reader. The autonomy package performs NO egress
(docs/EGRESS_GATE.md); the live GitHub read lives here in ``scripts/`` (gate-exempt) instead. It
fetches the closed ``joni-auftrag`` issues/PRs and feeds them into the pure ``index_from_issues``,
then prints the ``{component_key: success|failure}`` index. Fail-safe: ``{}`` on any error.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _rows(source: str) -> list[dict]:
    from joni.autonomy.metacognition import benchmark
    from joni.autonomy.metacognition.audit import AuditLog
    if source == "benchmark":
        return benchmark.joined_rows()
    return AuditLog(Path(source)).joined()


def _github_pr_index(slug: str, token: str, component_keys, *, timeout: int = 20) -> dict[str, str]:
    """Operator-run, fail-safe: fetch closed joni-auftrag PRs and index them. {} on any error."""
    from joni.autonomy.metacognition import pr_outcomes
    try:
        owner, repo = slug.split("/", 1)
        url = (f"https://api.github.com/repos/{owner}/{repo}/issues"
               f"?labels=joni-auftrag&state=closed&per_page=100")
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "joni-metacog"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - fixed https api host
            issues = json.load(r)
        return pr_outcomes.index_from_issues(issues if isinstance(issues, list) else [],
                                             component_keys)
    except Exception:  # noqa: BLE001 - the reader must never break the operator's run
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="benchmark",
                    help="'benchmark' (default) or a path to a metacognition.jsonl")
    ap.add_argument("--json", help="also write the report JSON here")
    ap.add_argument("--github", metavar="OWNER/REPO",
                    help="operator-run PR-outcome reader: fetch closed joni-auftrag PRs and print "
                         "the {component_key: success|failure} index, then exit")
    ap.add_argument("--component-keys", default="",
                    help="comma-separated component keys to match against PR titles/bodies")
    ap.add_argument("--token", default="", help="GitHub token (else uses $GITHUB_TOKEN)")
    args = ap.parse_args()

    if args.github:
        import os
        keys = [k.strip() for k in args.component_keys.split(",") if k.strip()]
        idx = _github_pr_index(args.github, args.token or os.getenv("GITHUB_TOKEN", ""), keys)
        print(json.dumps(idx, indent=2, ensure_ascii=False))
        return 0

    from joni.autonomy.metacognition import report as report_mod
    rows = _rows(args.source)
    rep = report_mod.build_report(rows)
    print(report_mod.render_markdown(rep))
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
