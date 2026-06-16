"""LLM topic gate - the semantic 'does this concept belong?' judgment a lexical filter cannot make.

Stage 1 (``quality.is_good_topic``) is lexical: it strips stopwords, placeholders and fragments,
but a lexically-perfect word can still be off-domain or incoherent ('laxiflora', 'convex',
'anthology'). Stage 2 (``quality.on_domain``) is a cheap contrastive embedding check. This is
**stage 3**: the pinned Granite model reads a candidate topic with a few of its claims and decides
whether it actually names a coherent, on-domain research concept - the pattern recognition a rule
cannot do.

The model is **non-authoritative**, exactly like every other model call here: it only produces a
*verdict* (valid / invalid + reason), captured for replay. The deterministic step then acts on it
- and only conservatively: an *invalid* verdict retires the topic's **0-support** claims through
the gate (``CLAIM_REJECT``); a claim that earned support is always kept, whatever the model says.
Verdicts are cached per topic (``topic_llm_seen``) so a topic is judged once, and the call rate is
bounded per cycle, so this never becomes a per-claim spend or a perf trap.

Opt-in behind the same master switch as the rest of the semantic layer (``JONI_SEMANTIC_PROPOSALS``)
with its own opt-out (``JONI_TOPIC_LLM``); off -> a clean no-op (the lexical/embedding stages stay).
"""

from __future__ import annotations

import json
import os
import re

from . import model_call, model_profile, projection, quality
from .config import paths
from .homeostasis import _supports_on

_SYS = (
    "You are a topic gatekeeper for an epistemic reasoning agent whose domain is AI agents, large "
    "language models, model routing/serving, memory and continuity, alignment and safety, "
    "evaluation and benchmarking, reasoning, epistemics (claims/evidence/provenance), and the "
    "software/ML engineering around them. Given a CANDIDATE TOPIC and example claims tagged with "
    "it, decide whether the topic names a coherent, on-domain research concept worth tracking, or "
    "is junk: a placeholder, an off-domain word, a fragment, or an incoherent cluster. Output ONLY "
    "a JSON object {\"valid\": true|false, \"reason\": <short>}. Be strict: when in doubt that it "
    "is a real, on-domain concept, answer false.")

_FENCE = re.compile(r"^```[a-zA-Z]*\n|\n```$")


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_TOPIC_LLM", "1") != "0"


def _max_calls() -> int:
    return max(0, int(os.getenv("JONI_TOPIC_LLM_MAX_CALLS", "3")))


def _parse_verdict(output: str) -> bool | None:
    body = _FENCE.sub("", (output or "").strip())
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("valid"), bool):
        return data["valid"]
    return None


def _candidate_topics(cs, seen: set) -> list[str]:
    """Topics worth the (bounded) LLM judgment: lexically good, not yet judged, and carrying enough
    claims to be a real cluster - so we never spend a call on a one-off or an obvious stopword."""
    from collections import Counter
    counts: Counter = Counter()
    for c in cs.active_claims():
        t = getattr(c, "topic", None)
        if t and t not in seen and quality.is_good_topic(t):
            counts[t] += 1
    return [t for t, n in counts.most_common() if n >= 2]


def review_topics(cs, extensions: dict, proto, cycle: int = 0, *, max_retire: int = 5) -> dict:
    """Judge a few new candidate topics with Granite and shed the ones it calls junk (0-support
    claims only, gate-recorded). Cached + bounded. No-op when disabled."""
    out = {"reviewed": 0, "rejected_topics": 0, "retired_claims": 0}
    if not enabled():
        return out
    seen = dict(extensions.get("topic_llm_seen", {}))   # topic -> "valid" | "invalid"
    pending = _candidate_topics(cs, set(seen))[: _max_calls()]
    if not pending:
        return out
    store_dir = paths().model_calls
    prof = model_profile.profile("joni-semantic")
    rejected: list[str] = []
    for topic in pending:
        sample = [c for c in cs.claims_on(topic)][:4]
        body = "\n".join(f"- {c.text}" for c in sample) or "(no claims)"
        user = f"CANDIDATE TOPIC: {topic}\n\nCLAIMS TAGGED '{topic}':\n{body}"
        output, cap = model_call.call(prof, _SYS, user, run_id=f"topicrev-c{cycle}",
                                      store_dir=store_dir)
        if output is None or cap is None:
            continue                                    # a failed call is no verdict, not a guess
        out["reviewed"] += 1
        valid = _parse_verdict(output)
        if valid is None:
            continue
        seen[topic] = "valid" if valid else "invalid"
        if not valid:
            rejected.append(topic)
    # act on the rejections: shed the 0-support claims of a topic the model judged junk
    for topic in rejected:
        for c in cs.claims_on(topic):
            if out["retired_claims"] >= max_retire:
                break
            if _supports_on(cs, c.id) > 0:
                continue
            try:
                cs.reject_claim(c.id)
            except Exception:  # noqa: BLE001 - a stubborn claim must never break the cycle
                continue
            out["retired_claims"] += 1
    out["rejected_topics"] = len(rejected)
    extensions["topic_llm_seen"] = dict(sorted(seen.items())[-2000:])
    if rejected:
        proto.record(cycle, "regulate",
                     f"Granite topic-review rejected {len(rejected)} topic(s) as junk/off-domain "
                     f"({', '.join(rejected)}) - shed {out['retired_claims']} 0-support claim(s); "
                     "a supported idea is kept regardless")
    return out
