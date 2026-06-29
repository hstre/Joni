"""The v2-graph slice scanner: produces the missing-opposition / provenance / scope inputs."""
from __future__ import annotations

from joni.layer9_v2.checks import slice_scan
from joni.layer9_v2.graph import links
from joni.layer9_v2.spaces import contents
from joni.layer9_v2.storage import sqlite as S


def _claim(conn, cid, *, topic="t", sources=(), derived=False, scope=()):
    return contents.put_content(
        conn, type="claim", title=cid, object_id=cid,
        payload={"text": cid, "topic": topic, "derived_from": list(["x"] if derived else []),
                 "scope": list(scope), "provenance": {"source_ids": list(sources),
                                                       "origin_type": "source"}})


def test_source_family_prefers_explicit_source():
    assert slice_scan.source_family({"source_ids": ["paper-1"]}) == "src:paper-1"
    assert slice_scan.source_family({"origin_type": "source", "run_id": "r9"}) == "origin:source:r9"


def test_omitted_opposition_only_when_outside_slice(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    with conn:
        a = _claim(conn, "A", sources=["s1"])
        b = _claim(conn, "B", sources=["s2"])      # contradicts A, NOT in the slice -> omitted
        c = _claim(conn, "C", sources=["s3"])      # contradicts A, IN the slice -> surfaced
        links.add_link(conn, b["id"], "contradicts", a["id"])
        links.add_link(conn, c["id"], "contradicts", a["id"])
    scan = slice_scan.scan_slice(conn, ["A", "C"])   # slice contains A and C, not B
    assert scan["graph_opposition_ids"] == ("B",)    # only the omitted one
    assert "contradicts" in scan["graph_opposition_texts"][0]


def test_provenance_and_scope_inputs(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    with conn:
        _claim(conn, "A", sources=["s1"], derived=False, scope=["proj-A"])
        _claim(conn, "B", sources=["s1"], derived=True, scope=[])   # same source family as A
    scan = slice_scan.scan_slice(conn, ["A", "B"])
    assert scan["provenance_sources"] == ("src:s1", "src:s1")        # one independent family
    assert scan["derived_flags"] == (False, True)
    assert scan["claim_scopes"] == ("proj-A", "")


def test_empty_slice_yields_empty_signals(tmp_path):
    conn = S.open_db(tmp_path / "t.sqlite")
    scan = slice_scan.scan_slice(conn, [])
    assert scan["graph_opposition_ids"] == () and scan["provenance_sources"] == ()
