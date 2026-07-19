"""P3: matched shelf methods get trialed in the loop and the measured verdict is recorded, so the
backlog drains on evidence. The model call is injected; OFF unless JONI_SANDBOX_LLM_TRIALS=1."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from joni.method_trial import lifecycle, problems

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                                reason="runs synthesised solvers in the POSIX sandbox")

# a correct unit-normalising solver (what synthesis would return for a normalisation method)
_GOOD = (
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
_ALWAYS_DIFFERENT = "def solve(payload):\n    return {'label':'different'}\n"


def _method(mid, name, summary):
    return SimpleNamespace(id=mid, name=name, summary=summary,
                           status=SimpleNamespace(value="candidate"), trial_count=0)


class _CS:
    def __init__(self, methods):
        self.core = SimpleNamespace(all=lambda _t: methods)
        self.recorded = []

    def record_method_trial(self, method_id, *, success, run_id):
        self.recorded.append((method_id, success))


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _call(src):
    def call(system, user, *, run_id, budget, runs_per_week):
        return src
    return call


def test_match_pairs_a_normalisation_method_and_skips_unrelated():
    assert problems.match("unit-lens", "normalise the unit before comparing") is not None
    assert problems.match("AttentionNet", "a study of transformer attention") is None


def test_disabled_is_a_clean_noop(monkeypatch):
    monkeypatch.delenv("JONI_SANDBOX_LLM_TRIALS", raising=False)
    cs = _CS([_method("M-1", "x", "normalise units")])
    out = lifecycle.run(cs, {}, _Proto(), call=_call(_GOOD))
    assert out["trialed"] == 0 and cs.recorded == []


def test_a_matched_method_is_trialed_and_a_benefit_recorded(monkeypatch):
    monkeypatch.setenv("JONI_SANDBOX_LLM_TRIALS", "1")
    cs = _CS([_method("M-1", "unit-lens", "normalise the unit before comparing quantities"),
              _method("M-2", "attn", "a study of attention")])   # M-2 has no benchmark
    ext = {}
    out = lifecycle.run(cs, ext, _Proto(), call=_call(_GOOD))
    assert out["trialed"] == 1                                   # only the matched method
    assert cs.recorded == [("M-1", True)]                        # benefit -> success recorded
    assert ext["sandbox_trials"][0]["verdict"] == "benefit"


def test_a_harmful_verdict_is_recorded_as_a_failure(monkeypatch):
    monkeypatch.setenv("JONI_SANDBOX_LLM_TRIALS", "1")
    cs = _CS([_method("M-1", "unit-lens", "normalise units before comparing")])
    out = lifecycle.run(cs, {}, _Proto(), call=_call(_ALWAYS_DIFFERENT))
    assert out["trialed"] == 1 and cs.recorded == [("M-1", False)]   # worse -> success=False


def test_record_method_trial_moves_the_ledger_counters():
    import desi_layer9 as l9
    from joni.autonomy.core_state import CoreState, seed_core
    cs = CoreState(seed_core())
    mid = cs.propose_method(name="unit-lens", summary="normalise units")
    cs.record_method_trial(mid, success=True, run_id="t")
    m = next(x for x in cs.core.all(l9.ObjectType.METHOD) if x.id == mid)
    assert m.trial_count == 1 and m.success_count == 1     # the counter moved via the gate
