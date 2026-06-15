"""The quality gate: stopwords / artifact tokens may not seed structure or leave the system."""

from joni.autonomy import quality


def test_meaningful_terms_pass():
    for t in ("routing", "alignment", "calibration", "retrieval", "distillation",
              "latency", "memory", "local-first"):
        assert quality.is_meaningful_term(t), t


def test_stopwords_and_qualifiers_are_rejected():
    for t in ("about", "large", "modes", "visual", "the", "with", "using", "model",
              "results", "approach", "single", "various"):
        assert not quality.is_meaningful_term(t), t


def test_artifact_tokens_are_rejected():
    # vowelless / acronym fragments and hyphenated number-units are not concepts
    for t in ("mllm", "llms", "mid-ir", "gpt-4", "a-b", "xyz"):
        assert not quality.is_meaningful_term(t), t


def test_substantive_hypothesis_gate():
    junk = "Across my routing claims, 'cotton' is a through-line - but 'about' recurs too."
    # 'about' is a stopword subject -> the whole thing is held back from external comms
    assert quality.is_substantive_hypothesis(junk) is False
    ok = "Across my routing claims, 'distillation' recurs as a single underlying factor."
    assert quality.is_substantive_hypothesis(ok) is True
    # a hypothesis that names no single-token subject is not judged here (allowed)
    assert quality.is_substantive_hypothesis("routing reduces latency under load") is True
