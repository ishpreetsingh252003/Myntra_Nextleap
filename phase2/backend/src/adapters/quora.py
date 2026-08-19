"""Live Quora collection — best-effort HTML search scrape.

CAUTION: Quora does not provide a public API and its HTML requires login for full
content. This adapter is best-effort: it tries the public search page and parses
question titles + answer snippets. If it gets nothing (or the site blocks bots),
it raises SourceUnavailable and the run report records the skip.
Recommended path: export Quora pages as JSON/HTML yourself and ingest via
web_json (custom schema) — same for forums and blogs.
"""
from __future__ import annotations

from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable


class QuoraAdapter:
    name = "quora"

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        raise SourceUnavailable("quora: use web_json fixtures for offline demo")

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        from .base import harden_socket

        try:
            import requests
        except ImportError:
            raise SourceUnavailable("quora skipped: requests not installed")
        harden_socket()

        queries = ctx.config.get("queries", ["shopping from myntra sizing", "wishlist vs buying clothes"])
        headers = {"User-Agent": "Mozilla/5.0 (compatible; DiscoveryEngine/0.1)"}
        total = 0
        for query in queries:
            try:
                resp = requests.get(
                    "https://www.quora.com/search",
                    params={"q": query}, headers=headers, timeout=20,
                )
                if resp.status_code != 200:
                    ctx.info(f"quora: HTTP {resp.status_code} for query {query!r}")
                    continue
                for item in self._parse(resp.text, query):
                    yield item
                    total += 1
            except Exception as exc:
                ctx.info(f"quora: query {query!r} failed: {exc}")
        if total == 0:
            raise SourceUnavailable(
                "quora: no content parsed (login wall/blocked). Export pages and use web_json instead"
            )
        ctx.info(f"quora: collected {total} items")

    def _parse(self, html: str, query: str) -> Iterator[dict[str, Any]]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise SourceUnavailable("quora skipped: beautifulsoup4 not installed")
        soup = BeautifulSoup(html, "html.parser")
        seen = 0
        for block in soup.select("a.q-box"):
            text = block.get_text(" ", strip=True)
            link = block.get("href", "")
            if not text or len(text) < 10 or link == "#":
                continue
            if not any(k in text.casefold() for k in ("wishlist", "buy", "size", "fit", "return", "quality", "price", "dress", "cloth", "deliver")):
                continue
            href = link if link.startswith("http") else f"https://www.quora.com{link}"
            yield build_record(
                source="quora",
                source_external_id=f"{query}:{seen}",
                url=href,
                text=text,
                author=None,
                timestamp=None,
                engagement={"query": query},
            )
            seen += 1