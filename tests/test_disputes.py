"""Priority 5: hundreds of pairwise conflicts condense into a few thematic Streitfragen. Read-only;
each dispute reports positions, shared premises and the decisive missing evidence. Nothing is
resolved and Layer 9 is never written."""
from __future__ import annotations

from types import SimpleNamespace

import desi_layer9 as l9
from joni.autonomy import disputes


def _conflict(cid, claim_ids, status="open"):
    return SimpleNamespace(id=cid, claim_ids=tuple(claim_ids),
                           conflict_status=SimpleNamespace(value=status))


def _claim(cid, text, topic="routing"):
    return SimpleNamespace(id=cid, text=text, topic=topic)


class _Core:
    def __init__(self, conflicts, claims):
        self._c = conflicts
        self._m = {c.id: c for c in claims}

    def all(self, t):
        if t == l9.ObjectType.CONFLICT:
            return self._c
        if t == l9.ObjectType.CLAIM:
            return list(self._m.values())
        return []                                   # no EVIDENCE / EVIDENCE_LINK -> no families

    def get(self, cid):
        return self._m.get(cid)


class _CS:
    def __init__(self, conflicts, claims):
        self.core = _Core(conflicts, claims)


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_two_tangles():
    claims = [
        _claim("C-1", "routing reduces latency under heavy load"),
        _claim("C-2", "routing increases latency under heavy load"),
        _claim("C-3", "routing has no effect on latency under load"),
        _claim("C-9", "attention improves recall", topic="attention"),
        _claim("C-10", "attention harms recall", topic="attention"),
    ]
    conflicts = [
        _conflict("X-1", ["C-1", "C-2"]),           # one tangle: C-1/C-2/C-3 (three pairwise)
        _conflict("X-2", ["C-2", "C-3"]),
        _conflict("X-3", ["C-1", "C-3"]),
        _conflict("X-9", ["C-9", "C-10"]),          # a separate, smaller tangle
    ]
    return _CS(conflicts, claims)


def test_condense_groups_pairwise_conflicts_into_thematic_disputes():
    disp = disputes.condense(_cs_two_tangles())
    assert len(disp) == 2                            # four pairwise conflicts -> two Streitfragen
    big = disp[0]                                    # sorted biggest tangle first
    assert big.size == 3 and set(big.claim_ids) == {"C-1", "C-2", "C-3"}
    assert big.topic == "routing"
    assert len(big.positions) == 3                   # the three sides


def test_a_dispute_reports_premises_and_the_decisive_gap():
    big = disputes.condense(_cs_two_tangles())[0]
    # the positions share content words -> common ground
    assert "latency" in big.shared_premises and "routing" in big.shared_premises
    # no evidence links in this core -> every position rests on no independent external source
    assert "keiner unabhängigen externen Quelle" in big.missing_evidence


def test_only_live_conflicts_are_condensed():
    claims = [_claim("C-1", "a"), _claim("C-2", "b")]
    cs = _CS([_conflict("X-1", ["C-1", "C-2"], status="resolved")], claims)
    assert disputes.condense(cs) == []              # a resolved conflict is not a live dispute


def test_run_disputes_writes_the_sheet_and_exposes_disputes(tmp_path):
    p = SimpleNamespace(disputes_sheet=tmp_path / "streitfragen.md",
                        disputes_series=tmp_path / "disputes_series.jsonl")
    ext: dict = {}
    out = disputes.run_disputes(_cs_two_tangles(), ext, _Proto(), cycle=7, paths=p)
    assert out == {"conflicts": 4, "disputes": 2}
    assert p.disputes_sheet.exists() and "Streitfragen" in p.disputes_sheet.read_text()
    assert len(ext["disputes"]) == 2 and ext["disputes"][0]["size"] == 3   # staged for the layer


def test_run_disputes_is_fail_open():
    out = disputes.run_disputes(SimpleNamespace(core=None), {}, _Proto(), cycle=1, paths=None)
    assert out == {"conflicts": 0, "disputes": 0}
