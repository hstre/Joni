"""Method harvesting - Joni storing methods he finds, for Kevin.

When Joni reads something that describes a reusable technique - a framework, a library, a
named algorithm, an approach - he stores it in the shared Layer 9 core as a **method
candidate**. He never promotes it: a model/source-found method stays `candidate` until
Kevin trials it and a human/operator promotes it. Joni just fills the shelf.

GitHub repositories are treated as methods by default (a tool *is* a reusable technique);
papers/posts qualify when their text signals a method.
"""

from __future__ import annotations

_METHOD_HINTS = frozenset({
    "method", "technique", "approach", "algorithm", "framework", "procedure",
    "strategy", "recipe", "toolkit", "pipeline", "protocol", "scheme", "library",
    "how to", "heuristic",
})


def _looks_like_method(item) -> bool:
    if item.source == "github":
        return True
    blob = (item.title + " " + item.summary).lower()
    return any(h in blob for h in _METHOD_HINTS)


def harvest(cs, judged, extensions: dict, proto, cycle: int = 0, *, max_methods: int = 2) -> dict:
    seen = set(extensions.get("methods_seen", []))
    found = 0
    for item, rel in judged:
        if found >= max_methods:
            break
        if item.key in seen or not _looks_like_method(item):
            continue
        cs.propose_method(
            name=item.title[:80],
            summary=(item.summary or item.title)[:240],
            applicable_to=(rel.topic,) if rel.topic else (),
            origin=item.url)
        seen.add(item.key)
        found += 1
        proto.record(cycle, "method",
                     f"stored method candidate for Kevin: {item.title[:70]} (from {item.source})")
    extensions["methods_seen"] = sorted(seen)[-1000:]
    return {"methods": found}
