"""The first semantic proposal layer: Granite projects free text -> candidate claim proposals,
through the gate (never authoritative), captured for replay. Off by default."""

import desi_layer9 as l9
from joni.autonomy import model_call, projection
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


class _Item:
    def __init__(self, key, title, summary):
        self.key, self.title, self.summary = key, title, summary


class _Rel:
    def __init__(self, topic):
        self.topic = topic


def _mock_model(monkeypatch, payload):
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: payload)


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    cs = CoreState(seed_core())
    out = projection.project_and_learn(cs, [(_Item("k", "t", "s"), _Rel("routing"))],
                                       {}, _Proto(), 1)
    assert out == {"projected": 0, "claims": 0}            # opt-in: nothing happens


def test_projects_claims_as_candidate_sources_through_the_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    _mock_model(monkeypatch, '[{"text":"Local routing reduces request latency","topic":"routing"},'
                             ' {"text":"Episodic memory aids agent continuity","topic":"memory"}]')
    cs = CoreState(seed_core())
    before = len(cs.active_claims())
    item = _Item("arxiv:1", "Routing for agents", "a paper about routing and memory")
    out = projection.project_and_learn(cs, [(item, _Rel("routing"))], {}, _Proto(), 7)
    assert out["projected"] == 1 and out["claims"] == 2
    assert len(cs.active_claims()) == before + 2
    # the projected claims are candidate-authority SOURCES, never the privileged HUMAN origin
    new = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if any(s.startswith("granite:") for s in (c.provenance.source_ids or ()))]
    assert len(new) == 2
    assert all(c.provenance.origin_type.value == "source" for c in new)
    assert all(c.authority.value == "candidate" for c in new)


def test_call_is_captured_and_replays(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    calls = []

    def fake(profile, system, user):
        calls.append(1)
        return '[{"text":"Routing reduces latency","topic":"routing"}]'
    monkeypatch.setattr(model_call, "_complete", fake)

    item = _Item("arxiv:9", "Routing", "routing paper")
    judged = [(item, _Rel("routing"))]
    ext1: dict = {}
    projection.project_and_learn(CoreState(seed_core()), judged, ext1, _Proto(), 5)
    # a fresh state in a new cycle: the SAME prompt replays from the persisted capture
    ext2: dict = {}
    projection.project_and_learn(CoreState(seed_core()), judged, ext2, _Proto(), 6)
    assert len(calls) == 1                                  # second cycle replayed, no new call
    assert ext1["semantic_calls"][0]["replayed"] is False
    assert ext2["semantic_calls"][0]["replayed"] is True


def test_state_slice_density_is_k(monkeypatch):
    cs = CoreState(seed_core())
    for i in range(6):
        cs.learn(f"routing claim number {i} about latency", "routing")
    sl = projection.state_slice(cs, "routing and latency", k=1)
    assert len(sl) <= 1                                     # k=1 -> at most one state element
    assert projection.state_slice(cs, "x", k=0) == []
