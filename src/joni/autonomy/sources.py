"""Where Joni looks - arXiv, Hacker News, Hugging Face.

Each source is a small, polite reader over a public API (no key, modest limits,
short timeouts, failures swallowed so a hiccup never breaks a run). Everything is
behind a ``Fetcher`` interface so the default offline path - a deterministic
``MockFetcher`` - keeps the loop and the tests fully reproducible with no network.

SSRN is intentionally omitted for now: it has no clean public API and scraping it is
fragile and ToS-sensitive. It can be added later behind this same interface.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from xml.etree import ElementTree as ET

_UA = "joni-autonomy/0.1 (research reader; +https://github.com/hstre/Joni)"
_TIMEOUT = 12


@dataclass(frozen=True)
class Item:
    source: str
    id: str
    title: str
    url: str
    summary: str
    score: float = 0.0

    @property
    def key(self) -> str:
        return f"{self.source}:{self.id}"


@runtime_checkable
class Fetcher(Protocol):
    name: str

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        ...


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310 - fixed hosts
        return resp.read()


class ArxivFetcher:
    name = "arxiv"

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        q = " OR ".join(f'all:{t}' for t in queries) or "all:machine learning"
        url = (
            "http://export.arxiv.org/api/query?"
            + urllib.parse.urlencode(
                {"search_query": q, "start": 0, "max_results": limit,
                 "sortBy": "submittedDate", "sortOrder": "descending"}
            )
        )
        try:
            root = ET.fromstring(_get(url))
        except Exception:  # noqa: BLE001 - network/parse: degrade quietly
            return []
        ns = {"a": "http://www.w3.org/2005/Atom"}
        items: list[Item] = []
        for entry in root.findall("a:entry", ns):
            title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
            url_ = (entry.findtext("a:id", default="", namespaces=ns) or "").strip()
            if title:
                items.append(Item("arxiv", url_.rsplit("/", 1)[-1], title, url_, summary))
        return items


class HackerNewsFetcher:
    name = "hackernews"

    def _search(self, term: str, hits: int) -> list[dict]:
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
            {"query": term, "tags": "story", "hitsPerPage": hits}
        )
        try:
            return json.loads(_get(url)).get("hits", [])
        except Exception:  # noqa: BLE001 - a failing term is just skipped
            return []

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        # Search each topic separately and merge - a single combined query (AND
        # semantics) matches almost nothing, which is why it used to return zero.
        terms = [q for q in queries if q][:4] or ["LLM agents"]
        merged: dict[str, Item] = {}
        for term in terms:
            for hit in self._search(term, max(3, limit)):
                title = hit.get("title") or hit.get("story_title") or ""
                oid = str(hit.get("objectID"))
                if not title or oid in merged:
                    continue
                link = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
                merged[oid] = Item("hackernews", oid, title, link,
                                   hit.get("story_text") or "", float(hit.get("points") or 0))

        # Fallback to popular AI stories if the topic searches came up empty.
        if not merged:
            for hit in self._search("LLM", max(3, limit)):
                title = hit.get("title") or ""
                oid = str(hit.get("objectID"))
                if title and oid not in merged:
                    merged[oid] = Item("hackernews", oid, title,
                                       hit.get("url") or f"https://news.ycombinator.com/item?id={oid}",
                                       hit.get("story_text") or "", float(hit.get("points") or 0))

        return sorted(merged.values(), key=lambda it: -it.score)[:limit]


class HuggingFaceFetcher:
    name = "huggingface"

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        try:
            data = json.loads(_get("https://huggingface.co/api/daily_papers"))
        except Exception:  # noqa: BLE001
            return []
        wanted = {q.lower() for q in queries}
        items: list[Item] = []
        for row in data:
            paper = row.get("paper", row)
            title = paper.get("title", "")
            summary = paper.get("summary", "")
            pid = paper.get("id", "")
            blob = (title + " " + summary).lower()
            if title and (not wanted or any(w in blob for w in wanted)):
                items.append(Item("huggingface", pid, title,
                                  f"https://huggingface.co/papers/{pid}", summary,
                                  float(paper.get("upvotes") or 0)))
            if len(items) >= limit:
                break
        return items


class MockFetcher:
    """Deterministic, offline source. Keeps the loop and tests reproducible."""

    name = "mock"

    _BANK = [
        Item("arxiv", "2406.00001", "Audit ledgers for local-first language agents",
             "https://arxiv.org/abs/2406.00001",
             "We argue local-first inference does not guarantee privacy without an "
             "append-only audit ledger for long-running agents."),
        Item("hackernews", "40000001", "Show HN: cheap model routing that measures when a "
             "small model suffices", "https://news.ycombinator.com/item?id=40000001",
             "A router that escalates to a larger model only when a deterministic check "
             "finds the cheap output inadequate.", 212.0),
        Item("arxiv", "2406.00003", "Calibration of self-modifying systems under approval gates",
             "https://arxiv.org/abs/2406.00003",
             "A study of calibration in systems that propose their own improvements under "
             "human approval gates."),
        Item("arxiv", "2406.00004", "Rethinking the conflict-resolution operator for routing "
             "agents", "https://arxiv.org/abs/2406.00004",
             "A proposal to change the scoring operator at the core of routing agents."),
        Item("huggingface", "2406.00002", "Episodic memory beats summarisation for agent "
             "continuity", "https://huggingface.co/papers/2406.00002",
             "Append-only episodic memory preserves continuity better than rolling "
             "summaries for long-running agents.", 88.0),
    ]

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        return list(self._BANK)[:limit]


def get_fetchers(*, online: bool) -> list[Fetcher]:
    if online:
        return [ArxivFetcher(), HackerNewsFetcher(), HuggingFaceFetcher()]
    return [MockFetcher()]
