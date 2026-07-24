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


def _dispute(**over):
    base = dict(claim_ids=["C-1", "C-2"], topic="routing", size=3)
    base.update(over)
    return base


def test_ingest_forms_weak_hints_and_condensed_disputes():
    cs = _CS({"H-1": "the term 'x' recurs; shared mechanism remains untested"})
    ext = {"hyp_pattern_hints": ["H-1"], "disputes": [_dispute()]}
    entries = hindsight.ingest(cs, ext, cycle=4)
    kinds = {e.kind for e in entries}
    assert pv.EntryKind.WEAK_HINT in kinds and pv.EntryKind.OPEN_CONTRADICTION in kinds
    hint = next(e for e in entries if e.kind is pv.EntryKind.WEAK_HINT)
    assert hint.refs == ("H-1",) and "recurs" in hint.content       # real content, real ref
    dispute = next(e for e in entries if e.kind is pv.EntryKind.OPEN_CONTRADICTION)
    assert dispute.refs == ("C-1", "C-2") and dispute.topic == "routing"   # the condensed dispute


def test_disputes_are_not_crowded_out_by_the_flood_of_pattern_hints():
    # the live-window bug: 462 pattern hints filled the budget before any dispute reached the layer,
    # so nothing taggable was staged and the trigger stayed idle. Disputes must be ingested first.
    cs = _CS({f"H-{i}": f"'x{i}' recurs" for i in range(50)})
    ext = {"hyp_pattern_hints": [f"H-{i}" for i in range(50)],     # a flood of junk
           "disputes": [_dispute(claim_ids=["C-1", "C-2"], topic="a"),
                        _dispute(claim_ids=["C-3", "C-4"], topic="b")]}
    entries = hindsight.ingest(cs, ext, cycle=1)
    contradictions = [e for e in entries if e.kind is pv.EntryKind.OPEN_CONTRADICTION]
    assert len(contradictions) == 2                # both disputes reached the layer (not crowded)
    assert all(e.attention_salience >= pv.TAG_THRESHOLD for e in contradictions)   # taggable


def test_event_salience_counts_later_learning_events():
    assert hindsight.event_salience({}) == 0.0                        # quiet cycle -> no trigger
    assert hindsight.event_salience({"sandbox_trials": [{"verdict": "benefit"}]}) >= 0.5
    assert hindsight.event_salience({"skills_proposed": [{"admissible": True}]}) >= 0.5


def test_a_quiet_cycle_ingests_but_triggers_no_review(tmp_path):
    cs = _CS()
    p = _paths(tmp_path)
    ext = {"disputes": [_dispute()]}                     # ingest, but no salient event
    out = hindsight.run(cs, ext, _Proto(), cycle=1, paths=p)
    assert out["ingested"] == 1 and out["reviewed"] == 0
    assert p.provisional.exists()
    assert not p.hindsight_provenance.exists()                       # nothing reactivated


def test_a_salient_event_reactivates_and_resolves_a_live_contradiction(tmp_path):
    cs = _CS({"C-1": "claim one", "C-2": "claim two"})       # the conflict's claims are live
    p = _paths(tmp_path)
    # cycle 1: an opened contradiction is ingested and tagged (attention 0.6 >= bar)
    hindsight.run(cs, {"disputes": [_dispute()]}, _Proto(), cycle=1, paths=p)
    assert any(e.stage is pv.LifecycleStage.TAGGED for e in pv.load(p.provisional))
    # cycle 2 (in window): a benefit trial is a salient event -> the tag is reactivated AND resolved
    ev = {"sandbox_trials": [{"verdict": "benefit"}]}
    out = hindsight.run(cs, ev, _Proto(), cycle=2, paths=p)
    assert out["reviewed"] == 1
    # a live contradiction resolves to contradiction_detected (the #5 feed); review_due is transient
    cd = [e for e in pv.load(p.provisional) if e.stage is pv.LifecycleStage.CONTRADICTION_DETECTED]
    assert len(cd) == 1 and cd[0].epistemic_significance == 1.0
    prov = json.loads(p.hindsight_provenance.read_text().splitlines()[-1])
    assert prov["cycle"] == 2 and prov["reactivated"][0]["outcome"] == "contradiction_detected"


def test_reactivation_never_consolidates(tmp_path):
    cs = _CS({"C-1": "claim one", "C-2": "claim two"})
    p = _paths(tmp_path)
    hindsight.run(cs, {"disputes": [_dispute()]}, _Proto(), cycle=1, paths=p)
    hindsight.run(cs, {"skills_proposed": [{"admissible": True}]}, _Proto(), cycle=2, paths=p)
    stages = {e.stage for e in pv.load(p.provisional)}
    # a review NEVER auto-consolidates into Layer 9; the strongest outcome here is a typed feed
    assert pv.LifecycleStage.CONSOLIDATED not in stages
    assert pv.LifecycleStage.CONTRADICTION_DETECTED in stages


def test_measure_significance_counts_live_refs():
    cs = _CS({"L-1": "live"})
    live = pv.ProvisionalEntry(kind=pv.EntryKind.WEAK_HINT, content="x", source="s",
                               refs=("L-1",), created_cycle=1)
    dead = pv.ProvisionalEntry(kind=pv.EntryKind.WEAK_HINT, content="x", source="s",
                               refs=("GONE",), created_cycle=1)
    assert hindsight.measure_significance(cs, live) == 1.0
    assert hindsight.measure_significance(cs, dead) == 0.0


def _review_due(**over):
    base = dict(kind=pv.EntryKind.WEAK_HINT, content="a bare hint", source="pattern_hint",
                refs=("L-1",), created_cycle=1, stage=pv.LifecycleStage.REVIEW_DUE, review_count=1)
    base.update(over)
    return pv.ProvisionalEntry(**base)


def test_decide_maps_measured_state_to_typed_outcomes():
    cs = _CS({"L-1": "live"})
    assert hindsight.decide(cs, _review_due(refs=("GONE",)), cycle=5).stage \
        is pv.LifecycleStage.REJECTED                        # gone refs -> rejected
    wf = ("Because load drives retries, when traffic is heavy we should observe errors; refuted "
          "if flat.")
    assert hindsight.decide(cs, _review_due(content=wf), cycle=5).stage \
        is pv.LifecycleStage.HYPOTHESIS_OPENED               # became testable -> #4 TEST
    assert hindsight.decide(cs, _review_due(kind=pv.EntryKind.OPEN_CONTRADICTION), cycle=5).stage \
        is pv.LifecycleStage.CONTRADICTION_DETECTED          # live contradiction -> #5 feed
    # fully anchored (sig 1.0) but not a claim -> an associative note only
    assert hindsight.decide(cs, _review_due(), cycle=5).stage is pv.LifecycleStage.LINKED_ONLY
    # partial significance, first review, no new evidence -> WAIT (re-tagged, count persists)
    waited = hindsight.decide(cs, _review_due(refs=("L-1", "GONE"), review_count=1), cycle=5)
    assert waited.stage is pv.LifecycleStage.TAGGED and waited.review_count == 1   # #4 WAIT
    # #4 ARCHIVE: after two evidence-free re-evaluations -> expired
    assert hindsight.decide(cs, _review_due(refs=("L-1", "GONE"), review_count=2), cycle=5).stage \
        is pv.LifecycleStage.EXPIRED


def test_run_is_fail_open_on_a_bad_paths(tmp_path):
    out = hindsight.run(_CS(), {}, _Proto(), cycle=1, paths=SimpleNamespace())
    assert out["ingested"] == 0 and out["reviewed"] == 0
