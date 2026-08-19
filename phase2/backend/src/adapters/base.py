"""Adapter interface and shared context."""
from __future__ import annotations

import socket
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterator, Protocol

NETWORK_TIMEOUT = 20


def harden_socket() -> None:
    """Belt-and-braces: give every socket a timeout so a hung host can't block a run."""
    socket.setdefaulttimeout(NETWORK_TIMEOUT)


@dataclass
class AdapterContext:
    """Shared per-run context passed to adapters."""

    config: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def info(self, message: str) -> None:
        self.log.append(message)

    # ---- date-window helpers ------------------------------------------
    def in_window(self, ts: str | None) -> bool:
        """True if ts (ISO) falls inside config from_date/to_date (client-side pre-filter)."""
        if not ts:
            return True
        frm = self.config.get("from_date")
        to = self.config.get("to_date")
        if frm is None and to is None:
            return True
        try:
            d = date.fromisoformat(ts[:10])
        except ValueError:
            return True
        if frm and d < date.fromisoformat(str(frm)[:10]):
            return False
        if to and d > date.fromisoformat(str(to)[:10]):
            return False
        return True

    def count_budget(self, default: int = 200) -> int:
        return int(self.config.get("count", default))


class Adapter(Protocol):
    """An adapter yields normalized raw records (pre-hash, id assigned later)."""

    name: str

    def from_fixtures(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        """Offline mode: read bundled sample files instead of the live source.
        Yields records with source already set. Used for demos/tests."""
        raise NotImplementedError

    def run(self, ctx: AdapterContext) -> Iterator[dict[str, Any]]:
        """Live collection mode. May raise SourceUnavailable if it cannot run."""
        raise NotImplementedError


class SourceUnavailable(RuntimeError):
    """Raised when a source cannot be collected (no creds, blocked, rate limited)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message