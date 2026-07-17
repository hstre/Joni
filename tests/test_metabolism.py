"""The homeostatic metabolism: pressures, the worst-constraint load, hysteresis, and the
read-only observe step that couples intake to consolidation."""
from types import SimpleNamespace

from joni.autonomy import metabolism as mb


def test_pressures_are_scaled_to_their_caps():
    vit = {"unsupported_hypotheses": 15, "stagnation_cycles": 6}
    p = mb.pressures(vit, open_conflicts=10, prev_open_conflicts=0, untested_methods=20)
    assert p["backlog"] == 0.5           # 15 / 30
    assert p["untested_methods"] == 0.5  # 20 / 40
    assert p["conflict_growth"] == 0.5   # (10-0) / 20
    assert p["stagnation"] == 0.5        # 6 / 12


def test_pressures_clamp_at_one():
    vit = {"unsupported_hypotheses": 999, "stagnation_cycles": 999}
    p = mb.pressures(vit, open_conflicts=999, prev_open_conflicts=0, untested_methods=999)
    assert all(v == 1.0 for v in p.values())


def test_conflict_growth_is_never_negative():
    # conflicts shrinking (consolidation working) is not a pressure
    p = mb.pressures({}, open_conflicts=2, prev_open_conflicts=10, untested_methods=0)
    assert p["conflict_growth"] == 0.0


def test_load_is_the_worst_pressure_not_the_average():
    assert mb.load({"a": 0.1, "b": 0.9, "c": 0.2}) == 0.9   # worst wins, not the mean
    assert mb.load({}) == 0.0


def test_hysteresis_avoids_flip_flopping():
    # hungry -> sated only at/above high
    assert mb.next_state("hungry", 0.69) == "hungry"
    assert mb.next_state("hungry", 0.70) == "sated"
    # sated -> hungry only at/below low
    assert mb.next_state("sated", 0.41) == "sated"
    assert mb.next_state("sated", 0.40) == "hungry"
    # inside the band, hold the current state (this is the whole point of the band)
    assert mb.next_state("hungry", 0.55) == "hungry"
    assert mb.next_state("sated", 0.55) == "sated"


def test_intake_allowed_accepts_a_string_or_a_record():
    assert mb.intake_allowed("hungry") is True
    assert mb.intake_allowed("sated") is False
    assert mb.intake_allowed({"state": "sated"}) is False
    assert mb.intake_allowed({"state": "hungry"}) is True


class _Core:
    def __init__(self, conflicts, methods):
        self._conf, self._meth = conflicts, methods

    def open_conflicts(self):
        return self._conf

    def all(self, _type):
        return self._meth          # observe only asks for METHOD objects


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _method(trial_count, status="candidate"):
    return SimpleNamespace(trial_count=trial_count, status=SimpleNamespace(value=status))


def test_observe_satiates_on_a_full_backlog_and_notes_the_transition():
    cs = SimpleNamespace(core=_Core([1, 2], [_method(0) for _ in range(40)]))
    ext = {"vitality": {"unsupported_hypotheses": 30, "stagnation_cycles": 12}}
    proto = _Proto()
    rec = mb.observe(cs, ext, proto, cycle=5)
    assert rec["state"] == "sated"                     # backlog 30/30 = 1.0 -> load 1.0
    assert rec["untested_methods"] == 40
    assert ext["metabolism"]["state"] == "sated"
    assert ext["metabolism_history"][-1]["cycle"] == 5
    assert any("metabolism" in s for _, s in proto.events)   # hungry -> sated recorded


def test_observe_counts_only_untried_candidate_methods():
    methods = [_method(0), _method(3), _method(0, status="retired")]
    cs = SimpleNamespace(core=_Core([], methods))
    rec = mb.observe(cs, {}, _Proto(), cycle=1)
    assert rec["untested_methods"] == 1                # trialed + retired drop out
    assert rec["state"] == "hungry"                    # tiny load -> stays hungry


def test_observe_holds_hungry_when_load_is_moderate():
    # a moderate load inside the hysteresis band must not satiate from a hungry start
    cs = SimpleNamespace(core=_Core([], [_method(0) for _ in range(20)]))
    ext = {"vitality": {"unsupported_hypotheses": 15}}   # backlog 0.5, methods 0.5 -> load 0.5
    rec = mb.observe(cs, ext, _Proto(), cycle=2)
    assert rec["load"] == 0.5 and rec["state"] == "hungry"
