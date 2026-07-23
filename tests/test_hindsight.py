"""H1+H2: the provisional layer is fed from real run signals (barred pattern hints, opened
contradictions), salient entries get tagged, and a sufficiently salient LATER event reactivates
in-window tags to review_due - content-independent, a review trigger not a rescue. Read-only wrt
Layer 9; append-only; provenance per trigger."""
from __future__ import annotations

import json
from types import SimpleNamespace

from joni.method_trial import hindsight
from joni.method_trial import provisional as pv


class _Core:
    def __init__(self, texts):
        self._t = texts

    def get(self, cid):
        t = self._t.get(cid)
        return SimpleNamespace(text=t) if t is not None else None


class _CS:
    def __init__(self, texts=None):
        self.core = _Core(texts or {})


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _paths(tmp_path):
    return SimpleNamespace(provisional=tmp_path / "provisional.jsonl",
                           hindsight_provenance=tmp_path / "prov.jsonl",
                           hindsight_panel=tmp_path / "hindsight.md")


def test_ingest_forms_weak_hints_and_open_contradictions():
    cs = _CS({"H-1": "the term 'x' recurs; shared mechanism remains untested"})
    ext = {"hyp_pattern_hints": ["H-1"], "conflicts_opened": [("C-1", "C-2")]}
    entries = hindsight.ingest(cs, ext, cycle=4)
    kinds = {e.kind for e in entries}
    assert pv.EntryKind.WEAK_HINT in kinds and pv.EntryKind.OPEN_CONTRADICTION in kinds
    hint = next(e for e in entries if e.kind is pv.EntryKind.WEAK_HINT)
    assert hint.refs == ("H-1",) and "recurs" in hint.content       # real content, real ref


def test_event_salience_counts_later_learning_events():
    assert hindsight.event_salience({}) == 0.0                        # quiet cycle -> no trigger
    assert hindsight.event_salience({"sandbox_trials": [{"verdict": "benefit"}]}) >= 0.5
    assert hindsight.event_salience({"skills_proposed": [{"admissible": True}]}) >= 0.5


def test_a_quiet_cycle_ingests_but_triggers_no_review(tmp_path):
    cs = _CS()
    p = _paths(tmp_path)
    ext = {"conflicts_opened": [("C-1", "C-2")]}                     # ingest, but no salient event
    out = hindsight.run(cs, ext, _Proto(), cycle=1, paths=p)
    assert out["ingested"] == 1 and out["reviewed"] == 0
    assert p.provisional.exists()
    assert not p.hindsight_provenance.exists()                       # nothing reactivated


def test_a_salient_later_event_reactivates_an_in_window_tag(tmp_path):
    cs = _CS()
    p = _paths(tmp_path)
    # cycle 1: an opened contradiction is ingested and tagged (attention 0.6 >= bar)
    hindsight.run(cs, {"conflicts_opened": [("C-1", "C-2")]}, _Proto(), cycle=1, paths=p)
    tagged = [e for e in pv.load(p.provisional) if e.stage is pv.LifecycleStage.TAGGED]
    assert len(tagged) == 1
    # cycle 2 (in window): a benefit trial is a salient event -> the tag is reactivated
    ev = {"sandbox_trials": [{"verdict": "benefit"}]}
    out = hindsight.run(cs, ev, _Proto(), cycle=2, paths=p)
    assert out["reviewed"] == 1
    due = [e for e in pv.load(p.provisional) if e.stage is pv.LifecycleStage.REVIEW_DUE]
    assert len(due) == 1
    # provenance records WHY it was reactivated
    prov = json.loads(p.hindsight_provenance.read_text().splitlines()[-1])
    assert prov["cycle"] == 2 and due[0].entry_id() in prov["reactivated"]


def test_reactivation_never_touches_layer9_or_consolidates(tmp_path):
    cs = _CS()
    p = _paths(tmp_path)
    hindsight.run(cs, {"conflicts_opened": [("C-1", "C-2")]}, _Proto(), cycle=1, paths=p)
    hindsight.run(cs, {"skills_proposed": [{"admissible": True}]}, _Proto(), cycle=2, paths=p)
    stages = {e.stage for e in pv.load(p.provisional)}
    # the strongest state reached is review_due - never consolidated (that is H3, human-gated)
    assert pv.LifecycleStage.CONSOLIDATED not in stages
    assert pv.LifecycleStage.REVIEW_DUE in stages


def test_run_is_fail_open_on_a_bad_paths(tmp_path):
    out = hindsight.run(_CS(), {}, _Proto(), cycle=1, paths=SimpleNamespace())
    assert out["ingested"] == 0 and out["reviewed"] == 0
