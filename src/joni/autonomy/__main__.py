"""``python -m joni.autonomy <command>`` - the autonomous Joni's entry point.

    run      run one autonomous cycle (research -> learn -> improve -> publish)
    verify   check the protected core against the lock (fail-safe gate)
    compact  slim + re-seal the state journal (drop dead measurement blobs) so a fresh
             job's full replay finishes inside a cycle - one-time maintenance, data only
    lock     (re)freeze the protected core into joni_core.lock - a HUMAN action
    approve  approve one drafted forum question for posting - a HUMAN action
             (the relay only ever posts approved drafts): approve <draft-id>

``run`` exits 42 once Joni has retired (runtime window elapsed), so a wrapper loop
can stop cleanly.
"""

from __future__ import annotations

import argparse
import sys

from . import governance, humans
from .config import paths
from .run import one_cycle

RETIRED_EXIT = 42


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="joni.autonomy")
    parser.add_argument("command",
                        choices=["run", "verify", "compact", "checkpoint", "lock", "approve"])
    parser.add_argument("ref", nargs="?", help="draft id for 'approve'")
    args = parser.parse_args(argv)
    root = paths().root

    if args.command == "approve":
        if not args.ref:
            print("usage: approve <draft-id>", file=sys.stderr)
            return 2
        ids = humans.approve(paths().forum_approved, args.ref)
        print(f"approved {args.ref} for posting; the relay may now post it. approved: {ids}")
        return 0

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

    if args.command == "compact":
        # Data-only maintenance: slim the bloated append-only journal (drop the dead
        # measurement.pairs blobs) and re-seal it, so a fresh job's full replay finishes inside a
        # cycle again. The protected core code is untouched; verify it first as a fail-safe.
        ok, changed = governance.verify_core(root)
        if not ok:
            print("CORE CHANGED without approval:", ", ".join(changed), file=sys.stderr)
            return 1
        from desi_layer9 import persistence
        summary = persistence.compact(paths().core)
        print(f"compacted {paths().core} -> {summary}")
        return 0

    if args.command == "checkpoint":
        # Write the committed cold-start checkpoint so a fresh CI job restores it instead of doing
        # the >100-min journal replay that parked the loop. The first run replays once (bootstrap);
        # later runs restore the existing checkpoint (fast) and re-seal it. Data-only; core safe.
        from desi_layer9 import persistence

        from ..layer9_v2.runtime import desi_store
        p = paths()
        # prefer the fast checkpoint restore; only the very first bootstrap pays the full replay
        core = desi_store.load_via_checkpoint(p.core, p.checkpoint) or persistence.load(p.core)
        if core is None:
            print("no core state to checkpoint", file=sys.stderr)
            return 1
        out = desi_store.write_checkpoint(core, p.checkpoint)
        mb = out.stat().st_size / 1e6
        print(f"wrote cold-start checkpoint -> {out} ({mb:.1f} MB)")
        return 0

    summary = one_cycle()
    print("cycle:", summary)
    return RETIRED_EXIT if summary.get("retired") else 0


if __name__ == "__main__":
    raise SystemExit(main())
