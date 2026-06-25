"""Joni's PDF input port - read the paper, extract candidate claims, anchored to source."""

import desi_layer9 as l9
from joni.autonomy import pdf, reader
from joni.autonomy.core_state import CoreState, seed_core
from joni.autonomy.pdf import PdfText


class _Proto:
    def __init__(self):
        self.events = []

    def record(self, cycle, kind, summary, **kw):
        self.events.append((kind, summary))


class _Rel:
    def __init__(self, topic):
        self.topic = topic
        self.relevant = True


class _Item:
    def __init__(self, source, key, url, title):
        self.source, self.key, self.url, self.title = source, key, url, title


class _Paths:
    def __init__(self, tmp):
        from pathlib import Path
        self.pdf_inbox = Path(tmp) / "inbox"
        self.pdf_urls = Path(tmp) / "pdf_urls.json"


def test_claim_sentences_keeps_claims_drops_boilerplate():
    text = ("Cheap local routing reduces end-to-end request latency for short tasks. "
            "Figure 2 shows the architecture. Copyright 2024 the authors. "
            "Memory pressure increases scheduling contention under heavy load. "
            "See the arxiv preprint for the full details.")
    out = pdf.claim_sentences(text, max_claims=5)
    assert any("latency" in s for s in out)
    assert any("contention" in s for s in out)
    assert not any("Figure" in s or "Copyright" in s or "arxiv" in s.lower() for s in out)
    assert all(s.endswith(".") for s in out)


def test_arxiv_pdf_url_derivation():
    assert pdf.arxiv_pdf_url("https://arxiv.org/abs/2406.00001", "k") == \
        "https://arxiv.org/pdf/2406.00001.pdf"
    assert pdf.arxiv_pdf_url("https://example.com/x", "notarxiv") is None


def test_reader_is_a_noop_without_pypdf(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "available", lambda: False)
    cs = CoreState(seed_core())
    out = reader.read_papers(cs, [], {}, _Proto(), 0, _Paths(tmp_path), online=True)
    assert out == {"papers": 0, "claims": 0, "available": False, "ocr": False}


def test_reader_ingests_arxiv_full_text_as_source_anchored_claims(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "read_arxiv", lambda item: PdfText(
        source_id=item.key, url=item.url, title=item.title,
        text="Cheap local routing reduces request latency for short tasks. "
             "Memory pressure increases scheduling contention under heavy load."))
    cs = CoreState(seed_core())
    before = len(cs.active_claims())
    item = _Item("arxiv", "2406.12345", "https://arxiv.org/abs/2406.12345", "A routing paper")
    ext: dict = {}
    out = reader.read_papers(cs, [(item, _Rel("routing"))], ext, _Proto(), 1,
                             _Paths(tmp_path), online=True)
    assert out["papers"] == 1 and out["claims"] >= 1
    assert len(cs.active_claims()) > before
    # the new claims are anchored to the paper's id in their provenance
    new = [c for c in cs.core.all(l9.ObjectType.CLAIM)
           if "2406.12345" in (c.provenance.source_ids or ())]
    assert new
    # reading the same paper again does nothing (deduped)
    out2 = reader.read_papers(cs, [(item, _Rel("routing"))], ext, _Proto(), 2,
                              _Paths(tmp_path), online=True)
    assert out2["papers"] == 0


def test_reader_reads_a_url_queue(monkeypatch, tmp_path):
    import json
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "read_url", lambda url, **k: PdfText(
        source_id=url, url=url, title="q",
        text="Persistent context reduces contradiction across long running sessions."))
    p = _Paths(tmp_path)
    p.pdf_urls.write_text(json.dumps(["https://papers.ssrn.com/sol3/Delivery.cfm/x.pdf"]))
    cs = CoreState(seed_core())
    out = reader.read_papers(cs, [], {}, _Proto(), 1, p, online=True)
    assert out["papers"] == 1 and out["claims"] >= 1
