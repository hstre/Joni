"""Query-based literature synthesis for the reading layer (Auftrag, paper: IRIS, arXiv:2504.16728).

Instead of reading single paper abstracts in isolation, synthesize the several papers Joni fetched
on one topic into ONE coherent, condensed feed item - what the recent literature jointly says about
that topic - which then enters Layer 9 as a SOURCE (candidate authority, conflict-checked, never
confirmed), exactly like a single paper or a forum reply.

Non-core boundary: it only adds a reading-layer input; the gate, the ledger and the operators are
untouched, and the synthesis is held no more strongly than any other source. Opt-in
(``JONI_LITERATURE_SYNTHESIS=1``), gated like every model arm (``JONI_SEMANTIC_PROPOSALS=1``),
cadence-spaced and budget-metered via Joni's own captured ``joni-hard`` model, and deduped per
(topic, source-set) so the same papers are never re-synthesised.
"""

from __future__ import annotations

import os

from . import model_call, model_profile, projection
from .config import paths

_SOURCES = {"arxiv", "huggingface", "zenodo", "openalex", "wikipedia", "openclaw"}

_SYS = (
    "You synthesize several research snippets into ONE coherent, faithful paragraph: what the "
    "recent literature jointly says about the given topic. Use ONLY what the snippets support - no "
    "invention, no citations, no hedging preamble. Output 2-4 plain declarative sentences."
)


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_LITERATURE_SYNTHESIS", "0") == "1"


def _every() -> int:
    return max(1, int(os.getenv("JONI_SYNTHESIS_EVERY", "6")))


def _matches(topic: str, item) -> bool:
    blob = (getattr(item, "title", "") + " " + (getattr(item, "summary", "") or "")).lower()
    return topic.lower() in blob


def synthesize(cs, extensions: dict, proto, cycle: int, *, items, budget=None,
               runs_per_week: int = 0) -> dict:
    """Synthesise (at most one per firing) the fetched papers on one rotating topic into a single
    SOURCE feed item. No-op when disabled, not yet due, or no topic has >=2 fetched papers."""
    if not enabled():
        return {"synthesized": 0}
    last = extensions.get("synthesis_last_cycle")
    if last is not None and cycle - last < _every():
        return {"synthesized": 0}
    topics = [t for t in cs.topics() if t and len(t) > 3]
    if not topics:
        return {"synthesized": 0}

    seen = set(extensions.setdefault("synthesis_seen", []))
    idx = int(extensions.get("synthesis_topic_idx", 0)) % len(topics)
    out = {"synthesized": 0}
    for off in range(len(topics)):
        topic = topics[(idx + off) % len(topics)]
        cand = [it for it in (items or [])
                if getattr(it, "source", "") in _SOURCES and getattr(it, "key", None)
                and _matches(topic, it)]
        key = topic + "|" + "|".join(sorted(it.key for it in cand))
        if len(cand) < 2 or key in seen:
            continue
        extensions["synthesis_topic_idx"] = (idx + off + 1) % len(topics)
        extensions["synthesis_last_cycle"] = cycle
        seen.add(key)
        snippets = "\n".join(
            f"- {getattr(it, 'title', '')}: {(getattr(it, 'summary', '') or '')[:300]}"
            for it in cand[:4])
        user = (f"TOPIC: {topic}\n\nSNIPPETS:\n{snippets}\n\n"
                f"Synthesize what this literature says about '{topic}'.")
        text, cap = model_call.call(
            model_profile.profile("joni-hard"), _SYS, user,
            run_id=f"joni-c{cycle}-synth", store_dir=paths().model_calls,
            escalation_reason="literature-synthesis", budget=budget, runs_per_week=runs_per_week)
        if text and text.strip():
            cid = cs.hear(text.strip()[:600], topic, handle="iris", platform="synthesis",
                          origin="literature-synthesis")
            out = {"synthesized": 1, "topic": topic, "claim": cid, "sources": len(cand[:4])}
            log = extensions.setdefault("synthesis_log", [])
            log.append({"cycle": cycle, "topic": topic, "claim": cid, "sources": len(cand[:4]),
                        "served_model": getattr(cap, "served_model", "") if cap else "",
                        "text": text.strip()[:200]})
            extensions["synthesis_log"] = log[-40:]
            proto.record(cycle, "research",
                         f"literature synthesis on '{topic}' from {len(cand[:4])} sources "
                         f"-> source {cid} (candidate, conflict-checked, never confirmed)")
        break
    extensions["synthesis_seen"] = sorted(seen)[-2000:]
    return out
