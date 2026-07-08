"""'forum' is a provenance, not a topic - the reclassification drains the category error.

Pins: content routes only INTO established topics (never mints one); a routed claim is re-filed
via a superseded-with-lineage successor that keeps text, source provenance and live support; an
unroutable 0-support claim is retired through the gate; a supported-but-unroutable claim is kept;
everything is bounded per cycle; and the inflow (humans._topic_for) uses the same router.
"""
from joni.autonomy import humans, persona, reclassify
from joni.autonomy.core_state import CoreState, seed_core
from joni.autonomy.homeostasis import _supports_on


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _with_routing_topic(cs):
    cs.learn("routing decides which model serves a query", "routing", source_id="arxiv:r1")
    cs.learn("routing tables need measured scores", "routing", source_id="arxiv:r2")


# --- the router ---------------------------------------------------------------------------- #

def test_route_topic_matches_whole_words_and_never_invents():
    topics = ["routing", "memory"]
    assert reclassify.route_topic("the routing layer is load-dependent", topics) == "routing"
    assert reclassify.route_topic("agents keep memories across sessions", topics) == "memory"
    assert reclassify.route_topic("totally unrelated chatter about weather", topics) is None
    assert reclassify.route_topic("subroutine grouting", topics) is None      # no substring hits


def test_real_topics_excludes_sinks_and_one_claim_orphans():
    cs = CoreState(seed_core())
    _with_routing_topic(cs)                                   # 2 active claims -> a destination
    cs.learn("a single narrow claim", "accessibility")        # 1 claim -> not a destination
    ts = reclassify.real_topics(cs)
    assert "routing" in ts
    assert "accessibility" not in ts and "forum" not in ts and "unsorted" not in ts


# --- the pass ------------------------------------------------------------------------------- #

def test_a_routable_forum_claim_is_refiled_with_lineage_provenance_and_support():
    cs = CoreState(seed_core())
    _with_routing_topic(cs)
    old = cs.hear("under load the routing prefers cheaper paths", "forum",
                  handle="alice", platform="hn")
    sup = cs.learn("a benchmark note on load-dependent paths", "routing", source_id="arxiv:s")
    cs.corroborate(old, cs.core.objects[sup])                 # live support to carry
    out = reclassify.reclassify_forum(cs, {}, _Proto(), 1)
    assert out["refiled"] == 1
    assert cs.core.objects[old].status.value == "superseded"  # stays in the chain forever
    new = [c for c in cs.active_claims()
           if f"refile-of:{old}" in (c.provenance.source_ids or ())]
    assert len(new) == 1
    nc = new[0]
    assert nc.topic == "routing"                              # the CONTENT topic
    assert nc.text == cs.core.objects[old].text               # text unchanged
    assert "hn:alice" in nc.provenance.source_ids             # source provenance carried
    assert old in nc.derived_from                             # auditable lineage
    assert _supports_on(cs, nc.id) == 1                       # live support carried


def test_unroutable_chatter_is_retired_but_supported_claims_are_kept():
    cs = CoreState(seed_core())
    _with_routing_topic(cs)
    chatter = cs.hear("nice idea, totally agree with everything", "forum",
                      handle="bob", platform="hn")
    kept = cs.hear("an unusual observation nobody can classify yet", "forum",
                   handle="eve", platform="hn")
    sup = cs.learn("independent note corroborating the observation", "routing",
                   source_id="arxiv:k")
    cs.corroborate(kept, cs.core.objects[sup])
    out = reclassify.reclassify_forum(cs, {}, _Proto(), 1)
    assert cs.core.objects[chatter].status.value == "rejected"
    assert cs.core.objects[kept].status.value == "active"     # supported: mis-filed > lost
    assert out["retired"] == 1 and out["kept_supported"] == 1


def test_the_pass_is_bounded_per_cycle():
    cs = CoreState(seed_core())
    for i in range(7):
        cs.hear(f"pure chatter number {i} nothing classifiable", "forum",
                handle=f"u{i}", platform="hn")
    out = reclassify.reclassify_forum(cs, {}, _Proto(), 1, max_refile=2, max_retire=3)
    assert out["retired"] == 3                                # capped
    assert out["remaining"] == 4


def test_housekeeping_never_becomes_a_persona_lesson():
    cs = CoreState(seed_core())
    for i in range(4):
        cs.hear(f"chatter {i} without any classifiable subject", "forum",
                handle=f"u{i}", platform="hn")
    reclassify.reclassify_forum(cs, {}, _Proto(), 1)
    cors = persona.extract_corrections(cs)
    lessons = persona.crystallize(cors)
    assert all(ls.theme != "forum" for ls in lessons)         # sink theme earns no lesson
    md = persona.render_md(lessons, cors, tick=1)
    assert "Housekeeping in Sink-Themen" in md                # counted separately, honestly


# --- the inflow uses the same router --------------------------------------------------------- #

def test_new_forum_voices_land_on_content_topics_when_clear():
    cs = CoreState(seed_core())
    _with_routing_topic(cs)
    assert humans._topic_for(cs, "routing under load looks brittle") == "routing"
    assert humans._topic_for(cs, "thanks, great post!") == "forum"       # unclear -> sink
