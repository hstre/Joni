"""Drain the 'forum' category error - provenance is not a topic.

85% of Joni's active claims carry the topic ``forum``. But 'forum' says where a claim came FROM,
not what it is ABOUT - provenance posing as a topic, exactly the category-purity violation the
Alexandria protocol forbids. As long as that stock stands, every panel metric (top-bucket
dominance, entropy, weak-claim share) mostly measures this one mistake.

Two deterministic, bounded, gate-recorded moves per cycle, both fail-open per item:

  * **re-file** - a forum claim whose content clearly names one of Joni's real tracked topics is
    moved there: a successor claim is minted with the same text + source provenance (explicit
    ``refile-of`` marker, derived_from lineage), live support carried, the original superseded
    (``core_state.refile_claim``). Nothing invents a topic here: content can only route INTO an
    established topic, never mint one (that path has its own gate).
  * **retire** - a 0-support forum claim whose content routes nowhere is chatter from the
    pre-substance-gate era: rejected through the gate (still in the chain, no longer active).

A supported claim that routes nowhere is KEPT and counted honestly - support means someone found
it worth corroborating; mis-filed is better than lost. The same router also serves the inflow
(``humans._topic_for``), so new forum voices land on content topics whenever one clearly fits.

Persona safety: 'forum' is a _SINK_THEME - a housekeeping rejection/supersede here never becomes
a persona lesson, and the persona headline counts sink corrections separately.
"""

from __future__ import annotations

import os
import re

from . import quality

_WORD = re.compile(r"[A-Za-z][A-Za-z-]*")


def real_topics(cs) -> list[str]:
    """The topics content may route INTO: lexically good, not a sink, and carrying at least two
    active claims (a real cluster - a one-claim orphan is not a destination)."""
    from collections import Counter
    counts: Counter = Counter()
    for c in cs.active_claims():
        t = getattr(c, "topic", None)
        if t and t != "forum" and not quality.is_reserved_topic(t) and quality.is_good_topic(t):
            counts[t] += 1
    return sorted(t for t, n in counts.items() if n >= 2)


def route_topic(text: str, topics: list[str]) -> str | None:
    """Which established topic does this text clearly name? Deterministic lexical routing: a
    topic matches when it appears as a whole word in the text (naive singular/plural both ways).
    Most hits wins; ties break alphabetically (stable); no hit -> None. This can only choose
    among *existing* topics - it never invents one."""
    words = {w.lower() for w in _WORD.findall(text or "")}
    both = (words | {w + "s" for w in words} | {w[:-1] for w in words if w.endswith("s")}
            | {w[:-3] + "y" for w in words if w.endswith("ies")})
    best: str | None = None
    best_hits = 0
    for t in topics:
        parts = t.lower().split("-")
        hits = sum(1 for p in parts if p in both)
        if hits == len(parts) and hits > 0 and (hits > best_hits or
                                                (hits == best_hits and (best is None or t < best))):
            best, best_hits = t, hits
    return best


def reclassify_forum(cs, extensions: dict, proto, cycle: int = 0, *,
                     max_refile: int | None = None, max_retire: int | None = None) -> dict:
    """One bounded pass over the active 'forum' stock: re-file what routes, retire unroutable
    0-support chatter, keep (and count) supported claims that route nowhere."""
    from .homeostasis import supports_map
    if max_refile is None:
        max_refile = max(0, int(os.getenv("JONI_REFILE_MAX", "8")))
    if max_retire is None:
        max_retire = max(0, int(os.getenv("JONI_FORUM_RETIRE_MAX", "25")))
    out = {"refiled": 0, "retired": 0, "kept_supported": 0, "remaining": 0}
    stock = sorted((c for c in cs.active_claims() if getattr(c, "topic", None) == "forum"),
                   key=lambda c: int(c.id.split("-")[-1]))
    if not stock:
        return out
    topics = real_topics(cs)
    smap = supports_map(cs)
    moved: list[str] = []
    for c in stock:
        if out["refiled"] >= max_refile and out["retired"] >= max_retire:
            break
        target = route_topic(c.text, topics)
        try:
            if target is not None and out["refiled"] < max_refile:
                cs.refile_claim(c.id, target)
                out["refiled"] += 1
                if target not in moved:
                    moved.append(target)
            elif target is None and smap.get(c.id, 0) == 0 and out["retired"] < max_retire:
                cs.reject_claim(c.id)
                out["retired"] += 1
            elif target is None and smap.get(c.id, 0) > 0:
                out["kept_supported"] += 1          # supported but unroutable: kept, honestly
        except Exception:  # noqa: BLE001 - one stubborn claim must never break the pass
            continue
    out["remaining"] = sum(1 for c in cs.active_claims()
                           if getattr(c, "topic", None) == "forum")
    if out["refiled"] or out["retired"]:
        proto.record(cycle, "regulate",
                     f"forum reclassification: {out['refiled']} re-filed"
                     + (f" ({', '.join(moved[:6])})" if moved else "")
                     + f", {out['retired']} unroutable 0-support claim(s) retired, "
                       f"{out['kept_supported']} supported kept, {out['remaining']} remaining "
                       "- provenance is not a topic")
    return out
