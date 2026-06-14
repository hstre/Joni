"""The relay's one-pass logic - pure enough to test without a network or a VPS.

A pass: load the published outbox + human approvals, release only the approved-and-unposted
drafts (the moderation gate), post them through the platform adapter (or just count them in
dry-run), ingest any replies, and report. Git sync is the caller's job (``__main__``).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..autonomy.humans import select_postable
from .adapters import NotReady, get_adapter


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _reply_key(r: dict) -> str:
    return f"{r.get('platform','')}|{r.get('handle','')}|{r.get('text','')}"


def one_pass(paths, *, live: bool, env: dict | None = None) -> dict:
    """Run one relay pass. Returns a summary; mutates the outbox/inbox files only on a real
    post or a real reply. In dry-run (``live=False``) nothing leaves and nothing is written."""
    outbox = _load(paths.forum_outbox, [])
    approved = _load(paths.forum_approved, [])
    postable = select_postable(outbox, approved)

    posted = would_post = 0
    for d in postable:
        adapter = get_adapter(d.get("platform", ""), env)
        if live and adapter.ready():
            try:
                url = adapter.post(d.get("question", ""))
            except NotReady:
                would_post += 1
                continue
            d["status"], d["posted_url"] = "posted", url
            posted += 1
        else:
            would_post += 1                    # dry-run, or no live adapter for this platform

    heard = 0
    if live:
        inbox = _load(paths.forum_inbox, [])
        seen = {_reply_key(r) for r in inbox if isinstance(r, dict)}
        platforms = {d.get("platform", "") for d in outbox}
        for platform in sorted(p for p in platforms if p):
            adapter = get_adapter(platform, env)
            if not adapter.ready():
                continue
            for reply in adapter.fetch_replies():
                if _reply_key(reply) not in seen:
                    inbox.append(reply)
                    seen.add(_reply_key(reply))
                    heard += 1
        if heard:
            _save(paths.forum_inbox, inbox)

    if posted:
        _save(paths.forum_outbox, outbox)

    return {"postable": len(postable), "would_post": would_post, "posted": posted,
            "heard": heard, "live": live}
