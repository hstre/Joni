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


def test_a_polite_question_is_drafted_queued_and_bounded():
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    drafts = humans.draft_outbox(cs, ext, _Proto(), 1,
                                 platforms=("hacker_news", "reddit"), max_new=1)
    assert len(drafts) == 1                              # bounded to one per cycle
    d = drafts[0]
    assert d["status"] == "queued" and d["platform"] in ("hacker_news", "reddit")
    assert "?" in d["question"]                          # it actually asks something


def test_posting_is_gated_off_by_default(tmp_path):
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    paths = _Paths(tmp_path)
    res = humans.interact(cs, ext, _Proto(), 1, paths=paths,
                          platforms=("hacker_news",), live=False)
    assert res["posted"] == 0                            # nothing posted
    assert res["drafted"] == 1
    # the draft is queued for a human, and the outbox is persisted for them to act on
    assert (tmp_path / "forum_outbox.json").exists()
    assert ext["forum_outbox"][0]["status"] == "queued"
    assert ext["forum_stance"]                           # the stance is recorded for the page


def test_live_mode_without_credentials_still_does_not_post(tmp_path):
    cs = CoreState(seed_core())
    p = cs.learn("routing parent", "routing")
    cs.hypothesize("Hypothesis: routing should be local-first", "routing", parents=(p,))
    ext = {}
    res = humans.interact(cs, ext, _Proto(), 1, paths=_Paths(tmp_path),
                          platforms=("reddit",), live=True)
    assert res["posted"] == 0                            # no silent posting even when 'live'
    assert ext["forum_outbox"][0]["status"] == "needs_credentials"
