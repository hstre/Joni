"""Joni's self-diagnostic: from measured state he finds what is not working, turns each into a
search query (-> topic search) and steers Doktores at the top weakness. Proposes only."""

from joni.autonomy import introspect
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_diagnoses_stalled_development_and_weak_semantics():
    cs = CoreState(seed_core())
    ext = {"vitality": {"development": 0, "stagnation_cycles": 3, "usable_semantic_rate": 0.1}}
    findings = introspect.diagnose(cs, ext)
    modules = {f["module"] for f in findings}
    assert "emergence" in modules and "semantics-measurement" in modules
    assert all(f.get("query") and f.get("improve") for f in findings)


def test_apply_feeds_topic_search_and_steers_doktores():
    cs = CoreState(seed_core())
    ext = {"vitality": {"development": 0, "stagnation_cycles": 3, "usable_semantic_rate": 0.1}}
    out = introspect.apply(cs, ext, _Proto(), 1)
    assert out["findings"] >= 1
    # the diagnostic's queries flow into the topic search
    assert any("hypothesis development" in q for q in ext["learned_queries"])
    # the top weakness steers Doktores' next scout
    assert ext["introspection_module"] == ext["introspection"][0]["module"]


def test_no_findings_when_healthy_clears_the_steer():
    cs = CoreState(seed_core())
    ext = {"vitality": {"development": 5, "stagnation_cycles": 0, "usable_semantic_rate": 0.9},
           "introspection_module": "emergence"}
    out = introspect.apply(cs, ext, _Proto(), 1)
    assert out["findings"] == 0
    assert "introspection_module" not in ext            # steer cleared when nothing is wrong
