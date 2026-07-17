"""Collapse-Resistance-Panel: deterministic metrics, thresholds, and the read-only contract."""
from collections import Counter
from types import SimpleNamespace

from joni.autonomy import collapse_panel as cp
from joni.autonomy.core_state import CoreState, seed_core


def _claim(cid, status, authority="candidate"):
    return SimpleNamespace(id=cid, status=SimpleNamespace(value=status),
                           authority=SimpleNamespace(value=authority))


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


def test_weak_claim_ratio_rides_on_hollow_presented_strong():
    # 'active' is a WORKING state, not strong (operator's point 1): only confirmed OR
    # authority>=reviewed claims are 'presented strong'. The alarm rides on the HOLLOW share of
    # those - no independent external source family (points 1 + 6) - so a pile of active working
    # claims can never trip it, and synthetic self-support never reads as grounded.
    claims = [
        _claim("c1", "active"), _claim("c2", "active"),          # working state - NOT strong
        _claim("c3", "confirmed"),                                # presented strong, hollow
        _claim("c4", "active", authority="reviewed"),             # presented strong, grounded
        _claim("c5", "candidate"),                                # weak candidate: fine
    ]
    support = {
        "c3": {"links": 1, "families": 0, "reviewed": 0},         # hollow: no external family
        "c4": {"links": 3, "families": 2, "reviewed": 1},         # 2 independent external families
    }
    r = cp.weak_claim_ratio(claims, support)
    assert r["presented_strong"] == 2                             # c3 + c4, not the active c1/c2
    assert r["hollow_count"] == 1 and r["strong_weak_ratio"] == 0.5
    assert r["reviewed_backed"] == 1
    assert r["level"] == cp.OK                          # 50% hollow < warn -> no false alarm


def test_weak_claim_alarm_only_from_hollow_strong_not_active_mass():
    # 100 active working claims with no support: must NOT alarm (they are not 'strong')
    claims = [_claim(f"a{i}", "active") for i in range(100)]
    claims += [_claim("s1", "confirmed"), _claim("s2", "confirmed")]   # 2 hollow presented-strong
    r = cp.weak_claim_ratio(claims, {})
    assert r["presented_strong"] == 2 and r["strong_weak_ratio"] == 1.0
    assert r["level"] == cp.ALARM                                 # the 2 hollow strong, not the 100


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


def test_conflict_depth_reconciles_the_two_counts():
    # 'live' = open + under_review (matches core.open_conflicts). TOLERATED is held on purpose and
    # is NOT live - the panel used to count it as open, which is why its number sat above the
    # dashboard's. Now all statuses are reported so the two numbers reconcile (point 8).
    conflicts = [_cf(["C1", "C2"]), _cf(["C3", "C4"], status="under_review"),
                 _cf(["C5", "C6"], status="tolerated"), _cf(["C7", "C8"], status="resolved")]
    d = cp.conflict_depth(conflicts)
    assert d["open_conflicts"] == 2                     # open + under_review only
    assert d["tolerated"] == 1 and d["closed"] == 1
    assert d["total_conflicts"] == 4
    assert d["by_status"] == {"open": 1, "under_review": 1, "tolerated": 1, "resolved": 1}


def test_novelty_windows_and_starvation_alarm():
    assert cp.novelty([0] * 7)["level"] == cp.ALARM             # fully dry fast window
    warnish = cp.novelty([2, 0, 0, 1, 0, 0, 0, 0, 1, 0] * 3)    # >50% zero, mean<1
    assert warnish["level"] == cp.WARN
    assert cp.novelty([2, 3, 2, 3] * 8)["level"] == cp.OK       # healthy intake


def test_repetition_selfmodel_uses_objects_and_keeps_digits():
    # the OLD artefact: same trait, only the count changes. Measured on real self-model OBJECTS
    # with digits KEPT, these are DISTINCT self-claims (new info), not a false digit-strip repeat.
    counting = [SimpleNamespace(text=f"I hold {n} contradictions open") for n in (214, 215, 219)]
    devs = ["C-1/C-2: duplicate - no link"] * 19 + ["linked C-3 <-> C-4"]
    r = cp.repetition(devs, counting)
    assert r["selfmodel_repeat_ratio"] == 0.0        # 3 distinct self-claims, no false repeat
    assert r["selfmodel_count"] == 3
    assert r["duplicate_dev_share"] == 0.95


def test_repetition_still_catches_a_genuine_remint():
    # a truly identical trait text repeated IS a real re-mint (the reference bug)
    dupe = [SimpleNamespace(text="my drift metric ignores seasonality")] * 4
    r = cp.repetition([], dupe)
    assert r["selfmodel_repeat_ratio"] == 0.75       # 4 texts, 1 distinct


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


def test_guard_liveness_names_the_dark_guards(monkeypatch):
    # the finding that motivated the metric: on_domain is fail-open without an embedder, so three
    # passes silently wave everything through - the panel must SAY so, not let silence read as ok.
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: False)
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    g = cp.guard_liveness()
    assert g["level"] == "alarm"                      # only lexical filters left
    assert "embedding_domain_gate" in g["dark"] and "granite_topic_gate" in g["dark"]
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    g2 = cp.guard_liveness()
    assert g2["level"] == "warn"                      # Granite judges, embeddings still dark
    monkeypatch.setattr(embeddings, "available", lambda: True)
    assert cp.guard_liveness()["level"] == "ok"


def test_the_summary_renders_the_guard_row(monkeypatch):
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: False)
    monkeypatch.delenv("JONI_SEMANTIC_PROPOSALS", raising=False)
    rec = {"cycle": 1, "run": 1, "active_claims": 0, "overall": "alarm", "metrics": {
        "top_bucket_dominance": {"top_bucket": "-", "share": 0, "is_sink": False, "level": "ok"},
        "topic_entropy": {"entropy_brutto": 0, "entropy_netto": 0, "real_topics": 0, "level": "ok"},
        "weak_claim_ratio": {"strong_weak_ratio": 0, "strong_claims": 0, "reviewed_backed": 0,
                             "level": "ok"},
        "degeneracy": {"degeneration_score": 0, "decidable_percent": 0,
                       "unsupported_hypotheses": 0, "level": "ok"},
        "conflict_depth": {"open_conflicts": 0, "tolerated": 0, "closed": 0, "max_component": 0,
                           "cyclic_components": 0, "level": "ok"},
        "novelty": {"new_mean_7": 0, "new_mean_30": 0, "zero_new_share_30": 0, "level": "ok"},
        "repetition": {"duplicate_dev_share": 0, "selfmodel_repeat_ratio": 0, "selfmodel_count": 0,
                       "level": "ok"},
        "cold_replay": {"load_seconds": 0, "level": "ok"},
        "guard_liveness": cp.guard_liveness(),
    }}
    md = cp.render_summary(rec)
    assert "Guard-Liveness" in md and "dunkel:" in md and "embedding_domain_gate" in md
