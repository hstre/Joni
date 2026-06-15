"""Joni stores methods he finds as candidates in Layer 9 - for Kevin, never promoted."""

import desi_layer9 as l9
from joni.autonomy import methods
from joni.autonomy.core_state import CoreState
from joni.autonomy.improve import judge
from joni.autonomy.sources import Item


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _judged(cs, items):
    return [(it, judge(cs, it)) for it in items]


def test_github_repo_is_stored_as_a_candidate_method():
    cs = CoreState(l9.Layer9())
    cs.learn("cheap local routing works", "routing")          # gives a 'routing' topic
    item = Item("github", "remix-run/react-router", "react-router",
                "https://github.com/remix-run/react-router", "declarative routing", 50000.0)
    out = methods.harvest(cs, _judged(cs, [item]), {}, _Proto())
    assert out["methods"] == 1
    m = cs.core.all(l9.ObjectType.METHOD)[0]
    assert m.status is l9.Status.CANDIDATE                    # never active/authoritative
    assert m.authority is not l9.Authority.AUTHORITATIVE
    assert m.name == "react-router" and m.origin.startswith("https://github.com")


def test_paper_with_method_language_is_stored():
    cs = CoreState(l9.Layer9())
    cs.learn("routing matters", "routing")
    item = Item("arxiv", "1", "A new framework for cheap routing",
                "http://x", "we propose a method and algorithm for routing", 0.0)
    out = methods.harvest(cs, _judged(cs, [item]), {}, _Proto())
    assert out["methods"] == 1


def test_non_method_finding_is_not_stored():
    cs = CoreState(l9.Layer9())
    cs.learn("routing matters", "routing")
    item = Item("arxiv", "2", "Observations about user onboarding", "http://x",
                "a survey of how people feel", 0.0)
    out = methods.harvest(cs, _judged(cs, [item]), {}, _Proto())
    assert out["methods"] == 0


def test_methods_are_deduped_by_source():
    cs = CoreState(l9.Layer9())
    cs.learn("routing matters", "routing")
    item = Item("github", "a/b", "b", "https://github.com/a/b", "a tool", 1.0)
    ext = {}
    methods.harvest(cs, _judged(cs, [item]), ext, _Proto())
    before = len(cs.core.all(l9.ObjectType.METHOD))
    methods.harvest(cs, _judged(cs, [item]), ext, _Proto())   # same source -> no new method
    assert len(cs.core.all(l9.ObjectType.METHOD)) == before


def test_kevin_could_use_them_only_after_promotion():
    import pytest
    pytest.importorskip("kevin")          # Kevin isn't installed in Joni's own CI
    cs = CoreState(l9.Layer9())
    item = Item("github", "a/b", "b", "https://github.com/a/b", "a tool", 1.0)
    methods.harvest(cs, [(item, judge(cs, item))], {}, _Proto())
    # candidates are not yet usable - a human/Kevin must promote them
    from kevin.layer9_link import usable_methods
    assert usable_methods(cs.core) == []


def _fake_domain(monkeypatch):
    """Inject an embedder: AI/agent text is on-domain, generic C++/dev tooling is off-domain."""
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: True)
    off = ("c++", "coding-style", "coding style", "guidelines", "frontend", "ui frameworks",
           "devops", "deployment", "infrastructure", "cotton", "medicine", "cooking")

    def cd(probe, anchor):
        p_off = any(k in probe.lower() for k in off)
        a_off = any(k in anchor.lower() for k in off)
        return 0.15 if (p_off == a_off) else 0.9
    monkeypatch.setattr(embeddings, "cosine_distance", cd)


def test_off_domain_github_repo_is_not_harvested(monkeypatch):
    _fake_domain(monkeypatch)
    cs = CoreState(l9.Layer9())
    cs.learn("cheap local routing works", "routing")
    item = Item("github", "isocpp/CppCoreGuidelines", "CppCoreGuidelines",
                "https://github.com/isocpp/CppCoreGuidelines",
                "The C++ Core Guidelines are a set of coding-style guidelines.", 40000.0)
    out = methods.harvest(cs, _judged(cs, [item]), {}, _Proto())
    assert out["methods"] == 0                       # off-domain dev tooling -> not shelved


def test_on_domain_method_is_still_harvested(monkeypatch):
    _fake_domain(monkeypatch)
    cs = CoreState(l9.Layer9())
    cs.learn("routing matters", "routing")
    item = Item("arxiv", "9", "A framework for model routing in LLM agents",
                "http://x", "a method for routing and inference in agent systems", 0.0)
    out = methods.harvest(cs, _judged(cs, [item]), {}, _Proto())
    assert out["methods"] == 1
