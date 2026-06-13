"""Joni reviews itself hourly and reports it - as provisional self-model claims."""

import json
from datetime import UTC, datetime, timedelta

import desi_layer9 as l9
from joni.autonomy import self_review
from joni.autonomy.core_state import CoreState, seed_core


def _cs():
    return CoreState(seed_core())


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_self_model_claims_are_provisional_not_facts():
    cs = _cs()
    ext = {"topics_added": ["calibration"]}
    review = self_review.run_review(cs, ext, _Proto(), 1, days=1, spend=0.0)
    sm = cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM)
    assert sm                                    # at least one provisional self-model claim
    assert all(c.status is l9.Status.CANDIDATE for c in sm)   # provisional, never confirmed
    assert all(c.authority is not l9.Authority.AUTHORITATIVE for c in sm)
    assert review["assessments"] and review["headline"]


def test_review_records_protocol_and_narrative():
    cs = _cs()
    proto = _Proto()
    self_review.run_review(cs, {"topics_added": []}, proto, 1, days=0, spend=0.0)
    assert any(k == "self_review" for k, _ in proto.events)
    # a narrative summary describes the review; it is language, untrusted
    ns = cs.core.all(l9.ObjectType.NARRATIVE_SUMMARY)
    assert ns and ns[0].authority is l9.Authority.UNTRUSTED


def test_review_is_hourly_not_every_cycle():
    now = datetime.now(UTC)
    assert self_review.should_review({}, now) is True             # never reviewed -> yes
    fresh = {"last_review_ts": now.isoformat()}
    assert self_review.should_review(fresh, now) is False          # just reviewed -> no
    old = {"last_review_ts": (now - timedelta(hours=2)).isoformat()}
    assert self_review.should_review(old, now) is True             # an hour passed -> yes


def test_unchanged_assessment_is_not_re_minted():
    cs = _cs()
    ext = {"topics_added": []}
    self_review.run_review(cs, ext, _Proto(), 1, days=0, spend=0.0)
    before = len(cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM))
    # same metrics -> same assessment text -> no new self-model claim minted
    self_review.run_review(cs, ext, _Proto(), 2, days=0, spend=0.0)
    after = len(cs.core.all(l9.ObjectType.SELF_MODEL_CLAIM))
    assert after == before


def test_review_shows_up_on_the_site(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.delenv("JONI_ONLINE", raising=False)
    from joni.autonomy.run import one_cycle
    summary = one_cycle()
    assert summary["reviewed"] is True                            # first cycle reviews
    html = (tmp_path / "docs" / "index.html").read_text()
    assert "Self-review" in html
    ext = json.loads((tmp_path / "state" / "extensions.json").read_text())
    assert ext["last_review"]["assessments"]
