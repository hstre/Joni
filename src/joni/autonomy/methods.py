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


def harvest(cs, judged, extensions: dict, proto, cycle: int = 0, *, max_methods: int = 2,
            budget=None, runs_per_week: int = 0) -> dict:
    from ..method_trial import problems
    from . import method_review, quality
    seen = set(extensions.get("methods_seen", []))
    found = rejected_titles = 0
    for item, rel in judged:
        if found >= max_methods:
            break
        if item.key in seen or not _looks_like_method(item):
            continue
        # A paper's TITLE is not a procedure. The breakdown showed ~68% of shelved 'methods' were
        # long harvested paper titles ('MemoryWAM: Efficient World Action Modeling ...'), never
        # trialable. Only shelve a source-derived method whose title reads as a SHORT procedure name
        # (a repo name, a named technique) - the same short-name gate the trial matcher applies. A
        # GitHub repo is exempt: a repo IS a tool. (Extracting the real procedure FROM a paper is a
        # separate feature; this just stops shelving the title as if it were the method.)
        if item.source != "github" and not problems.is_short_procedure_name(item.title):
            seen.add(item.key)                 # a paper title, not a procedure - never re-asked
            rejected_titles += 1
            proto.record(cycle, "method",
                         f"not a procedure (paper title), not shelved: {item.title[:70]}")
            continue
        # Domain gate: a GitHub repo is treated as a method by default, but generic off-domain
        # tooling (e.g. C++ coding guidelines) is not Joni's subject - don't shelve it for Kevin.
        if not quality.on_domain_text(f"{item.title} {item.summary}"):
            seen.add(item.key)                 # judged once, off-domain - don't reconsider
            continue
        # Granite gatekeeper BEFORE the shelf (the embedding gate above is fail-open without an
        # embedder, i.e. dead in the production runner; the hint words match every second paper
        # abstract). Invalid -> never shelved, finalised; no verdict -> unburned, retried later;
        # gate disabled -> the legacy lexical harvest stands alone.
        if method_review.enabled():
            verdict = method_review.judge_method(
                item.title[:80], item.summary or item.title, extensions=extensions,
                cycle=cycle, budget=budget, runs_per_week=runs_per_week)
            if verdict is None:
                continue
            if verdict is False:
                seen.add(item.key)             # a real verdict: not a method, never re-asked
                proto.record(cycle, "method",
                             f"method candidate rejected by the gate: {item.title[:70]}")
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
    return {"methods": found, "titles_rejected": rejected_titles}
