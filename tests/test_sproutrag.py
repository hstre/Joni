"""SproutRAG candidate extraction (Auftrag #160): a long source yields multi-granular, coherent
passages via the embedding tree - so a coherent multi-sentence unit is RECALLED as one candidate
instead of being fragmented across single sentences. Embeddings-only, deterministic, opt-in.

The acceptance metric (+3pp Recall@5 on a labelled long-document benchmark) needs a benchmark Joni
does not have; these tests pin the MECHANISM and a recall-proxy on a planted coherent passage.
"""

import pytest

from joni.autonomy import embeddings, sprout


def _themed(text: str) -> list[float]:
    """A deterministic stand-in projector: sentences on the same theme get the same vector, so a
    run of same-theme sentences is highly self-similar and trees into one coherent span."""
    t = text.lower()
    return [
        float("quantum" in t or "qubit" in t or "error correction" in t),
        float("garden" in t or "soil" in t or "compost" in t),
        float("market" in t or "stock" in t or "finance" in t),
        0.1,  # tiny base term so no sentence is the zero vector
    ]


@pytest.fixture()
def themed_embedder(monkeypatch):
    monkeypatch.setenv("JONI_SPROUTRAG", "1")
    embeddings._reset_for_tests(_themed, name="themed", revision="t", dim=4)
    yield
    embeddings._reset_for_tests(None)


# A long source: a coherent QUANTUM run (s2-s4) embedded among off-topic distractors.
_DOC = (
    "The market rallied on strong quarterly earnings. "          # s0 finance
    "My compost heap needs turning before the soil dries. "      # s1 garden
    "Quantum error correction suppresses decoherence in hardware. "  # s2 quantum
    "A surface-code qubit needs many physical qubits per logical one. "  # s3 quantum
    "Quantum error correction thresholds set the fault-tolerance bar. "  # s4 quantum
    "The garden beds drain poorly after heavy autumn rain. "     # s5 garden
    "Stock futures slipped ahead of the finance ministry briefing."  # s6 finance
)


def test_long_source_recalls_the_coherent_passage_as_one_candidate(themed_embedder):
    out = sprout.extract(_DOC)
    assert out, "a long, multi-sentence source must yield candidates"
    # the planted quantum run is recalled as ONE multi-sentence passage (not fragmented)
    quantum = [c for c in out if "qubit" in c.lower() and "error correction" in c.lower()]
    assert quantum, f"the coherent quantum passage was not recalled as a span: {out}"
    assert quantum[0].count(".") >= 2, "the recalled quantum candidate should span >=2 sentences"


def test_output_is_multi_granular_and_bounded(themed_embedder):
    out = sprout.extract(_DOC, max_candidates=5)
    assert len(out) <= 5
    # mixed granularity: at least one multi-sentence span AND at least one single sentence
    assert any(c.count(".") >= 2 for c in out)
    assert any(c.count(".") == 1 for c in out)


def test_deterministic(themed_embedder):
    assert sprout.extract(_DOC) == sprout.extract(_DOC)


def test_short_source_is_left_alone(themed_embedder):
    assert sprout.extract("Only one sentence here. And a second.") == []


def test_disabled_is_a_noop(monkeypatch):
    monkeypatch.setenv("JONI_SPROUTRAG", "0")
    embeddings._reset_for_tests(_themed, name="themed", revision="t", dim=4)
    try:
        assert sprout.extract(_DOC) == []
    finally:
        embeddings._reset_for_tests(None)


def test_unavailable_embeddings_fall_back(monkeypatch):
    monkeypatch.setenv("JONI_SPROUTRAG", "1")
    embeddings._reset_for_tests(None)   # no model -> available() is False
    assert sprout.extract(_DOC) == []
