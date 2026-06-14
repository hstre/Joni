"""Per-platform forum adapters - the only place the relay touches the outside world.

Each adapter knows how to post and how to fetch replies for one platform. None is wired for
real network calls yet: ``implemented = False`` everywhere, so ``ready()`` is always False and
the relay stays dry-run. Implementing one (with the operator's credentials, via the official
API, respecting the platform's bot policy and rate limits) is a localised change here - flip
``implemented`` and fill ``post``/``fetch_replies``/``_has_creds``.
"""

from __future__ import annotations

import os


class NotReady(RuntimeError):
    """Raised when a live action is attempted on an adapter that is not configured."""


class ForumAdapter:
    platform = "base"
    implemented = False                     # set True only when real API calls are wired

    def __init__(self, env: dict | None = None):
        self.env = env if env is not None else dict(os.environ)

    def _has_creds(self) -> bool:
        return False

    def ready(self) -> bool:
        """May we make live calls? Only when the adapter is implemented AND has credentials."""
        return self.implemented and self._has_creds()

    def post(self, text: str) -> str:
        raise NotReady(f"{self.platform}: live posting is not configured")

    def fetch_replies(self) -> list[dict]:
        return []


class HuggingFaceAdapter(ForumAdapter):
    platform = "huggingface"
    # TODO(creds): implement via the HF Hub API (community discussions). Then implemented=True.

    def _has_creds(self) -> bool:
        return bool(self.env.get("HF_TOKEN"))


class RedditAdapter(ForumAdapter):
    platform = "reddit"
    # TODO(creds): implement via the official Reddit API (script app); respect bot rules.

    def _has_creds(self) -> bool:
        return all(self.env.get(k) for k in
                   ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET",
                    "REDDIT_USERNAME", "REDDIT_PASSWORD"))


class HackerNewsAdapter(ForumAdapter):
    platform = "hacker_news"
    # HN has no posting API and discourages bots: treat as read-mostly unless explicitly allowed.


class LessWrongAdapter(ForumAdapter):
    platform = "lesswrong"


_ADAPTERS = {a.platform: a for a in
             (HuggingFaceAdapter, RedditAdapter, HackerNewsAdapter, LessWrongAdapter)}


def get_adapter(platform: str, env: dict | None = None) -> ForumAdapter:
    """The adapter for a platform, or a base adapter (never ready) for an unknown one."""
    return _ADAPTERS.get(platform, ForumAdapter)(env)
