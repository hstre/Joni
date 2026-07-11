"""OpenRouter file-parser OCR: capture-stable parsing, the gate, and the scanned-PDF fallback."""
from joni.autonomy import doc_ocr, model_call, pdf


def test_doc_ocr_dormant_without_the_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("JONI_OCR_OPENROUTER", raising=False)
    monkeypatch.setenv("JONI_SEMANTIC_PROPOSALS", "1")
    assert doc_ocr.parse(b"%PDF data", "x.pdf", store_dir=tmp_path) is None   # off -> no-op


def test_doc_ocr_parses_via_file_parser_and_is_capture_stable(tmp_path, monkeypatch):
    monkeypatch.setenv("JONI_OCR_OPENROUTER", "1")
    monkeypatch.setattr(doc_ocr, "enabled", lambda: True)   # OCR on; don't hang on the embed model
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


def test_ocr_uses_a_large_transcription_budget_not_the_768_proposal_cap(monkeypatch):
    from joni.autonomy import model_profile
    # the proposal profile caps completions at 768 tokens - which would truncate a scan at ~2 pages
    assert model_profile.profile("joni-semantic").sampling.max_tokens == 768
    # OCR pins its own, much larger echo budget so a full document is not cut off
    assert doc_ocr._ocr_profile().sampling.max_tokens >= 8000
    monkeypatch.setenv("JONI_OCR_MAX_TOKENS", "20000")
    assert doc_ocr._ocr_profile().sampling.max_tokens == 20000
    # ...but never below the floor, even if misconfigured low
    monkeypatch.setenv("JONI_OCR_MAX_TOKENS", "10")
    assert doc_ocr._ocr_profile().sampling.max_tokens == 768


def test_ocr_attachment_is_always_pdf_scoped(tmp_path, monkeypatch):
    # OpenRouter's file-parser is PDF-scoped; parse must send application/pdf, never an image mime
    monkeypatch.setenv("JONI_OCR_OPENROUTER", "1")
    monkeypatch.setattr(doc_ocr, "enabled", lambda: True)   # OCR on; don't hang on the embed model
    seen = {}

    def fake_complete(profile, system, user, attachment=None):
        seen["file_data"] = attachment["file_data"]
        return "TEXT"

    monkeypatch.setattr(model_call, "_complete", fake_complete)
    doc_ocr.parse(b"%PDF-bytes", "scan.png", store_dir=tmp_path)   # even a .png name
    assert seen["file_data"].startswith("data:application/pdf;base64,")


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


def test_scanned_inbox_pdf_is_ocred_not_silently_dropped(tmp_path, monkeypatch):
    # a scanned PDF dropped in the inbox: pypdf yields no text, so without a fallback it used to be
    # marked processed and lost. With the fallback it is transcribed instead.
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "")     # no text layer = a scan
    (tmp_path / "scan.pdf").write_bytes(b"%PDF-scan")
    seen: set[str] = set()
    docs = pdf.read_inbox(tmp_path, seen, ocr_fallback=lambda data, name: "OCR OF THE SCAN")
    assert [d.text for d in docs] == ["OCR OF THE SCAN"]
    assert "scan.pdf" in seen                                          # read -> now processed


def test_paid_ocr_calls_are_capped_per_cycle(tmp_path, monkeypatch):
    # a folder of un-OCR-able scans must NOT fire one paid OCR call per scan every cycle: the
    # attempts are capped at `limit`, the rest are left for the next cycle (not marked processed).
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "")     # every pdf is a scan
    for i in range(5):
        (tmp_path / f"scan{i}.pdf").write_bytes(b"%PDF-scan")
    calls = {"n": 0}

    def ocr(data, name):
        calls["n"] += 1
        return None                                                   # never yields text

    seen: set[str] = set()
    pdf.read_inbox(tmp_path, seen, limit=2, ocr_fallback=ocr, attempts={})
    assert calls["n"] == 2                                            # capped, not 5
    assert seen == set()                                             # nothing burned; retry next


def test_inbox_scan_is_retried_on_a_transient_ocr_miss_then_given_up(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "")
    (tmp_path / "scan.pdf").write_bytes(b"%PDF-scan")
    seen: set[str] = set()
    attempts: dict = {}
    # OCR keeps returning nothing (a transient backend miss): the file is NOT marked processed yet
    for _ in range(2):
        assert pdf.read_inbox(tmp_path, seen, ocr_fallback=lambda d, n: None,
                              attempts=attempts, max_attempts=3) == []
        assert "scan.pdf" not in seen
    # ...but after max_attempts empty tries it is given up (so it can't loop / re-charge forever)
    pdf.read_inbox(tmp_path, seen, ocr_fallback=lambda d, n: None, attempts=attempts,
                   max_attempts=3)
    assert "scan.pdf" in seen


def test_inbox_pdf_without_ocr_and_no_text_is_marked_processed(tmp_path, monkeypatch):
    # no OCR path and no text layer -> nothing to do, so mark processed (don't retry forever)
    monkeypatch.setattr(pdf, "available", lambda: True)
    monkeypatch.setattr(pdf, "extract_text", lambda data, **k: "")
    (tmp_path / "empty.pdf").write_bytes(b"%PDF")
    seen: set[str] = set()
    assert pdf.read_inbox(tmp_path, seen) == []
    assert "empty.pdf" in seen


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


class _StubBudget:
    def __init__(self, remaining):
        self.remaining_eur = remaining
        self.charged = 0.0

    def can_spend(self, amount, *, runs_per_week=0):
        return amount <= self.remaining_eur

    def charge(self, amount):
        self.charged += amount
        self.remaining_eur -= amount


def test_paid_ocr_engine_is_budget_gated_and_charged(tmp_path, monkeypatch):
    # mistral-ocr bills per page; est_call_cost is €0 on the prepaid OpenRouter path, so doc_ocr
    # must gate + charge it itself, else the paid engine bypasses the weekly cap.
    monkeypatch.setenv("JONI_OCR_OPENROUTER", "1")
    monkeypatch.setattr(doc_ocr, "enabled", lambda: True)   # OCR on; don't hang on the embed model
    monkeypatch.setenv("JONI_OCR_ENGINE", "mistral-ocr")
    monkeypatch.setenv("JONI_COST_PER_OCR_CALL", "0.02")
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u, attachment=None: "SCAN TEXT")
    # cap reached -> the paid call is NOT made and nothing is charged
    poor = _StubBudget(0.0)
    assert doc_ocr.parse(b"%PDF-a", "x.pdf", store_dir=tmp_path, budget=poor) is None
    assert poor.charged == 0.0
    # enough budget -> parses and charges the live call once
    rich = _StubBudget(1.0)
    assert doc_ocr.parse(b"%PDF-a", "x.pdf", store_dir=tmp_path, budget=rich) == "SCAN TEXT"
    assert round(rich.charged, 4) == 0.02


def test_free_ocr_engine_is_not_charged(tmp_path, monkeypatch):
    monkeypatch.setenv("JONI_OCR_OPENROUTER", "1")
    monkeypatch.setattr(doc_ocr, "enabled", lambda: True)        # OCR on; don't hang on embed model
    monkeypatch.delenv("JONI_OCR_ENGINE", raising=False)          # default cloudflare-ai (free)
    monkeypatch.setattr(model_call, "_complete", lambda p, s, u, attachment=None: "TEXT")
    b = _StubBudget(0.0)                                          # even at €0 remaining
    assert doc_ocr.parse(b"%PDF-b", "x.pdf", store_dir=tmp_path, budget=b) == "TEXT"
    assert b.charged == 0.0                                       # free engine is never charged
