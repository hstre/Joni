"""Self-optimisation - Joni improving his own research *strategy* from his own results.

Most of Joni's semantic analyses come back ``insufficient-semantic-evidence`` because DESi
cannot find a clear frame in his thin, title-sized claims. A broader reader would just read
more of the same. Instead, Joni reads his *own* failure signal and adapts how he looks:

  * **under-framed** (mostly ``insufficient``) -> read full papers, not abstracts, and
    refine queries toward mechanism / evaluation framing (which tends to surface
    empirically-framed papers DESi can actually read);
  * **redundant** (mostly ``duplicate``) -> he is re-reading the same thing; broaden;
  * **over-broad topics** (mostly ``unrelated`` despite shared words) -> a topic is mixing
    frames; note it for refinement.

This is a *peripheral* improvement - it changes what Joni reads and the queries he uses
(state he is allowed to shape), never his protected logic. Deterministic, self-limiting,
and recorded: the adaptation is a provisional self-model claim plus a protocol event, so
the loop is auditable. Learned queries take effect next cycle - a closed loop over time.
"""

from __future__ import annotations

from collections import Counter

import desi_layer9 as l9

_MIN_SAMPLE = 8          # don't adapt on too few analyses
_INSUFFICIENT = "insufficient-semantic-evidence"


def assess(cs, *, recent: int = 40) -> dict:
    clusters = cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)[-recent:]
    dec = Counter(c.decision.value for c in clusters)
    total = sum(dec.values())

    def rate(k: str) -> float:
        return dec.get(k, 0) / total if total else 0.0

    return {"total": total, "decisions": dict(dec),
            "insufficient_rate": round(rate(_INSUFFICIENT), 3),
            "duplicate_rate": round(rate("duplicate"), 3),
            "unrelated_rate": round(rate("unrelated"), 3)}


def adapt(cs, extensions: dict, proto, cycle: int = 0) -> dict:
    a = assess(cs)
    if a["total"] < _MIN_SAMPLE:
        return {"changed": False, "gap": None, **a}

    learned = list(extensions.get("learned_queries", []))
    sm_done = set(extensions.get("strategy_sm", []))

    # -- under-framed: read full text + seek framed material ------------------------- #
    if a["insufficient_rate"] >= 0.6:
        topics = [t for t in cs.topics() if t][:2]
        refinements = [f"{t} mechanism" for t in topics] + [f"{t} evaluation" for t in topics]
        new = [q for q in refinements if q not in learned]
        extensions["read_fulltext_priority"] = True
        if new:
            extensions["learned_queries"] = (learned + new)[-8:]
        if "underframed" not in sm_done:
            cs.propose_self_model(
                "My inputs are often under-framed, so I get more from reading full papers "
                "and seeking mechanism/evaluation framing than from skimming abstracts.",
                evidence=[c.id for c in cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)[-5:]])
            sm_done.add("underframed")
            extensions["strategy_sm"] = sorted(sm_done)
        if new or "underframed" not in (extensions.get("strategy_seen") or []):
            proto.record(cycle, "strategy",
                         f"under-framed inputs ({int(a['insufficient_rate'] * 100)}% "
                         f"insufficient) -> read full text; refine queries: "
                         f"{', '.join(new) or '(already refined)'}")
            return {"changed": True, "gap": "underframed", "added": new, **a}
        return {"changed": False, "gap": "underframed", "added": [], **a}

    # -- redundant: broaden away from duplicates ------------------------------------- #
    if a["duplicate_rate"] >= 0.5:
        proto.record(cycle, "strategy",
                     f"redundant inputs ({int(a['duplicate_rate'] * 100)}% duplicate) -> "
                     "broaden: lean on self-invented hypotheses over re-reading")
        return {"changed": True, "gap": "redundant", "added": [], **a}

    # -- over-broad topics: a topic mixes frames ------------------------------------- #
    if a["unrelated_rate"] >= 0.5 and "overbroad" not in sm_done:
        cs.propose_self_model(
            "Some of my topics mix different frames, so shared words there do not mean "
            "shared concepts - I should split them more finely.",
            evidence=[c.id for c in cs.core.all(l9.ObjectType.SEMANTIC_CLUSTER)[-5:]])
        sm_done.add("overbroad")
        extensions["strategy_sm"] = sorted(sm_done)
        proto.record(cycle, "strategy",
                     f"over-broad topics ({int(a['unrelated_rate'] * 100)}% unrelated) -> "
                     "noted: split topics more finely")
        return {"changed": True, "gap": "overbroad", "added": [], **a}

    return {"changed": False, "gap": "ok", **a}
