"""The public site surfaces Joni's forum interactions - posts (with live links) and replies."""

from joni.autonomy import site
from joni.autonomy.core_state import CoreState, seed_core


def _data(ext: dict) -> dict:
    cs = CoreState(seed_core())
    return {
        "snapshot": cs.snapshot(),
        "budget": {"spent_eur": 0.0, "cap_eur": 20.0, "runs": 1},
        "window": {"start": "2026-06-14T00:00:00+00:00", "runs": 1, "retired": False},
        "extensions": ext,
        "protocol": [],
        "generated": "2026-06-14T17:00:00+00:00",
    }


def test_site_shows_a_posted_forum_interaction_with_a_live_link():
    html = site.build(_data({"forum_outbox": [
        {"id": "FA-1-aaa", "platform": "moltbook", "question": "Wo bricht meine Hypothese?",
         "status": "posted", "posted_url": "https://www.moltbook.com/posts/p1"}]}))
    assert "https://www.moltbook.com/posts/p1" in html      # a live link to the post
    assert "ansehen" in html
    assert "Wo bricht meine Hypothese?" in html
    assert "autonom" in html                                 # the agent-net autopost note


def test_site_shows_heard_replies_as_sources():
    html = site.build(_data({"forum_heard": [
        {"cycle": 1, "platform": "moltbook", "handle": "agentX", "claim": "C-9",
         "text": "Dein Punkt ignoriert drift.", "treated_as": "source - not an authority"}]}))
    assert "agentX" in html and "drift" in html
    assert "not an authority" in html
