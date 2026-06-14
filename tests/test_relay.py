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
        return _FakeResp({"id": "p123", "url": "https://www.moltbook.com/posts/p123"})

    monkeypatch.setattr(adapters.urllib.request, "urlopen", fake_urlopen)
    a = adapters.get_adapter("moltbook", {"MOLTBOOK_API_KEY": "moltbook_sk_x",
                                          "MOLTBOOK_SUBMOLT": "m/epistemics"})
    assert a.ready() is True                                   # implemented + has key
    url = a.post("Wo bricht meine Hypothese?\nMehr Details hier...")
    assert url == "https://www.moltbook.com/posts/p123"
    assert captured["url"] == "https://api.moltbook.com/posts"
    assert captured["method"] == "POST"
    assert captured["auth"] == "Bearer moltbook_sk_x"
    assert captured["body"]["submolt"] == "m/epistemics"
    assert captured["body"]["title"] == "Wo bricht meine Hypothese?"   # first line, capped
    assert captured["body"]["content"].startswith("Wo bricht")


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
