"""Generic JSON-file reader for exported/manual collections."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable

SCHEMAS = {"reddit", "app_store", "google_play", "youtube", "custom"}
_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "data" / "fixtures"


def _iso_from_epoch(epoch: float | int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat()


class WebJsonAdapter:
    """Reads JSON exports (fixtures or downloaded) for any source.

    Fixture schemas:
      reddit:      list of {id, title, selftext, author, permalink|url,
                            subreddit, score, created_utc}
      app_store:   list of {id, title, content|body|text, author, rating,
                            (iso) date|updated, app_id}
      google_play: list of {review_id, content|text, userName, score, at, app_id}
      youtube:     list of {id, text_display|text, author_display_name,
                            published_at, like_count, video_id}
      custom:      list of {source, external_id, url, text, author*, timestamp*,
                            engagement*}

    Files read from ctx.config["files"] (a list of paths).
    """

    name = "web_json"

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        return self._read(_FIXTURE_DIR, ctx, fixture=True)

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        return self._read(None, ctx, fixture=False)

    def _read(self, base: Path | None, ctx: AdapterContext, fixture: bool) -> Iterator[dict[str, Any]]:
        files = ctx.config.get("files", [])
        if fixture:
            pattern = ctx.config.get("fixture_pattern") or "*.json"
            if base and base.is_dir():
                files = [str(p) for p in sorted(base.glob(pattern))]
        if not files:
            raise SourceUnavailable(
                "web_json needs 'files' (paths to JSON exports) or fixtures to exist"
            )
        for path in files:
            items = _load(path)
            schema = ctx.config.get("schema", "reddit")
            for item in items:
                try:
                    read = _SCHEMA_READERS[schema](item)
                except KeyError:
                    read = _read_reddit(item)
                yield build_record(read["source"], read["external_id"], read["url"],
                                   read["text"], author=read.get("author"),
                                   timestamp=read.get("timestamp"),
                                   engagement=read.get("engagement"))
        ctx.info(f"web_json: read {len(files)} file(s)")


def _load(path: str) -> list[dict[str, Any]]:
    data = _read_json(Path(path))
    if isinstance(data, dict):
        for key in ("data", "children", "items", "results"):
            if key in data:
                data = data[key]
                break
    if not isinstance(data, list):
        raise SourceUnavailable(f"web_json: file {path} is not a list/known wrapper")
    return data


def _read_json(path: Path):
    try:
        return __import__("json").loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SourceUnavailable(f"web_json: file not found: {path}")


def _read_reddit(item: dict[str, Any]) -> dict[str, Any]:
    title = str(item.get("title") or "").strip()
    body = str(item.get("selftext") or item.get("body") or item.get("text") or "").strip()
    text = f"{title}\n\n{body}" if title and body else title or body
    external_id = item.get("id") or item.get("name") or item.get("external_id")
    permalink = item.get("permalink")
    url = permalink if permalink else item.get("url", "")
    if permalink and not url.startswith("http"):
        url = f"https://www.reddit.com{permalink}"
    return {
        "source": "reddit_web",
        "external_id": str(external_id),
        "url": url,
        "text": text,
        "author": item.get("author"),
        "timestamp": _iso_from_epoch(item.get("created_utc")) or item.get("created"),
        "engagement": {"score": item.get("score"), "num_comments": item.get("num_comments")},
    }


def _read_app_store(item: dict[str, Any]) -> dict[str, Any]:
    app_id = item.get("app_id", "unknown")
    external_id = str(item.get("id") or item.get("review_id") or item.get("external_id"))
    text = str(item.get("content") or item.get("body") or item.get("text") or "").strip()
    title = str(item.get("title") or "").strip()
    if title:
        text = f"{title}: {text}" if text else title
    url = item.get("url") or _app_url(app_id, external_id)
    rating = item.get("rating")
    return {
        "source": "app_store",
        "external_id": f"{app_id}:{external_id}",
        "url": url,
        "text": text,
        "author": item.get("author") or item.get("userName"),
        "timestamp": item.get("date") or item.get("updated") or item.get("timestamp"),
        "engagement": {"rating": rating},
    }


def _read_google_play(item: dict[str, Any]) -> dict[str, Any]:
    app_id = item.get("app_id", "unknown")
    external_id = str(item.get("review_id") or item.get("id") or item.get("external_id"))
    text = str(item.get("content") or item.get("text") or "").strip()
    url = item.get("url") or f"https://play.google.com/store/apps/details?id={app_id}"
    return {
        "source": "google_play",
        "external_id": f"{app_id}:{external_id}",
        "url": url,
        "text": text,
        "author": item.get("userName") or item.get("author"),
        "timestamp": item.get("at") or item.get("timestamp") or item.get("date"),
        "engagement": {"rating": item.get("score"), "thumbs_up": item.get("thumbsUpCount")},
    }


def _read_youtube(item: dict[str, Any]) -> dict[str, Any]:
    video_id = item.get("video_id", "unknown")
    external_id = str(item.get("id") or item.get("comment_id") or item.get("external_id"))
    url = item.get("url") or f"https://www.youtube.com/watch?v={video_id}"
    return {
        "source": "youtube_comments",
        "external_id": f"{video_id}:{external_id}",
        "url": url,
        "text": str(item.get("text_display") or item.get("text") or "").strip(),
        "author": item.get("author_display_name") or item.get("author"),
        "timestamp": item.get("published_at") or item.get("timestamp") or item.get("date"),
        "engagement": {"like_count": item.get("like_count")},
    }


def _custom(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(item["source"]),
        "external_id": str(item.get("external_id") or item.get("id")),
        "url": item.get("url", ""),
        "text": str(item.get("text") or item.get("content") or item.get("body") or ""),
        "author": item.get("author"),
        "timestamp": item.get("timestamp"),
        "engagement": item.get("engagement") or {},
    }


def _app_url(app_id: str, external_id: str) -> str:
    return f"https://apps.apple.com/in/app/myntra/id{app_id}"


_SCHEMA_READERS = {
    "reddit": _read_reddit,
    "app_store": _read_app_store,
    "google_play": _read_google_play,
    "youtube": _read_youtube,
    "custom": _custom,
}