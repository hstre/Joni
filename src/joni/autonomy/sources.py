"""Where Joni looks - arXiv, Hacker News, Hugging Face.

Each source is a small, polite reader over a public API (no key, modest limits,
short timeouts, failures swallowed so a hiccup never breaks a run). Everything is
behind a ``Fetcher`` interface so the default offline path - a deterministic
``MockFetcher`` - keeps the loop and the tests fully reproducible with no network.

SSRN is reached two ways: directly, by dropping its PDF download links in the ``pdf_urls``
queue (see ``reader.py``), and indirectly through ``OpenAlexFetcher`` below, which indexes
SSRN working papers. Zenodo has a clean public API and is a first-class fetcher.
"""

from __future__ import annotations

import json
import re
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


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, **(headers or {})})
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


class GitHubFetcher:
    name = "github"

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        import os
        headers = {"Accept": "application/vnd.github+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        terms = [q for q in queries if q][:4] or ["agent"]
        merged: dict[str, Item] = {}
        for term in terms:
            url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
                {"q": f"{term} in:name,description", "sort": "stars", "order": "desc",
                 "per_page": max(2, limit // 2)})
            try:
                data = json.loads(_get(url, headers))
            except Exception:  # noqa: BLE001 - rate limit / network: degrade quietly
                continue
            for repo in data.get("items", []):
                full = repo.get("full_name", "")
                if not full or full in merged:
                    continue
                merged[full] = Item(
                    "github", full, repo.get("name", full),
                    repo.get("html_url", f"https://github.com/{full}"),
                    repo.get("description") or "", float(repo.get("stargazers_count") or 0))
        return sorted(merged.values(), key=lambda it: -it.score)[:limit]


class ZenodoFetcher:
    """Zenodo - the open research repository (papers, datasets, software). Clean public API,
    no key. Covers a lot of material that never reaches arXiv."""

    name = "zenodo"

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        terms = [q for q in queries if q][:4] or ["machine learning"]
        merged: dict[str, Item] = {}
        for term in terms:
            url = "https://zenodo.org/api/records?" + urllib.parse.urlencode(
                {"q": term, "size": max(2, limit // 2), "sort": "mostrecent"})
            try:
                hits = json.loads(_get(url)).get("hits", {}).get("hits", [])
            except Exception:  # noqa: BLE001 - a failing term is just skipped
                continue
            for rec in hits:
                rid = str(rec.get("id") or "")
                meta = rec.get("metadata", {})
                title = (meta.get("title") or "").strip()
                if not title or rid in merged:
                    continue
                link = (rec.get("links", {}).get("self_html") or meta.get("doi_url")
                        or f"https://zenodo.org/records/{rid}")
                summary = re.sub(r"<[^>]+>", " ", meta.get("description") or "")[:500]
                merged[rid] = Item("zenodo", rid, title, link, summary.strip())
        return list(merged.values())[:limit]


def _openalex_abstract(inv: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]} - rebuild the text."""
    if not isinstance(inv, dict):
        return ""
    pos: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs if isinstance(idxs, list) else []:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))[:500]


class OpenAlexFetcher:
    """OpenAlex - a large open scholarly index (a CrossRef/MAG successor). No key. It indexes
    many venues arXiv misses, **including SSRN working papers**, so it is how Joni keeps SSRN
    in view without a fragile scraper. A ``mailto`` is sent to use the polite pool."""

    name = "openalex"

    def fetch(self, queries: list[str], *, limit: int) -> list[Item]:
        terms = [q for q in queries if q][:4] or ["machine learning"]
        merged: dict[str, Item] = {}
        mailto = "joni-autonomy@users.noreply.github.com"   # OpenAlex polite-pool identifier
        for term in terms:
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
                {"search": term, "per_page": max(2, limit // 2),
                 "sort": "publication_date:desc", "mailto": mailto})
            try:
                results = json.loads(_get(url)).get("results", [])
            except Exception:  # noqa: BLE001
                continue
            for work in results:
                wid = str(work.get("id") or "").rsplit("/", 1)[-1]
                title = (work.get("title") or work.get("display_name") or "").strip()
                if not title or wid in merged:
                    continue
                loc = work.get("primary_location") or {}
                link = (loc.get("landing_page_url") or work.get("doi")
                        or f"https://openalex.org/{wid}")
                summary = _openalex_abstract(work.get("abstract_inverted_index"))
                merged[wid] = Item("openalex", wid, title, link, summary,
                                   float(work.get("cited_by_count") or 0))
        return sorted(merged.values(), key=lambda it: -it.score)[:limit]


def get_fetchers(*, online: bool) -> list[Fetcher]:
    if online:
        return [ArxivFetcher(), HackerNewsFetcher(), HuggingFaceFetcher(), GitHubFetcher(),
                ZenodoFetcher(), OpenAlexFetcher()]
    return [MockFetcher()]
