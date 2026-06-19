"""Doktores' self-improvement review - the replacement for Kevin's creative arm.

Where Kevin generated free hypotheses from DESi blind spots, **Doktores** (Joni's independent
research organisation) does *method/tool review for self-improvement*: it reads the papers Joni
just fetched and the OpenClaw extensions on offer and asks, for each, the one question that
matters - **could this concretely make Joni better by extending one of his OWN non-core modules,
without touching the protected core?** When the answer is a grounded yes, it files an *Auftrag an
Claude* (a non-core extension order, with the source as evidence and a measurable acceptance
criterion), implemented by a human-gated PR through the normal joni-auftrag pipeline - never a
core change, never self-applied.

Boundaries (identical to ``commission.py``):
  * **non-core only** - a finding may target only a key in ``commission._EXTENSIBLE``; the model is
    given that exact allowlist and a finding naming anything else is dropped.
  * **a source, not a decision** - Doktores writes the order; a human implements and merges it.
  * **real, captured, budget-metered** - uses Joni's own ``joni-hard`` model (DeepSeek via
    ``model_call``), replay-stable; a live call only happens if the weekly budget allows.

Gated like every model arm (``JONI_SEMANTIC_PROPOSALS=1``), cadence-spaced, and deduped per source
item + a per-module cooldown, so a long run never spams Claude.
"""

from __future__ import annotations

import json
import os

from . import commission, model_call, model_profile, projection
from .config import paths

# Which fetched items Doktores reviews: external papers + community software extensions.
# (Encyclopedic Wikipedia background and raw HN threads are not method/tool sources, so they are not
# reviewed here.)
_REVIEWABLE_SOURCES = {"arxiv", "huggingface", "zenodo", "openalex", "openclaw", "github"}

_MAX_REVIEW = 3          # at most this many sources examined per firing (each is one model call)
_MAX_NEW = 1             # at most one fresh Auftrag filed per cycle
_COOLDOWN = 200          # cycles before Doktores may re-file an order for the same module

# Targeted scouting: each firing, Doktores searches for literature relevant to the NEXT non-core
# module (round-robin), so reviews are module-relevant instead of whatever the topic-fetch happened
# to return. The model still judges every candidate freely against the full allowlist (it may answer
# 'false', or map it to a different module) - the scouting only biases WHICH papers it sees.
_MODULE_QUERIES = {
    "semantics-measurement": ("semantic textual similarity", "sentence embedding evaluation",
                              "distributional semantics distance"),
    "conflict-qualifier": ("natural language inference contradiction", "claim contradiction "
                           "detection", "argument relation classification"),
    "reader-sources": ("scientific paper retrieval", "research literature recommendation",
                       "scholarly document search"),
    "emergence": ("automated hypothesis generation", "analogical reasoning across domains",
                  "scientific concept synthesis"),
    "method-trialing": ("method ablation evaluation protocol", "benchmark for method transfer",
                        "experimental validation of techniques"),
}

_SYS = (
    "You are Doktores, the method-review arm of an autonomous reasoning agent named Joni. You read "
    "ONE external paper or software extension and judge ONE thing: could it concretely improve one "
    "of Joni's OWN non-core modules (given to you as an allowlist), WITHOUT touching his protected "
    "core? Be strict and grounded: only say yes when the source actually describes a method, "
    "technique or tool that maps onto a listed module; never invent a capability the source does "
    "not support, and never propose a core change. Output ONLY a JSON object. If it genuinely "
    "helps one listed module: {\"applicable\": true, \"component_key\": <EXACTLY one key from the "
    "allowlist>, \"title\": <short German imperative order>, \"motivation\": <why, grounded in the "
    "source, German>, \"desired\": <the concrete non-core change to that module, German>, "
    "\"acceptance\": <a measurable acceptance criterion, German>}. Otherwise: {\"applicable\": "
    "false}. No prose, no markdown, no questions."
)


def enabled() -> bool:
    """On only when the model arm is configured (``JONI_SEMANTIC_PROPOSALS=1``) and a real model
    client exists - the same gate as the other proposal arms. ``JONI_DOKTORES=0`` force-disables."""
    return projection.enabled() and os.getenv("JONI_DOKTORES", "1") != "0"


def _every() -> int:
    """Cadence: at most one review firing per this many cycles - bounds spend, not curiosity."""
    return max(1, int(os.getenv("JONI_DOKTORES_EVERY", "4")))


def _allowlist_block() -> str:
    return "\n".join(f"- {key}: {desc}" for key, (desc, _risk) in commission._EXTENSIBLE.items())


def _user_prompt(item) -> str:
    return (
        f"SOURCE ({getattr(item, 'source', '?')}): {getattr(item, 'title', '')}\n"
        f"URL: {getattr(item, 'url', '')}\n"
        f"ABSTRACT/DESCRIPTION:\n{(getattr(item, 'summary', '') or '')[:1800]}\n\n"
        f"Joni's non-core modules you may target (and ONLY these):\n{_allowlist_block()}\n\n"
        "Could this source concretely improve exactly one of those modules without touching the "
        "protected core? Answer with the JSON object only."
    )


