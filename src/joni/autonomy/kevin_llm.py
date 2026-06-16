"""Kevin, for real - creative cross-domain transfer over his own pinned model.

Until now Kevin only ran deterministic transfer *trials* (``trials.py`` / ``kevin.trial_runner``)
on the method shelf; his ``deepseek-v4-pro`` profile was defined but never actually called, so
the telemetry showed zero Kevin calls. This wires Kevin's creative arm: given a slice of Joni's
claims across two different topics, Kevin (warm sampling, his own profile - NOT Joni's structured
projector) proposes a **bold but testable cross-domain transfer hypothesis** - an insight or
method from one area that might apply to the other.

Like every model output here it is only a **proposal**: it enters Layer 9 as a ``candidate``
hypothesis through the normal gate (derived from the two seed claims, never auto-confirmed), and
the call is fully captured (``model_call.py``) so it is replay-stable and shows up in the
dashboard telemetry as a Kevin call.

Rides the same master switch as the rest of the semantic layer (``JONI_SEMANTIC_PROPOSALS``),
with its own opt-out and a cadence so a creative leap is a deliberate, bounded act - not an
every-cycle spend.
"""

from __future__ import annotations

import os

from . import model_call, model_profile, projection
from .config import paths

_SYS = (
    "You are Kevin, a creative research partner for an epistemic reasoning agent. You are given "
    "some of the agent's current claims across TWO different topics. Propose a bold but TESTABLE "
    "cross-domain transfer: an insight, mechanism or method from one topic that might apply to "
    "the other. Output ONLY a JSON array of at most 2 objects {\"text\": <one falsifiable "
    "conjecture linking the two domains>, \"topic\": <short topic>}. Each is a single declarative, "
    "checkable statement - creative but concrete, no opinions, no meta-commentary, no questions.")


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_KEVIN_LLM", "1") != "0"


def _every() -> int:
    """Cadence: Kevin's creative call fires at most once per this many cycles (a deliberate leap,
    not an every-cycle spend). Env-dialled."""
    return max(1, int(os.getenv("JONI_KEVIN_EVERY", "3")))


def _kevin_usable(cs, topic: str) -> bool:
    """A topic carries enough real, non-trivial material for a far-analogy: at least two
    non-synthetic claims (not Joni's own bookkeeping 'X recurs as a through-line' lines)."""
    from .emerge import _is_synthetic
    real = [c for c in cs.claims_on(topic) if not _is_synthetic(c.text)]
    return len(real) >= 2


def propose(cs, extensions: dict, proto, cycle: int, *, budget=None,
            runs_per_week: int = 0) -> dict:
    """Once per cadence, let Kevin propose a cross-domain transfer hypothesis via his pinned
    ``deepseek-v4-pro`` profile. Candidate through the gate, captured for replay. No-op when
    disabled, not yet due, or fewer than two good topics exist."""
    out = {"kevin_calls": 0, "hypotheses": 0}
    if not enabled():
        return out
    last = extensions.get("kevin_last_cycle")
    if last is not None and cycle - last < _every():
        return out
    # Kevin's job is far-analogy, not junk-refinement (review #7). Only set him on topics that
    # (a) earned research status (>=3 claims across >=2 independent sources - never 'unsorted', a
    # thin word cluster, or a one-source fluke) AND (b) carry real, non-trivial material: at least
    # two non-synthetic claims (not Joni's own "X recurs as a through-line" bookkeeping).
    topics = [t for t in cs.research_topics() if _kevin_usable(cs, t)]
    if len(topics) < 2:
        return out
    ta, tb = topics[0], topics[1]
    claims_a, claims_b = cs.claims_on(ta), cs.claims_on(tb)
    if not claims_a or not claims_b:
        return out
    sa = "\n".join(f"- {c.text}" for c in claims_a[:3])
    sb = "\n".join(f"- {c.text}" for c in claims_b[:3])
    user = (f"TOPIC A ({ta}):\n{sa}\n\nTOPIC B ({tb}):\n{sb}\n\n"
            "Propose a cross-domain transfer hypothesis linking A and B.")
    prof = model_profile.profile("kevin")
    output, cap = model_call.call(prof, _SYS, user, run_id=f"kevin-c{cycle}",
                                  store_dir=paths().model_calls,
                                  budget=budget, runs_per_week=runs_per_week)
    if output is None or cap is None:
        return out
    out["kevin_calls"] = 1
    extensions["kevin_last_cycle"] = cycle          # cadence still bounds cost on a failed call
    props = projection._parse(output, f"{ta}+{tb}")
    if not output.strip() or not props:
        # An empty/truncated answer (reasoning model out of budget) or an unparseable one is a
        # FAILED creative call - NOT a '0-proposal success'. Record it honestly so the page shows a
        # real failure, not a silent zero. The instrumented capture (finish_reason=length /
        # reasoning_tokens) says which; raising the token budget is the fix for truncation.
        reason = "empty (model truncation?)" if not output.strip() else "no parseable proposal"
        log = extensions.setdefault("kevin_llm", [])
        log.append({"call_id": cap.call_id, "served_model": cap.served_model, "cycle": cycle,
                    "topics": [ta, tb], "replayed": cap.replayed, "failed": reason,
                    "content_len": len(output), "proposals": []})
        extensions["kevin_llm"] = log[-200:]
        proto.record(cycle, "kevin",
                     f"Kevin ({cap.served_model}) call produced NO proposal [{ta} × {tb}]: "
                     f"{reason} (content_len={len(output)}) - no hypothesis this round")
        return out
    parents = (claims_a[0].id, claims_b[0].id)
    ids = []
    for p in props[:2]:
        ids.append(cs.hypothesize(p["text"], p["topic"], parents=parents))
        out["hypotheses"] += 1
    log = extensions.setdefault("kevin_llm", [])
    # store the actual proposal TEXT (not just a count) so the site can show what Kevin suggested
    # and the panel's verdict can be matched to it by hypothesis id.
    log.append({"call_id": cap.call_id, "served_model": cap.served_model, "cycle": cycle,
                "topics": [ta, tb], "replayed": cap.replayed,
                "proposals": [{"id": i, "text": p["text"], "topic": p["topic"]}
                              for i, p in zip(ids, props[:2], strict=False)]})
    extensions["kevin_llm"] = log[-200:]
    proto.record(cycle, "kevin",
                 f"Kevin ({cap.served_model}) proposed {len(props)} cross-domain hypothesis(es) "
                 f"[{ta} × {tb}, replayed={cap.replayed}] - candidate(s) via the gate, "
                 "Joni decides")
    return out
