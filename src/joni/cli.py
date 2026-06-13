"""Joni CLI - run an identity forward, then ask it something, in two views.

    joni --ticks 8 "what's your take on privacy these days?"
    joni --ticks 12 --ledger "and on model routing?"

Runs offline (deterministic MockModel). The Conversation View is the apparent
person; the Epistemic View dissolves it into the state that produced it.
"""

from __future__ import annotations

import argparse

from .identity import Joni


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="joni",
        description="Joni - an operative identity that appears like a person and shows why.",
    )
    p.add_argument("prompt", nargs="?", default="what do you think about privacy?",
                   help="what to ask the identity")
    p.add_argument("--ticks", type=int, default=8, help="units of lived time to run first")
    p.add_argument("--budget", type=float, default=1.0, help="external-API budget")
    p.add_argument("--ledger", action="store_true", help="dump the full audit ledger")
    p.add_argument("--auto", action="store_true", help="show the autobiographical memory")
    p.add_argument("--state", metavar="PATH", default=None,
                   help="resume from / save to a persisted identity (lives on across runs)")
    return p


def _hr(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    joni = Joni(budget=args.budget, state_path=args.state)
    joni.live(ticks=args.ticks)
    if args.state:
        joni.save()
        print(f"(identity persisted to {args.state} · creativity engine: "
              f"{joni.snapshot()['creativity']})")

    snap = joni.snapshot()
    _hr(f"{snap['name']} · tick {snap['tick']}")
    print(f"claims={snap['claims']['active']}/{snap['claims']['total']} active  "
          f"goals={snap['goals']}  projects={snap['projects']}  prefs={snap['preferences']}  "
          f"memory={snap['memory']}  conflicts(open)={snap['open_conflicts']}")
    print(f"ledger={snap['ledger_events']} events  spend={snap['spend']}  "
          f"budget_left={snap['budget_remaining']}  topics={snap['topics']}")

    if args.auto:
        _hr("AUTOBIOGRAPHY (episodic memory)")
        from .memory import autobiography
        for line in autobiography(joni.state):
            print(" ", line)

    if args.ledger:
        _hr("AUDIT LEDGER (append-only)")
        for e in joni.state.ledger:
            cost = f"  cost={e.cost}" if e.cost else ""
            print(f"  {e.id}  t{e.tick}  {e.operator:<20} by {e.reviewed_by:<16} {e.summary}{cost}")

    r = joni.respond(args.prompt)
    _hr("CONVERSATION VIEW  (the apparent person)")
    print(" ", r.conversation)

    e = r.epistemic
    _hr("EPISTEMIC VIEW  (why it said that)")
    print(f"  claims        : {', '.join(e.claims) or '-'}")
    print(f"  goals         : {', '.join(e.goals) or '-'}")
    print(f"  memory        : {', '.join(e.memory) or '-'}")
    print(f"  operator      : {e.operator or '-'}")
    print(f"  trigger       : {e.trigger or '-'}")
    print(f"  reviewed_by   : {e.reviewed_by}")
    print(f"  ledger_event  : {e.ledger_event or '-'}")
    print(f"  routed_to     : {e.routed_to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
