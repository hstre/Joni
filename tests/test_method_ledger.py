"""Method Zustandsbuch: deterministic state derivation, transition logging, read-only view."""
import json
from types import SimpleNamespace

from joni.autonomy import method_ledger as ml


def _m(mid, status, name="m"):
    return SimpleNamespace(id=mid, name=name, status=SimpleNamespace(value=status))


def _env(mid, verdict):
    return {"payload": {"method_id": mid, "decision": {"verdict": verdict}}}


class _Core:
    def __init__(self, methods, envs):
        self._m, self._e = methods, envs

    def all(self, _otype):
        return self._m

    def method_trial_events(self):
        return self._e


class _CS:
    def __init__(self, core):
        self.core = core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_state_derivation_from_status_and_verdicts():
    assert ml._state_for("rejected", []) == ml.RETIRED
    assert ml._state_for("active", ["no_benefit"]) == ml.ACTIVE     # promoted wins
    assert ml._state_for("candidate", []) == ml.PROPOSED
    assert ml._state_for("candidate", ["success"]) == ml.READY
    assert ml._state_for("candidate", ["partial_success"]) == ml.READY
    assert ml._state_for("candidate", ["no_benefit"]) == ml.SHELVED
    assert ml._state_for("candidate", ["harmful", "no_benefit"]) == ml.SHELVED
    assert ml._state_for("candidate", ["no_benefit", "success"]) == ml.READY   # any positive
    assert ml._state_for("candidate", ["inconclusive"]) == ml.TRIALED


def test_snapshot_joins_methods_with_their_trial_verdicts():
    cs = _CS(_Core(
        [_m("M-1", "candidate", "reduction"), _m("M-2", "candidate", "portfolio"),
         _m("M-3", "rejected", "cpp-guide")],
        [_env("M-1", "success"), _env("M-2", "no_benefit"), _env("M-2", "no_benefit")]))
    rows = {r["method_id"]: r for r in ml.snapshot(cs)}
    assert rows["M-1"]["state"] == ml.READY and rows["M-1"]["n_trials"] == 1
    assert rows["M-2"]["state"] == ml.SHELVED and rows["M-2"]["n_trials"] == 2
    assert rows["M-3"]["state"] == ml.RETIRED and rows["M-3"]["n_trials"] == 0


def test_transitions_only_fire_on_a_state_change():
    rows = [{"method_id": "M-1", "name": "r", "state": ml.READY,
             "status": "candidate", "last_verdict": "success"}]
    first = ml.transitions(rows, {}, 1)                 # new method: None -> ready
    assert first and first[0]["from"] is None and first[0]["to"] == ml.READY
    same = ml.transitions(rows, {"M-1": ml.READY}, 2)   # unchanged -> nothing
    assert same == []


def _paths(tmp):
    return SimpleNamespace(method_ledger=tmp / "ml.md", method_ledger_series=tmp / "ml.jsonl")


def test_run_ledger_writes_table_and_transition_log(tmp_path):
    cs = _CS(_Core([_m("M-1", "candidate", "reduction")], [_env("M-1", "success")]))
    proto = _Proto()
    paths = _paths(tmp_path)
    res = ml.run_ledger(cs, proto, 7, paths=paths)
    assert res["methods"] == 1 and res["transitions"] == 1     # first sighting logs one transition
    assert "Methoden-Zustandsbuch" in (tmp_path / "ml.md").read_text()
    logged = [json.loads(x) for x in (tmp_path / "ml.jsonl").read_text().splitlines()]
    assert logged[0]["to"] == ml.READY and logged[0]["from"] is None
    assert any(k == "method_ledger" for k, _ in proto.events)
    # second run, same state -> no new transition appended
    ml.run_ledger(cs, proto, 8, paths=paths)
    assert len((tmp_path / "ml.jsonl").read_text().splitlines()) == 1
