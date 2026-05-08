"""Normalized event shape produced by every HF source adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


SOURCE_TRENDING = "trending_models"
SOURCE_NEW_MODELS = "new_models"
SOURCE_DAILY_PAPERS = "daily_papers"
SOURCE_WATCHLIST = "watchlist"

ALL_SOURCES = (
    SOURCE_TRENDING,
    SOURCE_NEW_MODELS,
    SOURCE_DAILY_PAPERS,
    SOURCE_WATCHLIST,
)


@dataclass
class Event:
    source: str
    event_id: str
    title: str
    url: str
    summary: str = ""
    author: str = ""
    likes: int = 0
    downloads: int = 0
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    fetched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def dedup_key(self) -> str:
        return f"{self.source}::{self.event_id}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        clean = {k: v for k, v in data.items() if k in known}
        return cls(**clean)
