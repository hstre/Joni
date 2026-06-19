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
    """Best-effort targeted paper search for one non-core module: arXiv, **relevance-sorted** and
    **phrase-quoted**, so it returns the most ON-TOPIC methods (the default ArxivFetcher sorts by
    date, which returns the newest paper regardless of relevance). Fails quietly to [] - a scouting
    outage is never fatal, the passively-fetched items still get reviewed."""
    if not queries:
        return []
    try:
        import urllib.parse
        from xml.etree import ElementTree as ET

        from .sources import Item, _get
        q = " OR ".join(f'all:"{t}"' for t in queries)
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": q, "start": 0, "max_results": 4,
             "sortBy": "relevance", "sortOrder": "descending"})
        root = ET.fromstring(_get(url))
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        for e in root.findall("a:entry", ns):
            title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
            summary = (e.findtext("a:summary", default="", namespaces=ns) or "").strip()
            url_ = (e.findtext("a:id", default="", namespaces=ns) or "").strip()
            if title:
                out.append(Item("arxiv", url_.rsplit("/", 1)[-1], title, url_, summary))
        return out
    except Exception:  # noqa: BLE001
        return []


_HYP_SYS = (
    "You are Doktores' Literature Scout. Given Joni's working HYPOTHESIS and one paper abstract, "
    "state in ONE plain sentence what this paper actually FINDS that bears on the hypothesis - "
    "evidence that SUPPORTS or CHALLENGES it - grounded ONLY in the abstract. No citations, no "
    "hedging preamble. If the abstract is not relevant to the hypothesis, output exactly NONE."
)


def _hyp_every() -> int:
    return max(1, int(os.getenv("JONI_DOKTORES_HYP_EVERY", "5")))


def _hyp_queries(h) -> tuple:
    import re
    topic = (getattr(h, "topic", "") or "").strip()
    words = re.findall(r"[A-Za-z]{5,}", getattr(h, "text", "") or "")[:3]
    return tuple(dict.fromkeys(q for q in ([topic] + words) if q))[:3]


def research_hypotheses(cs, extensions: dict, proto, cycle: int, *, budget=None,
                        runs_per_week: int = 0) -> dict:
    """Give Joni's OWN hypotheses to Doktores: scout literature for the next un-researched
    hypothesis and bring back what a paper FINDS about it as a SOURCE (candidate, conflict-checked,
    never confirmed) - so the idea can earn support or be challenged through the normal gated path,
    never by Doktores' say-so. No-op when disabled, not due, or every hypothesis already researched.
    """
    if not enabled():
        return {"researched": 0}
    last = extensions.get("doktores_hyp_last_cycle")
    if last is not None and cycle - last < _hyp_every():
        return {"researched": 0}
    hyps = cs.hypotheses()
    if not hyps:
        return {"researched": 0}

    done = extensions.setdefault("doktores_hyp_researched", [])
    done_set = set(done)
    target = next((h for h in sorted(hyps, key=lambda c: int(c.id.split("-")[-1]))
                   if h.id not in done_set), None)
    if target is None:
        return {"researched": 0}                       # all researched until new hypotheses appear

    extensions["doktores_hyp_last_cycle"] = cycle
    seen = set(extensions.setdefault("doktores_seen", []))
    papers = [p for p in _scout(_hyp_queries(target))
              if getattr(p, "key", None) and p.key not in seen][:2]
    store_dir = paths().model_calls
    added = 0
    for p in papers:
        seen.add(p.key)
        user = (f"HYPOTHESIS: {getattr(target, 'text', '')}\n\nPAPER: {getattr(p, 'title', '')}\n"
                f"{(getattr(p, 'summary', '') or '')[:1500]}\n\n"
                "What does this paper find that bears on the hypothesis? One sentence, or NONE.")
        out, _cap = model_call.call(
            model_profile.profile("joni-hard"), _HYP_SYS, user,
            run_id=f"joni-c{cycle}-dokhyp", store_dir=store_dir,
            escalation_reason="doktores-hypothesis-research",
            budget=budget, runs_per_week=runs_per_week)
        if out is None:
            break
        finding = out.strip()
        if not finding or finding.upper().startswith("NONE"):
            continue
        cid = cs.hear(finding[:500], getattr(target, "topic", "") or "research",
                      handle="doktores", platform="research", origin="internal-research")
        added += 1
        log = extensions.setdefault("doktores_hyp_log", [])
        log.append({"cycle": cycle, "hypothesis": target.id, "topic": getattr(target, "topic", ""),
                    "source": getattr(p, "title", "")[:120], "ref": getattr(p, "url", ""),
                    "claim": cid, "finding": finding[:200]})
        extensions["doktores_hyp_log"] = log[-40:]
        proto.record(cycle, "research",
                     f"Doktores researched hypothesis {target.id} "
                     f"-> evidence from {getattr(p, 'title', '')[:50]} (source {cid}, "
                     "conflict-checked, never confirmed)")
    done.append(target.id)
    extensions["doktores_hyp_researched"] = done[-500:]
    extensions["doktores_seen"] = sorted(seen)[-3000:]
    return {"researched": 1 if added else 0, "hypothesis": target.id, "evidence": added}


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
