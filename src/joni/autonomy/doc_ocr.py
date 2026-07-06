"""OpenRouter file-parser OCR/PDF backend — turn a scanned PDF or an image into text through Joni's
one captured, budget-metered model seam (Auftrag #7; operator: "OpenRouter hat ein PDF-Backend").

The document is parsed by OpenRouter's file-parser plugin (``cloudflare-ai`` free by default;
``mistral-ocr`` for real scans, paid per page) and the returned text enters the SAME governed
reading pipeline as any PDF — candidate claim sentences through the gate, the Semantic Layer still
deciding every relation. So OCR never lets Joni decide more by itself; it only lets him *read* more.

Capture-stable: the call goes through ``model_call.call`` with the file's sha folded into the replay
key, so the same document is parsed once and replayed free thereafter (no double charge). Opt-in
(``JONI_OCR_OPENROUTER=1``), gated like every model arm (``JONI_SEMANTIC_PROPOSALS=1``),
benefit-reviewed (``ocr_log``), budget-metered on the prepaid OpenRouter path. A dormant switch,
an unavailable key, or any error yields ``None`` — the caller then reads exactly as before.
"""
from __future__ import annotations

import base64
import hashlib
import os

from . import model_call, model_profile, projection
from .config import paths

_SYS = ("You are a document transcriber. Return the FULL plain text of the attached document, "
        "verbatim — no commentary, no summary, no markdown fences.")
_USER = "Transcribe the attached document to plain text."


def enabled() -> bool:
    from . import extension_review
    return (projection.enabled() and os.getenv("JONI_OCR_OPENROUTER", "0") == "1"
            and extension_review.active("ocr_openrouter"))


def _engine() -> str:
    # cloudflare-ai is free (PDF->markdown); mistral-ocr ($2/1000 pages) is for true scans.
    return os.getenv("JONI_OCR_ENGINE", "cloudflare-ai")


def parse(data: bytes, filename: str, *, budget=None, run_id: str = "ocr",
          store_dir=None, runs_per_week: int = 0) -> str | None:
    """Parse PDF/image ``data`` to text via OpenRouter's file-parser. Returns the text, or ``None``
    when dormant, on empty input, when the budget cap is reached, or on any failure. Never raises
    into the caller (a read-layer helper must never break the cycle)."""
    if not data or not enabled():
        return None
    mime = "application/pdf" if filename.lower().endswith(".pdf") else "image/png"
    attachment = {
        "filename": filename or "document.pdf",
        "engine": _engine(),
        "file_data": f"data:{mime};base64," + base64.b64encode(data).decode(),
        "sha": hashlib.sha256(data).hexdigest(),
    }
    try:
        text, _cap = model_call.call(
            model_profile.profile("joni-semantic"), _SYS, _USER,
            run_id=run_id, store_dir=store_dir or paths().model_calls,
            escalation_reason="ocr", budget=budget, runs_per_week=runs_per_week,
            attachment=attachment)
    except Exception:  # noqa: BLE001 - dormant/erroring OCR must never break the reading step
        return None
    return (text or "").strip() or None
