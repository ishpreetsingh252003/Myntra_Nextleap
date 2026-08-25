"""Load phase5 config (segmentation.yaml) + .env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BACKEND_DIR / "config" / "segmentation.yaml"
ENV_FILE = BACKEND_DIR / ".env"


def _load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def load_config() -> dict[str, Any]:
    _load_dotenv()
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"missing config: {CONFIG_PATH}")
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
