"""The local-embedding projector inside the DESi binding: cosine distance as an additional
channel, combined fail-closed by Layer 9. Uses an injected deterministic embedder so the
behaviour (and the required cases) are tested without the heavy model in this environment.
The real model is exercised in test_desi_semantic_integration.py.
"""

import desi_layer9 as l9
from desi_layer9 import SemanticDecision, SemanticState
from desi_layer9.semantics import decision
from desi_layer9.semantics.ports import SemanticMeasurement
from joni.autonomy import desi_semantics, embeddings

# Concept buckets -> a fixed vector. Paraphrases map to the same bucket (close) even with
# different words; different meanings map apart. Negation is invisible to it (as for a real
# embedding) - Layer 9's polarity channel must catch contradictions.
_BUCKETS = {
    "routing-latency": ("routing", "latency", "throughput", "speed", "fast", "delay", "quick"),
    "memory-context": ("memory", "context", "persistent", "retained", "recall", "session"),
    "ethics": ("moral", "duty", "ought", "ethical", "fair", "justice"),
}


def _fake_embed(text: str):
    t = text.lower()
    return [float(sum(w in t for w in words)) + 0.01 for words in _BUCKETS.values()]


def setup_function(_):
    embeddings._reset_for_tests(_fake_embed, name="fake-embed", revision="r1", dim=3,
                                normalized=False)


def teardown_function(_):
    embeddings._reset_for_tests(None)


def _measure(a, b):
    dm = desi_semantics._measure_distance(a, b)
    return SemanticMeasurement(
        pi_distance=dm["pi_distance"], cosine_distance=dm["cosine_distance"],
        distance_metric=dm["distance_metric"], embedding_model=dm["embedding_model"],
        embedding_revision=dm["embedding_revision"], embedding_dim=dm["embedding_dim"],
        embedding_normalized=dm["embedding_normalized"], duplicate=dm["duplicate"],
        polarity_clash=desi_semantics._polarity_clash(a, b),
        components=dm["components"], components_unavailable=dm["components_unavailable"])


def _decide(a, b):
    m = _measure(a, b)
    return decision.classify(m)[0], m


def test_distance_is_labelled_cosine_with_model_identity_not_jsd():
    _, m = _decide("routing keeps latency low", "fast throughput")
    assert m.distance_metric == "cosine"
    assert m.cosine_distance is not None
    assert m.pi_distance is None                       # never reported as √JSD
    assert m.embedding_model == "fake-embed" and m.embedding_revision == "r1"
    assert m.embedding_dim == 3
    assert any(c.startswith("local_embedding:") for c in m.components)


def test_paraphrase_low_lexical_overlap_gets_a_usable_comparison():
    d, m = _decide("routing keeps latency low", "fast throughput with little delay")
    assert m.cosine_distance is not None
    assert d is not SemanticDecision.INSUFFICIENT


def test_same_words_different_meaning_is_not_merged():
    d, _ = _decide("routing reduces latency", "routing is a moral duty we ought to honour")
    assert d in (SemanticDecision.UNRELATED, SemanticDecision.SUPPORTS,
                 SemanticDecision.INSUFFICIENT)
    assert d is not SemanticDecision.DUPLICATE


def test_semantically_similar_but_contradictory_is_not_merged():
    # same topic/words, opposite polarity -> the polarity channel must catch it
    (d, s, _) = decision.classify(_measure("routing increases latency",
                                           "routing does not increase latency"))
    assert d is SemanticDecision.CONTRADICTORY and s is SemanticState.SYNTHESIS_REJECTED


def test_identical_claims_are_duplicates():
    d, m = _decide("routing reduces latency", "routing reduces latency")
    assert m.cosine_distance == 0.0
    assert d is SemanticDecision.DUPLICATE


def test_model_change_invalidates_the_cache():
    embeddings.embed("routing reduces latency")
    assert embeddings.cache_size() >= 1
    # a new model revision -> different cache key space -> recomputed, old entry not reused
    embeddings._reset_for_tests(_fake_embed, name="fake-embed", revision="r2", dim=3)
    assert embeddings.cache_size() == 0
    embeddings.embed("routing reduces latency")
    assert embeddings.cache_size() == 1


def test_failed_model_download_fails_closed():
    embeddings._reset_for_tests(None)                  # simulate no/failed model
    assert embeddings.available() is False
    d, m = _decide("routing reduces latency", "fast throughput")
    assert m.cosine_distance is None
    assert "embedding_projector" in m.components_unavailable
    assert d is SemanticDecision.INSUFFICIENT          # fail closed, never a guess


def test_deterministic_replay_of_an_embedding_decision(tmp_path):
    from desi_layer9 import persistence
    from desi_layer9.semantics import adapter
    from semantic_stub import StubSemanticLayer
    core = l9.Layer9()
    from desi_layer9 import Operator, ProposalType, make_proposal
    from desi_layer9.provenance import Provenance

    def mk(t, s):
        core.submit(make_proposal(ProposalType.CLAIM_PROPOSAL, Operator.CLAIM_CREATE,
                    payload={"text": t, "topic": "t"}, proposer="source",
                    provenance=Provenance.from_source(s)), actor="joni")
        return core.all(l9.ObjectType.CLAIM)[-1]

    a, b = mk("routing reduces latency", "A"), mk("routing lowers delay", "B")
    adapter.analyse_pair(core, a, b, layer=StubSemanticLayer(cosine_distance=0.2))
    before = [(c.id, c.decision.value, c.measurement.get("distance_metric"))
              for c in core.all(l9.ObjectType.SEMANTIC_CLUSTER)]
    p = tmp_path / "l9.json"
    persistence.save(core, p)
    core2 = persistence.load(p)                        # strict load re-verifies the hash
    after = [(c.id, c.decision.value, c.measurement.get("distance_metric"))
             for c in core2.all(l9.ObjectType.SEMANTIC_CLUSTER)]
    assert before == after and before
