"""Joni's PDF input port - read the actual papers, not just the abstract.

Three ways in, all feeding the same governed pipeline (extracted sentences enter as
*candidate* claims through the gate; the DESi Semantic Layer still decides every relation,
so reading more does not let Joni decide more on its own):

  * **arXiv full text** - for a relevant arXiv hit, fetch the PDF and read it;
  * **PDF by URL** - a direct PDF link (incl. SSRN download links), read respectfully;
  * **local inbox** - drop PDFs in a folder; Joni reads new ones next cycle.

Extraction is Joni's own, deliberately light and deterministic: split into sentences,
keep the ones that read like a claim (declarative, has a content verb, sane length, not
boilerplate), dedupe, cap per paper. PDF-to-text uses ``pypdf`` as a soft dependency; if
it is absent the port is a clean no-op. Downloads are size-capped and time-limited.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

_TIMEOUT = 25
_MAX_BYTES = 8_000_000           # don't pull more than ~8 MB of PDF
_UA = {"User-Agent": "joni-autonomy/1.0 (+https://github.com/hstre/Joni)"}

# sentence-ish splitter and a small claim filter
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
_VERB = re.compile(
    r"\b(is|are|was|were|be|can|cannot|should|must|may|shows?|finds?|increases?|"
    r"decreases?|reduces?|improves?|causes?|enables?|requires?|implies?|suggests?|"
    r"demonstrates?|outperforms?|leads?|results?|depends?|correlates?|predicts?)\b", re.I)
_BOILER = re.compile(
    r"\b(arxiv|preprint|copyright|all rights reserved|figure|table|et al|"
    r"university|department|email|@|http|doi|references|acknowledg|appendix|"
    r"license|cc by|page \d)\b", re.I)


@dataclass(frozen=True)
class PdfText:
    source_id: str
    url: str
    title: str
    text: str


def available() -> bool:
    # pypdf is optional; in some environments even *importing* it can panic (a broken
    # native crypto backend raises pyo3 PanicException, not Exception) - so guard widely.
    try:
        import pypdf  # noqa: F401
        return True
    except BaseException:  # noqa: BLE001 - a broken optional dep must never crash the cycle
        return False


def _fetch(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
            return resp.read(_MAX_BYTES)
    except Exception:  # noqa: BLE001 - network/HTTP issues are non-fatal
        return None


def extract_text(pdf_bytes: bytes, *, max_pages: int = 12) -> str:
    """PDF bytes -> text (first ``max_pages`` pages). Empty string if unreadable."""
    if not pdf_bytes:
        return ""
    try:
        import io

        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        pages = reader.pages[:max_pages]
        return "\n".join((p.extract_text() or "") for p in pages)
    except BaseException:  # noqa: BLE001 - a malformed PDF / broken backend is not fatal
        return ""


def claim_sentences(text: str, *, max_claims: int = 5, min_words: int = 6,
                    max_words: int = 40) -> list[str]:
    """Deterministically pull a few claim-like sentences out of paper text."""
    text = re.sub(r"\s+", " ", text or "").strip()
    out: list[str] = []
    seen: set[str] = set()
    for raw in _SENT.split(text):
        s = raw.strip().strip("•-–* ").rstrip(".")
        words = s.split()
        if not (min_words <= len(words) <= max_words):
            continue
        if not _VERB.search(s) or _BOILER.search(s):
            continue
        if sum(c.isdigit() for c in s) > len(s) * 0.3:      # tables / numeric noise
            continue
        key = s.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(s + ".")
        if len(out) >= max_claims:
            break
    return out


def arxiv_pdf_url(item_url: str, source_id: str) -> str | None:
    """Derive the PDF url from an arXiv abstract url / id."""
    m = re.search(r"arxiv\.org/abs/([^/?#]+)", item_url or "")
    aid = m.group(1) if m else (source_id if re.match(r"^\d{4}\.\d+", source_id or "") else None)
    return f"https://arxiv.org/pdf/{aid}.pdf" if aid else None


def read_url(url: str, *, source_id: str = "", title: str = "") -> PdfText | None:
    """Read a direct PDF url (arXiv, SSRN download link, ...). Respectful, size-capped."""
    if not available():
        return None
    text = extract_text(_fetch(url) or b"")
    if not text.strip():
        return None
    return PdfText(source_id=source_id or url, url=url, title=title, text=text)


def read_arxiv(item) -> PdfText | None:
    """Read the full text of an arXiv item (Item with .url, .key, .title)."""
    url = arxiv_pdf_url(getattr(item, "url", ""), getattr(item, "key", ""))
    if not url:
        return None
    return read_url(url, source_id=getattr(item, "key", url), title=getattr(item, "title", ""))


def read_inbox(inbox: Path, processed: set[str], *, limit: int = 3) -> list[PdfText]:
    """Read new PDFs dropped into a local inbox folder. ``processed`` dedups by filename."""
    if not available() or not inbox.exists():
        return []
    out: list[PdfText] = []
    for path in sorted(inbox.glob("*.pdf")):
        if len(out) >= limit:
            break
        if path.name in processed:
            continue
        text = extract_text(path.read_bytes())
        processed.add(path.name)
        if text.strip():
            out.append(PdfText(source_id=f"inbox:{path.name}", url=str(path),
                               title=path.stem, text=text))
    return out
