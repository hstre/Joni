"""Per-platform forum adapters - the only place the relay touches the outside world.

Each adapter knows how to post and how to fetch replies for one platform. None is wired for
real network calls yet: ``implemented = False`` everywhere, so ``ready()`` is always False and
the relay stays dry-run. Implementing one (with the operator's credentials, via the official
API, respecting the platform's bot policy and rate limits) is a localised change here - flip
``implemented`` and fill ``post``/``fetch_replies``/``_has_creds``.
"""

from __future__ import annotations

import contextlib
import json
import os
import urllib.error
import urllib.request


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


class MoltbookAdapter(ForumAdapter):
    """Moltbook (api.moltbook.com) - an *agent-only* social network, so autonomous posting is
    the platform's intended use, not spam in a human community. Posts go to the submolt named
    by MOLTBOOK_SUBMOLT (default ``m/ai``).

    Safety: Moltbook has leaked agent keys before, so use a dedicated, rotatable key kept in
    root-only relay.env, and never put secrets in post content. Inbound replies (when wired)
    still enter Joni as SOURCES, never authorities."""

    platform = "moltbook"
    implemented = True
    BASE = "https://api.moltbook.com"

    def _has_creds(self) -> bool:
        return bool(self.env.get("MOLTBOOK_API_KEY"))

    def _submolt(self) -> str:
        return self.env.get("MOLTBOOK_SUBMOLT", "m/ai")

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.BASE + path, data=data, method=method,
            headers={"Authorization": f"Bearer {self.env['MOLTBOOK_API_KEY']}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode() or "{}")

    def post(self, text: str) -> str:
        if not self.ready():
            raise NotReady("moltbook: MOLTBOOK_API_KEY not set")
        title = (text.strip().splitlines() or ["Frage"])[0][:120] or "Frage"
        try:
            res = self._request("POST", "/posts", {
                "type": "text", "title": title, "content": text, "submolt": self._submolt()})
        except urllib.error.HTTPError as e:         # the API answered with an error status
            body = ""
            with contextlib.suppress(Exception):
                body = e.read().decode("utf-8", "ignore")[:160]
            raise NotReady(f"moltbook: HTTP {e.code} {body}".strip()) from e
        except urllib.error.URLError as e:          # network error -> not posted, retry later
            raise NotReady(f"moltbook: {e.reason}") from e
        pid = res.get("id") or res.get("post_id") or ""
        return res.get("url") or (f"https://www.moltbook.com/posts/{pid}" if pid else "")

    # fetch_replies: ingesting comments on Joni's own posts needs the "my posts / notifications"
    # endpoint, which the public docs don't pin down. Until confirmed, replies come back via the
    # human reply drop box (state/forum_replies.txt). Inherits the base no-op.


_ADAPTERS = {a.platform: a for a in
             (HuggingFaceAdapter, RedditAdapter, HackerNewsAdapter, LessWrongAdapter,
              MoltbookAdapter)}


def get_adapter(platform: str, env: dict | None = None) -> ForumAdapter:
    """The adapter for a platform, or a base adapter (never ready) for an unknown one."""
    return _ADAPTERS.get(platform, ForumAdapter)(env)
