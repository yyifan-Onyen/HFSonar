"""End-to-end pipeline: fetch → dedup → curate (Claude) → write (Claude) → save.

A run produces:
    runs/<UTC-ts>/
        prompts/01_curate.prompt.md
        prompts/02_write_<n>.prompt.md
        posts/<n>__<source>__<safe_id>.md      (final draft posts, with frontmatter)
        run_manifest.json                      (full event/curation record)
"""

from __future__ import annotations

import json
import logging
import re
import sys
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .events import Event
from .ledger import Ledger
from .operator import ClaudeOperator, FakeOperator, Operator, OperatorResult
from .sources.base import Source
from .sources.daily_papers import DailyPapers
from .sources.new_models import NewModels
from .sources.trending_models import TrendingModels
from .sources.watchlist import Watchlist


logger = logging.getLogger(__name__)


# ---------- config ----------


@dataclass
class Config:
    trending_limit: int = 20
    new_models_limit: int = 30
    daily_papers_limit: int = 15
    watchlist_limit: int = 3  # PER ORG
    top_k: int = 5
    min_likes: int = 5
    watchlist_orgs: list[str] = field(default_factory=list)
    claude_binary: str = "claude"
    claude_timeout: float = 180.0
    claude_model: str = ""

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        poll = data.get("poll", {})
        cur = data.get("curation", {})
        watch = data.get("watchlist", {})
        cl = data.get("claude", {})
        return cls(
            trending_limit=poll.get("trending_limit", 20),
            new_models_limit=poll.get("new_models_limit", 30),
            daily_papers_limit=poll.get("daily_papers_limit", 15),
            watchlist_limit=poll.get("watchlist_limit", 3),
            top_k=cur.get("top_k", 5),
            min_likes=cur.get("min_likes", 5),
            watchlist_orgs=list(watch.get("orgs", [])),
            claude_binary=cl.get("binary", "claude"),
            claude_timeout=float(cl.get("timeout", 180.0)),
            claude_model=cl.get("model", ""),
        )


# ---------- pipeline ----------


