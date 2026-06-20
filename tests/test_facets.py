"""Facet decomposition (Auftrag #136, after FaBle): split a source into its distinct facets so
candidate extraction is facet-aware. Opt-in, non-core, uses Joni's own captured model."""

from joni.autonomy import facets, model_call


def _on(monkeypatch, tmp_path, reply, *, on=True):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_FACET_DECOMP", "1" if on else "0")
    monkeypatch.setenv("JONI_AUTONOMY_ROOT", str(tmp_path))
    monkeypatch.setattr(model_call, "_complete", lambda profile, system, user: reply)


def test_off_by_default(monkeypatch, tmp_path):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.delenv("JONI_FACET_DECOMP", raising=False)
    assert facets.enabled() is False
    assert facets.decompose("a method that is fast on small inputs") == []


def test_decomposes_a_source_into_facets(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path,
        '["the method routes locally", "scope: only small inputs", "result: lower latency"]')
    units = facets.decompose("Local routing is fast for small inputs and lowers latency.")
    assert units == ["the method routes locally", "scope: only small inputs",
                     "result: lower latency"]


def test_a_single_facet_text_returns_one_unit(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path, '["one self-contained claim"]')
    assert facets.decompose("one self-contained claim") == ["one self-contained claim"]


def test_empty_or_unparseable_is_a_clean_no_op(monkeypatch, tmp_path):
    _on(monkeypatch, tmp_path, "not json at all")
    assert facets.decompose("some text") == []
    assert facets.decompose("   ") == []
