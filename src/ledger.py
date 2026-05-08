"""JSONL-backed dedup ledger.

One line per posted dedup_key. Append-only; we never rewrite history.
Loaded into a set on startup for O(1) membership checks.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = record.get("key")
                if isinstance(key, str):
                    self._seen.add(key)

    def has(self, key: str) -> bool:
        return key in self._seen

    def filter_unseen(self, keys: Iterable[str]) -> list[str]:
        return [k for k in keys if k not in self._seen]

    def record(self, key: str, *, source: str = "", note: str = "") -> None:
        if key in self._seen:
            return
        self._seen.add(key)
        record = {
            "key": key,
            "source": source,
            "note": note,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def __len__(self) -> int:
        return len(self._seen)
