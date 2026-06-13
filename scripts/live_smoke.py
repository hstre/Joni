#!/usr/bin/env python
"""A bounded, real-voice smoke test for Joni.

Run offline (MockModel) for a structural check, or against real DeepSeek in CI:

    JONI_USE_REAL_LLM=1 DEEPSEEK_API_KEY=sk-... python scripts/live_smoke.py

It lives the identity forward, asks the privacy question, and asserts the dual view
holds end to end: the apparent opinion change resolves to a real conflict_resolution
operator and a ledger event that actually exists. The real model only phrases the
state-grounded brief - the receipts come from deterministic state either way.

Skips cleanly (exit 0) when the real voice is requested but no key is present.
"""

from __future__ import annotations

import os
import sys

from joni import Joni


def main() -> int:
    real = os.getenv("JONI_USE_REAL_LLM") == "1"
    has_key = bool(
        os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY2")
        or os.getenv("OPENAI_API_KEY")
    )
    if real and not has_key:
        print("No model key present (e.g. fork PR) - skipping live smoke test.")
        return 0

    joni = Joni()
    joni.live(ticks=8)
    r = joni.respond("what's your take on privacy these days?")

    mode = "DeepSeek voice" if real else "MockModel"
    print(f"[{mode}] tick={joni.snapshot()['tick']}")
    print("CONVERSATION:", r.conversation)
    e = r.epistemic
    print(f"EPISTEMIC: operator={e.operator} trigger={e.trigger} "
          f"reviewed_by={e.reviewed_by} ledger_event={e.ledger_event} routed_to={e.routed_to}")

    # The dual view must hold regardless of the voice.
    assert r.conversation, "empty conversation"
    assert e.operator is not None and e.operator.value == "conflict_resolution", \
        "privacy turn should report a conflict-resolution opinion change"
    assert e.trigger is not None and e.trigger.value == "contradictory_evidence"
    assert e.ledger_event and e.ledger_event.startswith("L9-"), "missing ledger receipt"
    assert any(ev.id == e.ledger_event for ev in joni.state.ledger), \
        "cited ledger event must exist"
    print("OK: dual view intact - the apparent person dissolves into real receipts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