def _utc_run_id() -> str:
    # Microsecond precision so back-to-back cycles don't collide on the same dir.
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _safe_filename(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("._-")
    return s[:maxlen] or "unnamed"


def _candidate_block(events: list[Event]) -> str:
    lines = []
    for e in events:
        lines.append(f"- id: {e.dedup_key}")
        lines.append(f"  source: {e.source}")
        lines.append(f"  title: {e.title}")
        lines.append(f"  url: {e.url}")
        if e.author:
            lines.append(f"  author: {e.author}")
        if e.likes:
            lines.append(f"  likes: {e.likes}")
        if e.created_at:
            lines.append(f"  created_at: {e.created_at}")
        if e.summary:
            lines.append(f"  summary: {e.summary}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _render(template: str, vars: dict[str, str]) -> str:
    out = template
    for k, v in vars.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def _parse_curator_output(text: str) -> list[dict]:
    """The curator should reply with a JSON object {"chosen": [...]}.
    Be liberal in what we accept: strip code fences, find the first {...} block."""
    if not text:
        return []
    s = text.strip()
    if s.startswith("```"):
        # strip ```json ... ```
        s = re.sub(r"^```[a-zA-Z]*\n", "", s)
        s = re.sub(r"\n```$", "", s)
    # find the first {...}
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("curator output was not valid JSON; got: %s", s[:200])
        return []
    chosen = payload.get("chosen") or []
    return [c for c in chosen if isinstance(c, dict)]


# ---------- the run ----------


def build_sources(cfg: Config) -> list[tuple[Source, int]]:
    return [
        (TrendingModels(), cfg.trending_limit),
        (NewModels(), cfg.new_models_limit),
        (DailyPapers(), cfg.daily_papers_limit),
        (Watchlist(cfg.watchlist_orgs), cfg.watchlist_limit),
    ]


def fetch_all(sources: Iterable[tuple[Source, int]]) -> list[Event]:
    events: list[Event] = []
    for source, limit in sources:
        try:
            batch = source.fetch(limit)
        except Exception as e:
            logger.warning("source %s raised: %s", source.name, e)
            batch = []
        logger.info("source %s returned %d events", source.name, len(batch))
        events.extend(batch)
    return events


def filter_candidates(
    events: list[Event],
    ledger: Ledger,
    *,
    min_likes: int,
) -> list[Event]:
    seen_keys: set[str] = set()
    kept: list[Event] = []
    for e in events:
        if e.dedup_key in seen_keys:
            continue  # within-cycle dup across sources
        seen_keys.add(e.dedup_key)
        if ledger.has(e.dedup_key):
            continue
        # Watchlist and Daily Papers are always considered, regardless of like floor.
        if e.source in ("watchlist", "daily_papers"):
            kept.append(e)
            continue
        if e.likes >= min_likes:
            kept.append(e)
    return kept


def write_post_file(
    run_dir: Path,
    idx: int,
    event: Event,
    angle: str,
    body: str,
) -> Path:
    posts_dir = run_dir / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    safe_id = _safe_filename(event.event_id.replace("/", "__"))
    fname = f"{idx:02d}__{event.source}__{safe_id}.md"
    path = posts_dir / fname

    frontmatter = (
        "---\n"
        f"source: {event.source}\n"
        f"event_id: {event.event_id}\n"
        f"url: {event.url}\n"
        f"author: {event.author}\n"
        f"likes: {event.likes}\n"
        f"created_at: {event.created_at}\n"
        f"angle: {angle.replace(chr(10), ' ').strip()!r}\n"
        f"generated_at: {datetime.now(timezone.utc).isoformat()}\n"
        "---\n\n"
    )
    path.write_text(frontmatter + body.strip() + "\n", encoding="utf-8")
    return path


def run_cycle(
    *,
    repo_root: Path,
    cfg: Config,
    operator: Operator,
    ledger: Ledger,
) -> Path:
    run_id = _utc_run_id()
    run_dir = repo_root / "runs" / run_id
    (run_dir / "prompts").mkdir(parents=True, exist_ok=True)

    logger.info("=== HFSonar cycle %s ===", run_id)

    # 1. Fetch
    sources = build_sources(cfg)
    events = fetch_all(sources)
    candidates = filter_candidates(events, ledger, min_likes=cfg.min_likes)
    logger.info(
        "candidates after dedup+min_likes: %d (out of %d total)",
        len(candidates),
        len(events),
    )

    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "config": asdict(cfg),
        "totals": {
            "fetched": len(events),
            "candidates": len(candidates),
            "ledger_size_before": len(ledger),
        },
        "events_by_source": {},
        "candidates": [c.to_dict() for c in candidates],
        "curator": {"raw": "", "chosen": []},
        "posts": [],
    }
    by_source: dict[str, int] = {}
    for e in events:
        by_source[e.source] = by_source.get(e.source, 0) + 1
    manifest["events_by_source"] = by_source

    if not candidates:
        logger.info("no fresh candidates — skipping curator and writer.")
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return run_dir

    # 2. Curate
    curate_template = (repo_root / "src/prompts/01_curate.md").read_text(encoding="utf-8")
    curate_prompt = _render(
        curate_template,
        {
            "CYCLE_TIMESTAMP": run_id,
            "NUM_CANDIDATES": str(len(candidates)),
            "TOP_K": str(cfg.top_k),
            "CANDIDATES_BLOCK": _candidate_block(candidates),
        },
    )
    curate_prompt_path = run_dir / "prompts" / "01_curate.prompt.md"
    curate_prompt_path.write_text(curate_prompt, encoding="utf-8")

    curate_result = operator.run(curate_prompt_path, label="curate")
    chosen_records = _parse_curator_output(curate_result.text)
    manifest["curator"]["raw"] = curate_result.text
    manifest["curator"]["chosen"] = chosen_records
    logger.info("curator picked %d items", len(chosen_records))

    # Map dedup_key -> Event for fast lookup
    by_key = {e.dedup_key: e for e in candidates}
    # 3. Write each chosen post
    write_template = (repo_root / "src/prompts/02_write_post.md").read_text(encoding="utf-8")
    posts_written: list[dict] = []
    for i, rec in enumerate(chosen_records[: cfg.top_k], start=1):
        key = rec.get("event_dedup_key", "")
        angle = rec.get("angle", "")
        evt = by_key.get(key)
        if not evt:
            logger.warning("curator referenced unknown key: %s", key)
            continue
        write_prompt = _render(
            write_template,
            {
                "SOURCE": evt.source,
                "TITLE": evt.title,
                "URL": evt.url,
                "AUTHOR": evt.author or "(unknown)",
                "LIKES": str(evt.likes),
                "CREATED_AT": evt.created_at or "(unknown)",
                "TAGS": ", ".join(evt.tags) if evt.tags else "(none)",
                "SUMMARY": evt.summary or "(no summary)",
                "ANGLE": angle or "(no angle provided)",
            },
        )
        prompt_path = run_dir / "prompts" / f"02_write_{i:02d}.prompt.md"
        prompt_path.write_text(write_prompt, encoding="utf-8")
        result: OperatorResult = operator.run(prompt_path, label=f"write/{i}")
        body = result.text or "(empty draft)"
        post_path = write_post_file(run_dir, i, evt, angle, body)
        ledger.record(key, source=evt.source, note=f"posted in {run_id}")
        posts_written.append(
            {
                "index": i,
                "event_dedup_key": key,
                "post_path": str(post_path.relative_to(repo_root)),
                "angle": angle,
            }
        )

    manifest["posts"] = posts_written
    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["totals"]["ledger_size_after"] = len(ledger)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("wrote %d posts to %s", len(posts_written), run_dir)
    return run_dir


def make_operator(*, fake: bool, cfg: Config) -> Operator:
    if fake:
        return FakeOperator()
    return ClaudeOperator(
        binary=cfg.claude_binary,
        timeout=cfg.claude_timeout,
        model=cfg.claude_model,
    )
