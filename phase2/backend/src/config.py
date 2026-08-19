"""Load collection.yaml + .env into per-adapter configs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BACKEND_DIR / "config" / "collection.yaml"
ENV_FILE = BACKEND_DIR / ".env"


@dataclass
class CollectionPlan:
    adapter_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    targets: dict[str, int] = field(default_factory=dict)
    global_config: dict[str, Any] = field(default_factory=dict)


def _load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_plan() -> CollectionPlan:
    """Build adapter calls from collection.yaml for the enabled live sources."""
    _load_dotenv()
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"missing config: {CONFIG_PATH}")
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    settings = cfg.get("settings", {})

    calls: list[tuple[str, dict[str, Any]]] = []
    for source in cfg.get("enabled_sources", []):
        base = {"use_fixtures": False}
        if source == "google_play":
            base["app_ids"] = cfg.get("google_play_app_ids", [])
            base["count"] = settings.get("count", 200)
        elif source == "app_store":
            app_store = cfg.get("app_store", {})
            base["app_ids"] = cfg.get("app_store_app_ids", [])
            base["country"] = os.environ.get("APP_STORE_COUNTRY", "in")
            base["app_name"] = app_store.get("app_name", "myntra")
            base["how_many"] = settings.get("how_many", 50)
        elif source == "reddit":
            reddit = cfg.get("reddit", {})
            base.update(
                subreddits=reddit.get("subreddits", []),
                keywords=reddit.get("keywords", []),
                limit=settings.get("reddit_limit", 100),
                reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
                reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
                reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", "MyntraDiscoveryEngine/0.1"),
            )
        elif source == "youtube_comments":
            yt = cfg.get("youtube_comments", {})
            base.update(
                api_key=os.environ.get("YOUTUBE_API_KEY", ""),
                queries=yt.get("queries", []),
                max_videos=yt.get("max_videos", 3),
                max_comments=yt.get("max_comments", 30),
            )
        elif source == "quora":
            base["queries"] = cfg.get("quora", {}).get("queries", [])
        calls.append((source.replace("reddit_web", "web_json"), base))

    plan = CollectionPlan(adapter_calls=calls, targets=cfg.get("targets", {}), global_config=cfg)
    return plan