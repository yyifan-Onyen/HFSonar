#!/usr/bin/env python3
"""HFSonar CLI.

Subcommands:
    poll              Run a single fetch → curate → write cycle.
    loop --interval   Run forever, sleeping between cycles.
    list              Show recent runs and their post counts.

Examples:
    python main.py poll --fake-llm
    python main.py poll
    python main.py loop --interval 3600
    python main.py list
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from src.ledger import Ledger
from src.orchestrator import Config, make_operator, run_cycle


REPO_ROOT = Path(__file__).resolve().parent
LEDGER_PATH = REPO_ROOT / "state" / "ledger.jsonl"
CONFIG_PATH = REPO_ROOT / "config.toml"


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_poll(args: argparse.Namespace) -> int:
    cfg = Config.load(CONFIG_PATH)
    operator = make_operator(fake=args.fake_llm, cfg=cfg)
    ledger = Ledger(LEDGER_PATH)
    run_dir = run_cycle(
        repo_root=REPO_ROOT, cfg=cfg, operator=operator, ledger=ledger
    )
    print(f"\nrun complete: {run_dir.relative_to(REPO_ROOT)}")
    outreach_dir = run_dir / "outreach"
    drafts = sorted(outreach_dir.glob("*.md")) if outreach_dir.exists() else []
    print(f"outreach drafts written: {len(drafts)}")
    for p in drafts:
        print(f"  - {p.relative_to(REPO_ROOT)}")
    return 0


_should_stop = False


def _handle_signal(signum, frame):
    global _should_stop
    _should_stop = True
    logging.getLogger().warning("received signal %s — finishing current cycle then stopping", signum)


def cmd_loop(args: argparse.Namespace) -> int:
    cfg = Config.load(CONFIG_PATH)
    operator = make_operator(fake=args.fake_llm, cfg=cfg)
    ledger = Ledger(LEDGER_PATH)
    interval = max(60, args.interval)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    cycle = 0
    while not _should_stop:
        cycle += 1
        logging.info("--- loop cycle #%d ---", cycle)
        try:
            run_cycle(repo_root=REPO_ROOT, cfg=cfg, operator=operator, ledger=ledger)
        except Exception as e:
            logging.exception("cycle failed: %s", e)
        if _should_stop:
            break
        # Sleep in 1-second chunks so SIGINT is responsive.
        for _ in range(interval):
            if _should_stop:
                break
            time.sleep(1)
    logging.info("loop exiting after %d cycle(s)", cycle)
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    runs_root = REPO_ROOT / "runs"
    if not runs_root.exists():
        print("no runs yet.")
        return 0
    rows = []
    for run_dir in sorted(runs_root.iterdir()):
        if not run_dir.is_dir():
            continue
        manifest = run_dir / "run_manifest.json"
        outreach_count = (
            len(list((run_dir / "outreach").glob("*.md")))
            if (run_dir / "outreach").exists()
            else 0
        )
        candidates = "?"
        if manifest.exists():
            try:
                m = json.loads(manifest.read_text(encoding="utf-8"))
                candidates = str(m.get("totals", {}).get("candidates", "?"))
            except Exception:
                pass
        rows.append((run_dir.name, candidates, outreach_count))
    if not rows:
        print("no runs yet.")
        return 0
    print(f"{'run_id':<22} {'candidates':>11} {'outreach':>9}")
    print("-" * 47)
    for name, cand, outreach in rows:
        print(f"{name:<22} {cand:>11} {outreach:>9}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hfsonar")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_poll = sub.add_parser("poll", help="run a single cycle")
    p_poll.add_argument(
        "--fake-llm",
        action="store_true",
        help="use deterministic stub instead of invoking the claude CLI",
    )
    p_poll.set_defaults(func=cmd_poll)

    p_loop = sub.add_parser("loop", help="run cycles forever")
    p_loop.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="seconds between cycles (min 60, default 3600)",
    )
    p_loop.add_argument("--fake-llm", action="store_true")
    p_loop.set_defaults(func=cmd_loop)

    p_list = sub.add_parser("list", help="list past runs")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
