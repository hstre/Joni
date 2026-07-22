"""S4: probationary skills mature through REPEATED sandbox passes against their OWN verification;
a deterministic assessor surfaces promote/archive recommendations - it never writes a skill status
(activation stays human/Layer-9 gated). Re-trials are OFF unless JONI_SANDBOX_LLM_TRIALS=1."""
from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from joni.method_trial import skill, skill_lifecycle

# a correct unit-normalising solver (what synthesis returns for the normalisation method)
_GOOD_SOLVER = (
    "def solve(payload):\n"
    "    import re\n"
    "    U={'m':(1.0,'len'),'km':(1000.0,'len'),'cm':(0.01,'len'),'mm':(0.001,'len'),"
    "'g':(1.0,'mass'),'kg':(1000.0,'mass'),'mg':(0.001,'mass'),"
    "'s':(1.0,'time'),'min':(60.0,'time'),'h':(3600.0,'time')}\n"
    "    def c(x):\n"
    "        m=re.match(r'^\\s*([0-9]+(?:\\.[0-9]+)?)\\s*([a-z]+)\\s*$', x.strip().lower())\n"
    "        if not m or m.group(2) not in U: return None\n"
    "        f,d=U[m.group(2)]; return (round(float(m.group(1))*f,9), d)\n"
    "    ca,cb=c(payload['a']),c(payload['b'])\n"
    "    if ca is None or cb is None: return {'label':'unknown'}\n"
    "    return {'label':'same' if ca==cb else 'different'}\n"
)


def _method(sc, tc):
    return SimpleNamespace(id="M-1", name="unit-lens",
                           summary="normalise the unit before comparing",
                           success_count=sc, trial_count=tc)


class _CS:
    def __init__(self, method):
        self._m = method
        self.core = SimpleNamespace(get=lambda oid: method if oid == method.id else None)
        self.recorded = []

    def record_method_trial(self, method_id, *, success, run_id):
        self.recorded.append((method_id, success))
        self._m.trial_count += 1                     # accumulate like the real gate
        if success:
            self._m.success_count += 1


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cand(**over):
    base = dict(method_id="M-1", trigger="two measurement strings",
                procedure="normalise the unit before comparing",
                verification="frozen_unit_equality_v1", applicability_boundary="not free text",
                evidence_anchors=("M-1",), operational_reliability=1.0)
    base.update(over)
    return skill.SkillCandidate(**base)


def _seed(store, *cands):
    store.write_text("\n".join(json.dumps(c.to_record(), ensure_ascii=False) for c in cands) + "\n")


def test_load_candidates_takes_the_latest_per_skill_and_skips_junk(tmp_path):
    store = tmp_path / "skill_candidates.jsonl"
    _seed(store, _cand(), _cand())                          # same skill twice -> last wins
    store.write_text(store.read_text() + "{ not json\n")    # a malformed line must be skipped
    cands = skill_lifecycle.load_candidates(store)
    assert len(cands) == 1 and cands[0].verification == "frozen_unit_equality_v1"


def test_load_candidates_missing_store_is_empty(tmp_path):
    assert skill_lifecycle.load_candidates(tmp_path / "nope.jsonl") == []
    assert skill_lifecycle.load_candidates(None) == []


def test_assessment_runs_without_trials_and_writes_the_sheet_and_log(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_SANDBOX_LLM_TRIALS", raising=False)
    store = tmp_path / "skill_candidates.jsonl"
    _seed(store, _cand())
    sheet, log = tmp_path / "skill_lifecycle.md", tmp_path / "skill_lifecycle.jsonl"
    cs = _CS(_method(sc=4, tc=5))                            # already earned promotion by evidence
    ext = {}
    out = skill_lifecycle.run(cs, ext, _Proto(), store_path=store, log_path=log, sheet_path=sheet)
    assert out["assessed"] == 1 and out["retrials"] == 0     # no re-trial while disabled
    assert out["promote"] == 1
    assert cs.recorded == []                                 # NEVER wrote a status / trial
    assert sheet.exists() and "Empfohlen zur Aktivierung" in sheet.read_text()
    assert json.loads(log.read_text().splitlines()[0])["action"] == "promote"
    assert ext["skill_lifecycle"][0]["action"] == "promote"


def test_a_measured_failure_is_recommended_for_archival(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_SANDBOX_LLM_TRIALS", raising=False)
    store = tmp_path / "s.jsonl"
    _seed(store, _cand())
    cs = _CS(_method(sc=1, tc=4))                            # 0.25 reliability -> failed
    out = skill_lifecycle.run(cs, {}, _Proto(), store_path=store,
                              log_path=tmp_path / "l.jsonl", sheet_path=tmp_path / "s.md")
    assert out["archive"] == 1 and out["promote"] == 0


def test_no_candidates_is_a_clean_noop(tmp_path):
    out = skill_lifecycle.run(_CS(_method(0, 0)), {}, _Proto(), store_path=tmp_path / "empty.jsonl")
    assert out == {"assessed": 0, "retrials": 0, "promote": 0, "archive": 0}


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="runs a synthesised solver")
def test_retrial_reproves_the_skill_and_moves_the_counters(tmp_path, monkeypatch):
    monkeypatch.setenv("JONI_SANDBOX_LLM_TRIALS", "1")
    store = tmp_path / "s.jsonl"
    _seed(store, _cand())
    cs = _CS(_method(sc=0, tc=0))                            # fresh: must be re-proven from scratch

    def call(system, user, *, run_id, budget, runs_per_week):
        return _GOOD_SOLVER

    out = skill_lifecycle.run(cs, {}, _Proto(), store_path=store, log_path=tmp_path / "l.jsonl",
                              sheet_path=tmp_path / "s.md", call=call)
    assert out["retrials"] == 1                              # the one eligible probationary skill
    assert cs.recorded == [("M-1", True)]                   # a benefit re-proof, recorded via gate


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="runs a synthesised solver")
def test_a_decided_skill_is_not_re_trialed(tmp_path, monkeypatch):
    monkeypatch.setenv("JONI_SANDBOX_LLM_TRIALS", "1")
    store = tmp_path / "s.jsonl"
    _seed(store, _cand())
    cs = _CS(_method(sc=4, tc=5))                            # already promote-ready -> no re-trial

    def call(system, user, *, run_id, budget, runs_per_week):
        return _GOOD_SOLVER

    out = skill_lifecycle.run(cs, {}, _Proto(), store_path=store, sheet_path=tmp_path / "s.md",
                              call=call)
    assert out["retrials"] == 0 and cs.recorded == []       # terminal skills cost no budget
