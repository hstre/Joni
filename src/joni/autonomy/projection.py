"""Semantic projection - the first non-authoritative LLM proposal layer.

This is the architecture correction: instead of extracting claims with a regex, the pinned
``joni-semantic`` model (Granite) reads a source and *proposes* atomic, checkable claims. The
proposals are exactly that - **proposals**: they enter Layer 9 through the normal gate as
``candidate`` SOURCE claims (never authoritative, conflict-checked, never auto-confirmed), and
the model call is fully captured (``model_call.py``) so it stays replay-stable.

The model is given a **DESi state slice of density ``state_k``** as context - the ``k`` most
relevant existing claims - so it projects *into Joni's state*, not into a vacuum. ``state_k`` is
the slice density, NOT a sampling ``top_k``.

Opt-in (``JONI_SEMANTIC_PROPOSALS=1``); off by default, so the running soak test is untouched.
The deterministic ``reader``/regex path stays in place as the control arm - the model does not
silently replace it.
"""

from __future__ import annotations

import json
import os
import re

from . import model_call, model_profile
from .config import paths

_SYS = (
    "You extract atomic, checkable factual claims from a source for an epistemic reasoning "
    "agent. Output ONLY a JSON array of objects {\"text\": <one verifiable statement>, "
    "\"topic\": <short topic>}. Each claim is a single declarative, falsifiable statement - no "
    "opinions, no meta-commentary, no questions. Use the provided existing-state context only to "
    "choose a relevant topic; never invent facts not in the source. At most 5 claims.")

_FENCE = re.compile(r"^```[a-zA-Z]*\n|\n```$")


def enabled() -> bool:
    return os.getenv("JONI_SEMANTIC_PROPOSALS") == "1"


def state_slice(cs, text: str, *, k: int) -> list[str]:
    """The ``k`` most relevant existing claims to ``text`` - the DESi state slice the projector
    sees as context. Embedding cosine when available, else lexical overlap. ``k`` is the slice
    density, not a sampling argument."""
    claims = cs.active_claims()
    if not claims or k <= 0:
        return []
    from . import embeddings
    if embeddings.available():
        scored = [(d, c) for c in claims
                  if (d := embeddings.cosine_distance(text, c.text)) is not None]
        scored.sort(key=lambda x: x[0])
        return [c.text for _, c in scored[:k]]
    from ..conflict import _content
    w = _content(text)
    ranked = sorted(claims, key=lambda c: -len(w & _content(c.text)))
    return [c.text for c in ranked[:k]]


def _parse(output: str, topic_hint: str) -> list[dict]:
    from . import quality
    body = _FENCE.sub("", (output or "").strip())
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return []
    hint = (topic_hint or "").strip().lower()
    out: list[dict] = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        topic = str(item.get("topic") or hint or "unsorted").strip().lower()[:40]
        # The semantic projection must NOT bypass the topic-quality gate the deterministic
        # track_topic path already obeys: a function word ("been", "because", "what") is not an
        # emergent concept. A junk topic falls back to the (good) hint, else "unsorted" - never a
        # stopword promoted to a tracked topic.
        if not quality.is_good_topic(topic):
            topic = hint if quality.is_good_topic(hint) else "unsorted"
        out.append({"text": text[:300], "topic": topic or "unsorted"})
    return out[:5]


def claim_proposals(text: str, *, topic_hint: str, cs, run_id: str, store_dir,
                    budget=None, runs_per_week: int = 0):
    """Project a source text into candidate claim proposals via the pinned Granite profile.
    Returns ``(proposals, capture)`` - ``([], None)`` if the call could not be made."""
    prof = model_profile.profile("joni-semantic")
    context = state_slice(cs, text, k=prof.state_k)
    ctx = "\n".join(f"- {t}" for t in context) or "(none yet)"
    user = (f"SOURCE:\n{text[:2000]}\n\nRELEVANT EXISTING STATE (state_k={prof.state_k}):\n{ctx}"
            f"\n\nTopic hint: {topic_hint}")
    output, cap = model_call.call(prof, _SYS, user, run_id=run_id, store_dir=store_dir,
                                  budget=budget, runs_per_week=runs_per_week)
    if output is None or cap is None:
        return [], None
    return _parse(output, topic_hint), cap


def project_and_learn(cs, judged, extensions: dict, proto, cycle: int, *,
                      max_items: int = 2, budget=None, runs_per_week: int = 0) -> dict:
    """When enabled, project a few read items into candidate claim proposals and submit them
    through the gate (SOURCE, candidate). The model call is captured for replay. No-op otherwise.
    The deterministic reader path is unchanged - this adds a model proposal arm, never replaces."""
    out = {"projected": 0, "claims": 0}
    if not enabled():
        return out
    from . import facets, sprout
    store_dir = paths().model_calls
    run_id = f"joni-c{cycle}"
    log = extensions.setdefault("semantic_calls", [])
    facet_log = extensions.setdefault("facet_log", [])
    sprout_log = extensions.setdefault("sprout_log", [])
    for item, rel in judged:
        if out["projected"] >= max_items:
            break
        text = f"{getattr(item, 'title', '')}. {getattr(item, 'summary', '')}".strip()
        topic_hint = getattr(rel, "topic", None) or "unsorted"
        # SproutRAG (#160): for a LONG source, expand into multi-granular, coherent passages with
        # the embedding tree (no LLM call). Only fires on a multi-sentence source; a short
        # title+summary trees to nothing and falls through unchanged.
        sprout_units = sprout.extract(text)
        if sprout_units:
            units = sprout_units
            sprout_log.append({"cycle": cycle, "source": getattr(item, "key", ""),
                               "candidates": len(sprout_units)})
        else:
            # FaBle (#136): project each FACET of the source on its own, so a faceted source yields
            # faceted candidates instead of one blurred whole. Disabled -> one unit (the whole
            # text), i.e. exactly the original behaviour.
            units = facets.decompose(text, budget=budget, runs_per_week=runs_per_week,
                                     cycle=cycle, store_dir=store_dir) or [text]
        item_claims = 0
        last_cap = None
        for unit in units[:3]:
            props, cap = claim_proposals(unit, topic_hint=topic_hint, cs=cs, run_id=run_id,
                                         store_dir=store_dir, budget=budget,
                                         runs_per_week=runs_per_week)
            if not props or cap is None:
                continue
            for p in props:
                cs.learn(p["text"], p["topic"], source_id=f"granite:{cap.call_id}")
                out["claims"] += 1
                item_claims += 1
            last_cap = cap
            log.append({"call_id": cap.call_id, "served_model": cap.served_model,
                        "state_k": cap.state_k, "replayed": cap.replayed,
                        "claims": len(props), "source": getattr(item, "key", "")})
        if item_claims == 0:
            continue
        out["projected"] += 1
        if len(units) > 1:
            facet_log.append({"cycle": cycle, "source": getattr(item, "key", ""),
                              "facets": len(units), "claims": item_claims})
        proto.record(cycle, "projected",
                     f"Granite projected {item_claims} claim proposal(s) from "
                     f"{getattr(item, 'key', '?')} across {len(units)} facet(s) "
                     f"[{getattr(last_cap, 'served_model', '?')}] - candidates via the gate")
    extensions["facet_log"] = facet_log[-200:]
    extensions["sprout_log"] = sprout_log[-200:]
    extensions["semantic_calls"] = log[-200:]
    return out
