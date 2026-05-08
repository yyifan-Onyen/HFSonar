"""Newly created HuggingFace models — sorted by createdAt desc."""

from __future__ import annotations

import logging

from ..events import Event, SOURCE_NEW_MODELS
from ._hf_common import model_info_to_event
from .base import Source

logger = logging.getLogger(__name__)


class NewModels(Source):
    name = SOURCE_NEW_MODELS

    def fetch(self, limit: int) -> list[Event]:
        try:
            from huggingface_hub import HfApi
        except ImportError as e:
            logger.error("huggingface_hub not installed: %s", e)
            return []

        api = HfApi()
        try:
            # Hub 1.x sorts descending implicitly, so newest models come first.
            results = list(api.list_models(sort="createdAt", limit=limit))
        except Exception as e:
            logger.warning("list_models createdAt failed: %s", e)
            return []
        return [model_info_to_event(info, SOURCE_NEW_MODELS) for info in results]
