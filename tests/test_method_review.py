"""The method gate: Granite judges a candidate BEFORE it is shelved for Kevin, and a bounded
review drains the already-shelved graveyard of paper-title 'methods'. Non-authoritative: an
invalid verdict only withholds/retires a 0-trial, source-harvested CANDIDATE through the gate;
trialed and joni-emergent methods are never touched; no verdict burns nothing."""

from types import SimpleNamespace

import desi_layer9 as l9
from joni.autonomy import method_review, methods, model_call
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _item(title, summary="a framework for agents", key=None, source="arxiv"):
    return SimpleNamespace(title=title, summary=summary, key=key or title[:20],
                           source=source, url=f"https://x/{key or title[:8]}")


def _rel(topic="routing"):
    return SimpleNamespace(topic=topic)


def _verdict(monkeypatch, mapping):
    def fake(profile, system, user):
        for needle, valid in mapping.items():
            if needle in user:
                return '{"valid": %s, "reason": "t"}' % ("true" if valid else "false")
        return '{"valid": true, "reason": "default"}'
    monkeypatch.setattr(model_call, "_complete", fake)


def test_harvest_shelves_only_gate_approved_methods(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    _verdict(monkeypatch, {"Cosmological": False, "speculative decoding": True})
    cs = CoreState(seed_core())
    ext: dict = {}
    proto = _Proto()
    # short procedure names (they pass the title filter and reach the Granite gate); the stub keys
    # on 'Cosmological' (reject) and 'speculative decoding' (approve) in the judged text.
    out = methods.harvest(cs, [
        (_item("Cosmological vorton framework", key="k1",
               summary="Cosmological equations framework"), _rel()),
        (_item("speculative decoding pipeline", key="k2",
               summary="a speculative decoding method"), _rel()),
    ], ext, proto, 1)
    names = [m.name for m in cs.core.all(l9.ObjectType.METHOD)]
    assert out["methods"] == 1
    assert any("speculative decoding" in n for n in names)
    assert not any("Cosmological" in n for n in names)     # junk never shelved
    assert "k1" in ext["methods_seen"]                     # a real verdict: never re-asked
    assert any("rejected by the gate" in s for _, s in proto.events)


def test_a_failed_gate_call_shelves_nothing_and_burns_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))

    def _down(p, s, u):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(model_call, "_complete", _down)
    cs = CoreState(seed_core())
    ext: dict = {}
    out = methods.harvest(cs, [(_item("A retrieval framework", key="k3"), _rel())],
                          ext, _Proto(), 1)
    assert out["methods"] == 0
    assert cs.core.all(l9.ObjectType.METHOD) == []
    assert "k3" not in ext.get("methods_seen", [])         # unburned: retried next cycle


def test_gate_disabled_keeps_the_legacy_lexical_harvest(monkeypatch, tmp_path):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    cs = CoreState(seed_core())
    out = methods.harvest(cs, [(_item("Any old framework", key="k4"), _rel())], {}, _Proto(), 1)
    assert out["methods"] == 1                             # legacy mode unchanged


def test_review_retires_junk_candidates_but_never_trialed_or_emergent_ones(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    _verdict(monkeypatch, {"Soundscapes": False, "vorton": False, "distillation": True})
    cs = CoreState(seed_core())
    junk1 = cs.propose_method(name="Participatory Soundscapes chapter 3",
                              summary="teaching through sound art", origin="https://x/1")
    junk2 = cs.propose_method(name="Superluminal vorton mechanics",
                              summary="causal preservation of warp metrics", origin="https://x/2")
    real = cs.propose_method(name="Sequence-level distillation",
                             summary="a training technique for small models", origin="https://x/3")
    emergent = cs.propose_method(name="catches-as-a-lens", summary="recurs across topics",
                                 origin="joni:emergent")
    proto = _Proto()
    out = method_review.review_methods(cs, {}, proto, 1)
    by_id = {m.id: m for m in cs.core.all(l9.ObjectType.METHOD)}
    assert out["rejected"] == 2
    assert by_id[junk1].status.value == "rejected"
    assert by_id[junk2].status.value == "rejected"
    assert by_id[real].status.value == "candidate"         # a real method stays shelved
    assert by_id[emergent].status.value == "candidate"     # governed elsewhere: untouched
    assert any("method-review retired" in s for _, s in proto.events)


def test_review_is_bounded_and_caches_verdicts(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setenv("JONI_METHOD_LLM_MAX_CALLS", "2")
    calls = []

    def fake(profile, system, user):
        calls.append(1)
        return '{"valid": false, "reason": "junk"}'
    monkeypatch.setattr(model_call, "_complete", fake)
    cs = CoreState(seed_core())
    for i in range(4):
        cs.propose_method(name=f"junk method number {i}", summary="x", origin=f"https://x/{i}")
    ext: dict = {}
    method_review.review_methods(cs, ext, _Proto(), 1)
    assert len(calls) == 2                                 # per-cycle call cap
    method_review.review_methods(cs, ext, _Proto(), 2)     # next cycle: 2 more, cached skipped
    assert len(calls) == 4
    assert len(ext["method_llm_seen"]) == 4


def test_review_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    cs = CoreState(seed_core())
    cs.propose_method(name="anything", summary="x", origin="https://x/9")
    out = method_review.review_methods(cs, {}, _Proto(), 1)
    assert out == {"reviewed": 0, "rejected": 0}
    assert cs.core.all(l9.ObjectType.METHOD)[0].status.value == "candidate"
