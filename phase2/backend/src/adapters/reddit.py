"""Live Reddit collection via PRAW (official API). Requires credentials in .env."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator

from ..raw import build_record
from .base import AdapterContext, SourceUnavailable


class RedditAdapter:
    name = "reddit"

    def __init__(self) -> None:
        self._reddit = None

    def _client(self, ctx: AdapterContext):
        if self._reddit is not None:
            return self._reddit
        client_id = ctx.config.get("reddit_client_id")
        client_secret = ctx.config.get("reddit_client_secret")
        user_agent = ctx.config.get("reddit_user_agent", "MyntraDiscoveryEngine/0.1")
        if not client_id or not client_secret:
            raise SourceUnavailable(
                "reddit skipped: REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET not set (set in phase2/backend/.env)"
            )
        try:
            import praw
        except ImportError:
            raise SourceUnavailable("reddit skipped: praw is not installed")
        self._reddit = praw.Reddit(
            client_id=client_id, client_secret=client_secret,
            user_agent=user_agent, check_for_async=False,
        )
        return self._reddit

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        # Live source. For offline demos use the web_json adapter on reddit fixtures.
        raise SourceUnavailable("reddit: use web_json fixtures for offline demo")

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        reddit = self._client(ctx)
        keywords = ctx.config.get("keywords", ["myntra", "wishlist"])
        subreddits = ctx.config.get("subreddits", [])
        limit = int(ctx.config.get("limit", 100))
        collected = 0
        try:
            for sub_name in subreddits or [""]:
                query = " OR ".join(keywords)
                submission_calls = (
                    reddit.subreddit(sub_name).search(query, sort="top", limit=limit)
                    if sub_name else reddit.subreddit("all").search(query, sort="top", limit=limit)
                )
                for submission in submission_calls:
                    text = submission.title
                    if submission.selftext:
                        text = f"{submission.title}\n\n{submission.selftext}"
                    yield build_record(
                        source="reddit",
                        source_external_id=str(submission.id),
                        url=f"https://www.reddit.com{submission.permalink}",
                        text=text,
                        author=submission.author.name if submission.author else None,
                        timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
                        engagement={"score": submission.score, "num_comments": submission.num_comments},
                    )
                    collected += 1
        except Exception as exc:  # pragma: no cover - depends on live API behavior
            raise SourceUnavailable(f"reddit live fetch failed: {exc}") from exc
        if collected == 0:
            raise SourceUnavailable("reddit live fetch returned nothing")
        ctx.info(f"reddit: collected {collected} submissions")