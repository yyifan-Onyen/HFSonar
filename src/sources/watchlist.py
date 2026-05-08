"""Watchlist: monitor specific orgs/users for new releases."""

from __future__ import annotations

import logging
from typing import Iterable

from ..events import Event, SOURCE_WATCHLIST
from ._hf_common import model_info_to_event
from .base import Source

logger = logging.getLogger(__name__)


class Watchlist(Source):
    name = SOURCE_WATCHLIST

    def __init__(self, orgs: Iterable[str]) -> None:
        self.orgs = list(orgs)

    def fetch(self, limit: int) -> list[Event]:
        """`limit` here is interpreted as a per-org budget (each watched org returns
        up to `limit` newest models). With ~10 orgs and limit=3 you get ~30 events."""
        try:
            from huggingface_hub import HfApi
        except ImportError as e:
            logger.error("huggingface_hub not installed: %s", e)
            return []

        api = HfApi()
        per_org = max(1, limit)
        events: list[Event] = []
        for org in self.orgs:
            try:
                results = list(
                    api.list_models(author=org, sort="createdAt", limit=per_org)
                )
            except Exception as e:
                logger.warning("watchlist fetch failed for org=%s: %s", org, e)
                continue
            for info in results:
                evt = model_info_to_event(info, SOURCE_WATCHLIST)
                evt.extra["watched_org"] = org
                events.append(evt)
        return events
