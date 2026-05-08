"""Source adapter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..events import Event


class Source(ABC):
    name: str = "abstract"

    @abstractmethod
    def fetch(self, limit: int) -> list[Event]:
        """Return up to `limit` events. Implementations should return [] on failure
        rather than raise, and log the error themselves."""
        raise NotImplementedError


def safe_int(value, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def truncate(text: str, maxlen: int = 600) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= maxlen:
        return text
    return text[: maxlen - 1].rstrip() + "…"
