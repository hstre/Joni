"""PR 1 - core schema & authority model: object defaults and metadata."""

import desi_layer9 as l9


def test_every_object_carries_governance_metadata():
    for obj in (l9.Claim(), l9.Method(), l9.Goal(), l9.MemoryEpisode(), l9.Proposal()):
        d = obj.common_dict()
        for key in (
            "id", "object_type", "created_tick", "last_changed_tick", "status",
            "authority", "provenance", "derived_from", "scope", "valid_from",
            "valid_until", "confidence_or_support", "taint", "created_by",
            "reviewed_by", "ledger_event",
        ):
            assert key in d


def test_new_objects_default_to_untrusted_candidate_clean():
    c = l9.Claim(text="x")
    assert c.status is l9.Status.CANDIDATE
    assert c.authority is l9.Authority.UNTRUSTED       # never authoritative by default
    assert c.taint.is_clean
    assert c.provenance.origin_type is l9.OriginType.UNKNOWN


def test_claim_does_not_embed_its_evidence():
    # A Claim has no evidence field; support is separate Evidence/EvidenceLink objects.
    assert not hasattr(l9.Claim(), "evidence")
    link = l9.EvidenceLink(claim_id="C-1", evidence_id="E-1",
                           relation=l9.RelationType.SUPPORTS)
    assert link.object_type is l9.ObjectType.EVIDENCE_LINK


def test_methods_are_versionable_with_explicit_derivation():
    v1 = l9.Method(name="m", version=1)
    v2 = l9.Method(name="m", version=2, parent_methods=("M-1",))
    v1.superseded_by = "M-2"
    assert v2.version == 2 and v2.parent_methods == ("M-1",)
    assert v1.superseded_by == "M-2"


def test_id_minter_is_sequential_and_replay_stable():
    a, b = l9.IdMinter(), l9.IdMinter()
    seq_a = [a.next(l9.ObjectType.CLAIM), a.next(l9.ObjectType.CLAIM), a.next(l9.ObjectType.METHOD)]
    seq_b = [b.next(l9.ObjectType.CLAIM), b.next(l9.ObjectType.CLAIM), b.next(l9.ObjectType.METHOD)]
    assert seq_a == seq_b == ["C-1", "C-2", "M-1"]


def test_operational_state_and_narrative_are_distinct_classes():
    assert l9.OperationalState().object_type is l9.ObjectType.OPERATIONAL_STATE
    assert l9.SelfModelClaim().object_type is l9.ObjectType.SELF_MODEL_CLAIM
    assert l9.NarrativeSummary().object_type is l9.ObjectType.NARRATIVE_SUMMARY
