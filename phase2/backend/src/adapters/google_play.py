"""Live Google Play Store review collection via google-play-scraper."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable


class GooglePlayAdapter:
    name = "google_play"

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        raise SourceUnavailable("google_play: use web_json fixtures for offline demo")

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        from .base import harden_socket

        app_ids = ctx.config.get("app_ids", [])
        if not app_ids:
            raise SourceUnavailable("google_play skipped: no app_ids configured")
        try:
            from google_play_scraper import Sort, reviews
        except ImportError:
            raise SourceUnavailable("google_play skipped: google-play-scraper not installed")
        harden_socket()
        budget = ctx.count_budget(default=200)
        for app_id in app_ids:
            try:
                items, _continuation = reviews(
                    app_id, sort=Sort.NEWEST, count=budget
                )
            except Exception as exc:  # live API may fail for various reasons
                raise SourceUnavailable(f"google_play fetch failed for {app_id}: {exc}") from exc
            if not items:
                raise SourceUnavailable(f"google_play: 0 reviews returned for {app_id}")
            for review in items:
                ts = _iso(review.get("at"))
                if not ctx.in_window(ts):
                    continue
                yield build_record(
                    source="google_play",
                    source_external_id=f"{app_id}:{review.get('reviewId')}",
                    url=f"https://play.google.com/store/apps/details?id={app_id}",
                    text=review.get("content") or "",
                    author=review.get("userName"),
                    timestamp=ts,
                    engagement={
                        "rating": review.get("score"),
                        "thumbs_up": review.get("thumbsUpCount"),
                        "reply_content": review.get("replyContent"),
                        "reply_date": _iso(review.get("repliedAt")),
                    },
                )
        ctx.info(f"google_play: collected reviews for {len(app_ids)} app(s)")


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)