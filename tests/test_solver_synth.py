"""P2: an LLM synthesises a solver from a method's text; the sandbox contains it and the metric
alone judges it. The model call is injected, so no live model is needed to prove the pipeline."""
from __future__ import annotations

import sys

import pytest

from joni.method_trial import sandbox_trial
from joni.method_trial import solver_synth as ss

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"),
                                reason="runs synthesised solvers in the POSIX sandbox")

_TASK_DESC = ("payload has keys 'a' and 'b' (measurement strings like '5 km'); return\n"
              "{'label': 'same'} if they denote the same quantity else {'label': 'different'}.")

# a correct unit-normalising solver, as an LLM might return it (inside a markdown fence)
_GOOD = '''```python
def solve(payload):
    import re
    U = {"m":(1.0,"len"),"km":(1000.0,"len"),"cm":(0.01,"len"),"mm":(0.001,"len"),
         "g":(1.0,"mass"),"kg":(1000.0,"mass"),"mg":(0.001,"mass"),
         "s":(1.0,"time"),"min":(60.0,"time"),"h":(3600.0,"time")}
    def c(x):
        m = re.match(r"^\\s*([0-9]+(?:\\.[0-9]+)?)\\s*([a-z]+)\\s*$", x.strip().lower())
        if not m or m.group(2) not in U: return None
        f,d = U[m.group(2)]; return (round(float(m.group(1))*f,9), d)
    ca,cb = c(payload["a"]), c(payload["b"])
    if ca is None or cb is None: return {"label":"unknown"}
    return {"label":"same" if ca==cb else "different"}
```'''

_ALWAYS_DIFFERENT = "def solve(payload):\n    return {'label': 'different'}\n"
_UNSAFE = ("def solve(payload):\n    import os\n    os.system('echo pwned')\n"
           "    return {'label':'same'}\n")


def _fake_call(src):
    def call(system, user, *, run_id, budget, runs_per_week):
        return src
    return call


def _problem():
    return sandbox_trial.unit_equality_spec()   # its intervention_src is ignored / replaced


def test_extract_code_handles_fences_and_prose():
    assert ss._extract_code("```python\ndef solve(p):\n    return {}\n```").startswith("def solve")
    assert ss._extract_code("here you go:\ndef solve(p): return {}").startswith("def solve")
    assert ss._extract_code("I cannot help with that.") is None


def test_synthesis_returns_none_when_the_model_is_silent():
    assert ss.synthesize_solver("normalise units", _TASK_DESC, call=_fake_call(None)) is None
    assert ss.synthesize_solver("", _TASK_DESC, call=_fake_call(_GOOD)) is None


def test_a_synthesised_good_solver_is_trialed_and_shows_benefit():
    out = ss.trial_method(None, "Normalise the unit before comparing two quantities.",
                          _problem(), _TASK_DESC, call=_fake_call(_GOOD))
    assert out["trialed"] is True
    assert out["verdict"] == "benefit"
    assert out["result"]["intervention"] == 0.0 and out["result"]["passed"] is True


def test_a_worse_solver_is_recorded_honestly_as_harmful():
    out = ss.trial_method(None, "Always answer different.", _problem(), _TASK_DESC,
                          call=_fake_call(_ALWAYS_DIFFERENT))
    assert out["trialed"] is True and out["verdict"] == "harmful"   # worse than the baseline


def test_unsafe_generated_code_is_contained_not_executed():
    # the P0 sandbox blocks 'import os'; the solver fails every case -> contained, never a crash
    out = ss.trial_method(None, "do something", _problem(), _TASK_DESC, call=_fake_call(_UNSAFE))
    assert out["trialed"] is True
    assert out["verdict"] in {"no_benefit", "harmful"}
    assert out["result"]["intervention"] == 1.0                    # every case failed, contained


def test_no_solver_when_synthesis_fails():
    out = ss.trial_method(None, "x", _problem(), _TASK_DESC, call=_fake_call("sorry, no code here"))
    assert out["trialed"] is False and out["verdict"] == "no_solver"
