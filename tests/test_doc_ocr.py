"""OpenRouter file-parser OCR: capture-stable parsing, the gate, and the scanned-PDF fallback."""
from joni.autonomy import doc_ocr, model_call, pdf


def test_doc_ocr_dormant_without_the_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_OCR_OPENROUTER", raising=False)
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    assert doc_ocr.parse(b"%PDF data", "x.pdf", store_dir=tmp_path) is None   # off -> no-op


def test_doc_ocr_parses_via_file_parser_and_is_capture_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    monkeypatch.setenv("JONI_OCR_OPENROUTER", "1")
    calls = {"n": 0}

    def fake_complete(profile, system, user, attachment=None):
        calls["n"] += 1
        # the file-parser path was taken: a file attachment with an engine, not a plain prompt
        assert attachment and attachment["engine"] and attachment["file_data"].startswith("data:")
        return "TRANSCRIBED SCAN TEXT"

    monkeypatch.setattr(model_call, "_complete", fake_complete)
    out = doc_ocr.parse(b"%PDF-scan-bytes", "paper.pdf", store_dir=tmp_path)
    assert out == "TRANSCRIBED SCAN TEXT" and calls["n"] == 1
    # SAME bytes -> replayed from the capture (file sha in the key), no second live call, no charge
    again = doc_ocr.parse(b"%PDF-scan-bytes", "paper.pdf", store_dir=tmp_path)
    assert again == "TRANSCRIBED SCAN TEXT" and calls["n"] == 1
    # DIFFERENT bytes -> a fresh parse (the file identity is part of the replay key)
    doc_ocr.parse(b"%PDF-other-bytes", "paper.pdf", store_dir=tmp_path)
    assert calls["n"] == 2


def test_pdf_read_url_uses_ocr_fallback_only_on_a_scanned_pdf(monkeypatch):
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "_fetch", lambda url: b"scanned-image-bytes")
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "")     # no text layer = a scan
    seen = {}

    def ocr(data, name):
        seen["args"] = (data, name)
        return "OCR TEXT"

    doc = pdf.read_url("http://x/paper.pdf", ocr_fallback=ocr)
    assert doc is not None and doc.text == "OCR TEXT"
    assert seen["args"][0] == b"scanned-image-bytes"    # the raw bytes were handed over
    # unchanged behaviour without a fallback: a scanned PDF stays unreadable (None)
    assert pdf.read_url("http://x/paper.pdf") is None


def test_pdf_read_url_keeps_the_text_layer_when_present(monkeypatch):
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "_fetch", lambda url: b"pdf-with-text")
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "real extracted text")
    called = {"ocr": False}

    def ocr(data, name):
        called["ocr"] = True
        return "SHOULD NOT BE USED"

    doc = pdf.read_url("http://x/p.pdf", ocr_fallback=ocr)
    # OCR must NOT be called when a text layer is present
    assert doc.text == "real extracted text" and called["ocr"] is False
