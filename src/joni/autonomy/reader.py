"""The 'read the actual paper' step of a cycle.

Turns Joni from an abstract-skimmer into a reader. For a few relevant arXiv hits it pulls
the PDF and reads it; it drains a small queue of direct PDF urls (incl. SSRN download
links); and it reads any new documents dropped in the local inbox - PDF, **Markdown**
(``*.md``) and **LaTeX** (``*.tex``). The Markdown/LaTeX ports need no pypdf, so they read
offline. Extracted claim-sentences enter as **candidate** claims through the gate, anchored
to their source - the Semantic Layer still governs every relation, so reading more never
lets Joni decide more by itself.

Bounded per cycle (a couple of papers, a few claims each) and deduped, so it is cheap and
works through new material over time.
"""

from __future__ import annotations

import json

from . import documents, ocr, pdf


def starved_topics(cs, *, min_hyps: int = 1) -> list[str]:
    """Topics Joni keeps hypothesising on but for which he has **no** supporting evidence.

    These are exactly the ideas that go barren (the ``starved_topic`` commission). Surfacing
    them lets the cycle put them at the front of the query list so their material is actually
    fetched, instead of falling off the capped query set."""
    from .homeostasis import _supports_on  # local import: avoid an import cycle
    by_topic: dict[str, list] = {}
    for h in cs.hypotheses():
        topic = getattr(h, "topic", None)
        if topic:
            by_topic.setdefault(topic, []).append(h)
    starved = []
    for topic, hyps in by_topic.items():
        if len(hyps) >= min_hyps and sum(_supports_on(cs, h.id) for h in hyps) == 0:
            starved.append(topic)
    return starved


def _load_urls(path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [u for u in data if isinstance(u, str)] if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def read_papers(cs, judged, extensions: dict, proto, cycle: int, paths, *, online: bool,
                max_papers: int = 2, max_urls: int = 2, max_claims: int = 5) -> dict:
    # The PDF steps need pypdf; the Markdown/LaTeX inbox ports do not, so they run even when
    # pypdf is absent (a clean way to read material offline).
    pdf_ok = pdf.available()

    read_keys = set(extensions.get("pdf_read", []))
    url_seen = set(extensions.get("pdf_urls_seen", []))
    inbox_seen = set(extensions.get("pdf_inbox_seen", []))
    md_seen = set(extensions.get("md_inbox_seen", []))
    tex_seen = set(extensions.get("tex_inbox_seen", []))
    ocr_seen = set(extensions.get("ocr_inbox_seen", []))
    papers = claims = 0

    def ingest(doc, topic: str, label: str) -> None:
        nonlocal papers, claims
        sents = pdf.claim_sentences(doc.text, max_claims=max_claims)
        for s in sents:
            cs.learn(s, topic, source_id=doc.source_id)
            claims += 1
        if sents:
            papers += 1
            proto.record(cycle, "read",
                         f"read full text of {label}: {len(sents)} claim(s) "
                         f"[{doc.source_id}]", refs={"url": doc.url, "topic": topic})

    # 1. arXiv full text for relevant hits.
    if pdf_ok and online:
        for item, rel in judged:
            if papers >= max_papers:
                break
            if getattr(item, "source", "") != "arxiv" or item.key in read_keys:
                continue
            read_keys.add(item.key)
            doc = pdf.read_arxiv(item)
            if doc is not None:
                ingest(doc, rel.topic or "unsorted", item.title[:60])

    # 2. a queue of direct PDF urls (incl. SSRN download links).
    if pdf_ok and online:
        for url in _load_urls(paths.pdf_urls):
            if papers >= max_papers + max_urls or url in url_seen:
                continue
            url_seen.add(url)
            doc = pdf.read_url(url)
            if doc is not None:
                topic = (cs.topics() or ["unsorted"])[0]
                ingest(doc, topic, url.rsplit("/", 1)[-1][:60])

    # 3. local PDF inbox (works offline too).
    if pdf_ok:
        for doc in pdf.read_inbox(paths.pdf_inbox, inbox_seen, limit=max_urls):
            topic = (cs.topics() or ["unsorted"])[0]
            ingest(doc, topic, doc.title[:60])

    # 4. local Markdown inbox - no pypdf needed, so it works fully offline.
    for doc in documents.read_markdown_inbox(paths.pdf_inbox, md_seen, limit=max_urls):
        ingest(doc, (cs.topics() or ["unsorted"])[0], doc.title[:60])

    # 5. local LaTeX inbox - paper sources (e.g. arXiv source). Also offline.
    for doc in documents.read_latex_inbox(paths.pdf_inbox, tex_seen, limit=max_urls):
        ingest(doc, (cs.topics() or ["unsorted"])[0], doc.title[:60])

    # 6. local image/scanned inbox via OCR (Auftrag #161). Optional, fail-closed: with no OCR
    # backend installed this reads nothing and the cycle is unchanged.
    for doc in ocr.read_inbox(paths.pdf_inbox, ocr_seen, limit=max_urls):
        ingest(doc, (cs.topics() or ["unsorted"])[0], doc.title[:60])

    extensions["pdf_read"] = sorted(read_keys)[-2000:]
    extensions["pdf_urls_seen"] = sorted(url_seen)[-2000:]
    extensions["pdf_inbox_seen"] = sorted(inbox_seen)[-2000:]
    extensions["md_inbox_seen"] = sorted(md_seen)[-2000:]
    extensions["tex_inbox_seen"] = sorted(tex_seen)[-2000:]
    extensions["ocr_inbox_seen"] = sorted(ocr_seen)[-2000:]
    return {"papers": papers, "claims": claims, "available": pdf_ok, "ocr": ocr.available()}