def _parse(output: str) -> dict | None:
    if not output:
        return None
    try:
        obj = json.loads(output)
    except json.JSONDecodeError:
        start, end = output.find("{"), output.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            obj = json.loads(output[start:end + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _scout(queries) -> list:
    """Best-effort targeted paper search for one non-core module. Fails quietly to [] (a scouting
    outage is never fatal - the passively-fetched items still get reviewed)."""
    if not queries:
        return []
    try:
        from .sources import ArxivFetcher
        return ArxivFetcher().fetch(list(queries), limit=4)
    except Exception:  # noqa: BLE001
        return []


def review(cs, extensions: dict, proto, cycle: int, *, items, budget=None,
           runs_per_week: int = 0) -> list[dict]:
    """Review up to ``_MAX_REVIEW`` fresh papers/OpenClaw extensions for a non-core improvement to
    Joni, filing at most ``_MAX_NEW`` *Auftrag an Claude* this cycle. Returns the new orders (the
    caller routes them into ``commissions_new`` so the workflow opens joni-auftrag issues, exactly
    like ``commission.assess``). No-op when disabled, not yet due, or no real source on offer."""
    if not enabled():
        return []
    last = extensions.get("doktores_last_cycle")
    if last is not None and cycle - last < _every():           # cadence bounds spend
        return []

    seen = set(extensions.setdefault("doktores_seen", []))
    filed = extensions.setdefault("doktores_filed", {})        # component_key -> last cycle filed
    log = extensions.setdefault("doktores_review", [])         # for the page

    # Scout literature targeted at the NEXT non-core module (round-robin), reviewed first; the
    # passively-fetched items fill any remaining slots. Both deduped against Doktores' own seen-set.
    mkeys = list(commission._EXTENSIBLE)
    midx = int(extensions.get("doktores_module_idx", 0)) % len(mkeys)
    extensions["doktores_module_idx"] = (midx + 1) % len(mkeys)
    scouted = _scout(_MODULE_QUERIES.get(mkeys[midx], ()))
    reviewable, batch = [], set()
    for it in list(scouted) + list(items or []):
        k = getattr(it, "key", None)
        if (getattr(it, "source", "") in _REVIEWABLE_SOURCES
                and k and k not in seen and k not in batch):
            reviewable.append(it)
            batch.add(k)
    if not reviewable:
        return []

    extensions["doktores_last_cycle"] = cycle
    store_dir = paths().model_calls
    new: list[dict] = []
    examined = 0
    for item in reviewable[:_MAX_REVIEW]:
        seen.add(item.key)
        prof = model_profile.profile("joni-hard")
        output, cap = model_call.call(
            prof, _SYS, _user_prompt(item), run_id=f"joni-c{cycle}-doktores",
            store_dir=store_dir, escalation_reason="doktores-self-improvement-review",
            budget=budget, runs_per_week=runs_per_week)
        if output is None:                                     # budget cap reached -> stop cleanly
            break
        examined += 1
        verdict = _parse(output)
        applicable = bool(verdict and verdict.get("applicable") is True)
        key = str(verdict.get("component_key", "")) if verdict else ""
        entry = {"cycle": cycle, "source": getattr(item, "source", ""),
                 "title": getattr(item, "title", "")[:160], "url": getattr(item, "url", ""),
                 "served_model": getattr(cap, "served_model", "") if cap else "",
                 "applicable": applicable, "component_key": key if applicable else ""}
        log.append(entry)

        if not applicable or key not in commission._EXTENSIBLE:
            continue                                           # not a grounded non-core fit
        last_filed = filed.get(key)
        if last_filed is not None and cycle - last_filed < _COOLDOWN:
            continue                                           # this module ordered recently
        if len(new) >= _MAX_NEW:
            continue
        order = commission._commission(
            f"doktores:{key}", key, cycle=cycle,
            title=str(verdict.get("title") or "Erweiterung aus Doktores-Review"),
            motivation=str(verdict.get("motivation", "")),
            desired=str(verdict.get("desired", "")),
            acceptance=str(verdict.get("acceptance", "")),
            evidence={"found_by": "doktores", "source": getattr(item, "source", ""),
                      "ref": getattr(item, "url", ""), "source_title": getattr(item, "title", "")})
        order["found_by"] = "doktores"                         # provenance: literature/tool review
        filed[key] = cycle
        commission_log = extensions.setdefault("commissions", [])
        commission_log.append(order)
        extensions["commissions"] = commission_log[-50:]
        new.append(order)
        proto.record(cycle, "commission",
                     f"Doktores-Auftrag an Claude: {order['title']} - {key} (non-core, aus "
                     f"{getattr(item, 'source', '?')}: {getattr(item, 'title', '')[:60]})")

    extensions["doktores_seen"] = sorted(seen)[-3000:]
    extensions["doktores_review"] = log[-60:]
    if examined and not new:
        proto.record(cycle, "research",
                     f"Doktores reviewed {examined} source(s) for self-improvement - no non-core "
                     "fit this cycle")
    return new
