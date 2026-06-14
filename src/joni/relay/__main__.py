"""``python -m joni.relay`` - the VPS relay loop.

Defaults to dry-run (posts nothing). Git sync keeps the published state current so a human can
approve drafts and the loop can hear replies. Posting only ever happens for approved drafts and
only through an implemented, credentialed adapter.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import time

from ..autonomy.config import paths
from .agent import one_pass


def _git(args: list[str], cwd: str) -> int:
    return subprocess.run(["git", *args], cwd=cwd, check=False).returncode


def _git_pull(root: str) -> None:
    _git(["pull", "--ff-only", "--quiet"], root)


def _git_push_state(root: str) -> None:
    """Commit only the two relay-owned state files and push. Never touches code or core."""
    rc = _git(["add", "state/forum_inbox.json", "state/forum_outbox.json"], root)
    if rc != 0:
        return
    if _git(["diff", "--cached", "--quiet"], root) == 0:
        return                                  # nothing staged
    _git(["commit", "--quiet", "-m", "relay: post approved draft(s) / ingest reply(ies)"], root)
    _git(["push", "--quiet"], root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="joni.relay")
    parser.add_argument("--live", action="store_true",
                        help="allow posting via implemented+credentialed adapters (else dry-run)")
    parser.add_argument("--interval", type=int, default=300, help="seconds between passes")
    parser.add_argument("--once", action="store_true", help="run a single pass and exit")
    parser.add_argument("--no-git", action="store_true", help="do not pull/push (local test)")
    args = parser.parse_args(argv)

    p = paths()
    root = str(p.root)
    env = dict(os.environ)

    while True:
        if not args.no_git:
            _git_pull(root)
        summary = one_pass(p, live=args.live, env=env)
        mode = "live" if args.live else "dry-run"
        print(f"relay [{mode}]: {summary}", flush=True)
        if not args.no_git and (summary["posted"] or summary["heard"]):
            _git_push_state(root)
        if args.once:
            return 0
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
