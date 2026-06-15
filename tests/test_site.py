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


def test_site_shows_what_the_expert_panel_discussed():
    html = site.build(_data({"panel_last": {
        "question": "Joni holds two claims in a hard contradiction:\n- (C-5) routing is local\n"
                    "- (C-6) routing is never local",
        "roles": {"claude": "assessor", "chatgpt": "adversarial", "deepseek": "consistency"},
        "phase3": {"claude": "Consistent only if 'local' is scoped to latency-bound tasks.",
                   "chatgpt": "Counter-assumption: under cost pressure the second claim wins.",
                   "deepseek": "The two resolve by separating the deployment assumption."},
        "cycle": 42}}))
    assert "Expertenrunde" in html
    assert "assessor" in html and "adversarial" in html and "consistency" in html
    assert "latency-bound tasks" in html                 # an actual assessment is shown
    assert "Joni entscheidet" in html                    # advisory framing preserved


def test_site_panel_card_is_empty_until_a_round_happens():
    html = site.build(_data({}))
    assert "Expertenrunde" in html
    assert "Noch keine Runde" in html
