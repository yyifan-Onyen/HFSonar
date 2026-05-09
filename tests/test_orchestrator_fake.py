"""End-to-end smoke test using FakeOperator + a stub source set.

Exercises: candidate filtering, prompt rendering for all 3 stages, curator JSON
parsing, research JSON parsing, outreach draft loop, output frontmatter,
manifest, ledger persistence.

Does NOT touch the network or the claude CLI.
"""

from __future__ import annotations

import json
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
def stub_repo(tmp_path: Path):
    src_root = Path(__file__).resolve().parents[1]
    (tmp_path / "src" / "prompts").mkdir(parents=True)
    for name in ("01_curate.md", "02_research_author.md", "03_draft_outreach.md"):
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

    monkeypatch.setattr(
        orchestrator,
        "build_sources",
        lambda c: [(StubSource("stub", _events()), 50)],
    )

    run_dir = run_cycle(repo_root=stub_repo, cfg=cfg, operator=operator, ledger=ledger)

    assert run_dir.exists()

    # 3 outreach drafts in runs/<ts>/outreach/
    drafts = sorted((run_dir / "outreach").glob("*.md"))
    assert len(drafts) == 3, f"expected 3 outreach drafts, got {len(drafts)}"

    # 3-stage prompts saved per item: 1 curate + (3 research + 3 outreach) = 7
    prompts = sorted((run_dir / "prompts").glob("*.md"))
    assert len(prompts) == 7, f"expected 7 prompt files, got {len(prompts)}"

    # First draft must have JSON frontmatter the runner wrote (not LLM-emitted).
    body = drafts[0].read_text(encoding="utf-8")
    assert body.startswith("---\n")
    fm_end = body.index("\n---\n", 4)
    fm_json = body[4:fm_end]
    fm = json.loads(fm_json)
    for key in ("source", "event_id", "event_url", "primary_author", "coauthors", "generated_at"):
        assert key in fm, f"missing frontmatter key: {key}"

    # Manifest sanity
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert "candidates" in manifest
    assert "outreach" in manifest
    assert len(manifest["outreach"]) == 3

    # Ledger should now contain the 3 keys.
    assert len(ledger) == 3

    # Second cycle on the same data should produce 0 drafts (all deduped).
    run_dir2 = run_cycle(repo_root=stub_repo, cfg=cfg, operator=operator, ledger=ledger)
    drafts2 = (
        list((run_dir2 / "outreach").glob("*.md")) if (run_dir2 / "outreach").exists() else []
    )
    assert drafts2 == []
