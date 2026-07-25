"""Operator measure 2: a read-only classification of every candidate method into the five buckets
(testbereit / kein_benchmark / nicht_ausfuehrbar / scope_unklar / duplikat), so it is visible
whether the trial pipeline is starved for benchmarks or for real procedures."""
from __future__ import annotations

from types import SimpleNamespace

import desi_layer9 as l9
from joni.method_trial import method_breakdown as mb


def test_classify_assigns_each_method_to_the_right_bucket():
    seen: set = set()
    # matches the unit-equality benchmark keywords + short name -> testbereit
    assert mb.classify("unit-lens", "normalise the unit before comparing", seen) == "testbereit"
    # a short procedure/lens with a cue word but no benchmark keyword -> kein_benchmark
    assert mb.classify("cluster-lens", "cluster embeddings by density", seen) == "kein_benchmark"
    # a long harvested paper title -> not a procedure at all
    long_title = "TimeProVe: Propose then Verify for Efficient Long Video Temporal Reasoning"
    assert mb.classify(long_title, "a paper on video reasoning", seen) == "nicht_ausfuehrbar"
    # short-named but no procedural cue -> scope unclear
    assert mb.classify("wisdom", "a general notion of insight", seen) == "scope_unklar"
    # a repeat of an earlier normalised name+summary -> duplicate
    assert mb.classify("unit-lens", "normalise the unit before comparing", seen) == "duplikat"


def _method(mid, name, summary, status="candidate"):
    return SimpleNamespace(id=mid, name=name, summary=summary,
                           status=SimpleNamespace(value=status))


class _CS:
    def __init__(self, methods):
        self.core = SimpleNamespace(all=lambda t: methods if t == l9.ObjectType.METHOD else [])


def test_compute_counts_all_candidate_methods():
    cs = _CS([
        _method("M-1", "unit-lens", "normalise the unit before comparing"),   # testbereit
        _method("M-2", "cluster-lens", "cluster items by similarity"),        # kein_benchmark
        _method("M-3", "A Very Long Harvested Paper Title About Attention", "..."),  # nicht_ausf.
        _method("M-4", "aura", "an ineffable quality"),                       # scope_unklar
        _method("M-9", "retired", "x", status="rejected"),                    # not a candidate
    ])
    rec = mb.compute(cs)
    assert rec["total"] == 4                                # the rejected one is excluded
    c = rec["counts"]
    assert c["testbereit"] == 1 and c["kein_benchmark"] == 1
    assert c["nicht_ausfuehrbar"] == 1 and c["scope_unklar"] == 1
    assert rec["examples"]["testbereit"] == ["unit-lens"]


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def test_run_breakdown_writes_the_sheet_and_exposes_counts(tmp_path):
    p = SimpleNamespace(method_breakdown_sheet=tmp_path / "method_breakdown.md",
                        method_breakdown_series=tmp_path / "method_breakdown.jsonl")
    cs = _CS([_method("M-1", "unit-lens", "normalise the unit before comparing")])
    ext: dict = {}
    rec = mb.run_breakdown(cs, ext, _Proto(), cycle=3, paths=p)
    assert rec["counts"]["testbereit"] == 1
    assert ext["method_breakdown"]["testbereit"] == 1
    assert p.method_breakdown_sheet.exists()
    assert "Methoden-Breakdown" in p.method_breakdown_sheet.read_text()
    assert p.method_breakdown_series.exists()


def test_run_breakdown_is_fail_open():
    out = mb.run_breakdown(SimpleNamespace(core=None), {}, _Proto(), cycle=1, paths=None)
    assert out["total"] == 0
