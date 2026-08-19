"""Live Apple App Store review collection via app-store-scraper."""
from __future__ import annotations

from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable


class AppStoreAdapter:
    name = "app_store"

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        raise SourceUnavailable("app_store: use web_json fixtures for offline demo")

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        from .base import harden_socket

        app_ids = ctx.config.get("app_ids", [])
        if not app_ids:
            raise SourceUnavailable("app_store skipped: no app_ids configured")
        try:
            from app_store_scraper import AppStore
        except ImportError:
            raise SourceUnavailable("app_store skipped: app-store-scraper not installed")
        harden_socket()
        for app_id in app_ids:
            app = AppStore(
                country=ctx.config.get("country", "in"),
                app_name=ctx.config.get("app_name", "myntra"),
                app_id=app_id,
            )
            try:
                app.review(how_many=int(ctx.config.get("how_many", 50)))
            except Exception as exc:  # live API may fail
                raise SourceUnavailable(f"app_store fetch failed for {app_id}: {exc}") from exc
            if not app.reviews:
                raise SourceUnavailable(
                    f"app_store: 0 reviews returned for {app_id} (endpoint region-blocked or changed)"
                )
            for review in app.reviews:
                ts = review.get("date").isoformat() if review.get("date") else None
                if not ctx.in_window(ts):
                    continue
                yield build_record(
                    source="app_store",
                    source_external_id=f"{app_id}:{review.get('id')}",
                    url=f"https://apps.apple.com/in/app/id{app.id}",
                    text=_review_text(review),
                    author=review.get("userName"),
                    timestamp=ts,
                    engagement={"rating": review.get("rating"), "title": review.get("title")},
                )
        ctx.info(f"app_store: collected reviews for {len(app_ids)} app(s)")


def _review_text(review: dict[str, Any]) -> str:
    title = str(review.get("title") or "").strip()
    body = str(review.get("review") or "").strip()
    if title and body:
        return f"{title}: {body}"
    return title or body