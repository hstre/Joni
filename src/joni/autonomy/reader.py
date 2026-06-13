"""The 'read the actual paper' step of a cycle.

Turns Joni from an abstract-skimmer into a reader. For a few relevant arXiv hits it pulls
the PDF and reads it; it drains a small queue of direct PDF urls (incl. SSRN download
links); and it reads any new PDFs dropped in the local inbox. Extracted claim-sentences
enter as **candidate** claims through the gate, anchored to their source - the Semantic
Layer still governs every relation, so reading more never lets Joni decide more by itself.

Bounded per cycle (a couple of papers, a few claims each) and deduped, so it is cheap and
works through new material over time.
"""

from __future__ import annotations

import json

from . import pdf


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
    if not pdf.available():
        return {"papers": 0, "claims": 0, "available": False}

    read_keys = set(extensions.get("pdf_read", []))
    url_seen = set(extensions.get("pdf_urls_seen", []))
    inbox_seen = set(extensions.get("pdf_inbox_seen", []))
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
    if online:
        for item, rel in judged:
            if papers >= max_papers:
                break
            if getattr(item, "source", "") != "arxiv" or item.key in read_keys:
                continue
            read_keys.add(item.key)
            doc = pdf.read_arxiv(item)
            if doc is not None:
                ingest(doc, rel.topic or "unsorted", item.title[:60])

    # 2. a queue of direct PDF urls (incl. SSRN).
    if online:
        for url in _load_urls(paths.pdf_urls):
            if papers >= max_papers + max_urls or url in url_seen:
                continue
            url_seen.add(url)
            doc = pdf.read_url(url)
            if doc is not None:
                topic = (cs.topics() or ["unsorted"])[0]
                ingest(doc, topic, url.rsplit("/", 1)[-1][:60])

    # 3. local inbox (works offline too).
    for doc in pdf.read_inbox(paths.pdf_inbox, inbox_seen, limit=max_urls):
        topic = (cs.topics() or ["unsorted"])[0]
        ingest(doc, topic, doc.title[:60])

    extensions["pdf_read"] = sorted(read_keys)[-2000:]
    extensions["pdf_urls_seen"] = sorted(url_seen)[-2000:]
    extensions["pdf_inbox_seen"] = sorted(inbox_seen)[-2000:]
    return {"papers": papers, "claims": claims, "available": True}
