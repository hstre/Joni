"""The one-time reconsolidation audit: classification verdicts, bounded grouping, and the
read-only contract (classify never writes; apply only touches junk)."""
from types import SimpleNamespace

from joni.autonomy import reconsolidation_audit as ra

# --- pure grouping / rendering ------------------------------------------------------------------

def test_group_counts_and_bounds_samples():
    items = ([{"id": f"j{i}", "label": f"junk{i}", "verdict": ra.JUNK, "reason": "r"}
              for i in range(20)]
             + [{"id": "b1", "label": "border", "verdict": ra.BORDERLINE, "reason": "r"}]
             + [{"id": "k1", "label": "keep", "verdict": ra.KEEP, "reason": "r"}])
    g = ra._group(items, sample=5)
    assert g[ra.JUNK]["count"] == 20 and len(g[ra.JUNK]["samples"]) == 5   # bounded
    assert g[ra.BORDERLINE]["count"] == 1 and g[ra.KEEP]["count"] == 1


def test_render_lists_junk_and_borderline_but_summarises_keep():
    report = {"topics": ra._group([], sample=5),
              "hypotheses": ra._group(
                  [{"id": "h", "label": "cotton recurs", "verdict": ra.JUNK,
                    "reason": "0 support"}],
                  sample=5),
              "methods": ra._group([], sample=5),
              "totals": {"topics": 0, "hypotheses": 1, "methods": 0}}
    md = ra.render_markdown(report)
    assert "Reconsolidation Audit" in md and "cotton recurs" in md and "0 support" in md


# --- classification verdicts (real quality gates) -----------------------------------------------

def test_classify_topic_verdicts():
    assert ra.classify_topic("forum")[0] == ra.JUNK              # sink / provenance bucket
    assert ra.classify_topic("secure-openclaw")[0] == ra.JUNK    # a repo slug, not a subject
    assert ra.classify_topic("routing")[0] == ra.KEEP            # a genuine topic


def test_classify_hypothesis_verdicts():
    # a stopword-subject hypothesis is non-admissible on LEXICAL grounds - embedder-independent
    # (an off-domain-but-substantive subject like 'cotton' only reads as junk when the embedder is
    # live; without it on_domain fails open, exactly like every other domain gate in the system).
    junk = "Across my routing claims, 'about' recurs as a through-line."
    assert ra.classify_hypothesis(junk, support=0)[0] == ra.JUNK
    # the same non-admissible text WITH support is borderline, never auto-junk
    assert ra.classify_hypothesis(junk, support=2)[0] == ra.BORDERLINE
    ok = "retrieval calibration reduces drift under load"
    assert ra.classify_hypothesis(ok, support=0)[0] == ra.KEEP


def test_classify_method_verdicts():
    assert ra.classify_method("existing-as-a-lens", trial_count=0)[0] == ra.JUNK   # junk term
    assert ra.classify_method("calibration-as-a-lens", trial_count=0)[0] == ra.BORDERLINE
    assert ra.classify_method("existing-as-a-lens", trial_count=3)[0] == ra.KEEP   # trialed -> keep
    assert ra.classify_method("Some Harvested Paper Title", trial_count=0)[0] == ra.BORDERLINE


# --- end-to-end audit over a small real core ----------------------------------------------------

def test_audit_over_a_small_core_is_read_only_and_grouped():
    from joni.autonomy.core_state import CoreState, seed_core
    cs = CoreState(seed_core())
    cs.learn("calibration improves routing decisions", "routing")
    before = cs.core.count()
    report = ra.audit(cs)
    assert set(report) == {"topics", "hypotheses", "methods", "totals"}
    assert all(v in report["topics"] for v in (ra.JUNK, ra.BORDERLINE, ra.KEEP))
    assert cs.core.count() == before          # the audit wrote nothing


def test_group_handles_a_fake_stream():
    # verdicts flow straight through regardless of source object shape
    items = [{"id": o.id, "label": o.id, "verdict": ra.KEEP, "reason": "ok"}
             for o in [SimpleNamespace(id="a"), SimpleNamespace(id="b")]]
    g = ra._group(items, sample=15)
    assert g[ra.KEEP]["count"] == 2
