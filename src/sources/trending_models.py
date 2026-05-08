"""Trending HuggingFace models — sorted by recent likes."""

from __future__ import annotations

import logging

from ..events import Event, SOURCE_TRENDING
from ._hf_common import model_info_to_event
from .base import Source

logger = logging.getLogger(__name__)


class TrendingModels(Source):
    name = SOURCE_TRENDING

    def __init__(self, sort: str = "trendingScore") -> None:
        self.sort = sort

    def fetch(self, limit: int) -> list[Event]:
        try:
            from huggingface_hub import HfApi
        except ImportError as e:
            logger.error("huggingface_hub not installed: %s", e)
            return []

        api = HfApi()
        events: list[Event] = []
        # Hub 1.x sorts descending implicitly; older versions accepted "likes7d".
        # Try preferred keys in order and stop at the first that returns results.
        for sort_key in (self.sort, "likes", "downloads"):
            try:
                results = list(api.list_models(sort=sort_key, limit=limit))
            except Exception as e:
                logger.warning("list_models sort=%s failed: %s", sort_key, e)
                continue
            for info in results:
                events.append(model_info_to_event(info, SOURCE_TRENDING))
            if events:
                break
        return events
