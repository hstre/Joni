"""Doktores hands research back as a package - and Joni keeps governance.

The contract: a research_output package enters Layer 9 only through the epistemic channel as a
SOURCE (candidate authority, never confirmed), its publication is archived with no epistemic
weight, a rejected package never becomes belief, and a malformed package never crashes a cycle.
"""

import json

from joni.autonomy import research_intake
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


class _Paths:
    def __init__(self, d):
        self.research_inbox = d / "research_inbox.json"
        self.research_dir = d / "docs" / "research"


def _pkg(**over):
    base = {
        "id": "RO-1",
        "source_hypothesis_ids": ["C-1"],
        "theory": "context contamination drives variance",
        "predictions": ["same-model variance exceeds cross-model variance"],
        "reviewer_verdict": "accept",
        "confidence": 0.55,
        "recommended_claim_updates": [
            {"op": "add_claim", "text": "session variance dominates model variance",
             "topic": "variance"}],
        "publication": {"kind": "report", "title": "Variance Report",
                        "markdown": "## Results\nSession variance dominates."},
    }
    base.update(over)
    return base


def _seed(d, packages):
    p = _Paths(d)
    p.research_inbox.write_text(json.dumps(packages))
    return p


def test_a_package_enters_as_a_source_not_an_authority(tmp_path):
    cs = CoreState(seed_core())
    paths = _seed(tmp_path, [_pkg()])
    out = research_intake.ingest(cs, {}, _Proto(), 1, paths=paths)
    assert out["ingested"] == 1 and out["candidates"] == 1

    # the recommended update is now an active claim - but a SOURCE, never confirmed
    claim = next(c for c in cs.active_claims()
                 if "session variance dominates" in c.text.lower())
    assert claim.status.value == "active"
    assert claim.authority.value == "candidate"            # earns standing, not granted
    assert claim.provenance.origin_type.value == "source"  # NOT the privileged 'human'
    assert "origin:internal-research" in claim.provenance.source_ids


def test_publication_is_archived_with_provenance(tmp_path):
    cs = CoreState(seed_core())
    paths = _seed(tmp_path, [_pkg()])
    out = research_intake.ingest(cs, {}, _Proto(), 1, paths=paths)
    assert out["published"] == 1
    md = (paths.research_dir / "RO-1.md").read_text()
    assert "not externally replicated" in md          # provenance is explicit
    assert "SOURCE, not a confirmed belief" in md
    assert "Session variance dominates" in md          # the actual content


def test_a_rejected_package_never_becomes_belief_but_is_archived(tmp_path):
    cs = CoreState(seed_core())
    before = len(cs.active_claims())
    paths = _seed(tmp_path, [_pkg(id="RO-rej", reviewer_verdict="reject")])
    out = research_intake.ingest(cs, {}, _Proto(), 1, paths=paths)
    assert out["candidates"] == 0                       # epistemic channel skipped on reject
    assert len(cs.active_claims()) == before
    assert out["published"] == 1                        # still archived for the audit trail


def test_ingestion_is_deduped_by_package_id(tmp_path):
    cs = CoreState(seed_core())
    paths = _seed(tmp_path, [_pkg()])
    ext = {}
    first = research_intake.ingest(cs, ext, _Proto(), 1, paths=paths)
    second = research_intake.ingest(cs, ext, _Proto(), 2, paths=paths)
    assert first["candidates"] == 1 and second["candidates"] == 0   # not re-ingested


def test_a_malformed_package_does_not_crash_the_cycle(tmp_path):
    cs = CoreState(seed_core())
    paths = _seed(tmp_path, ["not a dict", {"id": "RO-ok", "reviewer_verdict": "accept",
                                            "recommended_claim_updates": [
                                                {"op": "add_claim", "text": "ok claim",
                                                 "topic": "t"}]}])
    out = research_intake.ingest(cs, {}, _Proto(), 1, paths=paths)
    assert out["ingested"] == 1 and out["candidates"] == 1   # the good one still lands


def test_empty_inbox_is_a_noop(tmp_path):
    cs = CoreState(seed_core())
    paths = _Paths(tmp_path)                            # no inbox file at all
    out = research_intake.ingest(cs, {}, _Proto(), 1, paths=paths)
    assert out == {"ingested": 0, "candidates": 0, "conflicts": 0, "published": 0}
