"""``python -m joni.autonomy <command>`` - the autonomous Joni's entry point.

    run      run one autonomous cycle (research -> learn -> improve -> publish)
    verify   check the protected core against the lock (fail-safe gate)
    lock     (re)freeze the protected core into joni_core.lock - a HUMAN action

``run`` exits 42 once Joni has retired (runtime window elapsed), so a wrapper loop
can stop cleanly.
"""

from __future__ import annotations

import argparse
import sys

from . import governance
from .config import paths
from .run import one_cycle

RETIRED_EXIT = 42


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="joni.autonomy")
    parser.add_argument("command", choices=["run", "verify", "lock"])
    args = parser.parse_args(argv)
    root = paths().root

    if args.command == "lock":
        path = governance.write_lock(root)
        print(f"froze protected core -> {path}")
        return 0

    if args.command == "verify":
        ok, changed = governance.verify_core(root)
        if ok:
            print("core OK - protected modules match the lock")
            return 0
        print("CORE CHANGED without approval:", ", ".join(changed), file=sys.stderr)
        return 1

    summary = one_cycle()
    print("cycle:", summary)
    return RETIRED_EXIT if summary.get("retired") else 0


if __name__ == "__main__":
    raise SystemExit(main())
