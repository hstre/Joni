"""LLM method gate - is this actually a reusable, on-domain technique Kevin could trial?

The lexical harvest (``methods._looks_like_method``) triggers on hint words ('framework',
'approach', 'pipeline'), which every second paper abstract contains - and the embedding domain
gate (``quality.on_domain_text``) is fail-open without an embedder, i.e. DEAD in the production
runner. Result: a shelf of 200+ 'methods' that are off-domain paper titles ('Cosmological
equations from a compressible vorton vacuum'), with zero ready for a trial.

This is the same discipline the topic mint got (``topic_review``): the pinned Granite model
judges a candidate BEFORE it is shelved, and a bounded review drains the already-shelved
graveyard. The model is **non-authoritative**: an *invalid* verdict only withholds/retires a
0-trial CANDIDATE through the gate (``METHOD_REJECT``, protocolled); a method with any recorded
trial, or one minted by Joni's own governed emergence path (``joni:*`` origins, which pass the
Layer-9 synthesis-eligible gate), is never touched. No verdict (call failed, gate off) shelves
nothing and burns nothing - the candidate is judged again later.

Opt-in behind the same master switch as the rest of the semantic layer
(``JONI_SEMANTIC_PROPOSALS``) with its own opt-out (``JONI_METHOD_LLM``); off -> the legacy
lexical harvest stands alone.
"""

from __future__ import annotations

import json
import os
import re

import desi_layer9 as l9

from . import model_call, model_profile, projection
from .config import paths

_SYS = (
    "You are a method gatekeeper for an epistemic reasoning agent whose domain is AI agents, "
    "large language models, model routing/serving, memory and continuity, alignment and safety, "
    "evaluation and benchmarking, reasoning, epistemics (claims/evidence/provenance), and the "
    "software/ML engineering around them. Given a candidate METHOD (name + summary), decide "
    "whether it names a reusable technique, tool, algorithm or procedure that could actually be "
    "APPLIED within that domain - or is junk: an off-domain paper title, a result/finding rather "
    "than a method, marketing copy, or an incoherent fragment. Output ONLY a JSON object "
    "{\"valid\": true|false, \"reason\": <short>}. Be strict: when in doubt that it is a real, "
    "applicable, on-domain method, answer false.")

_FENCE = re.compile(r"^```[a-zA-Z]*\n|\n```$")


def enabled() -> bool:
    return projection.enabled() and os.getenv("JONI_METHOD_LLM", "1") != "0"


def _max_calls() -> int:
    return max(0, int(os.getenv("JONI_METHOD_LLM_MAX_CALLS", "3")))


def _parse_verdict(output: str) -> bool | None:
    body = _FENCE.sub("", (output or "").strip())
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("valid"), bool):
        return data["valid"]
    return None


def judge_method(name: str, summary: str, *, extensions: dict, cycle: int = 0,
                 budget=None, runs_per_week: int = 0) -> bool | None:
    """One cached Granite verdict for a candidate method: ``True`` (a real, applicable method) /
    ``False`` (junk) / ``None`` (no verdict - gate disabled, call failed, unparseable; the caller
    must treat that as 'not judged', never as a guess). Verdicts are cached by method NAME in
    ``method_llm_seen`` so harvest-time and review-time judgments share one memory."""
    seen = dict(extensions.get("method_llm_seen", {}))
    key = (name or "").strip()[:80]
    if key in seen:
        return seen[key] == "valid"
    if not enabled():
        return None
    user = f"CANDIDATE METHOD: {key}\n\nSUMMARY:\n{(summary or '(none)').strip()[:600]}"
    prof = model_profile.profile("joni-semantic")
    output, cap = model_call.call(prof, _SYS, user, run_id=f"methodrev-c{cycle}",
                                  store_dir=paths().model_calls, budget=budget,
                                  runs_per_week=runs_per_week)
    if output is None or cap is None:
        return None                             # a failed call is no verdict, not a guess
    valid = _parse_verdict(output)
    if valid is None:
        return None
    seen[key] = "valid" if valid else "invalid"
    extensions["method_llm_seen"] = dict(sorted(seen.items())[-2000:])
    return valid


def review_methods(cs, extensions: dict, proto, cycle: int = 0, *,
                   max_retire: int = 5, budget=None, runs_per_week: int = 0) -> dict:
    """Drain the shelved graveyard: judge a few not-yet-judged CANDIDATE methods and retire the
    junk through the gate. Only source-harvested (non-``joni:*``), 0-trial candidates are ever
    touched; a trialed method is Kevin's business, a governed emergent one already passed Layer 9.
    Cached + bounded per cycle. No-op when disabled."""
    out = {"reviewed": 0, "rejected": 0}
    if not enabled():
        return out
    seen = extensions.get("method_llm_seen", {})
    judged_calls = 0
    for m in cs.core.all(l9.ObjectType.METHOD):
        if out["rejected"] >= max_retire or judged_calls >= _max_calls():
            break
        name = (m.name or "").strip()[:80]
        if (m.status.value != "candidate" or (m.origin or "").startswith("joni")
                or getattr(m, "trial_count", 0) > 0):
            continue
        cached = name in seen
        valid = judge_method(name, m.summary or "", extensions=extensions, cycle=cycle,
                             budget=budget, runs_per_week=runs_per_week)
        if not cached:
            judged_calls += 1
        if valid is None:
            continue
        if not cached:
            out["reviewed"] += 1
        if valid:
            continue
        try:
            cs.reject_method(m.id)
        except Exception:  # noqa: BLE001 - a stubborn method must never break the cycle
            continue
        out["rejected"] += 1
    if out["rejected"]:
        proto.record(cycle, "regulate",
                     f"Granite method-review retired {out['rejected']} junk method "
                     f"candidate(s) - not a reusable, on-domain technique; trialed and "
                     "emergent methods untouched")
    return out
