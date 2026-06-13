from joni.memory import autobiography, recall, recent
from joni.operators import record_memory
from joni.state import Layer9


def _populate():
    s = Layer9()
    record_memory(s, "learned", "discovered local routing saves cost")
    s.tick = 1
    record_memory(s, "changed_mind", "rejected the privacy claim after evidence")
    s.tick = 2
    record_memory(s, "started_project", "began work on episodic memory")
    return s


def test_recall_ranks_by_relevance():
    s = _populate()
    hits = recall(s, "privacy evidence", limit=2)
    assert hits
    assert "privacy" in hits[0].summary


def test_recent_is_newest_first():
    s = _populate()
    r = recent(s, 2)
    assert r[0].tick == 2
    assert r[1].tick == 1


def test_autobiography_is_chronological():
    s = _populate()
    lines = autobiography(s)
    assert len(lines) == 3
    assert lines[0].startswith("t0")
    assert "t2" in lines[2]


def test_recall_falls_back_to_recent_when_no_overlap():
    s = _populate()
    hits = recall(s, "zzz nonexistent topic", limit=2)
    assert len(hits) == 2  # falls back to recent
