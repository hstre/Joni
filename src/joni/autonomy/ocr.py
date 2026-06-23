"""Optical-character-recognition input port (Auftrag #161, after "Unlimited OCR" 2606.23050).

Lets Joni read SCANNED / image documents: drop ``*.png`` / ``*.jpg`` / ``*.tiff`` ... in the inbox
and the extracted text enters the SAME governed reading pipeline as PDF / Markdown / LaTeX -
candidate claim-sentences through the gate, anchored to their source; the DESi Semantic Layer still
decides every relation, so reading an image never lets Joni decide more by itself.

The transcription is done by a pluggable ``OcrBackend``. The long-horizon model the Auftrag cites
(Unlimited OCR / the DeepSeek-OCR encoder - dozens of pages in one forward pass) is a heavy vision
model Joni's CPU CI cannot host, so - exactly as ``embeddings.py`` treats its projector and
``facets.py`` treats FaBle - the backend is loaded **fail-closed and OPTIONAL**: a real engine
present -> real transcription; none -> the port reports unavailable and the cycle reads exactly as
before. The real model is registered through ``set_backend`` once its package is installed; a
deterministic backend is injected the same way in tests. Never a hard dependency.

Acceptance note (a 50-page scan transcribed in <120s with no per-page linear blow-up): that is a
property of the real model on real hardware and needs both the weights and a 50-page fixture - and
neither is in CI. This lands the reader + backend seam + a mechanism test; the headline metric is
the backend's to meet, and is documented as such rather than faked.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .documents import Doc

# Image kinds a scanned document arrives as (a PDF can be exported to these page images upstream).
_IMAGE_PATTERNS = ("*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff", "*.bmp", "*.webp")


@runtime_checkable
class OcrBackend(Protocol):
    """The OCR engine seam: turn one image file into its transcribed text. The Unlimited-OCR model
    is registered here once available; tests register a deterministic stub."""

    name: str

    def transcribe(self, image_path: str) -> str:
        ...


_BACKEND: OcrBackend | bool | None = None   # None = untried, False = absent, or a backend


def _load() -> OcrBackend | None:
    """Resolve the OCR backend fail-closed. No real engine is bundled (the cited model is heavy and
    its weights are not in CI); a generic local engine is used only if it happens to be installed,
    otherwise the port stays dormant. Operators wire the real model via ``set_backend``."""
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND or None
    try:
        import pytesseract  # a common, light local OCR engine - used only if present
        from PIL import Image

        class _Tesseract:
            name = "pytesseract"

            def transcribe(self, image_path: str) -> str:
                return pytesseract.image_to_string(Image.open(image_path)) or ""

        _BACKEND = _Tesseract()
        return _BACKEND
    except Exception:  # noqa: BLE001 - no engine installed: dormant port, never a crash
        _BACKEND = False
        return None


def available() -> bool:
    return _load() is not None


def info() -> dict:
    backend = _load()
    return {"backend": getattr(backend, "name", "none"), "available": backend is not None}


def set_backend(backend: OcrBackend | None) -> None:
    """Register the OCR engine (e.g. the Unlimited-OCR model once its package is installed), or
    ``None`` to mark the port unavailable. The runtime hook that lifts this from 'built' to 'in the
    runtime path' without a code change."""
    global _BACKEND
    _BACKEND = backend if backend is not None else False


def _reset_for_tests(backend: OcrBackend | None = None) -> None:
    """Inject a deterministic backend in tests, or reset to 'untried'."""
    global _BACKEND
    _BACKEND = backend if backend is not None else None


@dataclass(frozen=True)
class OcrReader:
    """Reads image/scanned files from an inbox via its ``backend`` into the standard ``Doc``s."""

    backend: OcrBackend

    def read_inbox(self, inbox: Path, processed: set[str], *, limit: int = 2) -> list[Doc]:
        if not inbox.exists():
            return []
        files: set[Path] = set()
        for pat in _IMAGE_PATTERNS:
            files.update(inbox.glob(pat))
        out: list[Doc] = []
        for path in sorted(files):
            if len(out) >= limit:
                break
            if path.name in processed:
                continue
            processed.add(path.name)
            try:
                text = self.backend.transcribe(str(path)) or ""
            except Exception:  # noqa: BLE001 - a broken engine fails closed, never breaks the cycle
                continue
            if text.strip():
                out.append(Doc(source_id=f"ocr:{path.name}", url=str(path),
                               title=path.stem, text=text))
        return out


def read_inbox(inbox: Path, processed: set[str], *, limit: int = 2) -> list[Doc]:
    """New image files from the inbox -> transcribed ``Doc``s, deduped by name, bounded by
    ``limit``; ``[]`` when no OCR backend is available (the cycle then reads exactly as before)."""
    backend = _load()
    if backend is None:
        return []
    return OcrReader(backend).read_inbox(inbox, processed, limit=limit)
