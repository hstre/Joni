"""The relay obeys the moderation gate and stays dry-run until an adapter is wired.

No network here: we check the pure pass logic and the adapter readiness contract.
"""

import json

import pytest

from joni.relay import adapters
from joni.relay.agent import one_pass


class _FakeResp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_moltbook_adapter_posts_to_a_submolt(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["auth"] = req.headers.get("Authorization")
        captured["body"] = json.loads(req.data.decode())
        # Real success body nests the created post under "post".
        return _FakeResp({"success": True, "message": "Post created!",
                          "post": {"id": "p123", "title": "Wo bricht meine Hypothese?",
                                   "verification_status": "pending"}})

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "moltbook_sk_x",
                                          "MOLTBOOK_SUBMOLT": "epistemics"})
    assert a.ready() is True                                   # implemented + has key
    url = a.post("Wo bricht meine Hypothese?\nMehr Details hier...")
    assert url == "https://www.moltbook.com/posts/p123"        # id pulled from nested "post"
    assert captured["url"] == "https://www.moltbook.com/api/v1/posts"   # real API base
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer moltbook_sk_x"
    assert captured["body"]["submolt_name"] == "epistemics"   # real field name, no m/ prefix
    assert captured["body"]["title"] == "Wo bricht meine Hypothese?"   # first line, capped
    assert captured["body"]["content"].startswith("Wo bricht")


def test_moltbook_adapter_accepts_a_flat_id_response(monkeypatch):
    """Forward-compat: if the API ever returns a flat id, we still capture it."""
    def fake_urlopen(req, timeout=0):
        return _FakeResp({"id": "flat9", "url": "https://www.moltbook.com/posts/flat9"})

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "k"})
    assert a.post("Q") == "https://www.moltbook.com/posts/flat9"


def test_moltbook_whoami_resolves_the_agent_profile(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return _FakeResp({"agent": {"name": "Joni", "karma": 12}})

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "k"})
    who = a.whoami()
    assert captured["url"] == "https://www.moltbook.com/api/v1/agents/me"
    assert captured["method"] == "GET"
    assert who == {"name": "Joni", "profile_url": "https://www.moltbook.com/u/Joni"}


def test_moltbook_whoami_is_empty_without_a_key():
    assert adapters.get_adapter("moltbook", {}).whoami() == {}


def test_moltbook_identity_falls_back_to_configured_name(monkeypatch):
    # the API gives no usable name, but MOLTBOOK_AGENT is configured -> link the profile anyway
    def fake_urlopen(req, timeout=0):
        return _FakeResp({"agent": {}})

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "k",
                                          "MOLTBOOK_AGENT": "epistemicwilly"})
    assert a.identity() == {"name": "epistemicwilly",
                            "profile_url": "https://www.moltbook.com/u/epistemicwilly"}


def test_moltbook_fetch_replies_reads_comments_on_joni_posts(monkeypatch):
    """Joni reviews his own posts: /home + profile name the posts, then each post's comments
    (nested replies flattened) come back as SOURCE entries - his own comments skipped."""
    def fake_urlopen(req, timeout=0):
        url = req.full_url
        if url.endswith("/home"):
            return _FakeResp({"activity_on_your_posts": [
                {"post_id": "P1", "post_title": "Epistemic Infrastructure"}]})
        if "/agents/profile" in url:
            return _FakeResp({"recentPosts": [{"id": "P2", "title": "Blueprint Protocol"}]})
        if url.endswith("/posts/P1/comments?sort=new&limit=35"):
            return _FakeResp({"comments": [
                {"content": "Have you considered drift?", "author": {"name": "molty_x"},
                 "replies": [{"content": "good point", "author": {"name": "molty_y"}}]},
                {"content": "my own follow-up", "author": {"name": "epistemicwilly"}}]})
        if url.endswith("/posts/P2/comments?sort=new&limit=35"):
            return _FakeResp({"comments": []})
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "k",
                                          "MOLTBOOK_AGENT": "epistemicwilly"})
    replies = a.fetch_replies()
    texts = {(r["handle"], r["text"]) for r in replies}
    assert ("molty_x", "Have you considered drift?") in texts   # top-level comment
    assert ("molty_y", "good point") in texts                   # nested reply, flattened
    assert all(r["handle"] != "epistemicwilly" for r in replies)  # never hears its own voice
    assert all(r["platform"] == "moltbook" and r["post_id"] in {"P1", "P2"} for r in replies)


def test_moltbook_fetch_replies_empty_without_a_key():
    assert adapters.get_adapter("moltbook", {}).fetch_replies() == []


def test_moltbook_without_key_is_not_ready_and_refuses():
    a = adapters.get_adapter("moltbook", {})
    assert a.ready() is False                                  # implemented, but no key
    with pytest.raises(adapters.NotReady):
        a.post("anything")


class _Paths:
    def __init__(self, d):
        self.forum_outbox = d / "forum_outbox.json"
        self.forum_inbox = d / "forum_inbox.json"
        self.forum_approved = d / "forum_approved.json"


def _seed(d, *, approved):
    (d / "forum_outbox.json").write_text(json.dumps([
        {"id": "FA-1-aaa", "platform": "reddit", "question": "Wo bricht das?",
         "status": "drafted", "posted_url": None}
    ]))
    (d / "forum_approved.json").write_text(json.dumps(approved))


def test_dry_run_posts_nothing_even_for_an_approved_draft(tmp_path):
    _seed(tmp_path, approved=["FA-1-aaa"])
    out = one_pass(_Paths(tmp_path), live=False)
    assert out["postable"] == 1 and out["would_post"] == 1 and out["posted"] == 0
    # the outbox file is left untouched in dry-run
    assert json.loads((tmp_path / "forum_outbox.json").read_text())[0]["status"] == "drafted"


def test_unapproved_drafts_are_never_postable(tmp_path):
    _seed(tmp_path, approved=[])                     # nothing approved
    out = one_pass(_Paths(tmp_path), live=False)
    assert out["postable"] == 0 and out["would_post"] == 0


def test_live_without_a_wired_adapter_still_posts_nothing(tmp_path):
    _seed(tmp_path, approved=["FA-1-aaa"])
    # even with credentials in the env, no adapter is implemented yet -> ready() is False
    out = one_pass(_Paths(tmp_path), live=True,
                   env={"REDDIT_CLIENT_ID": "x", "REDDIT_CLIENT_SECRET": "x",
                        "REDDIT_USERNAME": "x", "REDDIT_PASSWORD": "x"})
    assert out["posted"] == 0 and out["would_post"] == 1
    assert json.loads((tmp_path / "forum_outbox.json").read_text())[0]["status"] == "drafted"


def test_adapter_readiness_contract():
    hf = adapters.get_adapter("huggingface", {"HF_TOKEN": "t"})
    assert hf.platform == "huggingface"
    assert hf._has_creds() is True                   # creds present...
    assert hf.ready() is False                        # ...but not implemented yet -> not ready
    unknown = adapters.get_adapter("myspace", {})
    assert unknown.ready() is False                   # unknown platform -> base, never ready
