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
import urllib.parse
import urllib.request


class NotReady(RuntimeError):
    """Raised when a live action is attempted on an adapter that is not configured."""


# Read-path failures we treat as "nothing to report" rather than crash the cycle: API error
# statuses, network errors, malformed JSON, or a missing key on a not-really-ready adapter.
_READ_ERRORS = (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError)


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
    """Moltbook - an *agent-only* social network, so autonomous posting is the platform's
    intended use, not spam in a human community. Posts go to the submolt named by
    MOLTBOOK_SUBMOLT (default ``general``; a plain community name, no ``m/`` prefix).

    API per moltbook.com/skill.md: ``POST https://www.moltbook.com/api/v1/posts`` with body
    ``submolt_name`` / ``title`` / ``content`` / ``type``, Bearer auth.

    Safety: Moltbook has leaked agent keys before, so use a dedicated, rotatable key kept in
    root-only relay.env, and never put secrets in post content. Inbound replies (when wired)
    still enter Joni as SOURCES, never authorities."""

    platform = "moltbook"
    implemented = True
    BASE = "https://www.moltbook.com/api/v1"

    def _has_creds(self) -> bool:
        return bool(self.env.get("MOLTBOOK_API_KEY"))

    def _submolt(self) -> str:
        return self.env.get("MOLTBOOK_SUBMOLT", "general")

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
        title = (text.strip().splitlines() or ["Frage"])[0][:300] or "Frage"
        try:
            res = self._request("POST", "/posts", {
                "submolt_name": self._submolt(), "title": title, "content": text, "type": "text"})
        except urllib.error.HTTPError as e:         # the API answered with an error status
            body = ""
            with contextlib.suppress(Exception):
                body = e.read().decode("utf-8", "ignore")[:160]
            raise NotReady(f"moltbook: HTTP {e.code} {body}".strip()) from e
        except urllib.error.URLError as e:          # network error -> not posted, retry later
            raise NotReady(f"moltbook: {e.reason}") from e
        # Success body nests the created post: {"success": true, "post": {"id": "...", ...}}.
        # Fall back to a flat id for forward-compat. The public web post-view URL pattern isn't
        # documented, so the post id is the durable reference we can always capture.
        post = res.get("post") if isinstance(res.get("post"), dict) else res
        pid = post.get("id") or post.get("post_id") or res.get("id") or res.get("post_id") or ""
        return post.get("url") or res.get("url") or (
            f"https://www.moltbook.com/posts/{pid}" if pid else "")

    def whoami(self) -> dict:
        """Joni's own Moltbook profile (name, karma, ...). Lets the loop record his agent name
        once so his posts are findable at https://www.moltbook.com/u/<name>. Best-effort: a
        not-ready adapter or any API/network error yields an empty dict, never raises."""
        if not self.ready():
            return {}
        try:
            res = self._request("GET", "/agents/me")
        except _READ_ERRORS:
            return {}
        agent = res.get("agent") if isinstance(res.get("agent"), dict) else res
        name = agent.get("name") or agent.get("username") or ""
        out = {"name": name}
        if name:
            out["profile_url"] = f"https://www.moltbook.com/u/{name}"
        return out

    def _agent_name(self) -> str:
        """Joni's Moltbook handle - from the configured MOLTBOOK_AGENT, else a live whoami."""
        return self.env.get("MOLTBOOK_AGENT", "") or self.whoami().get("name", "")

    def identity(self) -> dict:
        """whoami(), or - if the API answer is unhelpful - the configured agent name, so the
        site can always link Joni's profile when MOLTBOOK_AGENT is set."""
        who = self.whoami()
        if who.get("name"):
            return who
        name = self.env.get("MOLTBOOK_AGENT", "")
        if name and self.ready():
            return {"name": name, "profile_url": f"https://www.moltbook.com/u/{name}"}
        return {}

    def _max_review(self) -> int:
        with contextlib.suppress(TypeError, ValueError):
            return max(0, int(self.env.get("MOLTBOOK_REVIEW_POSTS", "6")))
        return 6

    @staticmethod
    def _author_name(node: dict) -> str:
        a = node.get("author")
        if isinstance(a, dict):
            return a.get("name") or a.get("username") or "anon"
        return str(a or node.get("author_name") or "anon")

    def _collect_comment(self, c: dict, pid: str, title: str, me: str, out: list) -> None:
        """Flatten a comment and its nested replies into inbox-shaped SOURCE entries, skipping
        Joni's own comments (don't hear your own voice back)."""
        if not isinstance(c, dict):
            return
        handle = self._author_name(c)
        text = str(c.get("content") or c.get("text") or "").strip()
        if text and handle.lower() != me:
            out.append({"platform": "moltbook", "handle": handle, "text": text,
                        "post_id": str(pid), "post_title": title})
        for r in c.get("replies") or []:
            self._collect_comment(r, pid, title, me, out)

    def _my_posts(self) -> list[tuple[str, str]]:
        """Candidate (post_id, title) pairs to review: posts with new activity (from /home)
        plus a backlog sweep of recent posts (from the profile). Deduped, capped, best-effort."""
        posts: dict[str, str] = {}
        with contextlib.suppress(*_READ_ERRORS):
            home = self._request("GET", "/home")
            for item in home.get("activity_on_your_posts") or []:
                pid = item.get("post_id") or item.get("id")
                if pid:
                    posts[str(pid)] = item.get("post_title") or item.get("title") or ""
        name = self._agent_name()
        if name:
            with contextlib.suppress(*_READ_ERRORS):
                prof = self._request("GET", f"/agents/profile?name={urllib.parse.quote(name)}")
                for p in prof.get("recentPosts") or []:
                    pid = p.get("id") or p.get("post_id")
                    if pid:
                        posts.setdefault(str(pid), p.get("title") or "")
        return list(posts.items())[: self._max_review()]

    def fetch_replies(self) -> list[dict]:
        """Read the comments on Joni's own posts and return them as inbox replies (SOURCE).

        This is how Joni *reviews the reactions to his posts*: it gathers his posts (new
        activity + recent backlog), pulls each post's comments (nested replies flattened),
        and skips his own. Bounded per call; any API/network error yields what was gathered
        so far, never raises. The relay/loop dedupes, so re-reading old posts is harmless."""
        if not self.ready():
            return []
        me = (self._agent_name() or "").lower()
        out: list[dict] = []
        for pid, title in self._my_posts():
            with contextlib.suppress(*_READ_ERRORS):
                res = self._request("GET", f"/posts/{pid}/comments?sort=new&limit=35")
                for c in res.get("comments") or []:
                    self._collect_comment(c, pid, title, me, out)
        return out


_ADAPTERS = {a.platform: a for a in
             (HuggingFaceAdapter, RedditAdapter, HackerNewsAdapter, LessWrongAdapter,
              MoltbookAdapter)}


def get_adapter(platform: str, env: dict | None = None) -> ForumAdapter:
    """The adapter for a platform, or a base adapter (never ready) for an unknown one."""
    return _ADAPTERS.get(platform, ForumAdapter)(env)
