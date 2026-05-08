"""Shared helpers for HuggingFace ModelInfo handling."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..events import Event
from .base import safe_int, truncate


def _iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def model_info_to_event(info: Any, source: str) -> Event:
    """Convert a huggingface_hub ModelInfo (or similar duck-typed object) to an Event."""
    model_id = getattr(info, "modelId", None) or getattr(info, "id", None) or ""
    author = getattr(info, "author", "") or (
        model_id.split("/", 1)[0] if "/" in model_id else ""
    )
    likes = safe_int(getattr(info, "likes", 0))
    downloads = safe_int(getattr(info, "downloads", 0))
    created_at = _iso(getattr(info, "created_at", "") or getattr(info, "createdAt", ""))
    tags = list(getattr(info, "tags", []) or [])
    pipeline_tag = getattr(info, "pipeline_tag", "") or ""

    summary_bits = []
    if pipeline_tag:
        summary_bits.append(f"pipeline: {pipeline_tag}")
    if tags:
        summary_bits.append("tags: " + ", ".join(tags[:8]))
    if downloads:
        summary_bits.append(f"downloads: {downloads:,}")

    return Event(
        source=source,
        event_id=model_id,
        title=model_id,
        url=f"https://huggingface.co/{model_id}",
        summary=truncate(" · ".join(summary_bits), 400),
        author=author,
        likes=likes,
        downloads=downloads,
        created_at=created_at,
        tags=tags,
        extra={"pipeline_tag": pipeline_tag},
    )
