"""Adapters that emit raw conversation records (architecture plan 2.2)."""
from __future__ import annotations

from .base import Adapter, AdapterContext

_LIVE_MODULES = {
    "reddit": ("reddit", "RedditAdapter"),
    "google_play": ("google_play", "GooglePlayAdapter"),
    "app_store": ("app_store", "AppStoreAdapter"),
    "youtube_comments": ("youtube", "YouTubeAdapter"),
    "quora": ("quora", "QuoraAdapter"),
}

_STATIC = {
    "web_json": ("web_json", "WebJsonAdapter"),
    "csv_import": ("csv_import", "CsvImportAdapter"),
}


def get_adapter(name: str) -> Adapter:
    """Instantiate an adapter by name. Live adapters are imported lazily
    so the offline pipeline (and tests) never depend on them."""
    if name in _STATIC:
        module_name, class_name = _STATIC[name]
        cls = getattr(__import__(f"{__name__}.{module_name}", fromlist=[class_name]), class_name)
        return cls()
    if name in _LIVE_MODULES:
        module_name, class_name = _LIVE_MODULES[name]
        cls = getattr(__import__(f"{__name__}.{module_name}", fromlist=[class_name]), class_name)
        return cls()
    raise KeyError(f"unknown adapter: {name}")