"""End-to-end smoke test using FakeOperator + a stub source set.

Exercises: candidate filtering, prompt rendering, curator JSON parsing,
write loop, post file frontmatter, manifest, ledger persistence.

Does NOT touch the network or the claude CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from src import orchestrator
from src.events import Event, SOURCE_DAILY_PAPERS, SOURCE_TRENDING, SOURCE_WATCHLIST
from src.ledger import Ledger
from src.operator import FakeOperator
from src.orchestrator import Config, run_cycle
from src.sources.base import Source


class StubSource(Source):
    def __init__(self, name: str, events: Sequence[Event]):
        self.name = name
        self._events = list(events)

    def fetch(self, limit: int):
        return list(self._events[:limit])


@pytest.fixture
def stub_repo(tmp_path: Path, monkeypatch):
    # Copy the prompts into the tmp repo so orchestrator can read them by relative path.
    src_root = Path(__file__).resolve().parents[1]
    (tmp_path / "src" / "prompts").mkdir(parents=True)
    for name in ("01_curate.md", "02_write_post.md"):
        (tmp_path / "src" / "prompts" / name).write_text(
            (src_root / "src" / "prompts" / name).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return tmp_path


def _events():
    return [
        Event(
            source=SOURCE_TRENDING,
            event_id="meta-llama/Llama-3-8B",
            title="meta-llama/Llama-3-8B",
            url="https://huggingface.co/meta-llama/Llama-3-8B",
            author="meta-llama",
            likes=2000,
            summary="pipeline: text-generation · downloads: 1,000,000",
        ),
        Event(
            source=SOURCE_TRENDING,
            event_id="some-user/boring-finetune",
            title="some-user/boring-finetune",
            url="https://huggingface.co/some-user/boring-finetune",
            likes=2,  # below min_likes; should be filtered
        ),
        Event(
            source=SOURCE_DAILY_PAPERS,
            event_id="2402.99999",
            title="A Paper",
            url="https://huggingface.co/papers/2402.99999",
            summary="upvotes: 50 · placeholder abstract",
            likes=50,
        ),
        Event(
            source=SOURCE_WATCHLIST,
            event_id="Qwen/Qwen3-Next-7B",
            title="Qwen/Qwen3-Next-7B",
            url="https://huggingface.co/Qwen/Qwen3-Next-7B",
            author="Qwen",
            likes=0,  # watchlist bypasses min_likes
        ),
    ]


def test_run_cycle_end_to_end(stub_repo: Path, monkeypatch):
    cfg = Config(top_k=3, min_likes=5)
    operator = FakeOperator()
    ledger = Ledger(stub_repo / "state" / "ledger.jsonl")

    # Patch build_sources to return our stubs.
    monkeypatch.setattr(
        orchestrator,
        "build_sources",
        lambda c: [(StubSource("stub", _events()), 50)],
    )

    run_dir = run_cycle(repo_root=stub_repo, cfg=cfg, operator=operator, ledger=ledger)

    assert run_dir.exists()
    posts = sorted((run_dir / "posts").glob("*.md"))
    assert len(posts) == 3, f"expected 3 posts, got {len(posts)}"

    # First post should have a frontmatter block with required keys.
    body = posts[0].read_text(encoding="utf-8")
    assert body.startswith("---\n")
    for key in ("source:", "event_id:", "url:", "generated_at:", "angle:"):
        assert key in body

    # Manifest sanity
    manifest = (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    assert "candidates" in manifest
    assert "posts" in manifest

    # Ledger should now contain the 3 posted keys.
    assert len(ledger) == 3

    # Second cycle on the same data should produce 0 posts (all deduped).
    run_dir2 = run_cycle(repo_root=stub_repo, cfg=cfg, operator=operator, ledger=ledger)
    posts2 = list((run_dir2 / "posts").glob("*.md")) if (run_dir2 / "posts").exists() else []
    assert posts2 == []
