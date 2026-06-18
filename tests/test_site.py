"""The public site surfaces what Joni is doing. The human-task and forum surfaces (core
asks, Aufträge an Claude, the forum post-mappe) were retired when the autonomous loop was
stopped, so they no longer render; the expert-panel card and the rest stay."""

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


def test_site_no_longer_renders_the_retired_task_and_forum_surfaces():
    # The loop is stopped: core asks, Aufträge an Claude and the forum post-mappe are gone.
    html = site.build(_data({
        "forum_outbox": [{"id": "FA-1-aaa", "platform": "moltbook", "question": "Q?",
                          "status": "posted", "posted_url": "https://www.moltbook.com/posts/p1"}],
        "forum_heard": [{"cycle": 1, "platform": "moltbook", "handle": "agentX", "claim": "C-9",
                         "text": "Dein Punkt ignoriert drift.", "treated_as": "source"}],
        "commissions": [{"title": "do a thing", "component": "x"}],
        "asks": [{"request_type": "observation", "component": "core", "proposed_change": "y"}]}))
    for absent in ("Menschen &amp; Foren", "Aufträge an Claude", "Asks &mdash; waiting",
                   "du postest", "moltbook.com/posts/p1", "agentX", "do a thing"):
        assert absent not in html


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
