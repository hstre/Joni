"""The creativity engine - where Joni's new projects come from.

Joni's architecture names a creativity engine; this is its seam. A new project is
not invented by the renderer or a freeform model - it is proposed by a deterministic
engine from Joni's current state, then started by an audited operator like everything
else.

Two implementations behind one protocol:
  * ``LocalCreativity`` - self-contained and deterministic (the default). Builds a
    project idea from the strongest belief on a topic.
  * ``KevinCreativity`` - plugs in the sibling **Kevin** creativity-routing engine:
    it frames "how do I make progress on <topic>?" as a problem, routes it through
    unexplored-space -> wild variation -> method transfer -> selection, and turns the
    top promising candidate into a project. Opt in with ``JONI_USE_KEVIN=1``; if Kevin
    is not installed, Joni falls back to local creativity.

Both are deterministic (Kevin runs on its own MockLLM), so Joni stays replay-stable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .state import Layer9


@dataclass
class ProjectIdea:
    title: str
    topic: str
    rationale: str
    engine: str          # which engine proposed it (shows up as reviewed_by in the ledger)


@runtime_checkable
class CreativityEngine(Protocol):
    def propose(self, state: Layer9, topic: str) -> ProjectIdea:
        """Propose one new project for the given topic, grounded in current state."""


def _strongest_on(state: Layer9, topic: str):
    from .models import ClaimStatus

    live = [
        c for c in state.claims.values()
        if c.topic == topic and c.status in {ClaimStatus.ACTIVE, ClaimStatus.CONFIRMED}
    ]
    return max(live, key=lambda c: (c.support, c.id)) if live else None


class LocalCreativity:
    """Deterministic, self-contained idea generation. The default."""

    name = "local-creativity"

    def propose(self, state: Layer9, topic: str) -> ProjectIdea:
        strongest = _strongest_on(state, topic)
        if strongest is not None:
            title = f"Turn into practice: {strongest.text}"
            rationale = f"built on the strongest live belief on '{topic}' ({strongest.id})"
        else:
            title = f"Open exploratory work on {topic}"
            rationale = f"no strong belief yet on '{topic}' - explore it"
        return ProjectIdea(title=title, topic=topic, rationale=rationale, engine=self.name)


class KevinCreativity:
    """Plug in Kevin's creativity-routing engine as Joni's idea source."""

    name = "kevin"

    def __init__(self) -> None:
        # Import lazily so 'kevin' is a soft dependency.
        from kevin import Kevin  # noqa: F401  (presence check)

        self._fallback = LocalCreativity()

    def propose(self, state: Layer9, topic: str) -> ProjectIdea:
        from kevin import Kevin, Problem

        from .models import ClaimStatus

        known = tuple(
            c.text for c in state.claims.values()
            if c.topic == topic and c.status in {ClaimStatus.ACTIVE, ClaimStatus.CONFIRMED}
        )
        problem = Problem(
            statement=f"how do I make real progress on {topic}?",
            domain="self-improvement",
            known_approaches=known,
        )
        run = Kevin().run(problem, top_spaces=1)
        promising = [e for e in run.evaluations if e.verdict.value == "promising"]
        if not promising:
            return self._fallback.propose(state, topic)

        cand = {c.id: c for c in run.candidates}[promising[0].candidate_id]
        # Kevin candidates can be long and wild; distil a project title from the seed.
        title = _distil(cand.content)
        rationale = (
            f"proposed by Kevin: routed an under-worked space on '{topic}', varied it, "
            f"transferred a method, and selected the top candidate (score {promising[0].score})"
        )
        return ProjectIdea(title=title, topic=topic, rationale=rationale, engine=self.name)


def _distil(content: str, *, limit: int = 90) -> str:
    """Reduce a wild Kevin candidate to a project-title-sized phrase, deterministically."""
    head = content.split("  |  ", 1)[0].strip()       # drop the transferred-method tail
    head = head.rstrip(".?! ")
    if len(head) > limit:
        head = head[:limit].rsplit(" ", 1)[0] + "…"
    return head


def get_default_creativity() -> CreativityEngine:
    """Local creativity unless ``JONI_USE_KEVIN=1`` and Kevin is importable."""
    if os.getenv("JONI_USE_KEVIN") == "1":
        try:
            return KevinCreativity()
        except ImportError:  # pragma: no cover - depends on whether kevin is installed
            pass
    return LocalCreativity()
