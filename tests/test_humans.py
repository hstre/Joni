"""Joni may talk to people - but a person is a source, never an authority.

These tests pin the epistemic contract: forum input enters as a SOURCE (not the privileged
HUMAN origin), stays candidate-authority, opens a conflict when it contradicts a held claim
(not an override), and posting is gated off by default.
"""

import json

from joni.autonomy import humans
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


class _Paths:
    def __init__(self, d):
        self.forum_inbox = d / "forum_inbox.json"
        self.forum_outbox = d / "forum_outbox.json"
        self.forum_replies = d / "forum_replies.txt"
        self.post_sheet = d / "to_post.md"


def test_a_forum_person_is_a_source_not_an_authority():
    cs = CoreState(seed_core())
    cid = cs.hear("local routing is always better", "routing",
                  handle="someone", platform="hacker_news")
    c = cs.core.get(cid)
    assert c.status.value == "active"
    assert c.authority.value == "candidate"            # earns standing, not granted it
    assert c.provenance.origin_type.value == "source"  # NOT 'human' (the privileged origin)
    assert c.provenance.origin_type.value != "human"
    assert c.provenance.source_ids == ("hacker_news:someone",)


def test_a_contradicting_human_input_opens_a_conflict_not_an_override(tmp_path):
    cs = CoreState(seed_core())
    held = cs.learn("routing reduces latency", "routing")
    (tmp_path / "forum_inbox.json").write_text(json.dumps([
        {"platform": "reddit", "handle": "critic", "topic": "routing",
         "text": "routing does not reduce latency"}
    ]))
    out = humans.ingest_inbox(cs, {}, _Proto(), 1, tmp_path / "forum_inbox.json")
    assert out["heard"] == 1
    assert out["conflicts"] >= 1                              # a conflict was opened
    # held open, both kept: the held claim is contested, NOT rejected/superseded by the human
    assert cs.core.get(held).status.value == "contested"
    assert cs.core.get(held).status.value not in ("rejected", "superseded")


def test_inbox_ingestion_is_deduped(tmp_path):
    cs = CoreState(seed_core())
    msg = [{"platform": "huggingface", "handle": "u", "text": "attention is all you need"}]
    (tmp_path / "forum_inbox.json").write_text(json.dumps(msg))
    ext = {}
    first = humans.ingest_inbox(cs, ext, _Proto(), 1, tmp_path / "forum_inbox.json")
    second = humans.ingest_inbox(cs, ext, _Proto(), 2, tmp_path / "forum_inbox.json")
    assert first["heard"] == 1 and second["heard"] == 0   # the same reply is not re-heard


def test_a_polite_question_is_drafted_awaiting_approval_and_bounded():
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    drafts = humans.draft_outbox(cs, ext, _Proto(), 1,
                                 platforms=("hacker_news", "reddit"), max_new=1)
    assert len(drafts) == 1                              # bounded to one per cycle
    d = drafts[0]
    assert d["status"] == "drafted" and d["id"].startswith("FA-")
    assert d["platform"] in ("hacker_news", "reddit")
    assert "?" in d["question"]                          # it actually asks something


def test_the_loop_never_posts_even_when_live(tmp_path):
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    res = humans.interact(cs, ext, _Proto(), 1, paths=_Paths(tmp_path),
                          platforms=("reddit",), live=True)        # 'live' on, still
    assert res["posted"] == 0                            # the loop never posts
    assert res["drafted"] == 1
    assert (tmp_path / "forum_outbox.json").exists()     # published for human + relay
    assert ext["forum_outbox"][0]["status"] == "drafted"
    assert ext["forum_stance"]


def test_moderation_gate_only_releases_approved_drafts(tmp_path):
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    drafts = humans.draft_outbox(cs, ext, _Proto(), 1, platforms=("reddit",))
    fid = drafts[0]["id"]
    outbox = ext["forum_outbox"]
    # nothing is postable until a human approves
    assert humans.select_postable(outbox, []) == []
    approved = humans.approve(tmp_path / "forum_approved.json", fid)
    assert fid in approved
    postable = humans.select_postable(outbox, approved)
    assert [d["id"] for d in postable] == [fid]
    # an already-posted draft is not re-released
    outbox[0]["status"] = "posted"
    assert humans.select_postable(outbox, approved) == []


def test_pasted_replies_are_parsed():
    parsed = humans.ingest_replies_text(
        "# a comment\n"
        "\n"
        "hacker_news | userXY | drift ignores seasonality\n"
        "reddit | only two fields\n"
        "just a body with no pipes\n"
    )
    assert parsed == [
        {"platform": "hacker_news", "handle": "userXY", "text": "drift ignores seasonality"},
        {"platform": "reddit", "handle": "anon", "text": "only two fields"},
        {"platform": "forum", "handle": "anon", "text": "just a body with no pipes"},
    ]


def test_post_sheet_lists_unposted_drafts_in_copy_paste_form():
    outbox = [
        {"id": "FA-1-aaa", "platform": "reddit", "question": "Wo bricht das?", "status": "drafted"},
        {"id": "FA-1-bbb", "platform": "lesswrong", "question": "Quellen zu drift?",
         "status": "posted"},
    ]
    sheet = humans.render_post_sheet(outbox)
    assert "FA-1-aaa" in sheet and "Wo bricht das?" in sheet
    assert "FA-1-bbb" not in sheet            # already posted -> not on the sheet
    assert "Post-Mappe" in sheet


def test_pasted_replies_are_folded_into_the_inbox_and_heard(tmp_path):
    cs = CoreState(seed_core())
    paths = _Paths(tmp_path)
    paths.forum_replies.write_text("hacker_news | crit | routing locally is not always better\n")
    res = humans.interact(cs, {}, _Proto(), 1, paths=paths,
                          platforms=("hacker_news",), live=False)
    assert res["folded"] == 1
    assert res["heard"] == 1                                  # heard as a source this cycle
    # the drop box was consumed (reset to the template, no raw reply left behind)
    assert "routing locally is not always better" not in paths.forum_replies.read_text()
    # the reply now lives in the inbox, and a post sheet was written for the human
    inbox = json.loads(paths.forum_inbox.read_text())
    assert any("routing locally" in m["text"] for m in inbox)
    assert paths.post_sheet.exists() and "Post-Mappe" in paths.post_sheet.read_text()
