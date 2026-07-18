"""One-time, auditable reconsolidation of the ACCUMULATED legacy state (operator review, point 2).

The per-cycle drains (``homeostasis.retire_junk_*``, ``reclassify``) are deliberately rate-limited
(a few objects per cycle), so they take hundreds of cycles to work through a backlog that already
holds synthetic hypotheses over proper names, repo slugs, function words and random recurring terms
minted as "underlying factors", plus a large un-tested method pile. This module does the deliberate
full sweep the drip cannot: it **reads** the whole state and classifies every topic, hypothesis and
method into three buckets, with a reason for each -

  * ``junk``       - clearly not a research object: a sink/provenance topic, a name/slug/title
    fragment, a non-admissible 0-support hypothesis, an ``-as-a-lens`` method on a junk term. Only
    these are eligible for reclassification.
  * ``borderline`` - plausible but unproven: a non-admissible hypothesis that nonetheless has
    support, a real method that was simply never trialed. **Never auto-actioned** - a human decides.
  * ``keep``       - admissible / supported / trialed / reserved.

The classification is **read-only** and produces an auditable report. ``apply_junk`` is a separate,
bounded, opt-in step that only ever rejects ``junk``-verdict objects, and only through the existing
gate operators (``cs.reject_claim`` / ``cs.reject_method``) - so history and provenance are fully
preserved and nothing rewrites the ledger. Borderline objects are never touched.
"""
from __future__ import annotations

import desi_layer9 as l9

JUNK, BORDERLINE, KEEP = "junk", "borderline", "keep"
_LENS_SUFFIX = "-as-a-lens"


def classify_topic(topic: str) -> tuple[str, str]:
    from . import quality
    if quality.is_reserved_topic(topic):
        return KEEP, "reserved topic"
    if quality.is_sink_topic(topic):
        return JUNK, "sink / provenance bucket, not a subject"
    if not quality.is_good_topic(topic):
        return JUNK, "not a good topic (name, slug or title fragment)"
    return KEEP, "admissible topic"


def classify_hypothesis(text: str, *, support: int) -> tuple[str, str]:
    from . import quality
    if quality.hypothesis_admissible(text):
        return KEEP, "substantive and on-domain"
    if support > 0:
        return BORDERLINE, "not admissible but has support - a human decides"
    return JUNK, "not admissible and 0 support"


def classify_method(name: str, *, trial_count: int, status: str = "candidate") -> tuple[str, str]:
    if status in ("rejected", "superseded"):
        return KEEP, "already retired"       # already dealt with - not re-flagged, not re-rejected
    from . import quality
    if trial_count > 0:
        return KEEP, "trialed"
    if name.endswith(_LENS_SUFFIX):
        term = name[: -len(_LENS_SUFFIX)]
        if not (quality.is_meaningful_term(term) and quality.is_good_topic(term)):
            return JUNK, f"lens on a junk term '{term}', never trialed"
        return BORDERLINE, "lens on a real term but never trialed - a human decides"
    return BORDERLINE, "harvested method, never trialed - a human decides"


def _group(items: list[dict], *, sample: int) -> dict:
    """Group already-classified items into {verdict: {count, samples[]}} with bounded samples."""
    out: dict[str, dict] = {JUNK: {"count": 0, "samples": []},
                            BORDERLINE: {"count": 0, "samples": []},
                            KEEP: {"count": 0, "samples": []}}
    for it in items:
        b = out[it["verdict"]]
        b["count"] += 1
        if len(b["samples"]) < sample:
            b["samples"].append({"id": it["id"], "label": it["label"], "reason": it["reason"]})
    return out


