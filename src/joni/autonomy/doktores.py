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
_REVIEWABLE_SOURCES = {"arxiv", "huggingface", "zenodo", "openalex", "ssrn", "openclaw", "github"}

_MAX_REVIEW = 3          # at most this many sources examined per firing (each is one model call)
_MAX_NEW = 1             # at most one fresh Auftrag filed per cycle
_COOLDOWN = 200          # cycles before Doktores may re-file an order for the same module

# Scouting weights toward the high-signal sources. The passively-fetched topic feed is dominated by
# Zenodo's "most recent" firehose (mostly off-topic), so Doktores reviews the relevance-scouted
# papers FIRST and admits at most this many passive Zenodo items per firing.
_SCOUT_PER_SOURCE = 3
_ZENODO_PASSIVE_MAX = 1
# OpenAlex source id for SSRN's working-paper series; used to pull a dedicated SSRN slice. Best-
# effort: if it ever changes, that sub-query just returns [] and the rest of the scout still runs
# (and general OpenAlex search already surfaces SSRN works anyway).
_SSRN_OPENALEX_SOURCE = "S4210172589"
# SSRN is sorted by discipline and is mostly social-science/economics; on Joni's ML/CS module
# queries the open SSRN slice returned off-topic health/econ papers. So the SSRN slice is restricted
# to OpenAlex field 17 = Computer Science (which contains the AI/ML/NLP subfields), i.e. only the
# computer-science & AI papers on SSRN.
_SSRN_OPENALEX_FIELD = "fields/17"

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
    client exists - the same gate as the other proposal arms. ``JONI_DOKTORES=0`` force-disables,
    and the benefit-review can deactivate it (``extension_review``) if it stops contributing."""
    from . import extension_review
    return (projection.enabled() and os.getenv("JONI_DOKTORES", "1") != "0"
            and extension_review.active("doktores"))


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


def _arxiv_scout(queries) -> list:
    """arXiv, **relevance-sorted** and **phrase-quoted**, so it returns the most ON-TOPIC methods
    (the default ArxivFetcher sorts by date). Fails quietly to []."""
    try:
        import urllib.parse
        from xml.etree import ElementTree as ET

        from .sources import Item, _get
        q = " OR ".join(f'all:"{t}"' for t in queries)
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"search_query": q, "start": 0, "max_results": _SCOUT_PER_SOURCE,
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


def _openalex_scout(queries, *, ssrn: bool = False) -> list:
    """OpenAlex, **relevance-sorted** for the module's queries. ``ssrn=True`` restricts the slice to
    SSRN's **computer-science & AI** working papers (source filter + the Computer Science field), so
    SSRN is scouted directly without its social-science/econ bulk. Fails quietly to []."""
    try:
        import urllib.parse

        from .sources import Item, _get, _openalex_abstract
        params = {"search": " ".join(list(queries)[:3]), "per_page": _SCOUT_PER_SOURCE,
                  "sort": "relevance_score:desc",
                  "mailto": "joni-autonomy@users.noreply.github.com"}
        if ssrn:
            params["filter"] = (f"primary_location.source.id:{_SSRN_OPENALEX_SOURCE},"
                                f"primary_topic.field.id:{_SSRN_OPENALEX_FIELD}")
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        out = []
        for w in json.loads(_get(url)).get("results", []):
            wid = str(w.get("id") or "").rsplit("/", 1)[-1]
            title = (w.get("title") or w.get("display_name") or "").strip()
            if not title or not wid:
                continue
            loc = w.get("primary_location") or {}
            link = loc.get("landing_page_url") or w.get("doi") or f"https://openalex.org/{wid}"
            out.append(Item("ssrn" if ssrn else "openalex", wid, title, link,
                            _openalex_abstract(w.get("abstract_inverted_index"))))
        return out
    except Exception:  # noqa: BLE001
        return []


def _github_scout(queries) -> list:
    """Search GitHub directly for module-relevant repositories (sorted by stars), so a tool/method
    shipped only as code - not a paper - is seen too. Reuses GitHubFetcher; quiet on []."""
    try:
        from .sources import GitHubFetcher
        return GitHubFetcher().fetch(list(queries)[:3], limit=_SCOUT_PER_SOURCE)
    except Exception:  # noqa: BLE001
        return []


def _scout(queries) -> list:
    """Best-effort targeted scouting for one non-core module across the high-signal sources, each
    **relevance-sorted** and best-effort: arXiv + OpenAlex (which also indexes SSRN) + a dedicated
    SSRN slice + a direct GitHub repo search. The merged, deduped list is reviewed FIRST, ahead of
    the Zenodo-heavy passive feed. A scouting outage is never fatal - passive items still get
    reviewed."""
    if not queries:
        return []
    out, seen = [], set()
    for it in (_arxiv_scout(queries) + _openalex_scout(queries)
               + _openalex_scout(queries, ssrn=True) + _github_scout(queries)):
        k = getattr(it, "key", None)
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


_COH_SYS = (
    "You judge whether a research HYPOTHESIS is INTERNALLY COHERENT and logically stringent - "
    "self-consistent, free of internal contradiction, and a meaningful, testable conjecture. Judge "
    "ONLY its internal logic and clarity, NOT whether the literature supports it: a novel idea "
    "need not be backed by any paper yet, and lack of external support is NOT a reason to call it "
    "incoherent. Output ONLY a JSON object: {\"coherent\": true|false, \"reason\": <one "
    "short sentence on the logic>}."
)


def _hyp_every() -> int:
    return max(1, int(os.getenv("JONI_DOKTORES_HYP_EVERY", "5")))


def assess_hypotheses(cs, extensions: dict, proto, cycle: int, *, budget=None,
                      runs_per_week: int = 0) -> dict:
    """Doktores assesses Joni's OWN ideas for INTERNAL LOGICAL COHERENCE - not for literature
    support. A novel idea has no paper behind it yet; requiring external evidence would stop Joni
    inventing anything new. So the only bar here is: is the hypothesis self-consistent and logically
    stringent? The verdict is recorded and shown; it never confirms, activates or deletes the idea
    (the gated ladder still governs that). No-op when disabled, not due, or all ideas assessed.
    """
    if not enabled():
        return {"assessed": 0}
    last = extensions.get("doktores_hyp_last_cycle")
    if last is not None and cycle - last < _hyp_every():
        return {"assessed": 0}
    hyps = cs.hypotheses()
    if not hyps:
        return {"assessed": 0}

    done = extensions.setdefault("doktores_hyp_assessed", [])
    target = next((h for h in sorted(hyps, key=lambda c: int(c.id.split("-")[-1]))
                   if h.id not in set(done)), None)
    if target is None:
        return {"assessed": 0}                         # all assessed until new ideas appear

    user = (f"HYPOTHESIS: {getattr(target, 'text', '')}\nTOPIC: {getattr(target, 'topic', '')}\n\n"
            "Is this idea internally coherent and logically stringent?")
    out, _cap = model_call.call(
        model_profile.profile("joni-hard"), _COH_SYS, user,
        run_id=f"joni-c{cycle}-dokcoh", store_dir=paths().model_calls,
        escalation_reason="doktores-coherence-assessment",
        budget=budget, runs_per_week=runs_per_week)
    if out is None:
        return {"assessed": 0}                         # budget/unavailable - retry the idea later

    extensions["doktores_hyp_last_cycle"] = cycle
    verdict = _parse(out) or {}
    coherent = verdict.get("coherent") is True
    reason = str(verdict.get("reason", ""))[:200]
    done.append(target.id)
    extensions["doktores_hyp_assessed"] = done[-500:]
    log = extensions.setdefault("doktores_hyp_log", [])
    log.append({"cycle": cycle, "hypothesis": target.id, "topic": getattr(target, "topic", ""),
                "coherent": coherent, "reason": reason})
    extensions["doktores_hyp_log"] = log[-40:]
    proto.record(cycle, "research",
                 f"Doktores assessed idea {target.id} on '{getattr(target, 'topic', '')}': "
                 f"{'coherent' if coherent else 'INCOHERENT'} - {reason}")
    return {"assessed": 1, "hypothesis": target.id, "coherent": coherent}


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

    # Scout literature for a non-core module, reviewed first; the passively-fetched items fill the
    # rest. The self-diagnostic (introspect) steers Doktores to Joni's TOP measured weakness if it
    # named one; else round-robin over the modules. Both deduped against Doktores' own seen-set.
    mkeys = list(commission._EXTENSIBLE)
    steer = extensions.get("introspection_module")
    if steer in mkeys:
        target_module = steer
    else:
        midx = int(extensions.get("doktores_module_idx", 0)) % len(mkeys)
        extensions["doktores_module_idx"] = (midx + 1) % len(mkeys)
        target_module = mkeys[midx]
    scouted = _scout(_MODULE_QUERIES.get(target_module, ()))
    # Scouted (relevance-sorted arXiv/OpenAlex/SSRN/GitHub) is reviewed first; the passive feed
    # fills the rest, but the Zenodo "most recent" firehose is capped so it cannot crowd out the
    # on-topic finds.
    reviewable, batch, zen = [], set(), 0
    for it in list(scouted) + list(items or []):
        src = getattr(it, "source", "")
        k = getattr(it, "key", None)
        if src not in _REVIEWABLE_SOURCES or not k or k in seen or k in batch:
            continue
        if src == "zenodo":
            if zen >= _ZENODO_PASSIVE_MAX:
                continue
            zen += 1
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
