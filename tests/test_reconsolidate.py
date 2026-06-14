"""Joni occasionally re-reads his memory across a Kevin lens for cross-topic links."""

import desi_layer9 as l9
from joni.autonomy import reconsolidate
from joni.autonomy.core_state import CoreState
from semantic_stub import StubSemanticLayer


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


def _cs_with_a_kevin_lens():
    """Two topics with strongly overlapping claims, and a Kevin lens spanning both."""
    cs = CoreState(l9.Layer9())
    cs.learn("calibration improves routing decisions under load", "routing")
    cs.learn("calibration improves drift detection under load", "drift")
    cs.propose_method(name="calibration-as-a-lens",
                      summary="treat calibration as a transferable lens",
                      applicable_to=("routing", "drift"), origin="joni:emergent")
    return cs


def test_reconsolidate_links_cross_topic_claims_through_a_kevin_lens():
    cs = _cs_with_a_kevin_lens()
    ext: dict = {}
    out = reconsolidate.reconsolidate(cs, ext, _Proto(), cycle=12, layer=StubSemanticLayer())
    assert out["ran"] is True
    assert out["lens"] == "calibration-as-a-lens"
    assert out["links"] >= 1                       # a governed CROSS-topic link was forged
    assert ext["linked"]                           # remembered, so the pair is not redone


def test_reconsolidate_runs_only_on_its_cadence():
    cs = _cs_with_a_kevin_lens()
    out = reconsolidate.reconsolidate(cs, {}, _Proto(), cycle=7, layer=StubSemanticLayer())
    assert out["ran"] is False                     # 7 % 12 != 0 - not this cycle


def test_reconsolidate_is_a_noop_without_a_multi_topic_lens():
    cs = CoreState(l9.Layer9())
    cs.learn("calibration improves routing decisions under load", "routing")
    cs.learn("calibration improves drift detection under load", "drift")
    out = reconsolidate.reconsolidate(cs, {}, _Proto(), cycle=12, layer=StubSemanticLayer())
    assert out["ran"] is False                     # no Kevin lens to borrow yet
