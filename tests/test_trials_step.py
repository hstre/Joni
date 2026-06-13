"""Kevin trials Joni's shelf in-process each cycle - recorded, never promoted."""

import desi_layer9 as l9
from joni.autonomy import trials
from joni.autonomy.core_state import CoreState


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_no_op_without_kevin(monkeypatch):
    # Simulate Kevin not being installed: the step is a clean no-op.
    import builtins
    real_import = builtins.__import__

    def fake(name, *a, **k):
        if name == "kevin" or name.startswith("kevin."):
            raise ImportError("no kevin")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)
    cs = CoreState(l9.Layer9())
    out = trials.run_trials(cs, _Proto(), 0)
    assert out == {"trialed": 0, "succeeded": 0, "failed": 0, "activation_ready": 0}


def test_kevin_trials_the_methods_on_jonis_shelf():
    import pytest
    pytest.importorskip("kevin")
    cs = CoreState(l9.Layer9())
    mid = cs.propose_method(name="react-router",
                            summary="a declarative routing framework for the web",
                            applicable_to=("routing",), origin="https://github.com/x")
    proto = _Proto()
    out = trials.run_trials(cs, proto, 1)
    assert out["trialed"] == 1
    m = cs.core.get(mid)
    assert m.trial_count == 1
    assert m.status is l9.Status.CANDIDATE          # trialed, never promoted
    assert any(k == "trialed" for k, _ in proto.events)


def test_trials_dedup_within_the_same_run_id():
    import pytest
    pytest.importorskip("kevin")
    cs = CoreState(l9.Layer9())
    mid = cs.propose_method(name="five_whys", summary="a technique to chase a cause",
                            applicable_to=("routing",))
    trials.run_trials(cs, _Proto(), 3, run_id="same")
    trials.run_trials(cs, _Proto(), 3, run_id="same")     # same id -> no second trial
    assert cs.core.get(mid).trial_count == 1
