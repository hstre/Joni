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


def test_on_domain_is_fail_open_without_an_embedder(monkeypatch):
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: False)
    assert quality.on_domain("cotton") is True
    assert quality.admissible_term("cotton") is True


def _fake_distances(monkeypatch):
    """Deterministic stand-in: domain terms sit near domain anchors, off-domain near off-domain."""
    from joni.autonomy import embeddings
    monkeypatch.setattr(embeddings, "available", lambda: True)
    off = ("cotton", "textile", "farming", "medicine", "oncology", "geology", "cooking",
           "sports", "finance", "music", "animals", "history", "astronomy", "plants", "painting")

    def cd(probe, anchor):
        p_off = any(k in probe.lower() for k in off)
        a_off = any(k in anchor.lower() for k in off)
        return 0.15 if (p_off == a_off) else 0.9     # near when same side, far when crossed
    monkeypatch.setattr(embeddings, "cosine_distance", cd)


def test_on_domain_rejects_off_domain_real_words(monkeypatch):
    _fake_distances(monkeypatch)
    assert quality.on_domain("cotton") is False          # the headline case
    assert quality.on_domain("oncology") is False
    assert quality.admissible_term("cotton") is False    # meaningful word, but off-domain


def test_on_domain_keeps_real_domain_terms(monkeypatch):
    _fake_distances(monkeypatch)
    assert quality.on_domain("routing") is True
    assert quality.on_domain("alignment") is True
    assert quality.admissible_term("routing") is True


def test_hypothesis_admissible_holds_off_domain_subjects(monkeypatch):
    _fake_distances(monkeypatch)
    assert quality.hypothesis_admissible(
        "Across my routing claims, 'cotton' recurs as a through-line.") is False
    assert quality.hypothesis_admissible(
        "Across my routing claims, 'retrieval' recurs as a through-line.") is True
