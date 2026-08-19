"""Live YouTube comments collection via YouTube Data API v3 (free key required)."""
from __future__ import annotations

import urllib.parse
from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable

_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAdapter:
    name = "youtube_comments"

    def __init__(self) -> None:
        self._http = None

    def _client(self, ctx: AdapterContext):
        if self._http is not None:
            return self._http
        api_key = ctx.config.get("api_key")
        if not api_key:
            raise SourceUnavailable(
                "youtube_comments skipped: YOUTUBE_API_KEY not set (set in phase2/backend/.env)"
            )
        try:
            import requests
        except ImportError:
            raise SourceUnavailable("youtube_comments skipped: requests not installed")
        self._http = requests  # requests.get wrapper
        self._key = api_key
        return self._http

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        raise SourceUnavailable("youtube_comments: use web_json fixtures for offline demo")

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        import requests  # local, live-only

        api_key = ctx.config.get("api_key")
        if not api_key:
            raise SourceUnavailable("youtube_comments skipped: YOUTUBE_API_KEY not set")
        queries = ctx.config.get("queries", ["myntra haul review", "ajio clothes review"])
        max_videos = int(ctx.config.get("max_videos", 3))
        max_comments = int(ctx.config.get("max_comments", 30))
        total = 0
        for query in queries:
            video_ids = self._search(requests, api_key, query, max_videos)
            for video_id in video_ids:
                for comment in self._comments(requests, api_key, video_id, max_comments):
                    yield comment
                    total += 1
        if total == 0:
            raise SourceUnavailable("youtube_comments: no comments returned for queries")
        ctx.info(f"youtube_comments: collected {total} comments")

    def _search(self, requests, api_key: str, query: str, max_videos: int) -> list[str]:
        params = {
            "part": "snippet", "type": "video", "q": query,
            "maxResults": max_videos, "key": api_key, "safeSearch": "none",
        }
        resp = requests.get(f"{_BASE}/search", params=params, timeout=30)
        resp.raise_for_status()
        return [item["id"]["videoId"] for item in resp.json().get("items", [])]

    def _comments(self, requests, api_key: str, video_id: str, max_comments: int) -> Iterator[dict[str, Any]]:
        params = {
            "part": "snippet", "videoId": video_id,
            "maxResults": max_comments, "key": api_key,
        }
        resp = requests.get(f"{_BASE}/commentThreads", params=params, timeout=30)
        if resp.status_code != 200:
            return
        for item in resp.json().get("items", []):
            snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
            comment_id = item.get("id") or snippet.get("id")
            text = snippet.get("textDisplay", "")
            if not text.strip():
                continue
            yield build_record(
                source="youtube_comments",
                source_external_id=f"{video_id}:{comment_id}",
                url=f"https://www.youtube.com/watch?v={video_id}",
                text=urllib.parse.unquote(text),
                author=snippet.get("authorDisplayName"),
                timestamp=snippet.get("publishedAt"),
                engagement={"like_count": snippet.get("likeCount")},
            )