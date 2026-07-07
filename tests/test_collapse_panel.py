"""Collapse-Resistance-Panel: deterministic metrics, thresholds, and the read-only contract."""
from collections import Counter
from types import SimpleNamespace

from joni.autonomy import collapse_panel as cp
from joni.autonomy.core_state import CoreState, seed_core


def _claim(cid, status, evidence):
    return SimpleNamespace(id=cid, status=SimpleNamespace(value=status)), evidence


def test_top_bucket_dominance_levels_and_sink_flag():
    assert cp.top_bucket_dominance(Counter({"a": 9, "b": 1}))["level"] == cp.ALARM   # 90%
    assert cp.top_bucket_dominance(Counter({"a": 7, "b": 3}))["level"] == cp.WARN     # 70%
    assert cp.top_bucket_dominance(Counter({"a": 5, "b": 5}))["level"] == cp.OK       # 50%
    forum = cp.top_bucket_dominance(Counter({"forum": 8, "x": 2}))
    assert forum["is_sink"] is True and forum["level"] == cp.ALARM


def test_entropy_netto_excludes_the_sink_bucket():
    # forum dominates raw, but the real topics are evenly spread → netto entropy stays high
    t = Counter({"forum": 800, "a": 50, "b": 50, "c": 50, "d": 50})
    e = cp.topic_entropy(t)
    assert e["entropy_brutto"] < e["entropy_netto"]      # the sink depresses brutto
    assert e["real_topics"] == 4 and e["entropy_netto"] > 0.9   # a/b/c/d perfectly even


def test_weak_claim_ratio_rides_on_strong_claims():
    claims_ev = [
        _claim("c1", "active", 0), _claim("c2", "active", 1), _claim("c3", "active", 5),
        _claim("c4", "confirmed", 0), _claim("c5", "candidate", 0),   # weak candidate: fine
    ]
    claims = [c for c, _ in claims_ev]
    ev = {c.id: e for c, e in claims_ev}
    r = cp.weak_claim_ratio(claims, ev)
    # strong = active+confirmed = 4 claims, weak(≤1 link) = c1,c2,c4 = 3/4
    assert r["strong_claims"] == 4 and r["strong_weak_ratio"] == 0.75 and r["level"] == cp.WARN


def _cf(claim_ids, status="open"):
    return SimpleNamespace(claim_ids=claim_ids, conflict_status=SimpleNamespace(value=status),
                           topic="t")


def test_conflict_depth_detects_tangle_and_cycle():
    # a 3-claim cycle C1-C2-C3-C1 → one component, cyclic
    conflicts = [_cf(["C1", "C2"]), _cf(["C2", "C3"]), _cf(["C3", "C1"])]
    d = cp.conflict_depth(conflicts)
    assert d["open_conflicts"] == 3 and d["components"] == 1
    assert d["max_component"] == 3 and d["cyclic_components"] == 1


def test_conflict_depth_names_the_worst_topic_from_claim_topics():
    # a Conflict has no topic of its own; the worst topic is derived from its claims' topics
    conflicts = [_cf(["C1", "C2"]), _cf(["C3", "C4"])]
    topic_of = {"C1": "routing", "C2": "routing", "C3": "memory", "C4": "routing"}
    d = cp.conflict_depth(conflicts, topic_of)
    assert d["worst_topic"] == "routing"                 # 3 routing vs 1 memory
    # without the map it stays honest (None), never a bogus "?"
    assert cp.conflict_depth(conflicts)["worst_topic"] is None


def test_conflict_depth_excludes_resolved_conflicts():
    # resolved/superseded conflicts are no longer live contradictions -> excluded from count + graph
    conflicts = [_cf(["C1", "C2"]), _cf(["C2", "C3"], status="resolved"),
                 _cf(["C4", "C5"], status="superseded")]
    d = cp.conflict_depth(conflicts)
    assert d["open_conflicts"] == 1                     # only the one open conflict
    assert d["max_component"] == 2                      # resolved edges are absent from the graph


def test_novelty_windows_and_starvation_alarm():
    assert cp.novelty([0] * 7)["level"] == cp.ALARM             # fully dry fast window
    warnish = cp.novelty([2, 0, 0, 1, 0, 0, 0, 0, 1, 0] * 3)    # >50% zero, mean<1
    assert warnish["level"] == cp.WARN
    assert cp.novelty([2, 3, 2, 3] * 8)["level"] == cp.OK       # healthy intake


def test_repetition_flags_selfmodel_remint_and_dup_dev():
    # the historical bug: same trait, only the number changes → repeat after digit-strip
    sms = ["I hold 214 contradictions open", "I hold 215 contradictions open",
           "I hold 219 contradictions open"]
    devs = ["C-1/C-2: duplicate - no link"] * 19 + ["linked C-3 <-> C-4"]
    r = cp.repetition(devs, sms)
    assert r["selfmodel_repeat_ratio"] > 0.5        # 3 texts, 1 distinct after strip
    assert r["duplicate_dev_share"] == 0.95


def test_cold_replay_levels():
    assert cp.cold_replay(None)["level"] == cp.OK
    assert cp.cold_replay(20)["level"] == cp.OK
    assert cp.cold_replay(60)["level"] == cp.WARN
    assert cp.cold_replay(300)["level"] == cp.ALARM


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _paths(tmp):
    return SimpleNamespace(
        collapse_series=tmp / "collapse_series.jsonl",
        collapse_panel=tmp / "collapse_panel.md",
        protocol=tmp / "protocol.jsonl")


def test_run_panel_is_read_only_and_writes_its_artifacts(tmp_path):
    cs = CoreState(seed_core())
    a, b = cs.learn("claim a", "t"), cs.learn("claim b", "t")
    cs.open_conflict([a, b])
    before = len(cs.core.objects)                       # Layer-9 object count snapshot
    rec = cp.run_panel(cs, {"vitality": {"degeneration": 0}}, _Proto(), 42,
                       run=7, paths=_paths(tmp_path), load_seconds=12.3)
    assert rec and rec["cycle"] == 42 and rec["run"] == 7
    assert (tmp_path / "collapse_series.jsonl").exists()
    assert "Collapse-Resistance-Panel" in (tmp_path / "collapse_panel.md").read_text()
    # THE contract: the panel wrote nothing to Layer 9
    assert len(cs.core.objects) == before
