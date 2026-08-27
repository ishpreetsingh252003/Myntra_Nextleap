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
        max_pages = int(ctx.config.get("max_pages", 1000))
        page_size = int(ctx.config.get("page_size", 100))
        collected = 0
        for app_id in app_ids:
            token = None
            pages = 0
            reached_window = False  # reviews are NEWEST-first; stop once older than window
            while pages < max_pages:
                try:
                    items, token = reviews(
                        app_id, sort=Sort.NEWEST, count=page_size,
                        continuation_token=token,
                    )
                except Exception as exc:  # live API may fail
                    if collected == 0:
                        raise SourceUnavailable(f"google_play fetch failed for {app_id}: {exc}") from exc
                    break
                if not items:
                    break
                for review in items:
                    ts = _iso(review.get("at"))
                    if ts is None:
                        # no date -> keep (can't filter) but only if nothing older yet
                        if reached_window:
                            continue
                    elif not ctx.in_window(ts):
                        reached_window = True
                        continue
                    collected += 1
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
                pages += 1
                if token is None:
                    break
                if reached_window:
                    break  # we've gone past the window for this app
        if collected == 0:
            raise SourceUnavailable(f"google_play: no reviews in the selected window for {app_ids}")
        ctx.info(f"google_play: collected {collected} reviews in window for {len(app_ids)} app(s)")


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.astimezone(timezone.utc).isoformat()
    return str(dt)