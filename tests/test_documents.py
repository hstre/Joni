"""Joni's Markdown and LaTeX input ports - strip markup, keep claim sentences, work offline."""

import desi_layer9 as l9
from joni.autonomy import documents, pdf, reader
from joni.autonomy.core_state import CoreState, seed_core


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


class _Paths:
    def __init__(self, tmp):
        self.pdf_inbox = tmp / "inbox"
        self.pdf_urls = tmp / "pdf_urls.json"


def test_markdown_is_stripped_to_prose():
    md = ("# Heading\n\n"
          "Local routing **reduces** request latency for short tasks.\n\n"
          "```python\nprint('code is dropped')\n```\n\n"
          "See [the paper](http://example.com/x) for details.\n"
          "- a bullet that increases scheduling contention under load\n")
    text = documents.markdown_to_text(md)
    assert "code is dropped" not in text
    assert "#" not in text and "**" not in text
    claims = documents.claims_from(text)
    assert any("latency" in c for c in claims)
    assert any("contention" in c for c in claims)


def test_latex_is_stripped_to_prose():
    tex = (r"% a comment that must vanish" "\n"
           r"\section{Results}" "\n"
           r"The method \textbf{reduces} request latency for short tasks \cite{smith2024}." "\n"
           r"\begin{equation} E = mc^2 \end{equation}" "\n"
           r"Memory pressure increases scheduling contention under heavy load.")
    text = documents.latex_to_text(tex)
    assert "comment that must vanish" not in text
    assert "mc^2" not in text and "\\section" not in text and "cite" not in text
    claims = documents.claims_from(text)
    assert any("latency" in c for c in claims)
    assert any("contention" in c for c in claims)


def test_markdown_inbox_is_read_offline_without_pypdf(monkeypatch, tmp_path):
    # the Markdown/LaTeX ports must work even when pypdf is unavailable
    monkeypatch.setattr(pdf, "available", lambda: False)
    paths = _Paths(tmp_path)
    paths.pdf_inbox.mkdir()
    (paths.pdf_inbox / "note.md").write_text(
        "# Notes\n\nPersistent context **reduces** contradiction across long sessions.\n")
    cs = CoreState(seed_core())
    before = len(cs.active_claims())
    ext: dict = {}
    out = reader.read_papers(cs, [], ext, _Proto(), 1, paths, online=False)
    assert out["available"] is False                 # pypdf still absent...
    assert out["claims"] >= 1                          # ...but Markdown was read anyway
    assert len(cs.active_claims()) > before
    new = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if any("md:note.md" in s for s in (c.provenance.source_ids or ()))]
    assert new
    # second pass: the same file is not re-read
    out2 = reader.read_papers(cs, [], ext, _Proto(), 2, paths, online=False)
    assert out2["claims"] == 0


def test_latex_inbox_is_read(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "available", lambda: False)
    paths = _Paths(tmp_path)
    paths.pdf_inbox.mkdir()
    (paths.pdf_inbox / "paper.tex").write_text(
        r"\section{Intro} Cheap routing reduces end-to-end latency for short tasks.")
    cs = CoreState(seed_core())
    out = reader.read_papers(cs, [], {}, _Proto(), 1, paths, online=False)
    assert out["claims"] >= 1
    new = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if any("tex:paper.tex" in s for s in (c.provenance.source_ids or ()))]
    assert new
