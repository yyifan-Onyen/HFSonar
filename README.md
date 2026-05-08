# HFSonar

Real-time HuggingFace monitor with the Claude Code CLI as its writing/curation
backbone. Inspired by [AutoX-AI-Labs/AutoR](https://github.com/AutoX-AI-Labs/AutoR)'s
"Python orchestrator subprocess-invokes `claude`" pattern, adapted from a
one-shot research pipeline into a polling loop with persistent dedup.

Each cycle:

1. **Fetch** — pull from 4 HuggingFace sources in parallel:
   - Trending models (`huggingface_hub.list_models(sort="trendingScore")`)
   - Newly-created models (`sort="createdAt"`)
   - HF Daily Papers (`huggingface.co/api/daily_papers`)
   - Watchlist orgs (per-org newest releases for `meta-llama`, `mistralai`, `Qwen`,
     `deepseek-ai`, `google`, `microsoft`, `stabilityai`, `black-forest-labs`,
     `nvidia`, `anthropic`)
2. **Dedup** — drop anything already in `state/ledger.jsonl`, drop within-cycle
   duplicates, drop low-signal items (`min_likes` floor; watchlist + papers bypass it).
3. **Curate** — Claude (via `claude -p @prompt --output-format json`) is given the
   candidate list and asked to pick the top K worth posting, with a one-sentence
   "angle" for each.
4. **Write** — Claude drafts a markdown post for each chosen item using a
   per-platform style prompt + the project-local skills in `.claude/skills/guides/`.
5. **Save** — drafts land in `runs/<UTC-ts>/posts/*.md` with frontmatter; full
   record of the cycle in `runs/<UTC-ts>/run_manifest.json`. Ledger gets the new IDs.

No social platform is contacted. v1 is a pure local dry-run queue — you copy a
draft, decide if it's good, and post it yourself. Adding a real publisher
(Discord webhook → X API → etc.) is a single new module behind a `Publisher`
interface; not in v1.

## Install

Requires **Python 3.11+** (uses stdlib `tomllib`) and the [`claude` CLI](https://docs.claude.com/en/docs/claude-code) on PATH.

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Use

```bash
# Single cycle, real Claude
.venv/bin/python main.py poll

# Single cycle, deterministic stub (zero tokens — for dev/testing)
.venv/bin/python main.py poll --fake-llm

# Forever, hourly
.venv/bin/python main.py loop --interval 3600

# What's been run
.venv/bin/python main.py list
```

To run forever in the background, just `nohup` it or use `screen`/`tmux`:
```bash
nohup .venv/bin/python main.py loop --interval 3600 > hfsonar.log 2>&1 &
```

## Layout

```
HFSonar/
├── main.py                        # CLI: poll / loop / list
├── config.toml                    # tunables (limits, watchlist orgs, claude model)
├── requirements.txt
├── src/
│   ├── events.py                  # normalized Event dataclass + dedup_key
│   ├── ledger.py                  # append-only JSONL, set-backed in-memory
│   ├── operator.py                # ClaudeOperator (subprocess) + FakeOperator
│   ├── orchestrator.py            # the cycle: fetch → filter → curate → write → save
│   ├── prompts/
│   │   ├── 01_curate.md           # template w/ {{PLACEHOLDERS}}
│   │   └── 02_write_post.md
│   └── sources/
│       ├── base.py                # Source ABC, helpers
│       ├── _hf_common.py          # ModelInfo → Event normalizer
│       ├── trending_models.py
│       ├── new_models.py
│       ├── daily_papers.py
│       └── watchlist.py
├── .claude/skills/guides/         # auto-loaded by claude in this repo
│   ├── ai-news-tone.md
│   ├── post-formatting.md
│   └── hf-context.md
├── tests/                         # 11 pytest tests, all token-free
├── state/ledger.jsonl             # gitignored; persists across runs
└── runs/                          # gitignored; one dir per cycle
    └── 20YY...Z/
        ├── prompts/01_curate.prompt.md
        ├── prompts/02_write_NN.prompt.md
        ├── posts/NN__source__safe-id.md
        └── run_manifest.json
```

## Decisions locked in (challenge any of these)

- **Python 3.11+, no SDK.** Just `subprocess.run(["claude", "-p", "@file", "--output-format", "json"])`. Same pattern as AutoR.
- **Two Claude roles, one prompt template each.** Curator (JSON output) and Writer (markdown). Splitting them keeps each prompt small and lets us cap how many writer calls happen per cycle.
- **Run dir is the source of truth.** Every prompt sent to Claude is saved verbatim. Re-run the same prompt with `claude -p @runs/.../prompts/02_write_03.prompt.md` to debug a bad post.
- **JSONL ledger, not SQLite.** `git diff`-able, `tail -f`-able, dirt simple. v1 doesn't need indexes.
- **Local dry-run queue, no publisher.** Adding X/Discord/Telegram is a single `Publisher` module + a CLI flag. Out of scope until you actually want it.
- **`min_likes=5` floor + watchlist/papers bypass.** Keeps the curator from drowning in 30 spam re-uploads but never hides a release from a tracked org.
- **Polling cadence default 1h.** Daily Papers refreshes once a day; trending and new releases drift hourly. Tighter than 1h is wasteful.

## Tests

```bash
.venv/bin/pytest -q
```

Eleven tests covering the ledger, event round-tripping, curator-output parsing
(handles plain JSON, fenced JSON, and JSON embedded in prose), and a full
end-to-end cycle using the FakeOperator + a stub source set.

## How a real run looks

```
$ .venv/bin/python main.py poll --fake-llm
... source trending_models returned 20 events
... source new_models returned 30 events
... source daily_papers returned 15 events
... source watchlist returned 30 events
... candidates after dedup+min_likes: 67 (out of 95 total)
... curator picked 3 items
... wrote 3 posts to runs/.../

run complete: runs/20260508T222739_145839Z
posts written: 3
  - runs/.../posts/01__trending_models__SulphurAI__Sulphur-2-base.md
  - runs/.../posts/02__trending_models__deepseek-ai__DeepSeek-V4-Pro.md
  - runs/.../posts/03__trending_models__Zyphra__ZAYA1-8B.md
```

## What's intentionally NOT here (yet)

- **No publisher.** Drafts land on disk only.
- **No web UI / dashboard.** AutoR has a Studio; HFSonar's surface is just the
  filesystem and a `list` subcommand.
- **No image/video preview generation** for vision-model releases.
- **No multi-language post drafting.** English-only voice in the writer prompt;
  bilingual would be a second template + a curator hint.
- **No reviewer-agent / auto-publish gate.** AutoR has `--full-auto` with a
  reviewer agent; HFSonar would add this when we wire a real publisher.

Each is one module + one config flag away if/when you want it.