def audit(cs, *, sample: int = 15) -> dict:
    """Read-only classification of the whole legacy state. Returns a bounded, grouped report."""
    from . import homeostasis
    topic_items = [{"id": t, "label": t, "verdict": v, "reason": r}
                   for t in cs.topics() for v, r in [classify_topic(t)]]
    smap = homeostasis.supports_map(cs)
    hyp_items = []
    for h in cs.hypotheses():
        v, r = classify_hypothesis(h.text, support=smap.get(h.id, 0))
        hyp_items.append({"id": h.id, "label": h.text[:80], "verdict": v, "reason": r})
    meth_items = []
    for m in cs.core.all(l9.ObjectType.METHOD):
        v, r = classify_method(str(getattr(m, "name", "")),
                               trial_count=int(getattr(m, "trial_count", 0)),
                               status=getattr(getattr(m, "status", None), "value", "candidate"))
        meth_items.append({"id": m.id, "label": str(getattr(m, "name", ""))[:80],
                           "verdict": v, "reason": r})
    return {"topics": _group(topic_items, sample=sample),
            "hypotheses": _group(hyp_items, sample=sample),
            "methods": _group(meth_items, sample=sample),
            "totals": {"topics": len(topic_items), "hypotheses": len(hyp_items),
                       "methods": len(meth_items)}}


def render_markdown(report: dict) -> str:
    lines = ["# Joni - Reconsolidation Audit (read-only)", "",
             "Clear junk is eligible for gate-mediated rejection; **borderline is never "
             "auto-actioned** (a human decides); keep is admissible/supported/trialed.", ""]
    for kind in ("topics", "hypotheses", "methods"):
        g = report[kind]
        total = report["totals"][kind]
        lines.append(f"## {kind} - {total} total: "
                     f"{g[JUNK]['count']} junk / {g[BORDERLINE]['count']} borderline / "
                     f"{g[KEEP]['count']} keep")
        for verdict in (JUNK, BORDERLINE):
            if not g[verdict]["samples"]:
                continue
            lines.append(f"\n**{verdict}** (first {len(g[verdict]['samples'])}):")
            for s in g[verdict]["samples"]:
                lines.append(f"- `{s['label']}` - {s['reason']}")
        lines.append("")
    return "\n".join(lines)


def apply_junk(cs, proto, cycle: int = 0, *, kinds=("hypotheses", "methods"),
               max_apply: int = 10_000) -> dict:
    """OPT-IN, operator-run: reject only ``junk``-verdict hypotheses/methods through the existing
    gate operators (append-only, provenance preserved). Borderline and keep are never touched;
    topics are excluded by default (re-filing is ``reclassify``'s job). Bounded and fail-open."""
    from . import homeostasis
    done = {"hypotheses": 0, "methods": 0}
    if "hypotheses" in kinds:
        smap = homeostasis.supports_map(cs)
        for h in list(cs.hypotheses()):
            if done["hypotheses"] >= max_apply:
                break
            if classify_hypothesis(h.text, support=smap.get(h.id, 0))[0] != JUNK:
                continue
            try:
                cs.reject_claim(h.id)
                done["hypotheses"] += 1
            except Exception:  # noqa: BLE001 - a stubborn object must never break the sweep
                continue
    if "methods" in kinds:
        for m in list(cs.core.all(l9.ObjectType.METHOD)):
            if done["methods"] >= max_apply:
                break
            if classify_method(str(getattr(m, "name", "")),
                               trial_count=int(getattr(m, "trial_count", 0)),
                               status=getattr(getattr(m, "status", None), "value", "candidate")
                               )[0] != JUNK:
                continue
            try:
                cs.reject_method(m.id)
                done["methods"] += 1
            except Exception:  # noqa: BLE001
                continue
    proto.record(cycle, "regulate",
                 f"reconsolidation apply: rejected {done['hypotheses']} junk hypothesis(es), "
                 f"{done['methods']} junk method(s) (gate-mediated, provenance preserved)")
    return done


__all__ = ["classify_topic", "classify_hypothesis", "classify_method", "audit",
           "render_markdown", "apply_junk", "JUNK", "BORDERLINE", "KEEP"]
