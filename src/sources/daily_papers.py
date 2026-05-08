"""HuggingFace Daily Papers — fetched from the public papers API.

Endpoint: https://huggingface.co/api/daily_papers
Returns a list of recently curated papers with metadata (title, summary, upvotes,
arxiv id, authors). Schema is community-known; we tolerate unexpected shapes.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from ..events import Event, SOURCE_DAILY_PAPERS
from .base import Source, safe_int, truncate

logger = logging.getLogger(__name__)

API_URL = "https://huggingface.co/api/daily_papers"
USER_AGENT = "HFSonar/0.1 (https://github.com/local/hfsonar)"


def _extract_paper(record: dict[str, Any]) -> dict[str, Any]:
    """Daily Papers wraps the paper inside the record. Tolerate both shapes."""
    return record.get("paper") if isinstance(record.get("paper"), dict) else record


def _record_to_event(record: dict[str, Any]) -> Event | None:
    paper = _extract_paper(record)
    arxiv_id = (paper.get("id") or paper.get("arxivId") or "").strip()
    if not arxiv_id:
        return None
    title = (paper.get("title") or "").strip()
    summary = (paper.get("summary") or paper.get("abstract") or "").strip()
    upvotes = safe_int(paper.get("upvotes") or record.get("numUpvotes"))
    published_at = (
        record.get("publishedAt")
        or paper.get("publishedAt")
        or paper.get("submittedOnDailyAt")
        or ""
    )
    authors_raw = paper.get("authors") or []
    authors: list[str] = []
    for a in authors_raw:
        if isinstance(a, dict):
            name = a.get("name") or a.get("fullname")
            if name:
                authors.append(name)
        elif isinstance(a, str):
            authors.append(a)

    summary_bits = []
    if upvotes:
        summary_bits.append(f"upvotes: {upvotes}")
    if authors:
        summary_bits.append("by " + ", ".join(authors[:4]))
    if summary:
        summary_bits.append(truncate(summary, 480))

    return Event(
        source=SOURCE_DAILY_PAPERS,
        event_id=arxiv_id,
        title=title or arxiv_id,
        url=f"https://huggingface.co/papers/{arxiv_id}",
        summary=" · ".join(summary_bits),
        author=", ".join(authors[:3]),
        likes=upvotes,
        downloads=0,
        created_at=str(published_at),
        tags=[],
        extra={"arxiv_id": arxiv_id, "abstract_url": f"https://arxiv.org/abs/{arxiv_id}"},
    )


class DailyPapers(Source):
    name = SOURCE_DAILY_PAPERS

    def __init__(self, url: str = API_URL, timeout: float = 15.0) -> None:
        self.url = url
        self.timeout = timeout

    def fetch(self, limit: int) -> list[Event]:
        try:
            resp = requests.get(
                self.url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("daily_papers fetch failed: %s", e)
            return []

        if not isinstance(data, list):
            logger.warning("daily_papers returned non-list: %s", type(data).__name__)
            return []

        events: list[Event] = []
        for record in data[:limit]:
            if not isinstance(record, dict):
                continue
            evt = _record_to_event(record)
            if evt:
                events.append(evt)
        return events
