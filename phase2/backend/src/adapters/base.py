"""Adapter interface and shared context."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator, Protocol


@dataclass
class AdapterContext:
    """Shared per-run context passed to adapters."""

    config: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)

    def info(self, message: str) -> None:
        self.log.append(message)


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